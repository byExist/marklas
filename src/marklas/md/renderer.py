"""Union AST → Markdown rendering."""

from __future__ import annotations

import json
import re
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Generator

from marklas.nodes import blocks, inlines

# ── Table-cell markup constants ──────────────────────────────────────

CELL_BLOCK_SEP = "<br>"  # separates blocks inside a table cell
CELL_HARD_BREAK = "<br/>"  # hard break (line break) inside a table cell

_MD_ESCAPE_TABLE = str.maketrans(
    {
        "\\": "\\\\",
        "*": "\\*",
        "_": "\\_",
        "[": "\\[",
        "]": "\\]",
        "`": "\\`",
        "~": "\\~",
    }
)

# ── Rendering context ────────────────────────────────────────────────

_in_table_ctx: ContextVar[bool] = ContextVar("in_table", default=False)


@contextmanager
def _table_context() -> Generator[None]:
    token = _in_table_ctx.set(True)
    try:
        yield
    finally:
        _in_table_ctx.reset(token)


def _in_table() -> bool:
    return _in_table_ctx.get()


# ── Entry point ──────────────────────────────────────────────────────


def render(doc: blocks.Document, *, annotate: bool = True) -> str:
    parts = _render_doc_children(doc.children, annotate)
    return "\n\n".join(parts) + "\n" if parts else ""


# ── Doc dispatch ─────────────────────────────────────────────────────


def _render_doc_children(children: list[blocks.DocChild], annotate: bool) -> list[str]:
    return [_render_doc_child(c, annotate) for c in children]


def _render_doc_child(node: blocks.DocChild, annotate: bool) -> str:
    match node:
        case blocks.Paragraph():
            return _render_paragraph(node, annotate)
        case blocks.Heading():
            return _render_heading(node, annotate)
        case blocks.CodeBlock():
            return _render_code_block(node, annotate)
        case blocks.BlockQuote():
            return _render_blockquote(node, annotate)
        case blocks.ThematicBreak():
            return _render_thematic_break(node, annotate)
        case blocks.BulletList():
            return _render_bullet_list(node, annotate)
        case blocks.OrderedList():
            return _render_ordered_list(node, annotate)
        case blocks.Table():
            return _render_table(node, annotate)
        case blocks.Panel():
            return _render_panel(node, annotate)
        case blocks.Expand():
            return _render_expand(node, annotate)
        case blocks.TaskList():
            return _render_task_list(node, annotate)
        case blocks.DecisionList():
            return _render_decision_list(node, annotate)
        case blocks.LayoutSection():
            return _render_layout_section(node, annotate)
        case blocks.MediaSingle():
            return _render_media_single(node, annotate)
        case blocks.MediaGroup():
            return _render_media_group(node, annotate)
        case blocks.BlockCard():
            return _render_block_card(node, annotate)
        case blocks.EmbedCard():
            return _render_embed_card(node, annotate)
        case blocks.Extension():
            return _render_extension(node, annotate)
        case blocks.BodiedExtension():
            return _render_bodied_extension(node, annotate)
        case blocks.SyncBlock():
            return _render_sync_block(node, annotate)
        case blocks.BodiedSyncBlock():
            return _render_bodied_sync_block(node, annotate)


# ── Shared helpers ───────────────────────────────────────────────────


def _build_media_dict(media: blocks.Media) -> dict[str, Any]:
    d: dict[str, Any] = {}
    if media.media_type != "file":
        d["mediaType"] = media.media_type
    if media.id is not None:
        d["id"] = media.id
    if media.collection is not None:
        d["collection"] = media.collection
    if media.url is not None:
        d["url"] = media.url
    if media.alt is not None:
        d["alt"] = media.alt
    if media.width is not None:
        d["width"] = media.width
    if media.height is not None:
        d["height"] = media.height
    return d


def _to_tag(node: blocks.Block | inlines.Inline) -> str:
    name = type(node).__name__
    return name[0].lower() + name[1:]


# ── Block renderers ──────────────────────────────────────────────────


def _annotate_block(
    node: blocks.Block, content: str, annotate: bool, **attrs: Any
) -> str:
    if not annotate:
        return content
    tag = _to_tag(node)
    filtered = {k: v for k, v in attrs.items() if v is not None}
    attr_json = f" {json.dumps(filtered, ensure_ascii=False)}" if filtered else ""
    if _in_table():
        return f"<!-- adf:{tag}{attr_json} -->{content}<!-- /adf:{tag} -->"
    return f"<!-- adf:{tag}{attr_json} -->\n{content}\n<!-- /adf:{tag} -->"


