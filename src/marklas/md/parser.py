"""Markdown → Union AST parsing. Auto-restores difference-set nodes from `<!-- adf:... -->` comments."""

from __future__ import annotations

import json
import re
import textwrap
from typing import Any, Literal, cast

import mistune

from marklas.nodes import blocks, inlines


def parse(markdown: str) -> blocks.Document:
    tokens = cast(list[dict[str, Any]], _tokenize(markdown))
    children = _parse_blocks(tokens)
    return blocks.Document(children=children)


_tokenize = mistune.create_markdown(
    renderer="ast",
    plugins=["table", "strikethrough", "task_lists"],
)
_inline_parser = _tokenize.inline


# ---------------------------------------------------------------------------
# Pass 1: Annotation matching
# ---------------------------------------------------------------------------

_ADF_COMMENT_RE = re.compile(r"<!--\s*(/?)adf:(\w+)\s*(.*?)-->", re.DOTALL)


def _parse_adf_comment(raw: str) -> tuple[bool, str, dict[str, Any]] | None:
    """Return (closing, tag, attrs) if ADF comment, else None."""
    m = _ADF_COMMENT_RE.fullmatch(raw.strip())
    if not m:
        return None
    closing, tag, attr_str = m.groups()
    try:
        attrs: dict[str, Any] = json.loads(attr_str) if attr_str.strip() else {}
    except json.JSONDecodeError:
        return None
    return bool(closing), tag, attrs


_ADF_COMMENT_SPLIT_RE = re.compile(r"(<!--\s*/?adf:\w+\s*.*?-->)")


