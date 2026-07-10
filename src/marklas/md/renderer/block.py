"""ADF AST → Markdown renderer."""

from __future__ import annotations

import enum
import json
import re
from collections.abc import Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Generator

from marklas import ast

from . import cell


# ── Rendering context ──────────────────────────────────────────────────────────


class _Ctx(enum.Enum):
    BLOCK = "block"
    CELL = "cell"


_ctx: ContextVar[_Ctx] = ContextVar("ctx", default=_Ctx.BLOCK)
_plain_ctx: ContextVar[bool] = ContextVar("plain", default=False)


@contextmanager
def _cell_context() -> Generator[None]:
    token = _ctx.set(_Ctx.CELL)
    try:
        yield
    finally:
        _ctx.reset(token)


def _in_cell() -> bool:
    return _ctx.get() is _Ctx.CELL


def _is_plain() -> bool:
    return _plain_ctx.get()


# ── Params helpers ─────────────────────────────────────────────────────────────


def _escape_params(json_str: str) -> str:
    """& → &amp;, ' → &#39;"""
    return json_str.replace("&", "&amp;").replace("'", "&#39;")


def build_params(fields: dict[str, Any]) -> str | None:
    """Build escaped params JSON. Returns None if all values are None."""
    d = {k: v for k, v in fields.items() if v is not None}
    if not d:
        return None
    return _escape_params(json.dumps(d, ensure_ascii=False, separators=(",", ":")))


# ── HTML helpers ───────────────────────────────────────────────────────────────


def _attr_str(
    adf: str | None = None,
    params: str | None = None,
    **attrs: Any,
) -> str:
    parts: list[str] = []
    if not _is_plain():
        if adf is not None:
            parts.append(f'adf="{adf}"')
        if params is not None:
            parts.append(f"params='{params}'")
    for k, v in attrs.items():
        if v is None:
            continue
        name = k.replace("_", "-")
        parts.append(f'{name}="{v}"')
    return (" " + " ".join(parts)) if parts else ""


_PLAIN_STRIP_TAGS = {"span", "time", "div", "section"}


def el(tag: str, content: str, **attrs: Any) -> str:
    """<tag attrs>content</tag>"""
    if _is_plain() and tag in _PLAIN_STRIP_TAGS:
        return content
    return f"<{tag}{_attr_str(**attrs)}>{content}</{tag}>"


def block_el(tag: str, content: str, **attrs: Any) -> str:
    """<tag attrs>\\n\\ncontent\\n\\n</tag> (block context only)"""
    if _is_plain() and tag in _PLAIN_STRIP_TAGS:
        return content
    if _in_cell():
        return el(tag, content, **attrs)
    return f"<{tag}{_attr_str(**attrs)}>\n\n{content}\n\n</{tag}>"


def _data(adf_type: str, params: str | None = None) -> str:
    """<div adf="type" params='...'></div> (void/metadata block element)"""
    if _is_plain():
        return ""
    return f"<div{_attr_str(adf=adf_type, params=params)}></div>"


# ── MD text helpers ────────────────────────────────────────────────────────────


_MD_ESCAPE = str.maketrans(
    {
        "\\": "\\\\",
        "*": "\\*",
        "_": "\\_",
        "[": "\\[",
        "]": "\\]",
        "`": "\\`",
        "~": "\\~",
        # `<` opens inline_html in mistune's eyes. Without escape, text like
        # ` <br> ` would be reabsorbed as a HardBreak; `<span>literal</span>`
        # would be stripped as adf-less inline html.
        "<": "\\<",
    }
)


def inline_safe(text: str | None) -> str:
    """Escape text for an *unprotected* inline MD position.

    "Unprotected" = the surrounding block is parsed by mistune's inline
    parser, so markdown rules apply to the content (plain ``ast.Text``
    in a Paragraph/Heading, inline-parsed HTML body, etc.).

    Two transformations:

    1. ``\\n`` → space — ADF has no soft-break concept; an embedded ``\\n``
       has no canonical visual mapping, so collapse to a space (CommonMark
       softbreak semantics) before it surfaces as a real newline that
       would split the surrounding block.
    2. MD specials → backslash-escaped — so ``*foo*`` in a user-typed
       display name doesn't reparse as emphasis.

    See :func:`_wrap_code` / :func:`_wrap_codespan` for the *protected*
    (codespan) counterpart, and :func:`html_body_safe` for the *raw
    block_html* counterpart.
    """
    return (text or "").replace("\n", " ").translate(_MD_ESCAPE)


def html_body_safe(text: str | None) -> str:
    """Collapse ``\\n`` for an inline position inside a raw block_html body.

    Counterpart to :func:`inline_safe` for positions where mistune captures
    the whole tag (including body) as one block_html token, so the body
    skips inline parsing entirely. MD escape would survive as literal
    backslashes on round-trip; the only transformation still necessary is
    collapsing ``\\n`` so the body stays a single line and the tag isn't
    split.
    """
    return (text or "").replace("\n", " ")


def _escape_pipe(text: str) -> str:
    return text.replace("|", "\\|")


_BACKTICK_RE = re.compile(r"`+")


def _code_fence(code: str) -> str:
    runs = _BACKTICK_RE.findall(code)
    max_run = max((len(r) for r in runs), default=0)
    return "`" * max(3, max_run + 1)