def _render_paragraph(node: blocks.Paragraph, annotate: bool) -> str:
    content = _render_inlines(node.children, annotate)
    if node.alignment or node.indentation:
        return _annotate_block(
            node,
            content,
            annotate,
            align=node.alignment,
            indentation=node.indentation,
        )
    if _in_table():
        return content.strip()
    if not content and annotate:
        return _annotate_block(node, content, annotate)
    return content


def _render_heading(node: blocks.Heading, annotate: bool) -> str:
    if _in_table():
        tag = f"h{node.level}"
        inner = _render_inlines(node.children, annotate)
        return f"<{tag}>{inner}</{tag}>"
    content = "#" * node.level + " " + _render_inlines(node.children, annotate)
    if node.alignment or node.indentation:
        return _annotate_block(
            node,
            content,
            annotate,
            align=node.alignment,
            indentation=node.indentation,
        )
    return content


_BACKTICK_RUN_RE = re.compile(r"`+")


def _code_fence(code: str) -> str:
    runs = _BACKTICK_RUN_RE.findall(code)
    max_len = max((len(r) for r in runs), default=0)
    return "`" * max(3, max_len + 1)


def _render_code_block(node: blocks.CodeBlock, annotate: bool) -> str:
    if _in_table():
        code = node.code.replace("\n", CELL_BLOCK_SEP)
        html = f"<code>{code}</code>"
        if node.language:
            return _annotate_block(node, html, annotate, language=node.language)
        return html
    lang = node.language or ""
    fence = _code_fence(node.code)
    return f"{fence}{lang}\n{node.code}\n{fence}"


def _render_blockquote(node: blocks.BlockQuote, annotate: bool) -> str:
    if _in_table():
        inner = CELL_BLOCK_SEP.join(
            _render_blockquote_children(node.children, annotate)
        )
        return f"<blockquote>{inner}</blockquote>"
    inner = "\n\n".join(_render_blockquote_children(node.children, annotate))
    return "\n".join(f"> {line}" if line else ">" for line in inner.split("\n"))


def _render_thematic_break(node: blocks.ThematicBreak, annotate: bool) -> str:
    return "<hr>" if _in_table() else "---"


def _render_bullet_list(node: blocks.BulletList, annotate: bool) -> str:
    if _in_table():
        return _render_cell_list(node, annotate)
    items: list[str] = []
    for item in node.items:
        if item.checked is not None:
            marker = "- [x] " if item.checked else "- [ ] "
        else:
            marker = "- "
        body = _render_list_item_body(item.children, node.tight, annotate)
        items.append(marker + body)
    sep = "\n\n" if not node.tight else "\n"
    return sep.join(items)


def _render_ordered_list(node: blocks.OrderedList, annotate: bool) -> str:
    if _in_table():
        return _render_cell_list(node, annotate)
    items: list[str] = []
    for i, item in enumerate(node.items):
        num = node.start + i
        body = _render_list_item_body(item.children, node.tight, annotate)
        items.append(f"{num}. {body}")
    sep = "\n\n" if not node.tight else "\n"
    return sep.join(items)


def _render_list_item_body(
    children: list[blocks.ListItemChild], tight: bool, annotate: bool
) -> str:
    if tight and len(children) == 1 and isinstance(children[0], blocks.Paragraph):
        return _render_inlines(children[0].children, annotate)
    parts: list[str] = []
    for child in children:
        if _is_whitespace_only_paragraph(child):
            continue
        rendered = _render_listitem_child(child, annotate)
        parts.append(rendered)
    body = "\n".join(parts)
    lines = body.split("\n")
    if len(lines) > 1:
        return (
            lines[0] + "\n" + "\n".join("    " + ln if ln else "" for ln in lines[1:])
        )
    return body


def _is_whitespace_only_paragraph(node: blocks.ListItemChild) -> bool:
    return (
        isinstance(node, blocks.Paragraph)
        and len(node.children) > 0
        and all(
            isinstance(c, inlines.Text) and not c.text.strip() for c in node.children
        )
    )


