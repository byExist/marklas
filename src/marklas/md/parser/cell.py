"""Cell-content parser.

Mistune tokenizes table cell contents as a single inline stream — no
`block_html`, even for the `<aside adf="panel">`, `<h3>`, `<ul>` shapes
the renderer produces inside a cell. To recover block structure we re-pair
inline_html tokens into paired/void groups and promote each one to the
block-level AST node it represents.

This module is the cell counterpart to `block`: `block` handles the
"standard" mistune block stream (block_html, paragraph, list, …) and
delegates here whenever a cell needs to be parsed. The two modules cite
each other through `from . import block as _b` (module reference) so the
call-time attribute access avoids any partial-init cycle.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from marklas import ast

from . import block as block
from .inline import parse_inlines
from .ir import (
    HEADING_LEVELS,
    HtmlVoid,
    Token,
    collect,
    is_blockquote,
    is_list_item,
    is_nested_expand,
    is_panel,
    is_table_cell,
)
from .normalize import (
    find_paired_close,
    get_params,
    inline_content_text,
    parse_block_marks,
    parse_tag,
)


# ── Public entry points ──────────────────────────────────────────────────────


def parse_cell_content(
    tokens: list[dict[str, Any]],
) -> list[ast.TableCellContent]:
    """Entry from `block._build_table_row`. Always returns at least one node."""
    if not tokens:
        return [ast.Paragraph(content=[])]
    tokens = _unescape_codespan_pipes(tokens)
    blocks = collect(_parse_cell_blocks(tokens), is_table_cell)
    if not blocks:
        return [ast.Paragraph(content=[])]
    return blocks


def _unescape_codespan_pipes(
    tokens: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Reverse the cell-pipe escape that the renderer applied inside codespans.

    GFM splits cells on raw `|` even inside an inline code span, so the
    renderer escapes `|` as `\\|` across the whole cell. mistune unescapes
    cell text normally, but leaves codespan `raw` untouched (CommonMark
    has no escape inside code), so `\\|` survives into the AST. Walk the
    token tree and reverse the escape only for codespan nodes.
    """
    out: list[dict[str, Any]] = []
    for t in tokens:
        if t.get("type") == "codespan":
            raw = t.get("raw", "")
            if "\\|" in raw:
                t = {**t, "raw": raw.replace("\\|", "|")}
        children = t.get("children")
        if isinstance(children, list):
            t = {
                **t,
                "children": _unescape_codespan_pipes(
                    cast(list[dict[str, Any]], children)
                ),
            }
        out.append(t)
    return out


def group_inline_html(
    tokens: list[dict[str, Any]],
) -> list[dict[str, Any] | list[dict[str, Any]]]:
    """Split a cell token stream into inline runs and paired/void HTML groups.

    Exposed because `block.build_task_list` / `build_decision_list` /
    `_split_nested_task_lists` walk a cell's inline structure to assemble
    their items.
    """
    groups: list[dict[str, Any] | list[dict[str, Any]]] = []
    inline_buffer: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal inline_buffer
        if inline_buffer:
            groups.append(inline_buffer)
            inline_buffer = []

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.get("type") != "inline_html":
            inline_buffer.append(token)
            i += 1
            continue

        raw = token.get("raw", "")
        tag, attrs, closing = parse_tag(raw)

        if closing:
            inline_buffer.append(token)
            i += 1
            continue

        # Void: self-closing or known void HTML
        if raw.rstrip().endswith("/>") or tag in {"hr", "br"}:
            flush()
            groups.append(
                {
                    "_void": True,
                    "tag": tag,
                    "attrs": attrs,
                    "_open_token": token,
                }
            )
            i += 1
            continue

        # Paired
        close_idx = find_paired_close(tokens, i + 1, tag, token_type="inline_html")
        if close_idx is not None:
            flush()
            groups.append(
                {
                    "_paired": True,
                    "tag": tag,
                    "attrs": attrs,
                    "inner": tokens[i + 1 : close_idx],
                    "_open_token": tokens[i],
                    "_close_token": tokens[close_idx],
                }
            )
            i = close_idx + 1
            continue

        # No matching close — fall through as inline.
        inline_buffer.append(token)
        i += 1

    flush()
    return groups


# ── Internal ─────────────────────────────────────────────────────────────────


def _parse_cell_blocks(tokens: Sequence[Token]) -> list[ast.Node]:
    """Re-pair inline_html groups and promote each to a block-level AST node.

    Any HtmlPaired/HtmlVoid in the list is ignored — mistune emits cells as
    pure inline streams, so we only see raw dicts here.
    """
    raw_tokens: list[dict[str, Any]] = [t for t in tokens if isinstance(t, dict)]
    result: list[ast.Node] = []
    inline_buffer: list[dict[str, Any]] = []

    def flush_inline() -> None:
        nonlocal inline_buffer
        if inline_buffer:
            inlines = parse_inlines(inline_buffer)
            if inlines:
                result.append(ast.Paragraph(content=inlines))
            inline_buffer = []

    for group in group_inline_html(raw_tokens):
        if isinstance(group, list):
            inline_buffer.extend(group)
            continue
        if group.get("_void"):
            block = _promote_void(group["tag"], group["attrs"])
            if block is not None:
                flush_inline()
                result.append(block)
            else:
                inline_buffer.append(group["_open_token"])
            continue
        # paired
        block = _promote_paired(group["tag"], group["attrs"], group["inner"])
        if block is not None:
            flush_inline()
            result.append(block)
        else:
            # Inline-level paired (mention/date/status/inline mark) — restore
            # the original token sequence so inline parsing can recognize it.
            inline_buffer.append(group["_open_token"])
            inline_buffer.extend(group["inner"])
            inline_buffer.append(group["_close_token"])
    flush_inline()
    return result