def _media_fallback(id: str | None, alt: str | None) -> str:
    label = inline_safe(alt or "attachment")
    return f"📎 {label} ({id})" if id else f"📎 {label}"


# ── Entry point ────────────────────────────────────────────────────────────────


def render(doc: ast.Doc, *, plain: bool = False) -> str:
    token = _plain_ctx.set(plain)
    try:
        parts = render_blocks(doc.content)
        return "\n\n".join(parts) + "\n" if parts else ""
    finally:
        _plain_ctx.reset(token)


# ── Block marks ────────────────────────────────────────────────────────────────


def _block_marks_data(marks: Sequence[ast.Mark]) -> str | None:
    """<data adf="marks" params='...'> for block context. None if no block marks."""
    if _is_plain():
        return None
    d = block_marks_params(marks)
    if not d:
        return None
    return _data("marks", build_params(d))


def block_marks_params(marks: Sequence[ast.Mark]) -> dict[str, Any]:
    """Block mark fields as dict for cell context params merging."""
    d: dict[str, Any] = {}
    for m in marks:
        match m:
            case ast.AlignmentMark(align=align):
                d["align"] = align
            case ast.IndentationMark(level=level):
                d["indent"] = level
            case ast.BreakoutMark(mode=mode, width=width):
                d["breakoutMode"] = mode
                if width is not None:
                    d["breakoutWidth"] = width
            case ast.DataConsumerMark(sources=sources):
                d["dataConsumerSources"] = sources
            case ast.BorderMark(size=size, color=color):
                d["borderSize"] = size
                d["borderColor"] = color
            case ast.FontSizeMark(size=fsize):
                d["fontSize"] = fsize
            case ast.UnknownMark(type=type_, attrs=attrs):
                entry = (
                    {"type": type_}
                    if attrs is None
                    else {"type": type_, "attrs": attrs}
                )
                d.setdefault("unknownMarks", []).append(entry)
            case _:
                pass
    return d


# ── Block rendering ────────────────────────────────────────────────────────────


def render_blocks(children: Sequence[ast.Node]) -> list[str]:
    parts: list[str] = []
    prev_marker: str | None = None
    for c in children:
        # CommonMark merges adjacent bullet lists that share a marker into a
        # single list — so two ADF bulletLists in a row round-trip as one.
        # Alternate between "-" and "*" to keep them separate.
        if isinstance(c, ast.BulletList) and not _in_cell():
            marker = "*" if prev_marker == "-" else "-"
            rendered = _render_bullet_list(c, marker=marker)
            prev_marker = marker
        else:
            rendered = render_block(c)
            prev_marker = None
        # Drop blocks that rendered to nothing (plain-mode empty paragraphs,
        # void metadata divs). Otherwise the outer "\n\n".join would emit
        # them as extra blank lines between real content.
        if rendered:
            parts.append(rendered)
    return parts


def render_block(node: ast.Node) -> str:
    match node:
        case ast.Paragraph():
            return _render_paragraph(node)
        case ast.Heading():
            return _render_heading(node)
        case ast.CodeBlock():
            return _render_code_block(node)
        case ast.Blockquote():
            return _render_blockquote(node)
        case ast.BulletList():
            return _render_bullet_list(node)
        case ast.OrderedList():
            return _render_ordered_list(node)
        case ast.Rule():
            return _render_rule()
        case ast.Table():
            return _render_table(node)
        case ast.Panel():
            return _render_panel(node)
        case ast.Expand():
            return _render_expand(node)
        case ast.NestedExpand():
            return _render_nested_expand(node)
        case ast.TaskList():
            return render_task_list(node)
        case ast.DecisionList():
            return _render_decision_list(node)
        case ast.MediaSingle():
            return _render_media_single(node)
        case ast.MediaGroup():
            return _render_media_group(node)
        case ast.BlockCard():
            return _render_block_card(node)
        case ast.EmbedCard():
            return _render_embed_card(node)
        case ast.LayoutSection():
            return _render_layout_section(node)
        case ast.Extension():
            return _render_extension(node)
        case ast.BodiedExtension():
            return _render_bodied_extension(node)
        case ast.SyncBlock():
            return _render_sync_block(node)
        case ast.BodiedSyncBlock():
            return _render_bodied_sync_block(node)
        case ast.UnknownBlock():
            return _render_unknown_block(node)
        case _:
            raise ValueError(f"Unknown block: {type(node).__name__}")


# ── Block renderers (each function handles block/cell context internally) ───


_ORDERED_LIST_MARKER_RE = re.compile(r"^( {0,3})(\d+)([.)])(\s)")
_BULLET_LIST_MARKER_RE = re.compile(r"^( {0,3})([-+*])(\s)")


def _render_paragraph(node: ast.Paragraph) -> str:
    return cell.render_paragraph(node) if _in_cell() else _render_paragraph_block(node)