def _render_cell_list(
    node: blocks.BulletList | blocks.OrderedList, annotate: bool
) -> str:
    tag = "ol" if isinstance(node, blocks.OrderedList) else "ul"
    start_attr = (
        f' start="{node.start}"'
        if isinstance(node, blocks.OrderedList) and node.start != 1
        else ""
    )
    items: list[str] = []
    for item in node.items:
        body = CELL_BLOCK_SEP.join(_render_listitem_children(item.children, annotate))
        items.append(f"<li>{body}</li>")
    return f"<{tag}{start_attr}>{''.join(items)}</{tag}>"


def _render_table(node: blocks.Table, annotate: bool) -> str:
    col_count = len(node.head) if node.head else max(len(row) for row in node.body)

    def header() -> str:
        if node.head:
            cells = [_render_table_cell(cell, annotate) for cell in node.head]
        else:
            cells = [""] * col_count
        return "| " + " | ".join(cells) + " |"

    def delimiter() -> str:
        delimiters: list[str] = []
        for i in range(col_count):
            align = node.alignments[i] if i < len(node.alignments) else None
            match align:
                case "center":
                    delimiters.append(":---:")
                case "right":
                    delimiters.append("---:")
                case "left":
                    delimiters.append(":---")
                case _:
                    delimiters.append("---")
        return "| " + " | ".join(delimiters) + " |"

    def row(cells_row: list[blocks.TableCell]) -> str:
        cells = [_render_table_cell(cell, annotate) for cell in cells_row]
        while len(cells) < col_count:
            cells.append("")
        return "| " + " | ".join(cells) + " |"

    with _table_context():
        table_md = "\n".join([header(), delimiter(), *(row(r) for r in node.body)])
    attrs = _collect_table_attrs(node)
    if attrs:
        return _annotate_block(node, table_md, annotate, **attrs)
    return table_md


def _render_table_cell(cell: blocks.TableCell, annotate: bool) -> str:
    parts = _render_tablecell_children(cell.children, annotate)
    return _escape_cell_pipe(CELL_BLOCK_SEP.join(parts))


def _escape_cell_pipe(text: str) -> str:
    return text.replace("|", "\\|")


def _collect_table_attrs(node: blocks.Table) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    if node.display_mode is not None:
        attrs["displayMode"] = node.display_mode
    if node.is_number_column_enabled is not None:
        attrs["isNumberColumnEnabled"] = node.is_number_column_enabled
    if node.layout is not None:
        attrs["layout"] = node.layout
    if node.width is not None:
        attrs["width"] = node.width
    cell_attrs = _collect_cell_attrs(node)
    if cell_attrs:
        attrs["cells"] = cell_attrs
    return attrs


def _collect_cell_attrs(node: blocks.Table) -> list[list[Any]] | None:
    all_rows = [node.head, *node.body]
    result: list[list[Any]] = []
    has_any = False
    for row in all_rows:
        row_attrs: list[Any] = []
        for cell in row:
            cell_attr = _collect_single_cell_attr(cell)
            if cell_attr is not None:
                has_any = True
            row_attrs.append(cell_attr)
        result.append(row_attrs)
    return result if has_any else None


def _collect_single_cell_attr(cell: blocks.TableCell) -> Any:
    is_header = isinstance(cell, blocks.TableHeader)
    has_special = (
        (cell.colspan is not None and cell.colspan != 1)
        or (cell.rowspan is not None and cell.rowspan != 1)
        or cell.background
        or is_header
    )
    if has_special:
        attrs: dict[str, Any] = {}
        if cell.colspan is not None and cell.colspan != 1:
            attrs["colspan"] = cell.colspan
        if cell.rowspan is not None and cell.rowspan != 1:
            attrs["rowspan"] = cell.rowspan
        if cell.col_width:
            attrs["colwidth"] = cell.col_width
        if cell.background:
            attrs["background"] = cell.background
        if is_header:
            attrs["header"] = True
        return attrs
    if cell.col_width:
        return cell.col_width
    return None


# ── Blockquote dispatch ──────────────────────────────────────────────


def _render_blockquote_children(
    children: list[blocks.BlockQuoteChild], annotate: bool
) -> list[str]:
    return [_render_blockquote_child(c, annotate) for c in children]


def _render_blockquote_child(node: blocks.BlockQuoteChild, annotate: bool) -> str:
    match node:
        case blocks.Paragraph():
            return _render_paragraph(node, annotate)
        case blocks.BulletList():
            return _render_bullet_list(node, annotate)
        case blocks.OrderedList():
            return _render_ordered_list(node, annotate)
        case blocks.CodeBlock():
            return _render_code_block(node, annotate)
        case blocks.MediaGroup():
            return _render_media_group(node, annotate)
        case blocks.MediaSingle():
            return _render_media_single(node, annotate)
        case blocks.Extension():
            return _render_extension(node, annotate)


