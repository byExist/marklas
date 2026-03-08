from __future__ import annotations

from typing import Any
from uuid import uuid4

from marklas.nodes import blocks, inlines

from marklas.adf import schema


def _sort_marks(marks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(marks, key=lambda m: schema.MARK_ORDER.get(m["type"], 99))


# ── Public API ───────────────────────────────────────────────────────


def render(doc: blocks.Document) -> dict[str, Any]:
    content = _render_children(doc.children)
    return {"type": "doc", "version": 1, "content": content}


# ── Helpers ──────────────────────────────────────────────────────────


def _render_children(children: list[blocks.Block]) -> list[dict[str, Any]]:
    return [b for b in (_render_block(c) for c in children) if b is not None]


def _apply_block_marks(
    result: dict[str, Any],
    alignment: str | None,
    indentation: int | None,
) -> None:
    marks: list[dict[str, Any]] = []
    if alignment:
        marks.append({"type": "alignment", "attrs": {"align": alignment}})
    if indentation:
        marks.append({"type": "indentation", "attrs": {"level": indentation}})
    if marks:
        result["marks"] = marks


# ── Block dispatch ───────────────────────────────────────────────────


def _render_block(node: blocks.Block) -> dict[str, Any] | None:
    match node:
        case blocks.Paragraph():
            return _render_paragraph(node)
        case blocks.Heading():
            return _render_heading(node)
        case blocks.CodeBlock():
            return _render_code_block(node)
        case blocks.BlockQuote():
            return _render_blockquote(node)
        case blocks.ThematicBreak():
            return {"type": "rule"}
        case blocks.BulletList():
            return _render_bullet_list(node)
        case blocks.OrderedList():
            return _render_ordered_list(node)
        case blocks.TaskList():
            return _render_task_list(node)
        case blocks.DecisionList():
            return _render_decision_list(node)
        case blocks.Table():
            return _render_table(node)
        case blocks.Panel():
            return _render_panel(node)
        case blocks.Expand():
            return _render_expand(node)
        case blocks.NestedExpand():
            return _render_nested_expand(node)
        case blocks.LayoutSection():
            return _render_layout_section(node)
        case blocks.MediaSingle():
            return _render_media_single(node)
        case blocks.MediaGroup():
            return _render_media_group(node)
        case blocks.BlockCard():
            return _render_block_card(node)
        case blocks.EmbedCard():
            return _render_embed_card(node)
        case (
            blocks.Extension()
            | blocks.BodiedExtension()
            | blocks.SyncBlock()
            | blocks.BodiedSyncBlock()
        ):
            return node.raw
        case _:
            return None


# ── Block renderers ──────────────────────────────────────────────────


def _render_paragraph(node: blocks.Paragraph) -> dict[str, Any]:
    # Single Image → mediaSingle conversion (intersection reverse-mapping)
    if len(node.children) == 1 and isinstance(node.children[0], inlines.Image):
        img = node.children[0]
        media: dict[str, Any] = {
            "type": "media",
            "attrs": {"type": "external", "url": img.url},
        }
        return {"type": "mediaSingle", "content": [media]}

    result: dict[str, Any] = {
        "type": "paragraph",
        "content": _render_inlines(node.children),
    }
    _apply_block_marks(result, node.alignment, node.indentation)
    return result


def _render_heading(node: blocks.Heading) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "heading",
        "attrs": {"level": node.level},
        "content": _render_inlines(node.children),
    }
    _apply_block_marks(result, node.alignment, node.indentation)
    return result


def _render_code_block(node: blocks.CodeBlock) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{"type": "text", "text": node.code}]
    result: dict[str, Any] = {"type": "codeBlock", "content": content}
    if node.language is not None:
        result["attrs"] = {"language": node.language}
    return result


def _render_blockquote(node: blocks.BlockQuote) -> dict[str, Any]:
    return {"type": "blockquote", "content": _render_children(node.children)}


def _render_bullet_list(node: blocks.BulletList) -> dict[str, Any]:
    # Convert to taskList if any items have checked state (intersection reverse-mapping)
    if any(item.checked is not None for item in node.items):
        task_items: list[dict[str, Any]] = []
        for item in node.items:
            state = "DONE" if item.checked else "TODO"
            task_item: dict[str, Any] = {
                "type": "taskItem",
                "attrs": {"localId": str(uuid4()), "state": state},
            }
            content = _render_inlines_from_blocks(item.children)
            if content:
                task_item["content"] = content
            task_items.append(task_item)
        return {
            "type": "taskList",
            "attrs": {"localId": str(uuid4())},
            "content": task_items,
        }

    items = [_render_list_item(item) for item in node.items]
    return {"type": "bulletList", "content": items}