def _render_paragraph_block(node: ast.Paragraph) -> str:
    # Drop leading and trailing HardBreaks: a `<br>` at the very start
    # or end of a paragraph adds nothing visually (the paragraph break
    # above/below already implies a line break) and produces awkward
    # `<br>text…` or `…text<br>` output. Symmetric with heading.
    inlines = list(node.content)
    while inlines and isinstance(inlines[0], ast.HardBreak):
        inlines.pop(0)
    while inlines and isinstance(inlines[-1], ast.HardBreak):
        inlines.pop()
    # Collapse a paragraph whose remaining content is all whitespace text
    # + hardBreaks: visually empty already, but " \\\n " round-trips as
    # paragraph(text="\\"). Treat it as empty so the empty-paragraph path runs.
    if all(
        (isinstance(x, ast.Text) and not x.text.strip()) or isinstance(x, ast.HardBreak)
        for x in inlines
    ):
        inlines = []
    content = render_inlines(inlines)
    marks_prefix = _block_marks_data(node.marks)
    # Empty paragraph → "<p></p>": survives the round-trip as paired
    # block_html. Plain mode drops the marker — it's a round-trip device.
    if not content.strip():
        if _is_plain():
            return marks_prefix or ""
        result = "<p></p>"
        if marks_prefix:
            return f"{marks_prefix}\n\n{result}"
        return result
    # Strip leading whitespace — CommonMark trims it on parse anyway, and
    # keeping it would make mistune absorb the paragraph as indented lazy-
    # continuation content of any preceding list.
    result = content.lstrip()
    # Escape a leading list marker so a paragraph that starts with one
    # ("4. Setup guide", "- item") isn't reinterpreted as a list.
    result = _ORDERED_LIST_MARKER_RE.sub(r"\1\2\\\3\4", result)
    result = _BULLET_LIST_MARKER_RE.sub(r"\1\\\2\3", result)
    if marks_prefix:
        return f"{marks_prefix}\n\n{result}"
    return result


def _render_heading(node: ast.Heading) -> str:
    return cell.render_heading(node) if _in_cell() else _render_heading_block(node)


def _render_heading_block(node: ast.Heading) -> str:
    # Drop edge hardBreaks: rendering "# \\\n..." makes mistune treat the
    # backslash as the heading body and shove the rest into the next block.
    inlines = list(node.content)
    while inlines and isinstance(inlines[0], ast.HardBreak):
        inlines.pop(0)
    while inlines and isinstance(inlines[-1], ast.HardBreak):
        inlines.pop()
    content = render_inlines(inlines)
    marks_prefix = _block_marks_data(node.marks)
    result = f"{'#' * node.level} {content}"
    if marks_prefix:
        return f"{marks_prefix}\n\n{result}"
    return result


def _render_code_block(node: ast.CodeBlock) -> str:
    return (
        cell.render_code_block(node) if _in_cell() else _render_code_block_block(node)
    )


def _render_code_block_block(node: ast.CodeBlock) -> str:
    code = "".join(t.text for t in node.content)
    marks_prefix = _block_marks_data(node.marks)
    fence = _code_fence(code)
    lang = node.language or ""
    result = f"{fence}{lang}\n{code}\n{fence}"
    if marks_prefix:
        return f"{marks_prefix}\n\n{result}"
    return result


def _render_blockquote(node: ast.Blockquote) -> str:
    return (
        cell.render_blockquote(node) if _in_cell() else _render_blockquote_block(node)
    )


def _render_blockquote_block(node: ast.Blockquote) -> str:
    inner = "\n\n".join(render_blocks(node.content))
    return "\n".join(f"> {line}" if line else ">" for line in inner.split("\n"))


def _render_bullet_list(node: ast.BulletList, marker: str = "-") -> str:
    if _in_cell():
        return cell.render_bullet_list(node)
    return _render_bullet_list_block(node, marker=marker)


def _is_list_loose(items: Sequence[ast.Node]) -> bool:
    """CommonMark list is loose if any item directly contains more than
    one block-level element. ADF list items always wrap inline content
    in a `paragraph`, so `len(content) > 1` means paragraph + nested
    block — necessarily loose. Single-paragraph items are tight.
    """
    return any(len(getattr(item, "content", [])) > 1 for item in items)


def _render_bullet_list_block(node: ast.BulletList, marker: str = "-") -> str:
    sep = "\n\n" if _is_list_loose(node.content) else "\n"
    return sep.join(_render_list_item(item, f"{marker} ") for item in node.content)


def _render_ordered_list(node: ast.OrderedList) -> str:
    return (
        cell.render_ordered_list(node)
        if _in_cell()
        else _render_ordered_list_block(node)
    )


def _render_ordered_list_block(node: ast.OrderedList) -> str:
    start = node.order if node.order is not None else 1
    sep = "\n\n" if _is_list_loose(node.content) else "\n"
    parts = [
        _render_list_item(item, f"{start + i}. ") for i, item in enumerate(node.content)
    ]
    return sep.join(parts)


def _render_list_item(node: ast.ListItem, marker: str) -> str:
    indent = " " * len(marker)
    parts = render_blocks(node.content)
    if not parts:
        return marker.rstrip()
    body = "\n\n".join(parts)
    lines = body.split("\n")
    result = marker + lines[0]
    if len(lines) > 1:
        result += "\n" + "\n".join(indent + line if line else "" for line in lines[1:])
    return result


def _render_rule() -> str:
    return "<hr>" if _in_cell() else "---"


def panel_params(node: ast.Panel) -> str | None:
    return build_params(
        {
            "panelType": node.panel_type,
            "panelIcon": node.panel_icon,
            "panelIconId": node.panel_icon_id,
            "panelIconText": node.panel_icon_text,
            "panelColor": node.panel_color,
        }
    )