# ── ListItem dispatch ────────────────────────────────────────────────


def _render_listitem_children(
    children: list[blocks.ListItemChild], annotate: bool
) -> list[str]:
    return [_render_listitem_child(c, annotate) for c in children]


def _render_listitem_child(node: blocks.ListItemChild, annotate: bool) -> str:
    match node:
        case blocks.Paragraph():
            return _render_paragraph(node, annotate)
        case blocks.BulletList():
            return _render_bullet_list(node, annotate)
        case blocks.OrderedList():
            return _render_ordered_list(node, annotate)
        case blocks.CodeBlock():
            return _render_code_block(node, annotate)
        case blocks.MediaSingle():
            return _render_media_single(node, annotate)
        case blocks.Extension():
            return _render_extension(node, annotate)
        case blocks.TaskList():
            return _render_task_list(node, annotate)


# ── Annotated block renderers ────────────────────────────────────────


def _render_panel(node: blocks.Panel, annotate: bool) -> str:
    if _in_table():
        inner = CELL_BLOCK_SEP.join(_render_panel_children(node.children, annotate))
        content = f"<blockquote>{inner}</blockquote>"
    else:
        content = "\n\n".join(_render_panel_children(node.children, annotate))
    return _annotate_block(
        node,
        content,
        annotate,
        panelType=node.panel_type,
        panelIcon=node.panel_icon,
        panelIconId=node.panel_icon_id,
        panelIconText=node.panel_icon_text,
        panelColor=node.panel_color,
    )


def _render_expand(node: blocks.Expand, annotate: bool) -> str:
    if _in_table():
        inner = CELL_BLOCK_SEP.join(_render_expand_children(node.children, annotate))
        content = f"<blockquote>{inner}</blockquote>"
    else:
        content = "\n\n".join(_render_expand_children(node.children, annotate))
    return _annotate_block(node, content, annotate, title=node.title)


def _render_nested_expand(node: blocks.NestedExpand, annotate: bool) -> str:
    if _in_table():
        inner = CELL_BLOCK_SEP.join(
            _render_nested_expand_children(node.children, annotate)
        )
        content = f"<blockquote>{inner}</blockquote>"
    else:
        content = "\n\n".join(_render_nested_expand_children(node.children, annotate))
    return _annotate_block(node, content, annotate, title=node.title)


def _render_task_list(node: blocks.TaskList, annotate: bool) -> str:
    if _in_table():
        items: list[str] = []
        for item in node.items:
            marker = "[x] " if item.state == "DONE" else "[ ] "
            items.append(f"<li>{marker}{_render_inlines(item.children, annotate)}</li>")
        content = f"<ul>{''.join(items)}</ul>"
    else:
        items = []
        for item in node.items:
            marker = "- [x] " if item.state == "DONE" else "- [ ] "
            items.append(marker + _render_inlines(item.children, annotate))
        content = "\n".join(items)
    return _annotate_block(node, content, annotate)


def _render_decision_list(node: blocks.DecisionList, annotate: bool) -> str:
    if _in_table():
        items: list[str] = []
        for item in node.items:
            marker = "[x] " if item.state == "DECIDED" else "[ ] "
            items.append(f"<li>{marker}{_render_inlines(item.children, annotate)}</li>")
        content = f"<ul>{''.join(items)}</ul>"
    else:
        items = []
        for item in node.items:
            marker = "- [x] " if item.state == "DECIDED" else "- [ ] "
            items.append(marker + _render_inlines(item.children, annotate))
        content = "\n".join(items)
    return _annotate_block(node, content, annotate)


def _render_layout_section(node: blocks.LayoutSection, annotate: bool) -> str:
    parts: list[str] = []
    for col in node.columns:
        inner = "\n\n".join(_render_layoutcolumn_children(col.children, annotate))
        parts.append(_annotate_block(col, inner, annotate, width=col.width))
    return _annotate_block(node, "\n\n".join(parts), annotate)


def _render_media_single(node: blocks.MediaSingle, annotate: bool) -> str:
    if node.media.media_type == "external" and node.media.url:
        fallback = f"![{node.media.alt or ''}]({node.media.url})"
    else:
        alt = node.media.alt or "attachment"
        fallback = f"`\U0001f4ce {alt}`"
    media = _build_media_dict(node.media)
    return _annotate_block(
        node,
        fallback,
        annotate,
        layout=node.layout,
        width=node.width,
        widthType=node.width_type,
        media=media,
    )


