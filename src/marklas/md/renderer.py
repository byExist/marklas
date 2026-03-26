"""ADF AST → Markdown renderer."""

from __future__ import annotations

import enum
import json
import re
from collections.abc import Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import fields

from datetime import UTC, datetime
from typing import Any, Generator, cast

from marklas import ast


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


def _build_params(fields: dict[str, Any]) -> str | None:
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


_PLAIN_STRIP_TAGS = {"span", "time", "div", "section", "mark"}


def _el(tag: str, content: str, **attrs: Any) -> str:
    """<tag attrs>content</tag>"""
    if _is_plain() and tag in _PLAIN_STRIP_TAGS:
        return content
    return f"<{tag}{_attr_str(**attrs)}>{content}</{tag}>"


def _block_el(tag: str, content: str, **attrs: Any) -> str:
    """<tag attrs>\\n\\ncontent\\n\\n</tag> (block context only)"""
    if _is_plain() and tag in _PLAIN_STRIP_TAGS:
        return content
    if _in_cell():
        return _el(tag, content, **attrs)
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
    }
)


def _escape_md(text: str) -> str:
    return text.translate(_MD_ESCAPE)


def _escape_pipe(text: str) -> str:
    return text.replace("|", "\\|")


_BACKTICK_RE = re.compile(r"`+")


def _code_fence(code: str) -> str:
    runs = _BACKTICK_RE.findall(code)
    max_run = max((len(r) for r in runs), default=0)
    return "`" * max(3, max_run + 1)


def _media_fallback(id: str | None, alt: str | None) -> str:
    label = alt or "attachment"
    return f"📎 {label} ({id})" if id else f"📎 {label}"


# ── Entry point ────────────────────────────────────────────────────────────────


def render(doc: ast.Doc, *, plain: bool = False) -> str:
    token = _plain_ctx.set(plain)
    try:
        parts = _render_blocks(doc.content)
        return "\n\n".join(parts) + "\n" if parts else ""
    finally:
        _plain_ctx.reset(token)


# ── Block marks ────────────────────────────────────────────────────────────────


_BLOCK_MARK_TYPES = (
    ast.AlignmentMark,
    ast.IndentationMark,
    ast.BreakoutMark,
    ast.DataConsumerMark,
    ast.BorderMark,
)


def _block_marks_data(marks: Sequence[ast.Mark]) -> str | None:
    """<data adf="marks" params='...'> for block context. None if no block marks."""
    if _is_plain():
        return None
    d = _block_marks_params(marks)
    if not d:
        return None
    return _data("marks", _build_params(d))


def _block_marks_params(marks: Sequence[ast.Mark]) -> dict[str, Any]:
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
            case _:
                pass
    return d


# ── Block rendering ────────────────────────────────────────────────────────────


def _render_blocks(children: Sequence[ast.Node]) -> list[str]:
    return [_render_block(c) for c in children]


def _render_block(node: ast.Node) -> str:
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
            return _render_task_list(node)
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
        case _:
            raise ValueError(f"Unknown block: {type(node).__name__}")


# ── Block renderers (각 함수가 block/cell 컨텍스트 내부 처리) ──────────────────


def _render_paragraph(node: ast.Paragraph) -> str:
    content = _render_inlines(node.content)
    if _in_cell():
        marks_dict = _block_marks_params(node.marks)
        params = _build_params(marks_dict)
        return _el("p", content, params=params)
    marks_prefix = _block_marks_data(node.marks)
    result = content or "&nbsp;"
    if marks_prefix:
        return f"{marks_prefix}\n\n{result}"
    return result


def _render_heading(node: ast.Heading) -> str:
    content = _render_inlines(node.content)
    if _in_cell():
        marks_dict = _block_marks_params(node.marks)
        params = _build_params(marks_dict)
        return _el(f"h{node.level}", content, params=params)
    marks_prefix = _block_marks_data(node.marks)
    result = f"{'#' * node.level} {content}"
    if marks_prefix:
        return f"{marks_prefix}\n\n{result}"
    return result


def _render_code_block(node: ast.CodeBlock) -> str:
    code = "".join(t.text for t in node.content)
    if _in_cell():
        marks_dict = _block_marks_params(node.marks)
        if node.language:
            marks_dict["language"] = node.language
        params = _build_params(marks_dict)
        return _el("code", code.replace("\n", "<br>"), params=params)
    marks_prefix = _block_marks_data(node.marks)
    fence = _code_fence(code)
    lang = node.language or ""
    result = f"{fence}{lang}\n{code}\n{fence}"
    if marks_prefix:
        return f"{marks_prefix}\n\n{result}"
    return result