def _promote_void(tag: str, attrs: Mapping[str, str]) -> ast.TableCellContent | None:
    if tag == "hr":
        return ast.Rule()
    # Reuse the top-level void dispatch so cell-embedded extensions /
    # bodiedExtensions / syncBlocks round-trip the same way they do
    # outside a cell.
    node = block.build_html_void(HtmlVoid(tag=tag, attrs=attrs))
    if node is not None and is_table_cell(node):
        return node
    return None


def _promote_paired(
    tag: str, attrs: Mapping[str, str], inner: list[dict[str, Any]]
) -> ast.TableCellContent | None:
    """Promote a paired inline_html group to a block-level cell content node."""
    adf_type = attrs.get("adf", "")

    # Void-shaped extensions arrive paired because mistune splits empty
    # "<div ...></div>" into open/close tokens. Their content (if any) is
    # already encoded in attrs.params, so route them through the void
    # dispatch like at top level.
    if adf_type in {
        "extension",
        "bodiedExtension",
        "syncBlock",
        "bodiedSyncBlock",
        "unknownBlock",
    }:
        node = block.build_html_void(HtmlVoid(tag=tag, attrs=attrs))
        if node is not None and is_table_cell(node):
            return node
        return None

    # adf= convention paired blocks
    if adf_type == "mediaSingle":
        return block.build_media_single(attrs, [_wrap_inline_as_paragraph(inner)])
    if adf_type == "mediaGroup":
        return block.build_media_group(attrs, [_wrap_inline_as_paragraph(inner)])
    if adf_type == "panel":
        p = get_params(attrs)
        return ast.Panel(
            panel_type=p.get("panelType", "info"),
            content=collect(_parse_cell_blocks(inner), is_panel),
            panel_icon=p.get("panelIcon"),
            panel_icon_id=p.get("panelIconId"),
            panel_icon_text=p.get("panelIconText"),
            panel_color=p.get("panelColor"),
        )
    if adf_type == "nestedExpand":
        title, content_tokens = block.extract_summary(inner)
        p = get_params(attrs)
        return ast.NestedExpand(
            content=collect(_parse_cell_blocks(content_tokens), is_nested_expand),
            title=title or p.get("title"),
        )
    if adf_type == "decisionList":
        return block.build_decision_list(attrs, inner)
    if adf_type == "taskList":
        return block.build_task_list(attrs, inner)
    if adf_type in {"blockCard", "embedCard"}:
        return block.build_block_card(adf_type, attrs)

    # Raw HTML block-level mapping (no adf= attribute)
    if not adf_type:
        params = get_params(attrs)
        block_marks = parse_block_marks(params)
        if tag == "p":
            node = ast.Paragraph(content=parse_inlines(inner))
            if block_marks:
                node.marks = block_marks
            return node
        if (level := HEADING_LEVELS.get(tag)) is not None:
            heading = ast.Heading(level=level, content=parse_inlines(inner))
            if block_marks:
                heading.marks = block_marks
            return heading
        if tag in {"ul", "ol"}:
            start_str = attrs.get("start") if tag == "ol" else None
            start = int(start_str) if start_str and start_str.isdigit() else None
            return _parse_list(inner, ordered=(tag == "ol"), start=start)
        if tag == "code":
            # md table cells cannot contain literal newlines, so the renderer
            # encodes code-block newlines as <br> inside <code>. Reverse here
            # so codeBlock round-trips as multi-line text.
            text = block.BR_RE.sub("\n", inline_content_text(inner))
            code_content: list[ast.Text] = [ast.Text(text=text)] if text else []
            code = ast.CodeBlock(language=params.get("language"), content=code_content)
            breakout_marks = [m for m in block_marks if isinstance(m, ast.BreakoutMark)]
            if breakout_marks:
                code.marks = breakout_marks
            return code
        if tag == "blockquote":
            return ast.Blockquote(
                content=collect(_parse_cell_blocks(inner), is_blockquote)
            )

    return None


def _wrap_inline_as_paragraph(inner: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap inline tokens in a fake paragraph for builders that expect one."""
    return {"type": "paragraph", "children": inner}


def _parse_list(
    inner: list[dict[str, Any]], *, ordered: bool, start: int | None = None
) -> ast.BulletList | ast.OrderedList:
    items: list[ast.ListItem] = []
    for group in group_inline_html(inner):
        if isinstance(group, list):
            continue
        if group.get("_paired") and group["tag"] == "li":
            li_content = collect(_parse_cell_blocks(group["inner"]), is_list_item)
            if not li_content:
                li_content = [ast.Paragraph(content=[])]
            items.append(ast.ListItem(content=li_content))
    if ordered:
        order = start if start is not None else 1
        return ast.OrderedList(content=items, order=order if order != 1 else None)
    return ast.BulletList(content=items)


__all__ = ["parse_cell_content", "group_inline_html"]