def _render_media_group(node: blocks.MediaGroup, annotate: bool) -> str:
    fallbacks: list[str] = []
    for m in node.media_list:
        if m.media_type == "external" and m.url:
            fallbacks.append(f"![{m.alt or ''}]({m.url})")
        else:
            alt = m.alt or "attachment"
            fallbacks.append(f"`\U0001f4ce {alt}`")
    media_list = [_build_media_dict(m) for m in node.media_list]
    sep = CELL_BLOCK_SEP if _in_table() else "\n"
    return _annotate_block(node, sep.join(fallbacks), annotate, mediaList=media_list)


def _render_block_card(node: blocks.BlockCard, annotate: bool) -> str:
    fallback = f"[{node.url}]({node.url})" if node.url else "`\U0001f517 card link`"
    return _annotate_block(node, fallback, annotate, url=node.url, data=node.data)


def _render_embed_card(node: blocks.EmbedCard, annotate: bool) -> str:
    fallback = f"[{node.url}]({node.url})"
    return _annotate_block(
        node,
        fallback,
        annotate,
        url=node.url,
        layout=node.layout,
        width=node.width,
        originalWidth=node.original_width,
        originalHeight=node.original_height,
    )


def _extension_fallback(raw: dict[str, Any]) -> str:
    key = raw.get("attrs", {}).get("extensionKey", "")
    label = key or "Confluence macro"
    return f"`\u2699 {label}`"


def _render_extension(node: blocks.Extension, annotate: bool) -> str:
    content = _extension_fallback(node.raw)
    if annotate:
        return _annotate_block(node, content, annotate, raw=node.raw)
    return content


def _render_bodied_extension(node: blocks.BodiedExtension, annotate: bool) -> str:
    content = _extension_fallback(node.raw)
    if annotate:
        return _annotate_block(node, content, annotate, raw=node.raw)
    return content


def _render_sync_block(node: blocks.SyncBlock, annotate: bool) -> str:
    content = _extension_fallback(node.raw)
    if annotate:
        return _annotate_block(node, content, annotate, raw=node.raw)
    return content


def _render_bodied_sync_block(node: blocks.BodiedSyncBlock, annotate: bool) -> str:
    content = _extension_fallback(node.raw)
    if annotate:
        return _annotate_block(node, content, annotate, raw=node.raw)
    return content


# ── Panel dispatch ───────────────────────────────────────────────────


def _render_panel_children(
    children: list[blocks.PanelChild], annotate: bool
) -> list[str]:
    return [_render_panel_child(c, annotate) for c in children]


def _render_panel_child(node: blocks.PanelChild, annotate: bool) -> str:
    match node:
        case blocks.Paragraph():
            return _render_paragraph(node, annotate)
        case blocks.Heading():
            return _render_heading(node, annotate)
        case blocks.BulletList():
            return _render_bullet_list(node, annotate)
        case blocks.OrderedList():
            return _render_ordered_list(node, annotate)
        case blocks.CodeBlock():
            return _render_code_block(node, annotate)
        case blocks.TaskList():
            return _render_task_list(node, annotate)
        case blocks.DecisionList():
            return _render_decision_list(node, annotate)
        case blocks.ThematicBreak():
            return _render_thematic_break(node, annotate)
        case blocks.MediaGroup():
            return _render_media_group(node, annotate)
        case blocks.MediaSingle():
            return _render_media_single(node, annotate)
        case blocks.BlockCard():
            return _render_block_card(node, annotate)
        case blocks.Extension():
            return _render_extension(node, annotate)


# ── Expand dispatch ──────────────────────────────────────────────────


def _render_expand_children(
    children: list[blocks.ExpandChild], annotate: bool
) -> list[str]:
    return [_render_expand_child(c, annotate) for c in children]