def _render_blockquote(node: ast.Blockquote) -> str:
    if _in_cell():
        parts = _render_blocks(node.content)
        return _el("blockquote", "".join(parts))
    inner = "\n\n".join(_render_blocks(node.content))
    return "\n".join(f"> {line}" if line else ">" for line in inner.split("\n"))


def _li_content(children: Sequence[ast.Node]) -> str:
    """List item content in cell context. Single Paragraph → bare text."""
    if len(children) == 1 and isinstance(children[0], ast.Paragraph):
        return _render_inlines(children[0].content)
    return "".join(_render_block(c) for c in children)


def _render_bullet_list(node: ast.BulletList) -> str:
    if _in_cell():
        items = "".join(_el("li", _li_content(item.content)) for item in node.content)
        return _el("ul", items)
    return "\n".join(_render_list_item(item, "- ") for item in node.content)


def _render_ordered_list(node: ast.OrderedList) -> str:
    start = node.order or 1
    if _in_cell():
        items = "".join(_el("li", _li_content(item.content)) for item in node.content)
        return _el("ol", items, start=start if start != 1 else None)
    parts: list[str] = []
    for i, item in enumerate(node.content):
        parts.append(_render_list_item(item, f"{start + i}. "))
    return "\n".join(parts)


def _render_list_item(node: ast.ListItem, marker: str) -> str:
    indent = " " * len(marker)
    parts = _render_blocks(node.content)
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


def _render_panel(node: ast.Panel) -> str:
    params = _build_params(
        {
            "panelType": node.panel_type,
            "panelIcon": node.panel_icon,
            "panelIconId": node.panel_icon_id,
            "panelIconText": node.panel_icon_text,
            "panelColor": node.panel_color,
        }
    )
    if _in_cell():
        content = "".join(_render_blocks(node.content))
    else:
        content = "\n\n".join(_render_blocks(node.content))
    return _block_el("aside", content, adf="panel", params=params)


def _render_expand(node: ast.Expand) -> str:
    marks_prefix = _block_marks_data(node.marks)
    summary = _el("summary", node.title) if node.title else ""
    if _in_cell():
        content = "".join(_render_blocks(node.content))
        result = _el("details", summary + content, adf="expand")
    else:
        content = "\n\n".join(_render_blocks(node.content))
        inner = f"{summary}\n\n{content}" if summary else content
        result = _block_el("details", inner, adf="expand")
    if marks_prefix and not _in_cell():
        return f"{marks_prefix}\n\n{result}"
    return result


def _render_nested_expand(node: ast.NestedExpand) -> str:
    summary = _el("summary", node.title) if node.title else ""
    if _in_cell():
        content = "".join(_render_blocks(node.content))
        return _el("details", summary + content, adf="nestedExpand")
    content = "\n\n".join(_render_blocks(node.content))
    inner = f"{summary}\n\n{content}" if summary else content
    return _block_el("details", inner, adf="nestedExpand")


def _render_task_list(node: ast.TaskList) -> str:
    if _in_cell():
        items: list[str] = []
        for child in node.content:
            match child:
                case ast.TaskItem():
                    content = _render_inlines(child.content)
                    params = _build_params({"state": child.state})
                    items.append(_el("li", content, adf="taskItem", params=params))
                case ast.BlockTaskItem():
                    content = "".join(_render_blocks(child.content))
                    params = _build_params({"state": child.state})
                    items.append(_el("li", content, adf="taskItem", params=params))
                case ast.TaskList():
                    items.append(_render_task_list(child))
                case _:
                    pass
        return _el("ul", "".join(items), adf="taskList")
    parts: list[str] = []
    for child in node.content:
        match child:
            case ast.TaskItem():
                parts.append(_render_task_item(child))
            case ast.BlockTaskItem():
                parts.append(_render_block_task_item(child))
            case ast.TaskList():
                nested = _render_task_list(child)
                parts.append("\n".join("  " + line for line in nested.split("\n")))
            case _:
                pass
    return "\n".join(parts)


def _render_task_item(node: ast.TaskItem) -> str:
    checkbox = "[x]" if node.state == "DONE" else "[ ]"
    content = _render_inlines(node.content)
    return f"- {checkbox} {content}"