def _render_panel(node: ast.Panel) -> str:
    return cell.render_panel(node) if _in_cell() else _render_panel_block(node)


def _render_panel_block(node: ast.Panel) -> str:
    content = "\n\n".join(render_blocks(node.content))
    return block_el("aside", content, adf="panel", params=panel_params(node))


def _render_expand(node: ast.Expand) -> str:
    return cell.render_expand(node) if _in_cell() else _render_expand_block(node)


def _render_expand_block(node: ast.Expand) -> str:
    marks_prefix = _block_marks_data(node.marks)
    summary = el("summary", html_body_safe(node.title)) if node.title else ""
    content = "\n\n".join(render_blocks(node.content))
    inner = f"{summary}\n\n{content}" if summary else content
    result = block_el("details", inner, adf="expand")
    if marks_prefix:
        return f"{marks_prefix}\n\n{result}"
    return result


def _render_nested_expand(node: ast.NestedExpand) -> str:
    if _in_cell():
        return cell.render_nested_expand(node)
    return _render_nested_expand_block(node)


def _render_nested_expand_block(node: ast.NestedExpand) -> str:
    summary = el("summary", html_body_safe(node.title)) if node.title else ""
    content = "\n\n".join(render_blocks(node.content))
    inner = f"{summary}\n\n{content}" if summary else content
    return block_el("details", inner, adf="nestedExpand")


def render_task_list(node: ast.TaskList) -> str:
    return cell.render_task_list(node) if _in_cell() else _render_task_list_block(node)


def _render_task_list_block(node: ast.TaskList) -> str:
    # Loose iff any BlockTaskItem has multi-block content; TaskItem is
    # inline-only (effectively single-block), and nested TaskList carries
    # its own loose decision.
    loose = any(
        isinstance(c, ast.BlockTaskItem) and len(c.content) > 1 for c in node.content
    )
    sep = "\n\n" if loose else "\n"
    parts: list[str] = []
    for child in node.content:
        match child:
            case ast.TaskItem():
                parts.append(_render_task_item(child))
            case ast.BlockTaskItem():
                parts.append(_render_block_task_item(child))
            case ast.TaskList():
                nested = render_task_list(child)
                parts.append("\n".join("  " + line for line in nested.split("\n")))
            case _:
                pass
    return sep.join(parts)


def _render_task_item(node: ast.TaskItem) -> str:
    checkbox = "[x]" if node.state == "DONE" else "[ ]"
    content = render_inlines(node.content)
    return f"- {checkbox} {content}"


def _render_block_task_item(node: ast.BlockTaskItem) -> str:
    checkbox = "[x]" if node.state == "DONE" else "[ ]"
    marker = f"- {checkbox} "
    indent = " " * len(marker)
    parts = render_blocks(node.content)
    if not parts:
        return marker.rstrip()
    body = "\n\n".join(parts)
    lines = body.split("\n")
    result = marker + lines[0]
    if len(lines) > 1:
        result += "\n" + "\n".join(indent + line if line else "" for line in lines[1:])
    return result


def _render_decision_list(node: ast.DecisionList) -> str:
    items = "".join(_render_decision_item(item) for item in node.content)
    return block_el("ul", items, adf="decisionList")


def _render_decision_item(node: ast.DecisionItem) -> str:
    content = render_inlines(node.content)
    params = build_params({"state": node.state})
    return el("li", content, adf="decisionItem", params=params)


def _render_media_single(node: ast.MediaSingle) -> str:
    params_dict: dict[str, Any] = {
        "layout": node.layout,
        "width": node.width,
        "widthType": node.width_type,
    }
    # MediaSingle.marks (LinkMark) → params
    for m in node.marks:
        params_dict["linkHref"] = m.href
        if m.title:
            params_dict["linkTitle"] = m.title
    params = build_params(params_dict)
    parts: list[str] = []
    for child in node.content:
        match child:
            case ast.Media():
                parts.append(_render_media(child))
            case ast.Caption():
                parts.append(_render_caption(child))
            case _:
                pass
    content = "".join(parts)
    return block_el("figure", content, adf="mediaSingle", params=params)


def _render_media_group(node: ast.MediaGroup) -> str:
    content = "".join(_render_media(m) for m in node.content)
    return block_el("div", content, adf="mediaGroup")


def _render_media(node: ast.Media) -> str:
    display = _media_fallback(node.id, node.alt)
    params_dict: dict[str, Any] = {
        "type": node.type,
        "id": node.id,
        "collection": node.collection,
        "alt": node.alt,
        "width": node.width,
        "height": node.height,
        "url": node.url,
    }
    for m in node.marks:
        if isinstance(m, ast.BorderMark):
            params_dict["borderSize"] = m.size
            params_dict["borderColor"] = m.color
    params = build_params(params_dict)
    result = el("span", display, adf="media", params=params)
    return _wrap_media_marks(result, node.marks)


def _wrap_media_marks(content: str, marks: Sequence[ast.Mark]) -> str:
    """Wrap `content` in a media node's link/annotation marks (shared by block
    and inline media). BorderMark is params, handled by the caller.
    """
    for m in marks:
        if isinstance(m, (ast.LinkMark, ast.AnnotationMark)):
            content = _wrap_html_mark(content, m)
    return content