def _render_ordered_list(node: blocks.OrderedList) -> dict[str, Any]:
    items = [_render_list_item(item) for item in node.items]
    result: dict[str, Any] = {"type": "orderedList", "content": items}
    if node.start != 1:
        result["attrs"] = {"order": node.start}
    return result


def _render_list_item(item: blocks.ListItem) -> dict[str, Any]:
    return {"type": "listItem", "content": _render_children(item.children)}


def _render_task_list(node: blocks.TaskList) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for item in node.items:
        task_item: dict[str, Any] = {
            "type": "taskItem",
            "attrs": {"localId": item.local_id, "state": item.state},
        }
        content = _render_inlines(item.children)
        if content:
            task_item["content"] = content
        items.append(task_item)
    return {
        "type": "taskList",
        "attrs": {"localId": str(uuid4())},
        "content": items,
    }


def _render_decision_list(node: blocks.DecisionList) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for item in node.items:
        decision_item: dict[str, Any] = {
            "type": "decisionItem",
            "attrs": {"localId": item.local_id, "state": item.state},
        }
        content = _render_inlines(item.children)
        if content:
            decision_item["content"] = content
        items.append(decision_item)
    return {
        "type": "decisionList",
        "attrs": {"localId": str(uuid4())},
        "content": items,
    }


def _render_panel(node: blocks.Panel) -> dict[str, Any]:
    attrs: dict[str, Any] = {"panelType": node.panel_type}
    if node.panel_icon:
        attrs["panelIcon"] = node.panel_icon
    if node.panel_icon_id:
        attrs["panelIconId"] = node.panel_icon_id
    if node.panel_icon_text:
        attrs["panelIconText"] = node.panel_icon_text
    if node.panel_color:
        attrs["panelColor"] = node.panel_color
    return {"type": "panel", "attrs": attrs, "content": _render_children(node.children)}


def _render_expand(node: blocks.Expand) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "expand",
        "content": _render_children(node.children),
    }
    if node.title:
        result["attrs"] = {"title": node.title}
    return result


def _render_nested_expand(node: blocks.NestedExpand) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "nestedExpand",
        "content": _render_children(node.children),
    }
    if node.title:
        result["attrs"] = {"title": node.title}
    return result


def _render_layout_section(node: blocks.LayoutSection) -> dict[str, Any]:
    columns: list[dict[str, Any]] = []
    for col in node.columns:
        width = col.width if col.width is not None else 100 / len(node.columns)
        columns.append(
            {
                "type": "layoutColumn",
                "attrs": {"width": width},
                "content": _render_children(col.children),
            }
        )
    return {"type": "layoutSection", "content": columns}


def _render_media(media: blocks.Media) -> dict[str, Any]:
    attrs: dict[str, Any] = {"type": media.media_type}
    if media.url is not None:
        attrs["url"] = media.url
    if media.id is not None:
        attrs["id"] = media.id
    if media.collection is not None:
        attrs["collection"] = media.collection
    if media.alt is not None:
        attrs["alt"] = media.alt
    if media.width is not None:
        attrs["width"] = media.width
    if media.height is not None:
        attrs["height"] = media.height
    return {"type": "media", "attrs": attrs}


def _render_media_single(node: blocks.MediaSingle) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "mediaSingle",
        "content": [_render_media(node.media)],
    }
    attrs: dict[str, Any] = {}
    if node.layout is not None:
        attrs["layout"] = node.layout
    if node.width is not None:
        attrs["width"] = node.width
    if node.width_type is not None:
        attrs["widthType"] = node.width_type
    if attrs:
        result["attrs"] = attrs
    return result


def _render_media_group(node: blocks.MediaGroup) -> dict[str, Any]:
    return {
        "type": "mediaGroup",
        "content": [_render_media(m) for m in node.media_list],
    }


def _render_block_card(node: blocks.BlockCard) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    if node.url is not None:
        attrs["url"] = node.url
    if node.data is not None:
        attrs["data"] = node.data
    return {"type": "blockCard", "attrs": attrs}