def _render_block_task_item(node: ast.BlockTaskItem) -> str:
    checkbox = "[x]" if node.state == "DONE" else "[ ]"
    marker = f"- {checkbox} "
    indent = " " * len(marker)
    parts = _render_blocks(node.content)
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
    return _block_el("ul", items, adf="decisionList")


def _render_decision_item(node: ast.DecisionItem) -> str:
    content = _render_inlines(node.content)
    params = _build_params({"state": node.state})
    return _el("li", content, adf="decisionItem", params=params)


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
    params = _build_params(params_dict)
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
    return _block_el("figure", content, adf="mediaSingle", params=params)


def _render_media_group(node: ast.MediaGroup) -> str:
    content = "".join(_render_media(m) for m in node.content)
    return _block_el("div", content, adf="mediaGroup")


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
    params = _build_params(params_dict)
    result = _el("span", display, adf="media", params=params)
    for m in node.marks:
        if isinstance(m, ast.LinkMark):
            result = _el("a", result, href=m.href, title=m.title)
        elif isinstance(m, ast.AnnotationMark):
            result = _el(
                "mark",
                result,
                adf="annotation",
                params=_build_params({"id": m.id}),
            )
    return result


def _render_caption(node: ast.Caption) -> str:
    content = _render_inlines(node.content)
    return _el("figcaption", content, adf="caption")


def _render_block_card(node: ast.BlockCard) -> str:
    params_dict: dict[str, Any] = {
        "url": node.url,
        "layout": node.layout,
        "width": node.width,
        "data": node.data,
        "datasource": node.datasource,
    }
    params = _build_params(params_dict)
    display = node.url or ""
    return _block_el("div", display, adf="blockCard", params=params)


def _render_embed_card(node: ast.EmbedCard) -> str:
    params = _build_params(
        {
            "url": node.url,
            "layout": node.layout,
            "width": node.width,
            "originalHeight": node.original_height,
            "originalWidth": node.original_width,
        }
    )
    return _block_el("div", node.url, adf="embedCard", params=params)


def _render_layout_section(node: ast.LayoutSection) -> str:
    marks_prefix = _block_marks_data(node.marks)
    columns = "\n\n".join(_render_layout_column(col) for col in node.content)
    result = _block_el("section", columns, adf="layoutSection")
    if marks_prefix and not _in_cell():
        return f"{marks_prefix}\n\n{result}"
    return result


def _render_layout_column(node: ast.LayoutColumn) -> str:
    params = _build_params({"width": node.width})
    content = "\n\n".join(_render_blocks(node.content))
    return _block_el("div", content, adf="layoutColumn", params=params)


def _render_extension(node: ast.Extension) -> str:
    marks_prefix = _block_marks_data(node.marks)
    params = _build_params(
        {
            "extensionKey": node.extension_key,
            "extensionType": node.extension_type,
            "parameters": node.parameters,
            "text": node.text,
            "layout": node.layout,
        }
    )
    result = _data("extension", params)
    if marks_prefix and not _in_cell():
        return f"{marks_prefix}\n\n{result}"
    return result


def _render_bodied_extension(node: ast.BodiedExtension) -> str:
    content_dicts = [_node_to_dict(c) for c in node.content]
    params = _build_params(
        {
            "extensionKey": node.extension_key,
            "extensionType": node.extension_type,
            "parameters": node.parameters,
            "text": node.text,
            "layout": node.layout,
            "content": content_dicts,
        }
    )
    return _data("bodiedExtension", params)


def _render_sync_block(node: ast.SyncBlock) -> str:
    marks_prefix = _block_marks_data(node.marks)
    params = _build_params({"resourceId": node.resource_id})
    result = _data("syncBlock", params)
    if marks_prefix and not _in_cell():
        return f"{marks_prefix}\n\n{result}"
    return result


def _render_bodied_sync_block(node: ast.BodiedSyncBlock) -> str:
    content_dicts = [_node_to_dict(c) for c in node.content]
    params = _build_params(
        {
            "resourceId": node.resource_id,
            "content": content_dicts,
        }
    )
    return _data("bodiedSyncBlock", params)


# ── Table ──────────────────────────────────────────────────────────────────────


def _render_table(node: ast.Table) -> str:
    rows = node.content
    if not rows:
        return ""

    mode = _header_mode(node)

    with _cell_context():
        grid = _build_grid(rows)

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