def _render_caption(node: ast.Caption) -> str:
    content = render_inlines(node.content)
    return el("figcaption", content, adf="caption")


def _render_block_card(node: ast.BlockCard) -> str:
    params_dict: dict[str, Any] = {
        "url": node.url,
        "layout": node.layout,
        "width": node.width,
        "data": node.data,
        "datasource": node.datasource,
    }
    params = build_params(params_dict)
    display = node.url or ""
    return block_el("div", display, adf="blockCard", params=params)


def _render_embed_card(node: ast.EmbedCard) -> str:
    params = build_params(
        {
            "url": node.url,
            "layout": node.layout,
            "width": node.width,
            "originalHeight": node.original_height,
            "originalWidth": node.original_width,
        }
    )
    return block_el("div", node.url, adf="embedCard", params=params)


def _render_layout_section(node: ast.LayoutSection) -> str:
    columns = "\n\n".join(_render_layout_column(col) for col in node.content)
    result = block_el("section", columns, adf="layoutSection")
    # The marks prefix is a block-context-only sentinel (`<data adf="marks">`
    # on its own line); inside cells it would break the single-line cell.
    if _in_cell():
        return result
    marks_prefix = _block_marks_data(node.marks)
    if marks_prefix:
        return f"{marks_prefix}\n\n{result}"
    return result


def _render_layout_column(node: ast.LayoutColumn) -> str:
    params = build_params({"width": node.width})
    content = "\n\n".join(render_blocks(node.content))
    return block_el("div", content, adf="layoutColumn", params=params)


def _render_extension(node: ast.Extension) -> str:
    params = build_params(
        {
            "extensionKey": node.extension_key,
            "extensionType": node.extension_type,
            "parameters": node.parameters,
            "text": node.text,
            "layout": node.layout,
        }
    )
    visual = _nested_table_visual(node) if node.extension_key == "nested-table" else ""
    if visual:
        # Paired form so the inner table is visible to plain Markdown
        # renderers. Round-trip safety still rides on `params` (which
        # carries the full `parameters.adf`), so the inner is parser-ignored.
        result = el("div", visual, adf="extension", params=params)
    else:
        result = _data("extension", params)
    if _in_cell():
        return result
    marks_prefix = _block_marks_data(node.marks)
    if marks_prefix:
        return f"{marks_prefix}\n\n{result}"
    return result


def _nested_table_visual(node: ast.Extension) -> str:
    """Render the inner ADF doc embedded in ``parameters.adf`` for visibility.

    Confluence wraps cell-nested tables in a ``nested-table`` extension
    whose ``parameters.adf`` field carries the original doc as a JSON
    string (since ADF forbids ``table`` inside a ``tableCell``). We
    decode it and emit the inner table as inline HTML — GFM table
    syntax would explode the outer cell on the first `|`. The ``params``
    JSON on the outer element still carries the original ADF verbatim,
    so the inner is purely cosmetic from the parser's perspective.
    """
    from marklas.adf.parser import parse as parse_adf_doc

    inner_json = (node.parameters or {}).get("adf")
    if not isinstance(inner_json, str) or not inner_json:
        return ""
    try:
        inner_doc_raw = json.loads(inner_json)
    except json.JSONDecodeError:
        return ""
    try:
        inner_doc = parse_adf_doc(inner_doc_raw)
    except Exception:
        return ""
    parts: list[str] = []
    for child in inner_doc.content:
        if isinstance(child, ast.Table):
            parts.append(_render_table_html(child))
    return "".join(parts)


def _render_table_html(table: ast.Table) -> str:
    """Emit a Table as inline HTML so it can live inside a single cell."""
    row_parts: list[str] = []
    for row in table.content:
        cell_parts: list[str] = []
        for tc in row.content:
            tag = "th" if isinstance(tc, ast.TableHeader) else "td"
            extra: dict[str, Any] = {}
            if tc.colspan and tc.colspan != 1:
                extra["colspan"] = tc.colspan
            if tc.rowspan and tc.rowspan != 1:
                extra["rowspan"] = tc.rowspan
            with _cell_context():
                inner = _render_cell_content(tc.content)
            attr = _attr_str(**extra)
            cell_parts.append(f"<{tag}{attr}>{inner}</{tag}>")
        row_parts.append(f"<tr>{''.join(cell_parts)}</tr>")
    return f"<table>{''.join(row_parts)}</table>"


def _render_bodied_extension(node: ast.BodiedExtension) -> str:
    content_dicts = [_node_to_dict(c) for c in node.content]
    params = build_params(
        {
            "extensionKey": node.extension_key,
            "extensionType": node.extension_type,
            "parameters": node.parameters,
            "text": node.text,
            "layout": node.layout,
            "content": content_dicts,
        }
    )
    result = _data("bodiedExtension", params)
    if _in_cell():
        return result
    marks_prefix = _block_marks_data(node.marks)
    if marks_prefix:
        return f"{marks_prefix}\n\n{result}"
    return result


def _render_sync_block(node: ast.SyncBlock) -> str:
    params = build_params({"resourceId": node.resource_id})
    result = _data("syncBlock", params)
    if _in_cell():
        return result
    marks_prefix = _block_marks_data(node.marks)
    if marks_prefix:
        return f"{marks_prefix}\n\n{result}"
    return result


