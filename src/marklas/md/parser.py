"""Markdown → ADF AST parser."""

from __future__ import annotations

import html
import json
import re
from typing import Any, cast

import mistune

from marklas import ast

# ── Tokenization ──────────────────────────────────────────────────────────────

_md = mistune.create_markdown(
    renderer="ast",
    plugins=["table", "strikethrough", "task_lists"],
)


def _tokenize(md: str) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], _md(md))


# ── HTML tag parsing ──────────────────────────────────────────────────────────

_TAG_RE = re.compile(
    r"<(/?)(\w+)"
    r"((?:\s+[\w-]+(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'))?)*)"
    r"\s*/?>",
    re.DOTALL,
)
_ATTR_RE = re.compile(r"""([\w-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'))?""")


def _parse_tag(raw: str) -> tuple[str, dict[str, str], bool]:
    """Parse HTML tag → (tag_name, attrs_dict, is_closing)."""
    m = _TAG_RE.match(raw.strip())
    if not m:
        return ("", {}, False)
    closing = bool(m.group(1))
    tag = m.group(2).lower()
    attr_str = m.group(3) or ""
    attrs: dict[str, str] = {}
    for am in _ATTR_RE.finditer(attr_str):
        key = am.group(1)
        value = (
            am.group(2)
            if am.group(2) is not None
            else (am.group(3) if am.group(3) is not None else "")
        )
        attrs[key] = value
    return (tag, attrs, closing)


def _parse_params(raw: str) -> dict[str, Any]:
    """Unescape HTML attribute + JSON parse: params attr → dict."""
    unescaped = html.unescape(raw)
    try:
        return json.loads(unescaped)
    except (json.JSONDecodeError, ValueError):
        return {}


def _has_adf(attrs: dict[str, str]) -> bool:
    return "adf" in attrs


def _get_params(attrs: dict[str, str]) -> dict[str, Any]:
    return _parse_params(attrs.get("params", "{}"))


# ── Entry point ───────────────────────────────────────────────────────────────


def parse(md: str) -> ast.Doc:
    tokens = _tokenize(md)
    children = _parse_doc_children(tokens)
    return ast.Doc(content=children)


# ── Block normalization ───────────────────────────────────────────────────────
#
# Transform raw mistune token stream into a clean list:
#   - blank_line removed
#   - block_html open/close pairs merged → {"_kind": "html", "tag", "attrs", "inner"}
#   - void <div> (</div> in same raw) → {"_kind": "data", "attrs"} or metadata
#   - <div adf="marks"> → _marks attached to next block
#   - <div adf="table"> → _table_meta attached to next table


def _find_block_close(tokens: list[dict[str, Any]], start: int, tag: str) -> int | None:
    depth = 1
    for i in range(start, len(tokens)):
        if tokens[i].get("type") == "block_html":
            raw = tokens[i].get("raw", "").strip()
            t, _, closing = _parse_tag(raw)
            if t == tag:
                if closing:
                    depth -= 1
                    if depth == 0:
                        return i
                else:
                    depth += 1
    return None