def _build_grid(rows: Sequence[ast.TableRow]) -> list[list[str]]:
    """Build 2D cell grid, expanding colspan/rowspan into filler cells."""
    num_rows = len(rows)
    if num_rows == 0:
        return []

    max_cols = max(sum(c.colspan or 1 for c in row.content) for row in rows)
    grid: list[list[str | None]] = [[None] * max_cols for _ in range(num_rows)]

    for r, row in enumerate(rows):
        c = 0
        for cell in row.content:
            while c < max_cols and grid[r][c] is not None:
                c += 1
            if c >= max_cols:
                break
            cs = cell.colspan or 1
            rs = cell.rowspan or 1
            grid[r][c] = _render_cell(cell)
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
    colwidths = _collect_colwidths(node)
    if colwidths:
        d["colwidths"] = colwidths
    if not d:
        return None
    return _data("table", _build_params(d))


def _collect_colwidths(node: ast.Table) -> list[int] | None:
    """Extract column widths from first row's cells."""
    if not node.content:
        return None
    widths: list[int] = []
    has_any = False
    for cell in node.content[0].content:
        if cell.colwidth:
            widths.extend(cell.colwidth)
            has_any = True
        else:
            widths.extend([0] * (cell.colspan or 1))
    return widths if has_any else None


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


def _cell_meta(cell: ast.TableCell) -> str:
    """<data adf="cell" params='...'> prefix if colspan/rowspan/background."""
    d: dict[str, Any] = {}
    if cell.colspan and cell.colspan > 1:
        d["colspan"] = cell.colspan
    if cell.rowspan and cell.rowspan > 1:
        d["rowspan"] = cell.rowspan
    if cell.background:
        d["background"] = cell.background
    if not d:
        return ""
    return _data("cell", _build_params(d))


def _render_cell(cell: ast.TableCell) -> str:
    meta = _cell_meta(cell)
    content = _render_cell_content(cell.content)
    return _escape_pipe(meta + content)


def _render_cell_content(children: Sequence[ast.Node]) -> str:
    """Single Paragraph → bare text, else HTML tags per block."""
    if not children:
        return ""
    if len(children) == 1 and isinstance(children[0], ast.Paragraph):
        p = children[0]
        if not _block_marks_params(p.marks):
            return _render_inlines(p.content)
    return "".join(_render_block(c) for c in children)


# ── Inline rendering ──────────────────────────────────────────────────────────


def _render_inlines(children: Sequence[ast.Inline]) -> str:
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
        case _:
            raise ValueError(f"Unknown inline: {type(node).__name__}")


# ── Inline renderers ──────────────────────────────────────────────────────────


def _render_text(node: ast.Text) -> str:
    return _apply_marks(node.text, node.marks)


def _render_hard_break() -> str:
    return "<br>" if _in_cell() else "\\\n"


def _render_mention(node: ast.Mention) -> str:
    display = node.text or f"@{node.id}"
    params = _build_params(
        {
            "id": node.id,
            "accessLevel": node.access_level,
            "userType": node.user_type,
        }
    )
    return _el("span", display, adf="mention", params=params)


def _render_emoji(node: ast.Emoji) -> str:
    display = node.text or node.short_name
    params = _build_params(
        {
            "shortName": node.short_name,
            "id": node.id,
        }
    )
    return _el("span", display, adf="emoji", params=params)


def _render_date(node: ast.Date) -> str:
    ts = int(node.timestamp) / 1000
    dt = datetime.fromtimestamp(ts, tz=UTC)
    display = dt.strftime("%Y-%m-%d")
    return _el("time", display, adf="date", datetime=node.timestamp)


def _render_status(node: ast.Status) -> str:
    params = _build_params(
        {
            "color": node.color,
            "style": node.style,
        }
    )
    return _el("span", node.text, adf="status", params=params)


def _render_inline_card(node: ast.InlineCard) -> str:
    params = _build_params({"data": node.data}) if node.data else None
    display = node.url or ""
    return _el("a", display, adf="inlineCard", href=node.url, params=params)


def _render_placeholder(node: ast.Placeholder) -> str:
    return _el("span", node.text, adf="placeholder")


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
    params = _build_params(params_dict)
    result = _el("span", display, adf="mediaInline", params=params)
    for m in node.marks:
        if isinstance(m, ast.LinkMark):
            result = _el("a", result, href=m.href, title=m.title)
        elif isinstance(m, ast.AnnotationMark):
            result = _el(
                "mark",
                result,
                adf="annotation",
                params=_build_params({"id": m.id}),
            )
    return result