def _render_bodied_sync_block(node: ast.BodiedSyncBlock) -> str:
    content_dicts = [_node_to_dict(c) for c in node.content]
    params = build_params(
        {
            "resourceId": node.resource_id,
            "content": content_dicts,
        }
    )
    result = _data("bodiedSyncBlock", params)
    if _in_cell():
        return result
    marks_prefix = _block_marks_data(node.marks)
    if marks_prefix:
        return f"{marks_prefix}\n\n{result}"
    return result


def _render_unknown_block(node: ast.UnknownBlock) -> str:
    return _data("unknownBlock", build_params(node.raw))


# ── Table ──────────────────────────────────────────────────────────────────────


def _render_table(node: ast.Table) -> str:
    rows = node.content
    if not rows:
        return ""

    mode = _header_mode(node)

    with _cell_context():
        grid = _build_grid(rows, mode)

    if not grid or not grid[0]:
        return ""

    col_count = len(grid[0])
    gfm_lines: list[str] = []

    if mode in ("row", "both"):
        # First row = header content
        gfm_lines.append("| " + " | ".join(grid[0]) + " |")
        gfm_lines.append("| " + " | ".join(["---"] * col_count) + " |")
        for row in grid[1:]:
            gfm_lines.append("| " + " | ".join(row) + " |")
    else:
        # "none" / "column" — filler header row
        gfm_lines.append("| " + " | ".join([""] * col_count) + " |")
        gfm_lines.append("| " + " | ".join(["---"] * col_count) + " |")
        for row in grid:
            gfm_lines.append("| " + " | ".join(row) + " |")

    table_md = "\n".join(gfm_lines)

    meta = _table_meta(node, mode)
    if meta:
        return f"{meta}\n\n{table_md}"
    return table_md


def _expected_header(mode: str, r: int, c: int) -> bool:
    """Whether the cell at (r, c) is implicitly a TableHeader given table mode.

    mode is one of "row" / "column" / "both" / "none" (see `_header_mode`).
    """
    if mode == "row":
        return r == 0
    if mode == "column":
        return c == 0
    if mode == "both":
        return r == 0 or c == 0
    return False


def _build_grid(rows: Sequence[ast.TableRow], mode: str) -> list[list[str]]:
    """Build 2D cell grid, expanding colspan/rowspan into filler cells."""
    num_rows = len(rows)
    if num_rows == 0:
        return []

    max_cols = max(sum(c.colspan or 1 for c in row.content) for row in rows)
    grid: list[list[str | None]] = [[None] * max_cols for _ in range(num_rows)]

    for r, row in enumerate(rows):
        c = 0
        for tc in row.content:
            while c < max_cols and grid[r][c] is not None:
                c += 1
            if c >= max_cols:
                break
            cs = tc.colspan or 1
            rs = tc.rowspan or 1
            grid[r][c] = _render_cell(tc, expected_header=_expected_header(mode, r, c))
            for dr in range(rs):
                for dc in range(cs):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if rr < num_rows and cc < max_cols:
                        grid[rr][cc] = ""
            c += cs

    return [[v if v is not None else "" for v in row] for row in grid]


def _table_meta(node: ast.Table, mode: str) -> str | None:
    """<data adf="table" params='...'> if non-default attrs exist."""
    d: dict[str, Any] = {}
    if mode != "row":
        d["header"] = mode
    if node.layout is not None:
        d["layout"] = node.layout
    if node.display_mode is not None:
        d["displayMode"] = node.display_mode
    if node.is_number_column_enabled is not None:
        d["isNumberColumnEnabled"] = node.is_number_column_enabled
    if node.width is not None:
        d["width"] = node.width
    if node.colwidths:
        d["colwidths"] = node.colwidths
    if not d:
        return None
    return _data("table", build_params(d))


def _header_mode(node: ast.Table) -> str:
    """Determine: "row" | "none" | "column" | "both"."""
    if not node.content:
        return "row"

    first_row = node.content[0]
    first_row_header = all(isinstance(c, ast.TableHeader) for c in first_row.content)

    body = node.content[1:] if first_row_header else node.content
    first_col_header = bool(body) and all(
        len(row.content) > 0 and isinstance(row.content[0], ast.TableHeader)
        for row in body
    )

    if first_row_header and first_col_header:
        return "both"
    if first_row_header:
        return "row"
    if first_col_header:
        return "column"
    return "none"


def _cell_meta(cell: ast.TableCell, header_override: bool | None = None) -> str:
    """<data adf="cell" params='...'> prefix if colspan/rowspan/background.

    `header_override`, when set, records that this cell's type (TableHeader
    vs TableCell) deviates from what the table's header mode would imply
    — so the parser can restore the deviation on round-trip.
    """
    d: dict[str, Any] = {}
    if cell.colspan and cell.colspan > 1:
        d["colspan"] = cell.colspan
    if cell.rowspan and cell.rowspan > 1:
        d["rowspan"] = cell.rowspan
    if cell.background:
        d["background"] = cell.background
    if header_override is not None:
        d["header"] = header_override
    if not d:
        return ""
    return _data("cell", build_params(d))