def _render_expand_child(node: blocks.ExpandChild, annotate: bool) -> str:
    match node:
        case blocks.Paragraph():
            return _render_paragraph(node, annotate)
        case blocks.Heading():
            return _render_heading(node, annotate)
        case blocks.BulletList():
            return _render_bullet_list(node, annotate)
        case blocks.OrderedList():
            return _render_ordered_list(node, annotate)
        case blocks.CodeBlock():
            return _render_code_block(node, annotate)
        case blocks.TaskList():
            return _render_task_list(node, annotate)
        case blocks.DecisionList():
            return _render_decision_list(node, annotate)
        case blocks.ThematicBreak():
            return _render_thematic_break(node, annotate)
        case blocks.MediaGroup():
            return _render_media_group(node, annotate)
        case blocks.MediaSingle():
            return _render_media_single(node, annotate)
        case blocks.Panel():
            return _render_panel(node, annotate)
        case blocks.BlockQuote():
            return _render_blockquote(node, annotate)
        case blocks.Table():
            return _render_table(node, annotate)
        case blocks.NestedExpand():
            return _render_nested_expand(node, annotate)
        case blocks.BlockCard():
            return _render_block_card(node, annotate)
        case blocks.EmbedCard():
            return _render_embed_card(node, annotate)
        case blocks.Extension():
            return _render_extension(node, annotate)
        case blocks.BodiedExtension():
            return _render_bodied_extension(node, annotate)


# ── NestedExpand dispatch ────────────────────────────────────────────


def _render_nested_expand_children(
    children: list[blocks.NestedExpandChild], annotate: bool
) -> list[str]:
    return [_render_nested_expand_child(c, annotate) for c in children]


def _render_nested_expand_child(node: blocks.NestedExpandChild, annotate: bool) -> str:
    match node:
        case blocks.Paragraph():
            return _render_paragraph(node, annotate)
        case blocks.Heading():
            return _render_heading(node, annotate)
        case blocks.BulletList():
            return _render_bullet_list(node, annotate)
        case blocks.OrderedList():
            return _render_ordered_list(node, annotate)
        case blocks.CodeBlock():
            return _render_code_block(node, annotate)
        case blocks.TaskList():
            return _render_task_list(node, annotate)
        case blocks.DecisionList():
            return _render_decision_list(node, annotate)
        case blocks.ThematicBreak():
            return _render_thematic_break(node, annotate)
        case blocks.MediaGroup():
            return _render_media_group(node, annotate)
        case blocks.MediaSingle():
            return _render_media_single(node, annotate)
        case blocks.Panel():
            return _render_panel(node, annotate)
        case blocks.BlockQuote():
            return _render_blockquote(node, annotate)
        case blocks.Extension():
            return _render_extension(node, annotate)


# ── LayoutColumn dispatch ────────────────────────────────────────────


def _render_layoutcolumn_children(
    children: list[blocks.LayoutColumnChild], annotate: bool
) -> list[str]:
    return [_render_layoutcolumn_child(c, annotate) for c in children]


def _render_layoutcolumn_child(node: blocks.LayoutColumnChild, annotate: bool) -> str:
    match node:
        case blocks.Paragraph():
            return _render_paragraph(node, annotate)
        case blocks.Heading():
            return _render_heading(node, annotate)
        case blocks.BulletList():
            return _render_bullet_list(node, annotate)
        case blocks.OrderedList():
            return _render_ordered_list(node, annotate)
        case blocks.CodeBlock():
            return _render_code_block(node, annotate)
        case blocks.TaskList():
            return _render_task_list(node, annotate)
        case blocks.DecisionList():
            return _render_decision_list(node, annotate)
        case blocks.ThematicBreak():
            return _render_thematic_break(node, annotate)
        case blocks.MediaGroup():
            return _render_media_group(node, annotate)
        case blocks.MediaSingle():
            return _render_media_single(node, annotate)
        case blocks.Panel():
            return _render_panel(node, annotate)
        case blocks.BlockQuote():
            return _render_blockquote(node, annotate)
        case blocks.Table():
            return _render_table(node, annotate)
        case blocks.Expand():
            return _render_expand(node, annotate)
        case blocks.BlockCard():
            return _render_block_card(node, annotate)
        case blocks.EmbedCard():
            return _render_embed_card(node, annotate)
        case blocks.BodiedExtension():
            return _render_bodied_extension(node, annotate)
        case blocks.Extension():
            return _render_extension(node, annotate)


# ── TableCell dispatch ───────────────────────────────────────────────


def _render_tablecell_children(
    children: list[blocks.TableCellChild], annotate: bool
) -> list[str]:
    return [_render_tablecell_child(c, annotate) for c in children]