def _match_block_annotations(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Match block-level `<!-- adf:tag -->...<!-- /adf:tag -->` pairs into single tokens.

    Converts flat token list into a tree where annotation pairs become
    `{"type": tag, "attrs": {...}, "children": [...], "_annotated": True}` tokens.

    Also handles single-line block_html where mistune merges open+content+close
    into one token (e.g. `<!-- adf:mention {...} -->...<!-- /adf:mention -->`).
    These are split, re-tokenized, and annotation-matched inline.
    """
    stack: list[tuple[str, dict[str, Any], list[dict[str, Any]]]] = []
    result: list[dict[str, Any]] = []

    for token in tokens:
        target = stack[-1][2] if stack else result

        if token["type"] == "block_html":
            raw = token["raw"]
            parsed = _parse_adf_comment(raw)
            if parsed:
                closing, tag, attrs = parsed
                if not closing:
                    stack.append((tag, attrs, []))
                else:
                    if stack and stack[-1][0] == tag:
                        stag, sattrs, inner = stack.pop()
                        merged: dict[str, Any] = {
                            "type": stag,
                            "attrs": sattrs,
                            "children": inner,
                            "_annotated": True,
                        }
                        (stack[-1][2] if stack else result).append(merged)
                continue
            inline_children = _split_block_html(raw)
            if inline_children is not None:
                target.append({"type": "paragraph", "children": inline_children})
                continue

        target.append(token)

    while stack:
        _, _, inner = stack.pop()
        (stack[-1][2] if stack else result).extend(inner)

    return result


def _split_block_html(raw: str) -> list[dict[str, Any]] | None:
    """Split a block_html containing inline annotations into matched inline tokens.

    Returns None if the raw HTML doesn't contain ADF annotations.
    """
    stripped = raw.strip()
    if "<!-- adf:" not in stripped:
        return None

    parts = _ADF_COMMENT_SPLIT_RE.split(stripped)
    synthetic_tokens: list[dict[str, Any]] = []
    for part in parts:
        if not part:
            continue
        parsed = _parse_adf_comment(part)
        if parsed:
            synthetic_tokens.append({"type": "inline_html", "raw": part})
        else:
            state = _inline_parser.state_cls(env={})
            state.src = part
            synthetic_tokens.extend(_inline_parser.parse(state))

    if not synthetic_tokens:
        return None

    return _match_inline_annotations(synthetic_tokens)


def _match_inline_annotations(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Match inline-level `<!-- adf:tag -->...<!-- /adf:tag -->` pairs into single tokens."""
    stack: list[tuple[str, dict[str, Any], list[dict[str, Any]]]] = []
    result: list[dict[str, Any]] = []

    for token in tokens:
        target = stack[-1][2] if stack else result

        if token["type"] == "inline_html":
            parsed = _parse_adf_comment(token["raw"])
            if parsed:
                closing, tag, attrs = parsed
                if not closing:
                    stack.append((tag, attrs, []))
                else:
                    if stack and stack[-1][0] == tag:
                        stag, sattrs, inner = stack.pop()
                        merged: dict[str, Any] = {
                            "type": stag,
                            "attrs": sattrs,
                            "children": inner,
                            "_annotated": True,
                        }
                        (stack[-1][2] if stack else result).append(merged)
                continue
            continue

        target.append(token)

    while stack:
        _, _, inner = stack.pop()
        (stack[-1][2] if stack else result).extend(inner)

    return result


def _match_cell_annotations(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Match cell-level `<!-- adf:tag -->...<!-- /adf:tag -->` pairs into single tokens.

    Cell tokens are inline tokens from mistune. Annotation pairs may wrap
    HTML block representations (e.g. `<code>...</code>`, `<ul>...</ul>`).
    """
    stack: list[tuple[str, dict[str, Any], list[dict[str, Any]]]] = []
    result: list[dict[str, Any]] = []

    for tok in tokens:
        target = stack[-1][2] if stack else result

        if tok.get("type") == "inline_html":
            parsed = _parse_adf_comment(tok["raw"])
            if parsed:
                closing, tag, attrs = parsed
                if not closing:
                    stack.append((tag, attrs, []))
                else:
                    if stack and stack[-1][0] == tag:
                        stag, sattrs, inner = stack.pop()
                        merged: dict[str, Any] = {
                            "type": stag,
                            "attrs": sattrs,
                            "children": inner,
                            "_annotated": True,
                        }
                        (stack[-1][2] if stack else result).append(merged)
                continue

        target.append(tok)

    while stack:
        _, _, inner = stack.pop()
        (stack[-1][2] if stack else result).extend(inner)

    return result


# ---------------------------------------------------------------------------
# Pass 2: Block level
# ---------------------------------------------------------------------------


def _parse_blocks(tokens: list[dict[str, Any]]) -> list[blocks.Block]:
    matched = _match_block_annotations(tokens)
    result: list[blocks.Block] = []
    for token in matched:
        node = _parse_block(token)
        if node is not None:
            result.append(node)
    return result


def _parse_block(token: dict[str, Any]) -> blocks.Block | None:
    annotated = token.get("_annotated")
    match token["type"]:
        case "paragraph" if not annotated:
            return _parse_paragraph(token)
        case "heading" if not annotated:
            return _parse_heading(token)
        case "table" if not annotated:
            return _parse_table(token)
        case "block_code":
            return _parse_code_block(token)
        case "block_quote":
            return _parse_blockquote(token)
        case "thematic_break":
            return _parse_thematic_break()
        case "list":
            return _parse_list(token)
        case "paragraph":
            return _parse_annotated_paragraph(token)
        case "heading":
            return _parse_annotated_heading(token)
        case "table":
            return _parse_annotated_table(token)
        case "panel":
            return _parse_annotated_panel(token)
        case "expand":
            return _parse_annotated_expand(token)
        case "nestedExpand":
            return _parse_annotated_nested_expand(token)
        case "taskList":
            return _parse_annotated_task_list(token)
        case "decisionList":
            return _parse_annotated_decision_list(token)
        case "layoutSection":
            return _parse_annotated_layout_section(token)
        case "layoutColumn":
            return _parse_annotated_layout_column(token)
        case "mediaSingle":
            return _parse_annotated_media_single(token)
        case "mediaGroup":
            return _parse_annotated_media_group(token)
        case "blockCard":
            return _parse_annotated_block_card(token)
        case "embedCard":
            return _parse_annotated_embed_card(token)
        case "extension":
            return _parse_annotated_extension(token)
        case "bodiedExtension":
            return _parse_annotated_bodied_extension(token)
        case "syncBlock":
            return _parse_annotated_sync_block(token)
        case "bodiedSyncBlock":
            return _parse_annotated_bodied_sync_block(token)
        case "blank_line":
            return None
        case "block_html":
            return None
        case _:
            raise ValueError(f"Unknown block type: {token['type']}")


def _parse_paragraph(token: dict[str, Any]) -> blocks.Paragraph:
    children = _parse_inlines(token.get("children", []))
    return blocks.Paragraph(children=children)


def _parse_heading(token: dict[str, Any]) -> blocks.Heading:
    level = token["attrs"]["level"]
    children = _parse_inlines(token.get("children", []))
    return blocks.Heading(level=level, children=children)


def _parse_thematic_break() -> blocks.ThematicBreak:
    return blocks.ThematicBreak()


def _parse_code_block(token: dict[str, Any]) -> blocks.CodeBlock:
    code = token.get("raw", "")
    if code.endswith("\n"):
        code = code[:-1]
    code = textwrap.dedent(code)
    info = token.get("attrs", {}).get("info", "")
    language = info or None
    return blocks.CodeBlock(code=code, language=language)


def _parse_blockquote(token: dict[str, Any]) -> blocks.BlockQuote:
    children = _parse_blocks(token.get("children", []))
    return blocks.BlockQuote(children=children)


def _parse_list(token: dict[str, Any]) -> blocks.BulletList | blocks.OrderedList:
    ordered = token["attrs"]["ordered"]
    tight = token.get("tight", True)
    items: list[blocks.ListItem] = []
    start = 1

    if ordered:
        start_val = token["attrs"].get("start")
        if start_val is not None:
            start = start_val

    for child in token.get("children", []):
        if child["type"] not in ("list_item", "task_list_item"):
            continue
        item_children = _parse_list_item_children(child, tight)
        checked = child.get("attrs", {}).get("checked")
        items.append(blocks.ListItem(children=item_children, checked=checked))

    if ordered:
        return blocks.OrderedList(items=items, start=start, tight=tight)
    return blocks.BulletList(items=items, tight=tight)


def _parse_list_item_children(
    item_token: dict[str, Any], tight: bool
) -> list[blocks.Block]:
    matched = _match_block_annotations(item_token.get("children", []))
    children: list[blocks.Block] = []
    for child in matched:
        if child.get("_annotated"):
            node = _parse_block(child)
            if node is not None:
                children.append(node)
            continue
        match child["type"]:
            case "paragraph":
                children.append(_parse_paragraph(child))
            case "block_text":
                inls = _parse_inlines(child.get("children", []))
                children.append(blocks.Paragraph(children=inls))
            case "block_code":
                children.append(_parse_code_block(child))
            case "block_quote":
                children.append(_parse_blockquote(child))
            case "list":
                children.append(_parse_list(child))
            case "thematic_break":
                children.append(_parse_thematic_break())
            case "blank_line":
                pass
            case "block_html":
                inline_children = _split_block_html(child["raw"])
                if inline_children is not None:
                    inls = _parse_inlines(inline_children)
                    if inls:
                        children.append(blocks.Paragraph(children=inls))
            case _:
                raise ValueError(f"Unknown list item child type: {child['type']}")
    return children


def _parse_table(token: dict[str, Any]) -> blocks.Table:
    head: list[blocks.TableCell] = []
    body: list[list[blocks.TableCell]] = []
    alignments: list[Literal["left", "center", "right"] | None] = []
    for child in token.get("children", []):
        if child["type"] == "table_head":
            for cell_tok in child.get("children", []):
                align = cell_tok.get("attrs", {}).get("align")
                alignments.append(align)
                cell_children = _parse_cell_blocks(cell_tok.get("children", []))
                head.append(blocks.TableCell(children=cell_children))
        elif child["type"] == "table_body":
            for row_tok in child.get("children", []):
                row: list[blocks.TableCell] = []
                for cell_tok in row_tok.get("children", []):
                    cell_children = _parse_cell_blocks(cell_tok.get("children", []))
                    row.append(blocks.TableCell(children=cell_children))
                body.append(row)

    if head and all(
        not cell.children
        or (
            len(cell.children) == 1
            and isinstance(cell.children[0], blocks.Paragraph)
            and len(cell.children[0].children) == 1
            and isinstance(cell.children[0].children[0], inlines.Text)
            and not cell.children[0].children[0].text.strip()
        )
        for cell in head
    ):
        head = []

    return blocks.Table(head=head, body=body, alignments=alignments)


def _parse_annotated_paragraph(token: dict[str, Any]) -> blocks.Paragraph:
    attrs = token.get("attrs", {})
    inner_blocks = _parse_blocks(token.get("children", []))
    if inner_blocks and isinstance(inner_blocks[0], blocks.Paragraph):
        p = inner_blocks[0]
        p.alignment = attrs.get("align")
        p.indentation = attrs.get("indentation")
        return p
    inls = _flatten_inlines(inner_blocks)
    return blocks.Paragraph(
        children=inls,
        alignment=attrs.get("align"),
        indentation=attrs.get("indentation"),
    )


def _parse_annotated_heading(token: dict[str, Any]) -> blocks.Heading:
    attrs = token.get("attrs", {})
    inner_blocks = _parse_blocks(token.get("children", []))
    if inner_blocks and isinstance(inner_blocks[0], blocks.Heading):
        h = inner_blocks[0]
        h.alignment = attrs.get("align")
        h.indentation = attrs.get("indentation")
        return h
    inls = _flatten_inlines(inner_blocks)
    return blocks.Heading(
        level=attrs.get("level", 1),
        children=inls,
        alignment=attrs.get("align"),
        indentation=attrs.get("indentation"),
    )


def _parse_annotated_table(token: dict[str, Any]) -> blocks.Block:
    attrs = token.get("attrs", {})
    inner_blocks = _parse_blocks(token.get("children", []))
    if inner_blocks and isinstance(inner_blocks[0], blocks.Table):
        t = inner_blocks[0]
        t.display_mode = attrs.get("displayMode")
        t.is_number_column_enabled = attrs.get("isNumberColumnEnabled")
        t.layout = attrs.get("layout")
        t.width = attrs.get("width")
        _apply_cell_attrs(t, attrs.get("cells"))
        return t
    return inner_blocks[0] if inner_blocks else blocks.Paragraph(children=[])


def _parse_annotated_panel(token: dict[str, Any]) -> blocks.Panel:
    attrs = token.get("attrs", {})
    inner_blocks = _parse_blocks(token.get("children", []))
    children = _unwrap_blockquote(inner_blocks)
    return blocks.Panel(
        children=children,
        panel_type=attrs.get("panelType", "info"),
        panel_icon=attrs.get("panelIcon"),
        panel_icon_id=attrs.get("panelIconId"),
        panel_icon_text=attrs.get("panelIconText"),
        panel_color=attrs.get("panelColor"),
    )


def _parse_annotated_expand(token: dict[str, Any]) -> blocks.Expand:
    attrs = token.get("attrs", {})
    inner_blocks = _parse_blocks(token.get("children", []))
    children = _unwrap_blockquote(inner_blocks)
    return blocks.Expand(children=children, title=attrs.get("title"))


def _parse_annotated_nested_expand(token: dict[str, Any]) -> blocks.NestedExpand:
    attrs = token.get("attrs", {})
    inner_blocks = _parse_blocks(token.get("children", []))
    children = _unwrap_blockquote(inner_blocks)
    return blocks.NestedExpand(children=children, title=attrs.get("title"))


def _parse_annotated_media_single(token: dict[str, Any]) -> blocks.MediaSingle:
    attrs = token.get("attrs", {})
    media = _build_media(attrs.get("media", {}))
    return blocks.MediaSingle(
        media=media,
        layout=attrs.get("layout"),
        width=attrs.get("width"),
        width_type=attrs.get("widthType"),
    )


def _parse_annotated_media_group(token: dict[str, Any]) -> blocks.MediaGroup:
    attrs = token.get("attrs", {})
    media_list = [_build_media(m) for m in attrs.get("mediaList", [])]
    return blocks.MediaGroup(media_list=media_list)


def _parse_annotated_block_card(token: dict[str, Any]) -> blocks.BlockCard:
    attrs = token.get("attrs", {})
    return blocks.BlockCard(url=attrs.get("url"), data=attrs.get("data"))


def _parse_annotated_embed_card(token: dict[str, Any]) -> blocks.EmbedCard:
    attrs = token.get("attrs", {})
    return blocks.EmbedCard(
        url=attrs.get("url", ""),
        layout=attrs.get("layout", ""),
        width=attrs.get("width"),
        original_width=attrs.get("originalWidth"),
        original_height=attrs.get("originalHeight"),
    )


def _parse_annotated_extension(token: dict[str, Any]) -> blocks.Extension:
    return blocks.Extension(raw=token.get("attrs", {}))


def _parse_annotated_bodied_extension(token: dict[str, Any]) -> blocks.BodiedExtension:
    return blocks.BodiedExtension(raw=token.get("attrs", {}))


def _parse_annotated_sync_block(token: dict[str, Any]) -> blocks.SyncBlock:
    return blocks.SyncBlock(raw=token.get("attrs", {}))


def _parse_annotated_bodied_sync_block(token: dict[str, Any]) -> blocks.BodiedSyncBlock:
    return blocks.BodiedSyncBlock(raw=token.get("attrs", {}))


def _parse_annotated_task_list(token: dict[str, Any]) -> blocks.TaskList:
    inner_blocks = _parse_blocks(token.get("children", []))
    items = _extract_task_items(inner_blocks)
    return blocks.TaskList(items=items)


def _parse_annotated_decision_list(token: dict[str, Any]) -> blocks.DecisionList:
    inner_blocks = _parse_blocks(token.get("children", []))
    items = _extract_decision_items(inner_blocks)
    return blocks.DecisionList(items=items)


def _parse_annotated_layout_section(token: dict[str, Any]) -> blocks.LayoutSection:
    inner_blocks = _parse_blocks(token.get("children", []))
    columns = [b for b in inner_blocks if isinstance(b, blocks.LayoutColumn)]
    return blocks.LayoutSection(columns=columns)


def _parse_annotated_layout_column(token: dict[str, Any]) -> blocks.LayoutColumn:
    attrs = token.get("attrs", {})
    inner_blocks = _parse_blocks(token.get("children", []))
    return blocks.LayoutColumn(children=inner_blocks, width=attrs.get("width"))


# ---------------------------------------------------------------------------
# Pass 2: Inline block level (table cells)
# ---------------------------------------------------------------------------


_HTML_CELL_BLOCK_MAP: dict[str, str] = {
    "blockquote": "blockQuote",
    "h1": "heading",
    "h2": "heading",
    "h3": "heading",
    "h4": "heading",
    "h5": "heading",
    "h6": "heading",
    "ul": "bulletList",
    "ol": "orderedList",
    "code": "codeBlock",
}

_HTML_CELL_VOID_MAP: dict[str, str] = {
    "hr": "thematicBreak",
}


def _match_html_cell_blocks(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Match HTML open/close tag pairs for known block types into annotated-style tokens."""
    result: list[dict[str, Any]] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.get("_annotated"):
            result.append(tok)
            i += 1
            continue
        if tok.get("type") == "inline_html":
            tag = _extract_html_open_tag(tok["raw"])
            if tag and tag in _HTML_CELL_VOID_MAP:
                result.append(
                    {
                        "type": _HTML_CELL_VOID_MAP[tag],
                        "attrs": {},
                        "children": [],
                        "_annotated": True,
                    }
                )
                i += 1
                continue
            if tag and tag in _HTML_CELL_BLOCK_MAP:
                close_idx = _find_html_close_idx(tokens, i + 1, tag)
                if close_idx is not None:
                    attrs: dict[str, Any] = {}
                    block_type = _HTML_CELL_BLOCK_MAP[tag]
                    if block_type == "heading":
                        attrs["level"] = int(tag[1])
                    elif block_type == "orderedList":
                        start = _extract_html_attr(tok["raw"], "start")
                        if start is not None:
                            attrs["start"] = int(start)
                    result.append(
                        {
                            "type": block_type,
                            "attrs": attrs,
                            "children": tokens[i + 1 : close_idx],
                            "_annotated": True,
                        }
                    )
                    i = close_idx + 1
                    continue
        result.append(tok)
        i += 1
    return result


def _extract_html_open_tag(raw: str) -> str | None:
    """Extract tag name from an opening HTML tag, or None."""
    s = raw.strip().lower()
    if not s.startswith("<") or s.startswith("</"):
        return None
    # e.g. <blockquote>, <ol start="2">
    tag = s.lstrip("<").split(">")[0].split()[0].rstrip("/")
    return tag if tag else None


_HTML_ATTR_RE = re.compile(r"""(\w+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")


def _extract_html_attr(raw: str, name: str) -> str | None:
    """Extract a named attribute value from an HTML open tag."""
    for m in _HTML_ATTR_RE.finditer(raw):
        if m.group(1).lower() == name.lower():
            return m.group(2) if m.group(2) is not None else m.group(3)
    return None


def _find_html_close_idx(
    tokens: list[dict[str, Any]], start: int, tag: str
) -> int | None:
    """Find matching close tag index, handling nesting."""
    depth = 1
    for i in range(start, len(tokens)):
        tok = tokens[i]
        if tok.get("_annotated"):
            continue
        if tok.get("type") == "inline_html":
            raw = tok["raw"].strip().lower()
            if (
                raw.startswith(f"<{tag}")
                and raw.endswith(">")
                and not raw.startswith(f"</{tag}")
            ):
                depth += 1
            elif raw == f"</{tag}>":
                depth -= 1
                if depth == 0:
                    return i
    return None


def _classify_br(tok: dict[str, Any]) -> dict[str, Any]:
    """Classify ``<br>`` variants: ``<br>`` → block separator, ``<br/>`` → linebreak (hardBreak)."""
    if tok.get("type") != "inline_html":
        return tok
    raw = tok["raw"].strip().lower()
    if raw == "<br/>":
        return {"type": "linebreak"}
    if raw == "<br>":
        return {"type": "block_separator"}
    return tok


def _parse_cell_blocks(tokens: list[dict[str, Any]]) -> list[blocks.Block]:
    """Parse table cell inline tokens into blocks.

    Uses annotation matching to group tokens, then dispatches each group.
    Unannotated tokens become Paragraph (plain GFM).
    ``<br>`` = block separator, ``<br/>`` = hardBreak (linebreak).
    """
    matched = _match_html_cell_blocks(_match_cell_annotations(tokens))
    result: list[blocks.Block] = []
    loose: list[dict[str, Any]] = []

    def _flush_loose() -> None:
        if not loose:
            return
        children = _parse_inlines(loose)
        if children:
            result.append(blocks.Paragraph(children=children))
        loose.clear()

    _CELL_BLOCK_TAGS = {
        "paragraph",
        "codeBlock",
        "blockQuote",
        "heading",
        "thematicBreak",
        "bulletList",
        "orderedList",
        "panel",
        "expand",
        "nestedExpand",
        "taskList",
        "decisionList",
        "mediaSingle",
        "mediaGroup",
        "blockCard",
        "embedCard",
        "extension",
        "bodiedExtension",
        "syncBlock",
        "bodiedSyncBlock",
    }

    for tok in matched:
        if tok.get("_annotated") and tok["type"] in _CELL_BLOCK_TAGS:
            _flush_loose()
            block = _parse_cell_block(tok)
            result.append(block)
        elif tok.get("_annotated"):
            # Inline annotation (e.g. status, mention) — keep as loose tokens
            loose.append(tok)
        else:
            classified = _classify_br(tok)
            if classified.get("type") == "block_separator":
                _flush_loose()
            else:
                loose.append(classified)

    _flush_loose()
    return result


def _br_to_linebreak(tok: dict[str, Any]) -> dict[str, Any]:
    """Convert ``<br/>`` to linebreak inside annotated children."""
    if tok.get("type") == "inline_html" and tok["raw"].strip().lower() == "<br/>":
        return {"type": "linebreak"}
    return tok


def _parse_cell_block(token: dict[str, Any]) -> blocks.Block:
    """Dispatch an annotation-matched cell token to the appropriate handler."""
    tag = token["type"]
    attrs = token.get("attrs", {})
    inner = [_br_to_linebreak(t) for t in token.get("children", [])]

    match tag:
        case "paragraph":
            return _parse_cell_paragraph(attrs, inner)
        case "codeBlock":
            return _parse_cell_code_block(attrs, inner)
        case "blockQuote":
            return _parse_cell_blockquote(attrs, inner)
        case "heading":
            return _parse_cell_heading(attrs, inner)
        case "thematicBreak":
            return _parse_cell_thematic_break()
        case "bulletList":
            return _parse_cell_list("ul", attrs, inner)
        case "orderedList":
            return _parse_cell_list("ol", attrs, inner)
        case "panel":
            return _parse_cell_panel(attrs, inner)
        case "expand":
            return _parse_cell_expand(attrs, inner)
        case "nestedExpand":
            return _parse_cell_nested_expand(attrs, inner)
        case "taskList":
            return _parse_cell_task_list(inner)
        case "decisionList":
            return _parse_cell_decision_list(inner)
        case "mediaSingle":
            return _parse_cell_media_single(attrs)
        case "mediaGroup":
            return _parse_cell_media_group(attrs)
        case "blockCard":
            return _parse_cell_block_card(attrs)
        case "embedCard":
            return _parse_cell_embed_card(attrs)
        case "extension":
            return _parse_cell_extension(attrs)
        case "bodiedExtension":
            return _parse_cell_bodied_extension(attrs)
        case "syncBlock":
            return _parse_cell_sync_block(attrs)
        case "bodiedSyncBlock":
            return _parse_cell_bodied_sync_block(attrs)
        case _:
            raise ValueError(f"Unknown cell block type: {tag}")


def _parse_cell_paragraph(
    attrs: dict[str, Any], tokens: list[dict[str, Any]]
) -> blocks.Paragraph:
    children = _parse_inlines(tokens)
    return blocks.Paragraph(
        children=children,
        alignment=attrs.get("align"),
        indentation=attrs.get("indentation"),
    )


def _parse_cell_code_block(
    attrs: dict[str, Any], tokens: list[dict[str, Any]]
) -> blocks.CodeBlock:
    """<code>text<br>text</code> → CodeBlock"""
    inner = _strip_html_wrapper(tokens, "code")
    code = _inner_tokens_to_text(inner)
    code = code.replace("<br>", "\n")
    return blocks.CodeBlock(code=code, language=attrs.get("language"))


def _parse_cell_blockquote(
    _attrs: dict[str, Any], tokens: list[dict[str, Any]]
) -> blocks.BlockQuote:
    """<blockquote>content</blockquote> → BlockQuote"""
    inner = _strip_html_wrapper(tokens, "blockquote")
    children = _parse_cell_blocks(inner)
    return blocks.BlockQuote(children=children)


def _parse_cell_heading(
    attrs: dict[str, Any], tokens: list[dict[str, Any]]
) -> blocks.Heading:
    """<h3>inlines</h3> → Heading"""
    level = attrs.get("level", 1)
    tag = f"h{level}"
    inner = _strip_html_wrapper(tokens, tag)
    children = _parse_inlines(inner)
    return blocks.Heading(level=level, children=children)


def _parse_cell_list(
    html_tag: str, attrs: dict[str, Any], tokens: list[dict[str, Any]]
) -> blocks.BulletList | blocks.OrderedList:
    """<ul><li>...</li></ul> or <ol><li>...</li></ol> → List"""
    inner = _strip_html_wrapper(tokens, html_tag)
    li_groups = _split_by_tag(inner, "li")
    items: list[blocks.ListItem] = []
    for li_tokens in li_groups:
        item_blocks = _parse_cell_blocks(li_tokens)
        items.append(blocks.ListItem(children=item_blocks))

    start = attrs.get("start", 1)
    if html_tag == "ol":
        return blocks.OrderedList(items=items, start=start, tight=True)
    return blocks.BulletList(items=items, tight=True)


def _parse_cell_thematic_break() -> blocks.ThematicBreak:
    return blocks.ThematicBreak()


def _parse_cell_panel(
    attrs: dict[str, Any], tokens: list[dict[str, Any]]
) -> blocks.Panel:
    inner_content = _strip_html_wrapper(tokens, "blockquote")
    children = _parse_cell_blocks(inner_content)
    return blocks.Panel(
        children=children,
        panel_type=attrs.get("panelType", "info"),
        panel_icon=attrs.get("panelIcon"),
        panel_icon_id=attrs.get("panelIconId"),
        panel_icon_text=attrs.get("panelIconText"),
        panel_color=attrs.get("panelColor"),
    )


def _parse_cell_expand(
    attrs: dict[str, Any], tokens: list[dict[str, Any]]
) -> blocks.Expand:
    inner_content = _strip_html_wrapper(tokens, "blockquote")
    children = _parse_cell_blocks(inner_content)
    return blocks.Expand(children=children, title=attrs.get("title"))


def _parse_cell_nested_expand(
    attrs: dict[str, Any], tokens: list[dict[str, Any]]
) -> blocks.NestedExpand:
    inner_content = _strip_html_wrapper(tokens, "blockquote")
    children = _parse_cell_blocks(inner_content)
    return blocks.NestedExpand(children=children, title=attrs.get("title"))


def _parse_cell_task_list(tokens: list[dict[str, Any]]) -> blocks.TaskList:
    inner_content = _strip_html_wrapper(tokens, "ul")
    li_groups = _split_by_tag(inner_content, "li")
    items: list[blocks.TaskItem] = []
    for li_toks in li_groups:
        state, inls = _parse_cell_checklist_item(li_toks)
        items.append(blocks.TaskItem(children=inls, state=state or "TODO"))
    return blocks.TaskList(items=items)


def _parse_cell_decision_list(tokens: list[dict[str, Any]]) -> blocks.DecisionList:
    inner_content = _strip_html_wrapper(tokens, "ul")
    li_groups = _split_by_tag(inner_content, "li")
    items: list[blocks.DecisionItem] = []
    for li_toks in li_groups:
        state, inls = _parse_cell_checklist_item(li_toks)
        dstate = "DECIDED" if state == "DONE" else (state or "TODO")
        items.append(blocks.DecisionItem(children=inls, state=dstate))
    return blocks.DecisionList(items=items)


def _parse_cell_media_single(attrs: dict[str, Any]) -> blocks.MediaSingle:
    media = _build_media(attrs.get("media", {}))
    return blocks.MediaSingle(
        media=media,
        layout=attrs.get("layout"),
        width=attrs.get("width"),
        width_type=attrs.get("widthType"),
    )


def _parse_cell_media_group(attrs: dict[str, Any]) -> blocks.MediaGroup:
    media_list = [_build_media(m) for m in attrs.get("mediaList", [])]
    return blocks.MediaGroup(media_list=media_list)


def _parse_cell_block_card(attrs: dict[str, Any]) -> blocks.BlockCard:
    return blocks.BlockCard(url=attrs.get("url"), data=attrs.get("data"))


def _parse_cell_embed_card(attrs: dict[str, Any]) -> blocks.EmbedCard:
    return blocks.EmbedCard(
        url=attrs.get("url", ""),
        layout=attrs.get("layout", ""),
        width=attrs.get("width"),
        original_width=attrs.get("originalWidth"),
        original_height=attrs.get("originalHeight"),
    )


def _parse_cell_extension(attrs: dict[str, Any]) -> blocks.Extension:
    return blocks.Extension(raw=attrs)


def _parse_cell_bodied_extension(attrs: dict[str, Any]) -> blocks.BodiedExtension:
    return blocks.BodiedExtension(raw=attrs)


def _parse_cell_sync_block(attrs: dict[str, Any]) -> blocks.SyncBlock:
    return blocks.SyncBlock(raw=attrs)


def _parse_cell_bodied_sync_block(attrs: dict[str, Any]) -> blocks.BodiedSyncBlock:
    return blocks.BodiedSyncBlock(raw=attrs)


def _parse_cell_checklist_item(
    tokens: list[dict[str, Any]],
) -> tuple[str | None, list[inlines.Inline]]:
    """Parse [x]/[ ] prefix from cell list item tokens."""
    inls = _parse_inlines(tokens)
    if inls and isinstance(inls[0], inlines.Text):
        text = inls[0].text
        if text.startswith("[x] "):
            inls[0] = inlines.Text(text=text[4:])
            if not inls[0].text:
                inls = inls[1:]
            return "DONE", inls
        elif text.startswith("[ ] "):
            inls[0] = inlines.Text(text=text[4:])
            if not inls[0].text:
                inls = inls[1:]
            return "TODO", inls
    return None, inls


# ---------------------------------------------------------------------------
# Pass 2: Inline level
# ---------------------------------------------------------------------------


def _parse_inlines(tokens: list[dict[str, Any]]) -> list[inlines.Inline]:
    matched = _match_inline_annotations(tokens)
    result: list[inlines.Inline] = []
    for token in matched:
        node = _parse_inline(token)
        if node is not None:
            # Merge adjacent Text nodes (mistune may split e.g. "[" separately)
            if (
                isinstance(node, inlines.Text)
                and result
                and isinstance(result[-1], inlines.Text)
            ):
                result[-1] = inlines.Text(text=result[-1].text + node.text)
            else:
                result.append(node)
    return result


def _parse_inline(token: dict[str, Any]) -> inlines.Inline | None:
    match token["type"]:
        case "text":
            return _parse_text(token)
        case "strong":
            return _parse_strong(token)
        case "emphasis":
            return _parse_emphasis(token)
        case "strikethrough":
            return _parse_strikethrough(token)
        case "link":
            return _parse_link(token)
        case "image":
            return _parse_image(token)
        case "codespan":
            return _parse_codespan(token)
        case "linebreak":
            return _parse_linebreak(token)
        case "softbreak":
            return _parse_softbreak(token)
        case "mention":
            return _parse_annotated_mention(token)
        case "emoji":
            return _parse_annotated_emoji(token)
        case "date":
            return _parse_annotated_date(token)
        case "status":
            return _parse_annotated_status(token)
        case "inlineCard":
            return _parse_annotated_inline_card(token)
        case "mediaInline":
            return _parse_annotated_media_inline(token)
        case "underline":
            return _parse_annotated_underline(token)
        case "textColor":
            return _parse_annotated_text_color(token)
        case "backgroundColor":
            return _parse_annotated_background_color(token)
        case "subSup":
            return _parse_annotated_subsup(token)
        case "annotation":
            return _parse_annotated_annotation(token)
        case "placeholder":
            return _parse_annotated_placeholder(token)
        case "inlineExtension":
            return _parse_annotated_inline_extension(token)
        case _:
            raise ValueError(f"Unknown inline type: {token['type']}")


def _parse_text(token: dict[str, Any]) -> inlines.Text:
    return inlines.Text(text=token["raw"])


def _parse_strong(token: dict[str, Any]) -> inlines.Strong:
    children = _parse_inlines(token.get("children", []))
    return inlines.Strong(children=children)


def _parse_emphasis(token: dict[str, Any]) -> inlines.Emphasis:
    children = _parse_inlines(token.get("children", []))
    return inlines.Emphasis(children=children)


def _parse_strikethrough(token: dict[str, Any]) -> inlines.Strikethrough:
    children = _parse_inlines(token.get("children", []))
    return inlines.Strikethrough(children=children)


def _parse_link(token: dict[str, Any]) -> inlines.Link:
    url = token.get("attrs", {}).get("url") or token.get("link", "")
    title = token.get("attrs", {}).get("title")
    children = _parse_inlines(token.get("children", []))
    return inlines.Link(url=url, children=children, title=title)


def _parse_image(token: dict[str, Any]) -> inlines.Image:
    attrs = token.get("attrs", {})
    url = attrs.get("url", attrs.get("src", ""))
    alt = token.get("alt", attrs.get("alt", ""))
    title = attrs.get("title")
    if not alt and token.get("children"):
        alt_parts: list[str] = []
        for c in cast(list[dict[str, Any]], token["children"]):
            if c["type"] == "text":
                alt_parts.append(c["raw"])
        alt = "".join(alt_parts)
    return inlines.Image(url=url, alt=alt, title=title)


def _parse_codespan(token: dict[str, Any]) -> inlines.CodeSpan:
    return inlines.CodeSpan(code=token["raw"])


def _parse_linebreak(_token: dict[str, Any]) -> inlines.HardBreak:
    return inlines.HardBreak()


def _parse_softbreak(_token: dict[str, Any]) -> inlines.SoftBreak:
    return inlines.SoftBreak()


def _parse_annotated_inline_extension(token: dict[str, Any]) -> inlines.InlineExtension:
    return inlines.InlineExtension(raw=token.get("attrs", {}))


def _parse_annotated_mention(token: dict[str, Any]) -> inlines.Mention:
    attrs = token.get("attrs", {})
    return inlines.Mention(
        id=attrs.get("id", ""),
        text=attrs.get("text"),
        access_level=attrs.get("accessLevel"),
        user_type=attrs.get("userType"),
    )


def _parse_annotated_emoji(token: dict[str, Any]) -> inlines.Emoji:
    attrs = token.get("attrs", {})
    return inlines.Emoji(
        short_name=attrs.get("shortName", ""),
        text=attrs.get("text"),
        id=attrs.get("id"),
    )


def _parse_annotated_date(token: dict[str, Any]) -> inlines.Date:
    attrs = token.get("attrs", {})
    return inlines.Date(timestamp=attrs.get("timestamp", ""))


def _parse_annotated_status(token: dict[str, Any]) -> inlines.Status:
    attrs = token.get("attrs", {})
    return inlines.Status(
        text=attrs.get("text", ""),
        color=attrs.get("color", ""),
        style=attrs.get("style"),
    )


def _parse_annotated_inline_card(token: dict[str, Any]) -> inlines.InlineCard:
    attrs = token.get("attrs", {})
    url = attrs.get("url")
    if not url:
        inner = _parse_inlines(token.get("children", []))
        for child in inner:
            if isinstance(child, inlines.Link):
                url = child.url
                break
    return inlines.InlineCard(url=url, data=attrs.get("data"))


def _parse_annotated_media_inline(token: dict[str, Any]) -> inlines.MediaInline:
    attrs = token.get("attrs", {})
    return inlines.MediaInline(
        id=attrs.get("id"),
        collection=attrs.get("collection"),
        media_type=attrs.get("mediaType", "file"),
        alt=attrs.get("alt"),
        width=attrs.get("width"),
        height=attrs.get("height"),
    )


def _parse_annotated_underline(token: dict[str, Any]) -> inlines.Underline:
    children = _parse_inlines(token.get("children", []))
    return inlines.Underline(children=children)


def _parse_annotated_text_color(token: dict[str, Any]) -> inlines.TextColor:
    attrs = token.get("attrs", {})
    children = _parse_inlines(token.get("children", []))
    return inlines.TextColor(color=attrs.get("color", ""), children=children)


def _parse_annotated_background_color(token: dict[str, Any]) -> inlines.BackgroundColor:
    attrs = token.get("attrs", {})
    children = _parse_inlines(token.get("children", []))
    return inlines.BackgroundColor(color=attrs.get("color", ""), children=children)


def _parse_annotated_subsup(token: dict[str, Any]) -> inlines.SubSup:
    attrs = token.get("attrs", {})
    children = _parse_inlines(token.get("children", []))
    return inlines.SubSup(type=attrs.get("type", "sub"), children=children)


def _parse_annotated_annotation(token: dict[str, Any]) -> inlines.Annotation:
    attrs = token.get("attrs", {})
    children = _parse_inlines(token.get("children", []))
    return inlines.Annotation(
        id=attrs.get("id", ""),
        children=children,
        annotation_type=attrs.get("annotationType", "inlineComment"),
    )


def _parse_annotated_placeholder(token: dict[str, Any]) -> inlines.Placeholder:
    inner = _parse_inlines(token.get("children", []))
    text = ""
    for child in inner:
        if isinstance(child, inlines.Text):
            text += child.text
    return inlines.Placeholder(text=text)


# ---------------------------------------------------------------------------
# Shared builders
# ---------------------------------------------------------------------------


def _build_media(d: dict[str, Any]) -> blocks.Media:
    return blocks.Media(
        media_type=d.get("mediaType", "file"),
        url=d.get("url"),
        id=d.get("id"),
        collection=d.get("collection"),
        alt=d.get("alt"),
        width=d.get("width"),
        height=d.get("height"),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unwrap_blockquote(inner: list[blocks.Block]) -> list[blocks.Block]:
    """Legacy: if inner is a single BlockQuote, unwrap its children."""
    if len(inner) == 1 and isinstance(inner[0], blocks.BlockQuote):
        return inner[0].children
    return inner


def _flatten_inlines(block_nodes: list[blocks.Block]) -> list[inlines.Inline]:
    """Extract inlines from a list of blocks (typically single Paragraph)."""
    result: list[inlines.Inline] = []
    for b in block_nodes:
        if isinstance(b, blocks.Paragraph):
            result.extend(b.children)
    return result


def _extract_task_items(inner: list[blocks.Block]) -> list[blocks.TaskItem]:
    """Extract TaskItems from bullet list rendered inside annotation."""
    items: list[blocks.TaskItem] = []
    for block in inner:
        if isinstance(block, blocks.BulletList):
            for li in block.items:
                state = "DONE" if li.checked else "TODO"
                inls = _flatten_inlines(li.children)
                items.append(blocks.TaskItem(children=inls, state=state))
        elif isinstance(block, blocks.Paragraph):
            text_content = block.children
            state, inls = _check_task_prefix(text_content)
            items.append(blocks.TaskItem(children=inls, state=state))
    return items


def _extract_decision_items(
    inner: list[blocks.Block],
) -> list[blocks.DecisionItem]:
    """Extract DecisionItems from bullet list rendered inside annotation."""
    items: list[blocks.DecisionItem] = []
    for block in inner:
        if isinstance(block, blocks.BulletList):
            for li in block.items:
                state = "DECIDED" if li.checked else ""
                inls = _flatten_inlines(li.children)
                items.append(blocks.DecisionItem(children=inls, state=state))
        elif isinstance(block, blocks.Paragraph):
            text_content = block.children
            state, inls = _check_decision_prefix(text_content)
            items.append(blocks.DecisionItem(children=inls, state=state))
    return items


def _check_task_prefix(
    nodes: list[inlines.Inline],
) -> tuple[str, list[inlines.Inline]]:
    """Check for [x]/[ ] prefix in inline nodes."""
    if nodes and isinstance(nodes[0], inlines.Text):
        text = nodes[0].text
        if text.startswith("[x] "):
            rest = text[4:]
            new_nodes = ([inlines.Text(text=rest)] if rest else []) + list(nodes[1:])
            return "DONE", new_nodes
        elif text.startswith("[ ] "):
            rest = text[4:]
            new_nodes = ([inlines.Text(text=rest)] if rest else []) + list(nodes[1:])
            return "TODO", new_nodes
    return "TODO", list(nodes)


def _check_decision_prefix(
    nodes: list[inlines.Inline],
) -> tuple[str, list[inlines.Inline]]:
    """Check for [x]/[ ] prefix in inline nodes for decisions."""
    if nodes and isinstance(nodes[0], inlines.Text):
        text = nodes[0].text
        if text.startswith("[x] "):
            rest = text[4:]
            new_nodes = ([inlines.Text(text=rest)] if rest else []) + list(nodes[1:])
            return "DECIDED", new_nodes
        elif text.startswith("[ ] "):
            rest = text[4:]
            new_nodes = ([inlines.Text(text=rest)] if rest else []) + list(nodes[1:])
            return "", new_nodes
    return "", list(nodes)


def _apply_cell_attrs(table: blocks.Table, cell_attrs: list[list[Any]] | None) -> None:
    """Apply compact cell attrs to table cells."""
    if not cell_attrs:
        return
    all_rows = [table.head, *table.body]
    for row_idx, row_attr in enumerate(cell_attrs):
        if row_idx >= len(all_rows):
            break
        row = all_rows[row_idx]
        for col_idx, attr in enumerate(row_attr):
            if col_idx >= len(row):
                break
            cell = row[col_idx]
            if attr is None:
                continue
            if isinstance(attr, list):
                cell.col_width = attr
            elif isinstance(attr, dict):
                d = cast(dict[str, Any], attr)
                if d.get("colspan"):
                    cell.colspan = d["colspan"]
                if d.get("rowspan"):
                    cell.rowspan = d["rowspan"]
                if d.get("colwidth"):
                    cell.col_width = d["colwidth"]
                if d.get("background"):
                    cell.background = d["background"]
                if d.get("header"):
                    header = blocks.TableHeader(
                        children=cell.children,
                        colspan=cell.colspan,
                        rowspan=cell.rowspan,
                        col_width=cell.col_width,
                        background=cell.background,
                    )
                    row[col_idx] = header


def _strip_html_wrapper(tokens: list[dict[str, Any]], tag: str) -> list[dict[str, Any]]:
    """Remove opening and closing HTML tags from token list."""
    start = 0
    end = len(tokens)
    if tokens and tokens[0].get("type") == "inline_html":
        raw = tokens[0]["raw"].strip().lower()
        if raw.startswith(f"<{tag}") and raw.endswith(">"):
            start = 1
    if end > start and tokens[end - 1].get("type") == "inline_html":
        raw = tokens[end - 1]["raw"].strip().lower()
        if raw == f"</{tag}>":
            end -= 1
    return tokens[start:end]


def _split_by_tag(tokens: list[dict[str, Any]], tag: str) -> list[list[dict[str, Any]]]:
    """Split tokens by <tag>...</tag> pairs, returning inner content of each."""
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] | None = None

    for tok in tokens:
        if tok.get("type") == "inline_html":
            raw = tok["raw"].strip().lower()
            if (
                raw.startswith(f"<{tag}")
                and raw.endswith(">")
                and not raw.startswith(f"</{tag}")
            ):
                current = []
                continue
            elif raw == f"</{tag}>":
                if current is not None:
                    groups.append(current)
                    current = None
                continue
        if current is not None:
            current.append(tok)

    return groups


def _inner_tokens_to_text(tokens: list[dict[str, Any]]) -> str:
    """Extract plain text from inner tokens (for code blocks)."""
    parts: list[str] = []
    for tok in tokens:
        if tok["type"] == "text":
            parts.append(tok["raw"])
        elif tok["type"] == "linebreak":
            parts.append("<br>")
        elif tok["type"] == "inline_html":
            parts.append(tok["raw"].strip())
        elif tok["type"] == "codespan":
            parts.append(tok["raw"])
        else:
            parts.append(tok.get("raw", ""))
    return "".join(parts)