def _render_cell(cell: ast.TableCell, *, expected_header: bool = False) -> str:
    actual_header = isinstance(cell, ast.TableHeader)
    override = actual_header if actual_header != expected_header else None
    meta = _cell_meta(cell, header_override=override)
    content = _render_cell_content(cell.content)
    return _escape_pipe(meta + content)


def _render_cell_content(children: Sequence[ast.Node]) -> str:
    """Single Paragraph → bare text, else HTML tags per block."""
    if not children:
        return ""
    if len(children) == 1 and isinstance(children[0], ast.Paragraph):
        p = children[0]
        if not block_marks_params(p.marks):
            return render_inlines(p.content)
    return "".join(render_block(c) for c in children)


# ── Inline rendering ──────────────────────────────────────────────────────────


def render_inlines(children: Sequence[ast.Inline]) -> str:
    return "".join(_render_inline(c) for c in children)


def _render_inline(node: ast.Inline) -> str:
    match node:
        case ast.Text():
            return _render_text(node)
        case ast.HardBreak():
            return _render_hard_break()
        case ast.Mention():
            return _render_mention(node)
        case ast.Emoji():
            return _render_emoji(node)
        case ast.Date():
            return _render_date(node)
        case ast.Status():
            return _render_status(node)
        case ast.InlineCard():
            return _render_inline_card(node)
        case ast.Placeholder():
            return _render_placeholder(node)
        case ast.MediaInline():
            return _render_media_inline(node)
        case ast.InlineExtension():
            return _render_inline_extension(node)
        case ast.UnknownInline():
            return _render_unknown_inline(node)
        case _:
            raise ValueError(f"Unknown inline: {type(node).__name__}")


# ── Inline renderers ──────────────────────────────────────────────────────────


def _render_text(node: ast.Text) -> str:
    # All inline-safety (\n→space, MD escape) is folded into `inline_safe`
    # via `_apply_marks` → `_wrap_code`/`inline_safe`.
    return _apply_marks(node.text, node.marks)


def _render_hard_break() -> str:
    # `<br>` (not CommonMark's `\\\n`) in every context: the real newline
    # in `\\\n` lets mistune's block parser re-classify the next line
    # (e.g. `- `, `# `, `1.`, `---`) as starting a new block, splitting
    # one paragraph into many. `<br>` is inline_html — no real newline,
    # so block dispatch can't re-trigger. Parser already maps inline
    # `<br>` back to HardBreak via `normalize_inlines`.
    return "<br>"


def _render_mention(node: ast.Mention) -> str:
    display = inline_safe(node.text or f"@{node.id}")
    params = build_params(
        {
            "id": node.id,
            "accessLevel": node.access_level,
            "userType": node.user_type,
        }
    )
    return el("span", display, adf="mention", params=params)


def _render_emoji(node: ast.Emoji) -> str:
    display = inline_safe(node.text or node.short_name)
    params = build_params(
        {
            "shortName": node.short_name,
            "id": node.id,
        }
    )
    return el("span", display, adf="emoji", params=params)


def _render_date(node: ast.Date) -> str:
    ts = int(node.timestamp) / 1000
    dt = datetime.fromtimestamp(ts, tz=UTC)
    display = dt.strftime("%Y-%m-%d")
    return el("time", display, adf="date", datetime=node.timestamp)


def _render_status(node: ast.Status) -> str:
    params = build_params(
        {
            "color": node.color,
            "style": node.style,
        }
    )
    # Codespan-wrap the text so plain-Markdown viewers render it as a
    # distinct chip; the parser unwraps the codespan transparently.
    # Status text goes inside a codespan, which is protected from MD
    # interpretation — pass raw text; `_wrap_codespan` handles \n→space.
    return el("span", _wrap_codespan(node.text), adf="status", params=params)


def _wrap_codespan(text: str) -> str:
    """Wrap `text` in an inline-code span, padding the fence if needed.

    Counterpart to :func:`inline_safe` for the *protected* inline category:
    inside a codespan, MD specials render as literal characters, so the
    only safety transformation needed is collapsing ``\\n`` to space.
    """
    if not text:
        return ""
    text = text.replace("\n", " ")
    runs = _BACKTICK_RE.findall(text)
    fence = "`" * (max((len(r) for r in runs), default=0) + 1)
    # CommonMark trims one leading/trailing space inside a codespan when
    # both ends are spaces, and a span starting/ending with a backtick
    # needs the pad to disambiguate from the fence.
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def _render_inline_card(node: ast.InlineCard) -> str:
    params = build_params({"data": node.data}) if node.data else None
    display = node.url or ""
    return el("a", display, adf="inlineCard", href=node.url, params=params)


def _render_placeholder(node: ast.Placeholder) -> str:
    return el("span", inline_safe(node.text), adf="placeholder")


def _render_media_inline(node: ast.MediaInline) -> str:
    display = _media_fallback(node.id, node.alt)
    params_dict: dict[str, Any] = {
        "id": node.id,
        "collection": node.collection,
        "type": node.type,
        "alt": node.alt,
        "width": node.width,
        "height": node.height,
    }
    if node.data:
        params_dict["data"] = node.data
    for m in node.marks:
        if isinstance(m, ast.BorderMark):
            params_dict["borderSize"] = m.size
            params_dict["borderColor"] = m.color
    params = build_params(params_dict)
    result = el("span", display, adf="mediaInline", params=params)
    return _wrap_media_marks(result, node.marks)