def _render_tablecell_child(node: blocks.TableCellChild, annotate: bool) -> str:
    match node:
        case blocks.Paragraph():
            return _render_paragraph(node, annotate)
        case blocks.Heading():
            return _render_heading(node, annotate)
        case blocks.BulletList():
            return _render_bullet_list(node, annotate)
        case blocks.OrderedList():
            return _render_ordered_list(node, annotate)
        case blocks.CodeBlock():
            return _render_code_block(node, annotate)
        case blocks.TaskList():
            return _render_task_list(node, annotate)
        case blocks.DecisionList():
            return _render_decision_list(node, annotate)
        case blocks.ThematicBreak():
            return _render_thematic_break(node, annotate)
        case blocks.MediaGroup():
            return _render_media_group(node, annotate)
        case blocks.MediaSingle():
            return _render_media_single(node, annotate)
        case blocks.Panel():
            return _render_panel(node, annotate)
        case blocks.BlockQuote():
            return _render_blockquote(node, annotate)
        case blocks.NestedExpand():
            return _render_nested_expand(node, annotate)
        case blocks.BlockCard():
            return _render_block_card(node, annotate)
        case blocks.EmbedCard():
            return _render_embed_card(node, annotate)
        case blocks.Extension():
            return _render_extension(node, annotate)


# ── Inline dispatch ──────────────────────────────────────────────────


def _render_inlines(nodes: list[inlines.Inline], annotate: bool) -> str:
    trimmed = nodes
    while trimmed and isinstance(trimmed[-1], inlines.HardBreak):
        trimmed = trimmed[:-1]
    return "".join(_render_inline(n, annotate) for n in trimmed)


def _render_inline(node: inlines.Inline, annotate: bool) -> str:
    match node:
        case inlines.Text():
            return _render_text(node)
        case inlines.Strong():
            return _render_strong(node, annotate)
        case inlines.Emphasis():
            return _render_emphasis(node, annotate)
        case inlines.Strikethrough():
            return _render_strikethrough(node, annotate)
        case inlines.Link():
            return _render_link(node, annotate)
        case inlines.Image():
            return _render_image(node, annotate)
        case inlines.CodeSpan():
            return _render_code_span(node, annotate)
        case inlines.HardBreak():
            return _render_hard_break(node, annotate)
        case inlines.SoftBreak():
            return _render_soft_break(node, annotate)
        case inlines.Mention():
            return _render_mention(node, annotate)
        case inlines.Emoji():
            return _render_emoji(node, annotate)
        case inlines.Date():
            return _render_date(node, annotate)
        case inlines.Status():
            return _render_status(node, annotate)
        case inlines.InlineCard():
            return _render_inline_card(node, annotate)
        case inlines.MediaInline():
            return _render_media_inline(node, annotate)
        case inlines.Underline():
            return _render_underline(node, annotate)
        case inlines.TextColor():
            return _render_text_color(node, annotate)
        case inlines.BackgroundColor():
            return _render_background_color(node, annotate)
        case inlines.SubSup():
            return _render_subsup(node, annotate)
        case inlines.Annotation():
            return _render_annotation_inline(node, annotate)
        case inlines.Placeholder():
            return _render_placeholder(node, annotate)
        case inlines.InlineExtension():
            return _render_inline_extension(node, annotate)


# ── Inline renderers ─────────────────────────────────────────────────


def _wrap_mark(content: str, delimiter: str) -> str:
    stripped = content.strip(" ")
    if not stripped:
        return content
    leading = " " if content[0] == " " else ""
    trailing = " " if content[-1] == " " else ""
    return f"{leading}{delimiter}{stripped}{delimiter}{trailing}"


def _annotate_inline(
    node: inlines.Inline, content: str, annotate: bool, **attrs: Any
) -> str:
    if not annotate:
        return content
    tag = _to_tag(node)
    filtered = {k: v for k, v in attrs.items() if v is not None}
    attr_json = f" {json.dumps(filtered, ensure_ascii=False)}" if filtered else ""
    return f"<!-- adf:{tag}{attr_json} --> {content} <!-- /adf:{tag} -->"


def _render_text(node: inlines.Text) -> str:
    return node.text.translate(_MD_ESCAPE_TABLE)


def _render_strong(node: inlines.Strong, annotate: bool) -> str:
    return _wrap_mark(_render_inlines(node.children, annotate), "**")


def _render_emphasis(node: inlines.Emphasis, annotate: bool) -> str:
    return _wrap_mark(_render_inlines(node.children, annotate), "*")


def _render_strikethrough(node: inlines.Strikethrough, annotate: bool) -> str:
    return _wrap_mark(_render_inlines(node.children, annotate), "~~")