def _render_inline_extension(node: ast.InlineExtension) -> str:
    params = _build_params(
        {
            "extensionKey": node.extension_key,
            "extensionType": node.extension_type,
            "parameters": node.parameters,
            "text": node.text,
        }
    )
    return _el("span", "", adf="inlineExtension", params=params)


# ── Mark rendering ─────────────────────────────────────────────────────────────


def _wrap_code(text: str) -> str:
    """Wrap text in code span backticks, handling embedded backticks."""
    if "`" not in text:
        return f"`{text}`"
    runs = _BACKTICK_RE.findall(text)
    max_run = max(len(r) for r in runs)
    fence = "`" * (max_run + 1)
    if text.startswith("`") or text.endswith("`"):
        return f"{fence} {text} {fence}"
    return f"{fence}{text}{fence}"


def _wrap_flanking(text: str, delimiter: str) -> str:
    """Move leading/trailing spaces outside delimiter for CommonMark flanking."""
    leading = len(text) - len(text.lstrip(" "))
    trailing = len(text) - len(text.rstrip(" "))
    inner = text.strip(" ")
    if not inner:
        return text
    return f"{' ' * leading}{delimiter}{inner}{delimiter}{' ' * trailing}"


def _wrap_html_mark(text: str, mark: ast.Mark) -> str:
    match mark:
        case ast.UnderlineMark():
            return _el("u", text, adf="underline")
        case ast.TextColorMark(color=color):
            return _el(
                "span", text, adf="textColor", params=_build_params({"color": color})
            )
        case ast.BackgroundColorMark(color=color):
            return _el(
                "span", text, adf="bgColor", params=_build_params({"color": color})
            )
        case ast.SubSupMark(type=type_):
            tag = "sub" if type_ == "sub" else "sup"
            return _el(tag, text, adf="subSup")
        case ast.AnnotationMark(id=id_):
            return _el(
                "mark",
                text,
                adf="annotation",
                params=_build_params({"id": id_}),
            )
        case _:
            return text


def _apply_marks(text: str, marks: Sequence[ast.Mark]) -> str:
    if not marks:
        return _escape_md(text)

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
    result = _wrap_code(text) if code else _escape_md(text)

    # native MD marks
    for m in native:
        match m:
            case ast.StrongMark():
                result = _wrap_flanking(result, "**")
            case ast.EmMark():
                result = _wrap_flanking(result, "*")
            case ast.StrikeMark():
                result = _wrap_flanking(result, "~~")
            case _:
                pass

    # link
    if link:
        title = f' "{link.title}"' if link.title else ""
        result = f"[{result}]({link.href}{title})"

    # HTML marks (outermost)
    for m in html:
        result = _wrap_html_mark(result, m)

    return result


# ── AST → dict ─────────────────────────────────────────────────────────────────


def _node_to_dict(node: ast.Node) -> dict[str, Any]:
    """AST node → ADF-compatible dict (BodiedExtension/BodiedSyncBlock content)."""

    d: dict[str, Any] = {"type": _node_type_name(node)}
    for f in fields(node):
        val = getattr(node, f.name)
        if val is None:
            continue
        key = _snake_to_camel(f.name)
        if isinstance(val, ast.Node):
            d[key] = _node_to_dict(val)
        elif isinstance(val, Sequence) and not isinstance(val, str):
            items: list[Any] = []
            for v in cast(Sequence[Any], val):
                if isinstance(v, ast.Node):
                    items.append(_node_to_dict(v))
                elif isinstance(v, ast.Mark):
                    items.append(_mark_to_dict(v))
                else:
                    items.append(v)
            d[key] = items
        elif isinstance(val, ast.Mark):
            d[key] = _mark_to_dict(val)
        else:
            d[key] = val
    return d


def _mark_to_dict(mark: ast.Mark) -> dict[str, Any]:
    d: dict[str, Any] = {"type": _node_type_name(mark)}
    attrs: dict[str, Any] = {}
    for f in fields(mark):
        val = getattr(mark, f.name)
        if val is not None:
            attrs[_snake_to_camel(f.name)] = val
    if attrs:
        d["attrs"] = attrs
    return d


def _node_type_name(obj: ast.Node | ast.Mark) -> str:
    name = type(obj).__name__
    if name.endswith("Mark"):
        name = name[:-4]
    return name[0].lower() + name[1:]


def _snake_to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])