def _render_inline_extension(node: ast.InlineExtension) -> str:
    params = build_params(
        {
            "extensionKey": node.extension_key,
            "extensionType": node.extension_type,
            "parameters": node.parameters,
            "text": node.text,
        }
    )
    return el("span", "", adf="inlineExtension", params=params)


def _render_unknown_inline(node: ast.UnknownInline) -> str:
    return el("span", "", adf="unknownInline", params=build_params(node.raw))


# ── Mark rendering ─────────────────────────────────────────────────────────────


def _wrap_code(text: str) -> str:
    """Wrap text in code span backticks, handling embedded backticks.

    Counterpart to :func:`inline_safe` for the *protected* inline category:
    a codespan keeps its content as raw text (no MD escape interpretation),
    so the only transformation needed is collapsing ``\\n`` to space so the
    span doesn't sprout a real newline that breaks the surrounding block.
    """
    text = text.replace("\n", " ")
    if "`" not in text:
        return f"`{text}`"
    runs = _BACKTICK_RE.findall(text)
    max_run = max(len(r) for r in runs)
    fence = "`" * (max_run + 1)
    if text.startswith("`") or text.endswith("`"):
        return f"{fence} {text} {fence}"
    return f"{fence}{text}{fence}"


def _wrap_flanking(text: str, delimiter: str) -> str:
    """Move leading/trailing whitespace outside delimiter for CommonMark flanking.

    CommonMark's flanking rule rejects any Unicode whitespace adjacent to
    the delimiter (not just ASCII space). NBSP (U+00A0) inside ADF text
    must be pushed outside too, or `**foo\\u00a0**` re-parses as plain
    text on the next round-trip.
    """
    inner = text.strip()
    if not inner:
        return text
    leading_end = text.find(inner)
    trailing_start = leading_end + len(inner)
    return f"{text[:leading_end]}{delimiter}{inner}{delimiter}{text[trailing_start:]}"


def _wrap_html_mark(text: str, mark: ast.Mark) -> str:
    match mark:
        case ast.UnderlineMark():
            return el("u", text, adf="underline")
        case ast.TextColorMark(color=color):
            return el(
                "span", text, adf="textColor", params=build_params({"color": color})
            )
        case ast.BackgroundColorMark(color=color):
            return el(
                "span", text, adf="bgColor", params=build_params({"color": color})
            )
        case ast.SubSupMark(type=type_):
            tag = "sub" if type_ == "sub" else "sup"
            return el(tag, text, adf="subSup")
        case ast.AnnotationMark(id=id_):
            return el(
                "span",
                text,
                adf="annotation",
                params=build_params({"id": id_}),
            )
        case ast.UnknownMark(type=type_, attrs=attrs):
            return el(
                "span",
                text,
                adf="unknownMark",
                params=build_params({"type": type_, "attrs": attrs}),
            )
        case ast.LinkMark(href=href, title=title):
            # Only reached for media (text LinkMarks render as markdown
            # `[](url)` in `_apply_marks`). `adf=link` keeps parse from
            # stripping it as adf-less HTML.
            return el("a", text, adf="link", href=href, title=title)
        case _:
            return text


def _apply_marks(text: str, marks: Sequence[ast.Mark]) -> str:
    if not marks:
        return inline_safe(text)

    code: ast.CodeMark | None = None
    native: list[ast.Mark] = []
    link: ast.LinkMark | None = None
    html: list[ast.Mark] = []

    for m in marks:
        match m:
            case ast.CodeMark():
                code = m
            case ast.StrongMark() | ast.EmMark() | ast.StrikeMark():
                native.append(m)
            case ast.LinkMark():
                link = m
            case _:
                html.append(m)

    # innermost: code (no MD escape) or escaped text
    result = _wrap_code(text) if code else inline_safe(text)

    # native MD marks
    for m in native:
        match m:
            case ast.StrongMark():
                result = _wrap_flanking(result, "**")
            case ast.EmMark():
                result = _wrap_flanking(result, "*")
            case ast.StrikeMark():
                result = _wrap_flanking(result, "~~")
            case _:  # pragma: no cover
                pass

    # link — wrap href in angle brackets so URL-encoded characters and
    # parens inside the URL don't terminate the link destination early
    # (CommonMark: "<...>" allows any non-< non-> non-newline content).
    if link:
        title = f' "{link.title}"' if link.title else ""
        result = f"[{result}](<{link.href}>{title})"

    # HTML marks (outermost)
    for m in html:
        result = _wrap_html_mark(result, m)

    return result


# ── AST → dict ─────────────────────────────────────────────────────────────────


def _node_to_dict(node: ast.Node) -> dict[str, Any]:
    """AST node → ADF-compatible dict (BodiedExtension/BodiedSyncBlock content).

    Delegates to the canonical ADF renderer so per-node fields end up under
    the ADF-required `attrs` envelope.
    """
    from marklas.adf import renderer as _adf_renderer  # lazy: avoid import cycle

    result = _adf_renderer.render_block(node)
    if result is None:
        raise ValueError(f"cannot render {type(node).__name__} to ADF dict")
    return result