def _normalize_blocks(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize block token stream into self-contained items."""
    result: list[dict[str, Any]] = []
    pending_marks: list[ast.Mark] = []
    pending_table_meta: dict[str, Any] | None = None
    i = 0
    while i < len(tokens):
        token = tokens[i]
        t = token.get("type", "")

        if t == "blank_line":
            i += 1
            continue

        if t == "block_html":
            raw = token.get("raw", "").strip()
            tag, attrs, closing = _parse_tag(raw)

            if closing:
                i += 1
                continue

            if not _has_adf(attrs):
                i += 1
                continue

            adf_type = attrs.get("adf", "")

            # Self-contained: </tag> in same raw (void/metadata)
            if f"</{tag}>" in raw:
                params = _parse_params(attrs.get("params", "{}"))
                if adf_type == "marks":
                    pending_marks = _parse_block_marks(params)
                elif adf_type == "table":
                    pending_table_meta = params
                else:
                    block: dict[str, Any] = {"_kind": "data", "attrs": attrs}
                    if pending_marks:
                        block["_marks"] = pending_marks
                        pending_marks = []
                    result.append(block)
                i += 1
                continue

            # Paired: find matching close
            close_idx = _find_block_close(tokens, i + 1, tag)
            if close_idx is not None:
                inner = tokens[i + 1 : close_idx]
                block = {
                    "_kind": "html",
                    "tag": tag,
                    "attrs": attrs,
                    "inner": inner,
                }
                if pending_marks:
                    block["_marks"] = pending_marks
                    pending_marks = []
                result.append(block)
                i = close_idx + 1
                continue

            i += 1
            continue

        # Solo image paragraph → promote to block-level image
        if t == "paragraph":
            children = token.get("children", [])
            if len(children) == 1 and children[0].get("type") == "image":
                token = children[0]

        # Regular token — attach pending metadata
        out = dict(token)
        if pending_marks:
            out["_marks"] = pending_marks
            pending_marks = []
        if t == "table" and pending_table_meta is not None:
            out["_table_meta"] = pending_table_meta
            pending_table_meta = None
        result.append(out)
        i += 1

    return result


def _attach_marks(node: ast.Node, marks: list[ast.Mark]) -> None:
    if hasattr(node, "marks") and marks:
        setattr(node, "marks", list(getattr(node, "marks")) + marks)


# ── Context-specific block parsers ────────────────────────────────────────────


def _parse_doc_children(tokens: list[dict[str, Any]]) -> list[ast.DocContent]:
    result: list[ast.DocContent] = []
    for block in _normalize_blocks(tokens):
        node = _dispatch_block(block)
        if node:
            _attach_marks(node, block.get("_marks", []))
            result.append(cast(ast.DocContent, node))
    return result


def _parse_blockquote_children(
    tokens: list[dict[str, Any]],
) -> list[ast.BlockquoteContent]:
    result: list[ast.BlockquoteContent] = []
    for block in _normalize_blocks(tokens):
        node = _dispatch_block(block)
        if node:
            _attach_marks(node, block.get("_marks", []))
            result.append(cast(ast.BlockquoteContent, node))
    return result


def _parse_list_item_children(
    tokens: list[dict[str, Any]],
) -> list[ast.ListItemContent]:
    result: list[ast.ListItemContent] = []
    for token in tokens:
        t = token.get("type", "")
        if t == "blank_line":
            continue
        if t == "block_text":
            inlines = _parse_inlines(token.get("children", []))
            result.append(ast.Paragraph(content=inlines))
        elif t == "list":
            result.append(_parse_list(token))
        else:
            node = _parse_block(token)
            if node:
                result.append(cast(ast.ListItemContent, node))
    return result


def _parse_panel_children(tokens: list[dict[str, Any]]) -> list[ast.PanelContent]:
    result: list[ast.PanelContent] = []
    for block in _normalize_blocks(tokens):
        node = _dispatch_block(block)
        if node:
            _attach_marks(node, block.get("_marks", []))
            result.append(cast(ast.PanelContent, node))
    return result


def _parse_expand_children(tokens: list[dict[str, Any]]) -> list[ast.ExpandContent]:
    result: list[ast.ExpandContent] = []
    for block in _normalize_blocks(tokens):
        node = _dispatch_block(block)
        if node:
            _attach_marks(node, block.get("_marks", []))
            result.append(cast(ast.ExpandContent, node))
    return result


def _parse_nested_expand_children(
    tokens: list[dict[str, Any]],
) -> list[ast.NestedExpandContent]:
    result: list[ast.NestedExpandContent] = []
    for block in _normalize_blocks(tokens):
        node = _dispatch_block(block)
        if node:
            _attach_marks(node, block.get("_marks", []))
            result.append(cast(ast.NestedExpandContent, node))
    return result


def _parse_layout_column_children(
    tokens: list[dict[str, Any]],
) -> list[ast.BlockContent]:
    result: list[ast.BlockContent] = []
    for block in _normalize_blocks(tokens):
        node = _dispatch_block(block)
        if node:
            _attach_marks(node, block.get("_marks", []))
            result.append(cast(ast.BlockContent, node))
    return result


# ── Block dispatch ────────────────────────────────────────────────────────────


def _dispatch_block(block: dict[str, Any]) -> ast.Node | None:
    """Dispatch a normalized block to its parser."""
    kind = block.get("_kind")
    if kind == "html":
        return _parse_block_html(block["tag"], block["attrs"], block["inner"])
    if kind == "data":
        return _parse_data_element(block["attrs"])
    if block.get("type") == "table":
        return _parse_table(block, block.get("_table_meta"))
    return _parse_block(block)


def _parse_block(token: dict[str, Any]) -> ast.Node | None:
    """Dispatch a native mistune block token."""
    t = token.get("type", "")
    match t:
        case "paragraph":
            return _parse_paragraph(token)
        case "image":
            return _parse_image(token)
        case "heading":
            return _parse_heading(token)
        case "block_code":
            return _parse_code_block(token)
        case "block_quote":
            return _parse_blockquote(token)
        case "list":
            return _parse_list(token)
        case "thematic_break":
            return _parse_thematic_break()
        case _:
            return None


def _parse_block_html(
    _tag: str, attrs: dict[str, str], inner_tokens: list[dict[str, Any]]
) -> ast.Node | None:
    """Dispatch matched block HTML pair → AST node."""
    adf_type = attrs.get("adf", "")
    match adf_type:
        case "panel":
            return _parse_panel(attrs, inner_tokens)
        case "expand":
            return _parse_expand(adf_type, attrs, inner_tokens)
        case "nestedExpand":
            return _parse_expand(adf_type, attrs, inner_tokens)
        case "mediaSingle":
            return _parse_media_single(attrs, inner_tokens)
        case "mediaGroup":
            return _parse_media_group(attrs, inner_tokens)
        case "layoutSection":
            return _parse_layout_section(attrs, inner_tokens)
        case "decisionList":
            return _parse_decision_list(attrs, inner_tokens)
        case "blockCard" | "embedCard":
            return _parse_block_card(adf_type, attrs)
        case "taskList":
            return _parse_task_list_html(attrs, inner_tokens)
        case _:
            return None


# ── Block parsers ─────────────────────────────────────────────────────────────


def _parse_paragraph(token: dict[str, Any]) -> ast.Paragraph:
    children = token.get("children", [])
    if len(children) == 1 and children[0].get("type") == "text":
        raw = children[0].get("raw", "")
        if raw in ("\xa0", "&nbsp;"):
            return ast.Paragraph(content=[])
    return ast.Paragraph(content=_parse_inlines(children))


def _parse_heading(token: dict[str, Any]) -> ast.Heading:
    level = token.get("attrs", {}).get("level", 1)
    children = token.get("children", [])
    return ast.Heading(level=level, content=_parse_inlines(children))


def _parse_code_block(token: dict[str, Any]) -> ast.CodeBlock:
    raw = token.get("raw", "")
    if raw.endswith("\n"):
        raw = raw[:-1]
    info = token.get("attrs", {}).get("info", "")
    language = info.split()[0] if info else None
    content = [ast.Text(text=raw)] if raw else []
    return ast.CodeBlock(language=language, content=content)


def _parse_blockquote(token: dict[str, Any]) -> ast.Blockquote:
    children = token.get("children", [])
    return ast.Blockquote(content=_parse_blockquote_children(children))


def _parse_list(
    token: dict[str, Any],
) -> ast.BulletList | ast.OrderedList | ast.TaskList:
    attrs = token.get("attrs", {})
    ordered = attrs.get("ordered", False)
    children = token.get("children", [])

    is_task = any(c.get("type") == "task_list_item" for c in children)
    if is_task:
        items: list[ast.TaskListContent] = []
        for child in children:
            if child.get("type") == "task_list_item":
                items.append(_dispatch_task_item(child))
            elif child.get("type") == "list":
                nested = _parse_list(child)
                if isinstance(nested, ast.TaskList):
                    items.append(nested)
        return ast.TaskList(content=items)

    list_items = [_parse_list_item(c) for c in children if c.get("type") == "list_item"]

    if ordered:
        start = attrs.get("start", 1)
        return ast.OrderedList(content=list_items, order=start if start != 1 else None)
    return ast.BulletList(content=list_items)


def _parse_list_item(token: dict[str, Any]) -> ast.ListItem:
    return ast.ListItem(content=_parse_list_item_children(token.get("children", [])))


def _is_block_task_item(token: dict[str, Any]) -> bool:
    """BlockTaskItem if 2+ block children."""
    children = token.get("children", [])
    non_blank = [c for c in children if c.get("type") != "blank_line"]
    return len(non_blank) > 1


def _dispatch_task_item(token: dict[str, Any]) -> ast.TaskItem | ast.BlockTaskItem:
    if _is_block_task_item(token):
        return _parse_block_task_item(token)
    return _parse_task_item(token)


def _parse_task_item(token: dict[str, Any]) -> ast.TaskItem:
    checked = token.get("attrs", {}).get("checked", False)
    state = "DONE" if checked else "TODO"
    inlines: list[ast.Inline] = []
    for child in token.get("children", []):
        if child.get("type") in ("block_text", "paragraph"):
            inlines.extend(_parse_inlines(child.get("children", [])))
    return ast.TaskItem(state=state, content=inlines)


def _parse_block_task_item(token: dict[str, Any]) -> ast.BlockTaskItem:
    checked = token.get("attrs", {}).get("checked", False)
    state = "DONE" if checked else "TODO"
    content: list[ast.BlockTaskItemContent] = []
    for child in token.get("children", []):
        t = child.get("type", "")
        if t == "blank_line":
            continue
        if t == "block_text":
            inlines = _parse_inlines(child.get("children", []))
            content.append(ast.Paragraph(content=inlines))
        else:
            node = _parse_block(child)
            if node and isinstance(node, (ast.Paragraph, ast.Extension)):
                content.append(node)
    return ast.BlockTaskItem(state=state, content=content)


def _parse_thematic_break() -> ast.Rule:
    return ast.Rule()


def _parse_table(token: dict[str, Any], meta: dict[str, Any] | None) -> ast.Table:
    children = token.get("children", [])
    head_token = None
    body_rows: list[dict[str, Any]] = []
    for child in children:
        if child.get("type") == "table_head":
            head_token = child
        elif child.get("type") == "table_body":
            body_rows = child.get("children", [])

    header_mode = (meta or {}).get("header", "row")
    rows: list[ast.TableRow] = []

    if head_token:
        head_cells = head_token.get("children", [])
        if header_mode in ("row", "both"):
            row = _parse_table_row(head_cells, header=True)
            rows.append(row)

    for row_token in body_rows:
        row_cells = row_token.get("children", [])
        first_col_header = header_mode in ("column", "both")
        row = _parse_table_row(row_cells, first_col_header=first_col_header)
        rows.append(row)

    m = meta or {}
    return ast.Table(
        content=rows,
        layout=m.get("layout"),
        display_mode=m.get("displayMode"),
        is_number_column_enabled=m.get("isNumberColumnEnabled"),
        width=m.get("width"),
    )


def _parse_table_row(
    cells: list[dict[str, Any]],
    header: bool = False,
    first_col_header: bool = False,
) -> ast.TableRow:
    result: list[ast.TableCell | ast.TableHeader] = []
    skip = 0
    for idx, cell_token in enumerate(cells):
        if skip > 0:
            skip -= 1
            continue

        children = cell_token.get("children", [])
        cell_meta, content_children = _extract_cell_meta(children)
        content = _parse_cell_content(content_children)

        colspan = cell_meta.get("colspan")
        if colspan and colspan > 1:
            skip = colspan - 1

        is_header = header or (first_col_header and idx == 0)
        cls = ast.TableHeader if is_header else ast.TableCell
        result.append(
            cls(
                content=content,
                colspan=colspan,
                rowspan=cell_meta.get("rowspan"),
                background=cell_meta.get("background"),
            )
        )
    return ast.TableRow(content=result)


def _extract_cell_meta(
    children: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Extract <div adf="cell"> metadata from cell children. Returns (meta, remaining)."""
    if not children:
        return {}, children
    first = children[0]
    if first.get("type") == "inline_html":
        raw = first.get("raw", "")
        tag, attrs, _ = _parse_tag(raw)
        if tag == "div" and attrs.get("adf") == "cell":
            params = _get_params(attrs)
            # Skip the closing </div> too
            remaining = [
                c
                for c in children[1:]
                if not (
                    c.get("type") == "inline_html"
                    and c.get("raw", "").strip() == "</div>"
                )
            ]
            return params, remaining
    return {}, children


# ── Block HTML element parsers ────────────────────────────────────────────────


def _parse_panel(
    attrs: dict[str, str], inner_tokens: list[dict[str, Any]]
) -> ast.Panel:
    p = _get_params(attrs)
    return ast.Panel(
        panel_type=p.get("panelType", "info"),
        content=_parse_panel_children(inner_tokens),
        panel_icon=p.get("panelIcon"),
        panel_icon_id=p.get("panelIconId"),
        panel_icon_text=p.get("panelIconText"),
        panel_color=p.get("panelColor"),
    )


def _extract_summary(tokens: list[dict[str, Any]]) -> str | None:
    """Extract <summary>title</summary> from block_html tokens."""
    for token in tokens:
        if token.get("type") == "block_html":
            raw = token.get("raw", "").strip()
            m = re.match(r"<summary>(.*?)</summary>", raw, re.DOTALL)
            if m:
                return m.group(1)
    return None


def _strip_summary_token(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove the block_html token containing <summary>."""
    return [
        t
        for t in tokens
        if not (t.get("type") == "block_html" and "<summary>" in t.get("raw", ""))
    ]


def _parse_expand(
    adf_type: str, attrs: dict[str, str], inner_tokens: list[dict[str, Any]]
) -> ast.Expand | ast.NestedExpand:
    p = _get_params(attrs)
    title = _extract_summary(inner_tokens) or p.get("title")
    content_tokens = _strip_summary_token(inner_tokens)
    if adf_type == "nestedExpand":
        return ast.NestedExpand(
            content=_parse_nested_expand_children(content_tokens),
            title=title,
        )
    return ast.Expand(
        content=_parse_expand_children(content_tokens),
        title=title,
    )


def _parse_decision_list(
    attrs: dict[str, str], inner_tokens: list[dict[str, Any]]
) -> ast.DecisionList:
    items: list[ast.DecisionItem] = []
    for token in inner_tokens:
        if token.get("type") != "block_html":
            continue
        raw = token.get("raw", "").strip()
        for m in re.finditer(r"<li\s+([^>]*)>(.*?)</li>", raw, re.DOTALL):
            li_attr_str, li_content = m.group(1), m.group(2)
            _, li_attrs, _ = _parse_tag(f"<li {li_attr_str}>")
            li_params = _get_params(li_attrs)
            items.append(
                ast.DecisionItem(
                    state=li_params.get("state", ""),
                    content=[ast.Text(text=li_content)],
                )
            )
    return ast.DecisionList(content=items)


def _parse_task_list_html(
    attrs: dict[str, str], inner_tokens: list[dict[str, Any]]
) -> ast.TaskList:
    items: list[ast.TaskListContent] = []
    for token in inner_tokens:
        if token.get("type") != "block_html":
            continue
        raw = token.get("raw", "").strip()
        for m in re.finditer(r"<li\s+([^>]*)>(.*?)</li>", raw, re.DOTALL):
            li_attr_str, li_content = m.group(1), m.group(2)
            _, li_attrs, _ = _parse_tag(f"<li {li_attr_str}>")
            li_params = _get_params(li_attrs)
            state = li_params.get("state", "TODO")
            items.append(
                ast.TaskItem(
                    state="DONE" if state == "DONE" else "TODO",
                    content=[ast.Text(text=li_content)],
                )
            )
    return ast.TaskList(content=items)


def _parse_media_single(
    attrs: dict[str, str], inner_tokens: list[dict[str, Any]]
) -> ast.MediaSingle:
    p = _get_params(attrs)
    content: list[ast.Media | ast.Caption] = []
    # inner_tokens contain a paragraph with inline HTML
    for token in inner_tokens:
        if token.get("type") != "paragraph":
            continue
        children = token.get("children", [])
        normalized = _normalize_inlines(children)
        for item in normalized:
            if item.get("_kind") != "inline_html":
                continue
            item_attrs = item.get("attrs", {})
            item_adf = item_attrs.get("adf", "")
            if item_adf == "media":
                content.append(_parse_media(item_attrs))
            elif item_adf == "caption":
                inner = item.get("inner", [])
                caption_text = _inline_content_text(inner)
                content.append(ast.Caption(content=[ast.Text(text=caption_text)]))
    return ast.MediaSingle(
        content=content,
        width=p.get("width"),
        layout=p.get("layout"),
        width_type=p.get("widthType"),
    )


def _parse_media(attrs: dict[str, str]) -> ast.Media:
    p = _get_params(attrs)
    return ast.Media(
        type=p.get("type", "file"),
        id=p.get("id"),
        alt=p.get("alt"),
        collection=p.get("collection"),
        height=p.get("height"),
        width=p.get("width"),
        url=p.get("url"),
    )


def _parse_media_group(
    attrs: dict[str, str], inner_tokens: list[dict[str, Any]]
) -> ast.MediaGroup:
    medias: list[ast.Media] = []
    for token in inner_tokens:
        if token.get("type") != "paragraph":
            continue
        for item in _normalize_inlines(token.get("children", [])):
            if (
                item.get("_kind") == "inline_html"
                and item.get("attrs", {}).get("adf") == "media"
            ):
                medias.append(_parse_media(item["attrs"]))
    return ast.MediaGroup(content=medias)


def _parse_layout_section(
    attrs: dict[str, str], inner_tokens: list[dict[str, Any]]
) -> ast.LayoutSection:
    columns: list[ast.LayoutColumn] = []
    # inner_tokens contain block_html for <div adf="layoutColumn"> and </div>
    normalized = _normalize_blocks(inner_tokens)
    for block in normalized:
        if (
            block.get("_kind") == "html"
            and block.get("attrs", {}).get("adf") == "layoutColumn"
        ):
            columns.append(_parse_layout_column(block["attrs"], block["inner"]))
    return ast.LayoutSection(content=columns)


def _parse_layout_column(
    attrs: dict[str, str], inner_tokens: list[dict[str, Any]]
) -> ast.LayoutColumn:
    p = _get_params(attrs)
    return ast.LayoutColumn(
        width=p.get("width", 0),
        content=_parse_layout_column_children(inner_tokens),
    )


def _parse_block_card(
    adf_type: str, attrs: dict[str, str]
) -> ast.BlockCard | ast.EmbedCard:
    p = _get_params(attrs)
    if adf_type == "embedCard":
        return ast.EmbedCard(
            url=p.get("url", ""),
            layout=p.get("layout", "center"),
            width=p.get("width"),
            original_height=p.get("originalHeight"),
            original_width=p.get("originalWidth"),
        )
    return ast.BlockCard(
        url=p.get("url"),
        layout=p.get("layout"),
        width=p.get("width"),
        data=p.get("data"),
        datasource=p.get("datasource"),
    )


# ── <data> element parsing ────────────────────────────────────────────────────


def _parse_data_element(attrs: dict[str, str]) -> ast.Node | None:
    """Parse <data adf="type" params='...'> → Extension, SyncBlock, etc."""
    adf_type = attrs.get("adf", "")
    p = _get_params(attrs)
    match adf_type:
        case "extension":
            return ast.Extension(
                extension_key=p.get("extensionKey", ""),
                extension_type=p.get("extensionType", ""),
                parameters=p.get("parameters"),
                text=p.get("text"),
                layout=p.get("layout"),
            )
        case "bodiedExtension":
            return ast.BodiedExtension(
                extension_key=p.get("extensionKey", ""),
                extension_type=p.get("extensionType", ""),
                content=p.get("content", []),
                parameters=p.get("parameters"),
                text=p.get("text"),
                layout=p.get("layout"),
            )
        case "syncBlock":
            return ast.SyncBlock(resource_id=p.get("resourceId", ""))
        case "bodiedSyncBlock":
            return ast.BodiedSyncBlock(
                resource_id=p.get("resourceId", ""),
                content=p.get("content", []),
            )
        case _:
            return None


def _parse_block_marks(params: dict[str, Any]) -> list[ast.Mark]:
    """Parse block marks from <data adf="marks"> params."""
    marks: list[ast.Mark] = []
    if "align" in params:
        marks.append(ast.AlignmentMark(align=params["align"]))
    if "indent" in params:
        marks.append(ast.IndentationMark(level=params["indent"]))
    if "breakoutMode" in params:
        marks.append(
            ast.BreakoutMark(
                mode=params["breakoutMode"], width=params.get("breakoutWidth")
            )
        )
    if "dataConsumerSources" in params:
        marks.append(ast.DataConsumerMark(sources=params["dataConsumerSources"]))
    if "borderSize" in params:
        marks.append(
            ast.BorderMark(
                size=params["borderSize"], color=params.get("borderColor", "")
            )
        )
    return marks


# ── Inline parsing ────────────────────────────────────────────────────────────


def _find_inline_close(
    tokens: list[dict[str, Any]], start: int, tag: str
) -> int | None:
    depth = 1
    for i in range(start, len(tokens)):
        if tokens[i].get("type") == "inline_html":
            raw = tokens[i].get("raw", "")
            t, _, closing = _parse_tag(raw)
            if t == tag:
                if closing:
                    depth -= 1
                    if depth == 0:
                        return i
                else:
                    depth += 1
    return None


def _normalize_inlines(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize inline token stream.

    - inline_html pairs → {"_kind": "inline_html", "tag", "adf_type", "attrs", "inner"}
    - void inline_html → same with "inner": []
    - adf-less HTML → removed
    - other tokens → pass through
    """
    result: list[dict[str, Any]] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token.get("type") != "inline_html":
            result.append(token)
            i += 1
            continue

        raw = token.get("raw", "")
        tag, attrs, closing = _parse_tag(raw)

        if closing or not _has_adf(attrs):
            i += 1
            continue

        adf_type = attrs.get("adf", "")

        close_idx = _find_inline_close(tokens, i + 1, tag)
        if close_idx is not None:
            result.append(
                {
                    "_kind": "inline_html",
                    "tag": tag,
                    "adf_type": adf_type,
                    "attrs": attrs,
                    "inner": tokens[i + 1 : close_idx],
                }
            )
            i = close_idx + 1
            continue

        i += 1

    return result


def _parse_inlines(tokens: list[dict[str, Any]]) -> list[ast.Inline]:
    result: list[ast.Inline] = []
    for token in _normalize_inlines(tokens):
        if token.get("_kind") == "inline_html":
            result.append(
                _parse_inline_html(
                    token["tag"], token["adf_type"], token["attrs"], token["inner"]
                )
            )
        else:
            result.extend(_flatten_marks(token, []))
    return result


# ── Mark flattening ───────────────────────────────────────────────────────────


def _flatten_children(
    children: list[dict[str, Any]], marks: list[ast.Mark]
) -> list[ast.Inline]:
    result: list[ast.Inline] = []
    for child in children:
        result.extend(_flatten_marks(child, marks))
    return result


def _flatten_marks(
    token: dict[str, Any], parent_marks: list[ast.Mark]
) -> list[ast.Inline]:
    t = token.get("type", "")
    match t:
        case "strong":
            return _flatten_children(
                token.get("children", []), [*parent_marks, ast.StrongMark()]
            )
        case "emphasis":
            return _flatten_children(
                token.get("children", []), [*parent_marks, ast.EmMark()]
            )
        case "strikethrough":
            return _flatten_children(
                token.get("children", []), [*parent_marks, ast.StrikeMark()]
            )
        case "codespan":
            marks: list[ast.Mark] = [*parent_marks, ast.CodeMark()]
            return [ast.Text(text=token.get("raw", ""), marks=marks)]
        case "link":
            link_attrs = token.get("attrs", {})
            href = link_attrs.get("url", "") or link_attrs.get("link", "")
            title = link_attrs.get("title")
            link_marks: list[ast.Mark] = [
                *parent_marks,
                ast.LinkMark(href=href, title=title),
            ]
            return _flatten_children(token.get("children", []), link_marks)
        case "text":
            text = token.get("raw", "")
            if parent_marks:
                return [ast.Text(text=text, marks=parent_marks)]
            return [ast.Text(text=text)]
        case "softbreak":
            return [ast.Text(text=" ")]
        case "linebreak":
            return [ast.HardBreak()]
        case _:
            children = token.get("children", [])
            if children:
                return _flatten_children(children, parent_marks)
            return []


# ── Inline HTML element parsing ───────────────────────────────────────────────


def _inline_content_text(tokens: list[dict[str, Any]]) -> str:
    return "".join(t.get("raw", "") for t in tokens)


def _parse_inline_html(
    tag: str, adf_type: str, attrs: dict[str, str], content_tokens: list[dict[str, Any]]
) -> ast.Inline:
    content = _inline_content_text(content_tokens)
    match adf_type:
        case "mention":
            return _parse_mention(attrs, content)
        case "emoji":
            return _parse_emoji(attrs, content)
        case "date":
            return _parse_date(attrs)
        case "status":
            return _parse_status(attrs, content)
        case "inlineCard":
            return _parse_inline_card(attrs)
        case "placeholder":
            return _parse_placeholder(content)
        case "mediaInline":
            return _parse_media_inline(attrs)
        case "inlineExtension":
            return _parse_inline_data(attrs)
        case "underline" | "textColor" | "bgColor" | "subSup" | "annotation":
            return _parse_html_mark(tag, adf_type, attrs, content_tokens, content)
        case _:
            return ast.Text(text=content)


def _parse_html_mark(
    tag: str,
    adf_type: str,
    attrs: dict[str, str],
    content_tokens: list[dict[str, Any]],
    content: str,
) -> ast.Inline:
    """Parse HTML mark element → Text with mark attached."""
    mark: ast.Mark
    match adf_type:
        case "underline":
            mark = ast.UnderlineMark()
        case "textColor":
            mark = ast.TextColorMark(color=_get_params(attrs).get("color", ""))
        case "bgColor":
            mark = ast.BackgroundColorMark(color=_get_params(attrs).get("color", ""))
        case "subSup":
            mark = ast.SubSupMark(type="sub" if tag == "sub" else "sup")
        case "annotation":
            p = _get_params(attrs)
            mark = ast.AnnotationMark(
                id=p.get("id", ""),
                annotation_type=p.get("annotationType", "inlineComment"),
            )
        case _:
            return ast.Text(text=content)

    inlines = _parse_inlines(content_tokens)
    for node in inlines:
        if isinstance(node, ast.Text):
            node.marks = [*node.marks, mark]
    return inlines[0] if inlines else ast.Text(text=content)


def _parse_mention(attrs: dict[str, str], content: str) -> ast.Mention:
    p = _get_params(attrs)
    text = content.removeprefix("@") or None
    return ast.Mention(
        id=p.get("id", ""),
        text=text,
        access_level=p.get("accessLevel"),
        user_type=p.get("userType"),
    )


def _parse_emoji(attrs: dict[str, str], content: str) -> ast.Emoji:
    p = _get_params(attrs)
    short_name = p.get("shortName", "")
    text = content if content != short_name else None
    return ast.Emoji(short_name=short_name, id=p.get("id"), text=text)


def _parse_date(attrs: dict[str, str]) -> ast.Date:
    return ast.Date(timestamp=attrs.get("datetime", ""))


def _parse_status(attrs: dict[str, str], content: str) -> ast.Status:
    p = _get_params(attrs)
    return ast.Status(
        text=content or p.get("text", ""),
        color=p.get("color", "neutral"),
        style=p.get("style"),
    )


def _parse_inline_card(attrs: dict[str, str]) -> ast.InlineCard:
    p = _get_params(attrs) if "params" in attrs else {}
    return ast.InlineCard(url=attrs.get("href"), data=p.get("data"))


def _parse_placeholder(content: str) -> ast.Placeholder:
    return ast.Placeholder(text=content)


def _parse_media_inline(attrs: dict[str, str]) -> ast.MediaInline:
    p = _get_params(attrs)
    return ast.MediaInline(
        id=p.get("id", ""),
        collection=p.get("collection", ""),
        type=p.get("type"),
        alt=p.get("alt"),
        width=p.get("width"),
        height=p.get("height"),
        data=p.get("data"),
    )


def _parse_inline_data(attrs: dict[str, str]) -> ast.InlineExtension:
    p = _get_params(attrs)
    return ast.InlineExtension(
        extension_key=p.get("extensionKey", ""),
        extension_type=p.get("extensionType", ""),
        parameters=p.get("parameters"),
        text=p.get("text"),
    )


# ── Image (raw MD, solo only) ─────────────────────────────────────────────────


def _parse_image(token: dict[str, Any]) -> ast.MediaSingle:
    """![alt](url) (solo paragraph) → MediaSingle > Media(type="external")."""
    attrs = token.get("attrs", {})
    url = attrs.get("url", "") or attrs.get("src", "")
    alt = attrs.get("alt", "")
    if not alt:
        children = token.get("children", [])
        alt = "".join(c.get("raw", "") for c in children if c.get("type") == "text")
    return ast.MediaSingle(
        content=[ast.Media(type="external", url=url, alt=alt or None)],
    )


# ── Cell content parsing ──────────────────────────────────────────────────────


def _parse_cell_content(tokens: list[dict[str, Any]]) -> list[ast.TableCellContent]:
    """Parse cell inline tokens → block AST nodes (reverse of cell rendering)."""
    if not tokens:
        return [ast.Paragraph(content=[])]
    # Simple text → single Paragraph (bare text)
    inlines = _parse_inlines(tokens)
    return [ast.Paragraph(content=inlines)]