def _render_link(node: inlines.Link, annotate: bool) -> str:
    text = _render_inlines(node.children, annotate)
    if node.title:
        return f'[{text}]({node.url} "{node.title}")'
    return f"[{text}]({node.url})"


def _render_image(node: inlines.Image, annotate: bool) -> str:
    if node.title:
        return f'![{node.alt}]({node.url} "{node.title}")'
    return f"![{node.alt}]({node.url})"


def _render_code_span(node: inlines.CodeSpan, annotate: bool) -> str:
    if "`" not in node.code:
        return f"`{node.code}`"
    runs = _BACKTICK_RUN_RE.findall(node.code)
    n = max(len(r) for r in runs) + 1
    fence = "`" * n
    return f"{fence} {node.code} {fence}"


def _render_hard_break(node: inlines.HardBreak, annotate: bool) -> str:
    return CELL_HARD_BREAK if _in_table() else "\\\n"


def _render_soft_break(node: inlines.SoftBreak, annotate: bool) -> str:
    return "\n"


def _render_mention(node: inlines.Mention, annotate: bool) -> str:
    text = node.text or f"@{node.id}"
    fallback = f"`{text}`"
    return _annotate_inline(
        node,
        fallback,
        annotate,
        id=node.id,
        text=node.text,
        accessLevel=node.access_level,
        userType=node.user_type,
    )


def _render_emoji(node: inlines.Emoji, annotate: bool) -> str:
    fallback = node.text or f":{node.short_name}:"
    return _annotate_inline(
        node,
        fallback,
        annotate,
        shortName=node.short_name,
        text=node.text,
        id=node.id,
    )


def _render_date(node: inlines.Date, annotate: bool) -> str:
    dt = datetime.fromtimestamp(int(node.timestamp) / 1000, tz=UTC)
    fallback = f"`{dt.strftime('%Y-%m-%d')}`"
    return _annotate_inline(node, fallback, annotate, timestamp=node.timestamp)


def _render_status(node: inlines.Status, annotate: bool) -> str:
    fallback = f"`{node.text}`"
    return _annotate_inline(
        node,
        fallback,
        annotate,
        text=node.text,
        color=node.color,
        style=node.style,
    )


def _render_inline_card(node: inlines.InlineCard, annotate: bool) -> str:
    if node.url:
        fallback = f"[{node.url}]({node.url})"
    else:
        fallback = "`\U0001f517 card link`"
    if node.url and not node.data:
        return _annotate_inline(node, fallback, annotate)
    return _annotate_inline(node, fallback, annotate, url=node.url, data=node.data)


def _render_media_inline(node: inlines.MediaInline, annotate: bool) -> str:
    alt = node.alt or "attachment"
    fallback = f"`\U0001f4ce {alt}`"
    media_type = None if node.media_type == "file" else node.media_type
    return _annotate_inline(
        node,
        fallback,
        annotate,
        id=node.id,
        collection=node.collection,
        mediaType=media_type,
        alt=node.alt,
        width=node.width,
        height=node.height,
    )


def _render_underline(node: inlines.Underline, annotate: bool) -> str:
    content = _render_inlines(node.children, annotate)
    return _annotate_inline(node, content, annotate)


def _render_text_color(node: inlines.TextColor, annotate: bool) -> str:
    content = _render_inlines(node.children, annotate)
    return _annotate_inline(node, content, annotate, color=node.color)


def _render_background_color(node: inlines.BackgroundColor, annotate: bool) -> str:
    content = _render_inlines(node.children, annotate)
    return _annotate_inline(node, content, annotate, color=node.color)


def _render_subsup(node: inlines.SubSup, annotate: bool) -> str:
    content = _render_inlines(node.children, annotate)
    return _annotate_inline(node, content, annotate, type=node.type)


def _render_annotation_inline(node: inlines.Annotation, annotate: bool) -> str:
    content = _render_inlines(node.children, annotate)
    return _annotate_inline(
        node,
        content,
        annotate,
        id=node.id,
        annotationType=node.annotation_type,
    )


def _render_placeholder(node: inlines.Placeholder, annotate: bool) -> str:
    return ""


def _render_inline_extension(node: inlines.InlineExtension, annotate: bool) -> str:
    key = node.raw.get("attrs", {}).get("extensionKey", "")
    label = key or "Confluence macro"
    content = f"`\u2699 {label}`"
    if annotate:
        return _annotate_inline(node, content, annotate, raw=node.raw)
    return content