def _render_embed_card(node: blocks.EmbedCard) -> dict[str, Any]:
    attrs: dict[str, Any] = {"url": node.url, "layout": node.layout}
    if node.width is not None:
        attrs["width"] = node.width
    if node.original_width is not None:
        attrs["originalWidth"] = node.original_width
    if node.original_height is not None:
        attrs["originalHeight"] = node.original_height
    return {"type": "embedCard", "attrs": attrs}


def _render_table(node: blocks.Table) -> dict[str, Any]:
    # Collect all rows
    all_cell_rows: list[list[blocks.TableCell]] = []
    if node.head:
        all_cell_rows.append(node.head)
    for row in node.body:
        all_cell_rows.append(row)

    num_rows = len(all_cell_rows)
    num_cols = max((len(cells) for cells in all_cell_rows), default=0)

    # Calculate positions occupied by colspan/rowspan (excluding origin)
    occupied: list[list[bool]] = [[False] * num_cols for _ in range(num_rows)]
    for r, cells in enumerate(all_cell_rows):
        for col_idx, cell in enumerate(cells):
            cs = cell.colspan or 1
            rs = cell.rowspan or 1
            for dr in range(rs):
                for dc in range(cs):
                    if (
                        (dr > 0 or dc > 0)
                        and r + dr < num_rows
                        and col_idx + dc < num_cols
                    ):
                        occupied[r + dr][col_idx + dc] = True

    # Render while skipping occupied cells
    rows: list[dict[str, Any]] = []
    for r, cells in enumerate(all_cell_rows):
        row_cells: list[dict[str, Any]] = []
        for col_idx, cell in enumerate(cells):
            if col_idx < num_cols and occupied[r][col_idx]:
                continue
            cell_type = (
                "tableHeader" if isinstance(cell, blocks.TableHeader) else "tableCell"
            )
            cell_json: dict[str, Any] = {
                "type": cell_type,
                "content": _render_children(cell.children),
            }
            _apply_cell_attrs(cell, cell_json)
            row_cells.append(cell_json)
        rows.append({"type": "tableRow", "content": row_cells})

    result: dict[str, Any] = {"type": "table", "content": rows}

    table_attrs: dict[str, Any] = {}
    if node.display_mode is not None:
        table_attrs["displayMode"] = node.display_mode
    if node.is_number_column_enabled is not None:
        table_attrs["isNumberColumnEnabled"] = node.is_number_column_enabled
    if node.layout is not None:
        table_attrs["layout"] = node.layout
    if node.width is not None:
        table_attrs["width"] = node.width
    if table_attrs:
        result["attrs"] = table_attrs

    return result


def _apply_cell_attrs(cell: blocks.TableCell, cell_json: dict[str, Any]) -> None:
    cell_attrs: dict[str, Any] = {}
    if cell.colspan:
        cell_attrs["colspan"] = cell.colspan
    if cell.rowspan:
        cell_attrs["rowspan"] = cell.rowspan
    if cell.col_width:
        cell_attrs["colwidth"] = cell.col_width
    if cell.background:
        cell_attrs["background"] = cell.background
    if cell_attrs:
        cell_json["attrs"] = cell_attrs


# ── Inline rendering ─────────────────────────────────────────────────


def _render_inlines(nodes: list[inlines.Inline]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in nodes:
        result.extend(_flatten_inline(node, []))
    return result


def _render_inlines_from_blocks(
    block_nodes: list[blocks.Block],
) -> list[dict[str, Any]]:
    """Extract inlines from ListItem.children (block list) for taskItem content."""
    result: list[dict[str, Any]] = []
    for block in block_nodes:
        if isinstance(block, blocks.Paragraph):
            result.extend(_render_inlines(block.children))
    return result


def _flatten_inline(
    node: inlines.Inline, marks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    match node:
        case inlines.Text():
            if not node.text:
                return []
            text: dict[str, Any] = {"type": "text", "text": node.text}
            if marks:
                text["marks"] = _sort_marks(marks)
            return [text]

        case inlines.Strong():
            new_marks: list[dict[str, Any]] = [*marks, {"type": "strong"}]
            return [
                child for c in node.children for child in _flatten_inline(c, new_marks)
            ]

        case inlines.Emphasis():
            new_marks: list[dict[str, Any]] = [*marks, {"type": "em"}]
            return [
                child for c in node.children for child in _flatten_inline(c, new_marks)
            ]

        case inlines.Strikethrough():
            new_marks: list[dict[str, Any]] = [*marks, {"type": "strike"}]
            return [
                child for c in node.children for child in _flatten_inline(c, new_marks)
            ]

        case inlines.Link():
            link_mark: dict[str, Any] = {"type": "link", "attrs": {"href": node.url}}
            if node.title:
                link_mark["attrs"]["title"] = node.title
            new_marks: list[dict[str, Any]] = [*marks, link_mark]
            return [
                child for c in node.children for child in _flatten_inline(c, new_marks)
            ]

        case inlines.CodeSpan():
            text = {"type": "text", "text": node.code}
            new_marks: list[dict[str, Any]] = [*marks, {"type": "code"}]
            text["marks"] = _sort_marks(new_marks)
            return [text]

        case inlines.HardBreak():
            return [{"type": "hardBreak"}]

        case inlines.SoftBreak():
            return [{"type": "text", "text": " "}]

        case inlines.Image():
            # Inline Image → fallback to link mark + alt text
            link_mark = {"type": "link", "attrs": {"href": node.url}}
            if node.title:
                link_mark["attrs"]["title"] = node.title
            new_marks: list[dict[str, Any]] = [*marks, link_mark]
            alt_text = node.alt or node.url
            text = {"type": "text", "text": alt_text}
            text["marks"] = _sort_marks(new_marks)
            return [text]

        # Difference-set inline nodes
        case inlines.Mention():
            attrs: dict[str, Any] = {"id": node.id}
            if node.text is not None:
                attrs["text"] = node.text
            if node.access_level is not None:
                attrs["accessLevel"] = node.access_level
            if node.user_type is not None:
                attrs["userType"] = node.user_type
            return [{"type": "mention", "attrs": attrs}]

        case inlines.Emoji():
            attrs = {"shortName": node.short_name}
            if node.text is not None:
                attrs["text"] = node.text
            if node.id is not None:
                attrs["id"] = node.id
            return [{"type": "emoji", "attrs": attrs}]

        case inlines.Date():
            return [{"type": "date", "attrs": {"timestamp": node.timestamp}}]

        case inlines.Status():
            attrs = {"text": node.text, "color": node.color}
            if node.style is not None:
                attrs["style"] = node.style
            return [{"type": "status", "attrs": attrs}]

        case inlines.InlineCard():
            attrs = {}
            if node.url is not None:
                attrs["url"] = node.url
            if node.data is not None:
                attrs["data"] = node.data
            return [{"type": "inlineCard", "attrs": attrs}]

        case inlines.MediaInline():
            attrs = {}
            if node.id is not None:
                attrs["id"] = node.id
            if node.collection is not None:
                attrs["collection"] = node.collection
            attrs["type"] = node.media_type
            if node.alt is not None:
                attrs["alt"] = node.alt
            if node.width is not None:
                attrs["width"] = node.width
            if node.height is not None:
                attrs["height"] = node.height
            return [{"type": "mediaInline", "attrs": attrs}]

        case inlines.Placeholder():
            return [{"type": "placeholder", "attrs": {"text": node.text}}]

        case inlines.InlineExtension():
            return [node.raw]

        # Difference-set wrapping marks
        case inlines.Underline():
            new_marks: list[dict[str, Any]] = [*marks, {"type": "underline"}]
            return [
                child for c in node.children for child in _flatten_inline(c, new_marks)
            ]

        case inlines.TextColor():
            new_marks: list[dict[str, Any]] = [
                *marks,
                {"type": "textColor", "attrs": {"color": node.color}},
            ]
            return [
                child for c in node.children for child in _flatten_inline(c, new_marks)
            ]

        case inlines.BackgroundColor():
            new_marks: list[dict[str, Any]] = [
                *marks,
                {"type": "backgroundColor", "attrs": {"color": node.color}},
            ]
            return [
                child for c in node.children for child in _flatten_inline(c, new_marks)
            ]

        case inlines.SubSup():
            new_marks: list[dict[str, Any]] = [
                *marks,
                {"type": "subsup", "attrs": {"type": node.type}},
            ]
            return [
                child for c in node.children for child in _flatten_inline(c, new_marks)
            ]

        case inlines.Annotation():
            new_marks: list[dict[str, Any]] = [
                *marks,
                {
                    "type": "annotation",
                    "attrs": {"id": node.id, "annotationType": node.annotation_type},
                },
            ]
            return [
                child for c in node.children for child in _flatten_inline(c, new_marks)
            ]

        case _:
            return []
