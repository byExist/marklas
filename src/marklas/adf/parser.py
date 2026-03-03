from __future__ import annotations

from typing import Any, Literal, cast

from marklas.adf import schema
from marklas.nodes import blocks, inlines


def parse(doc: dict[str, Any]) -> blocks.Document:
    return blocks.Document(children=_parse_blocks(doc["content"]))


# ── Block dispatch ────────────────────────────────────────────────────


def _parse_blocks(nodes: list[schema.Block]) -> list[blocks.Block]:
    result: list[blocks.Block] = []
    for node in nodes:
        parsed = _parse_block(node)
        if parsed is not None:
            result.append(parsed)
    return result


def _parse_block(node: schema.Block) -> blocks.Block | None:
    t = node["type"]
    match t:
        case "paragraph":
            return _parse_paragraph(cast(schema.Paragraph, node))
        case "heading":
            return _parse_heading(cast(schema.Heading, node))
        case "codeBlock":
            return _parse_code_block(cast(schema.CodeBlock, node))
        case "blockquote":
            return _parse_blockquote(cast(schema.Blockquote, node))
        case "bulletList":
            return _parse_bullet_list(cast(schema.BulletList, node))
        case "orderedList":
            return _parse_ordered_list(cast(schema.OrderedList, node))
        case "taskList":
            return _parse_task_list(cast(schema.TaskList, node))
        case "decisionList":
            return _parse_decision_list(cast(schema.DecisionList, node))
        case "rule":
            return blocks.ThematicBreak()
        case "table":
            return _parse_table(cast(schema.Table, node))
        case "mediaSingle":
            return _parse_media_single(cast(schema.MediaSingle, node))
        case "mediaGroup":
            return _parse_media_group(cast(schema.MediaGroup, node))
        case "panel":
            return _parse_panel(cast(schema.Panel, node))
        case "expand":
            return _parse_expand(cast(schema.Expand, node))
        case "nestedExpand":
            return _parse_nested_expand(cast(schema.NestedExpand, node))
        case "layoutSection":
            return _parse_layout_section(cast(schema.LayoutSection, node))
        case "blockCard":
            return _parse_block_card(cast(schema.BlockCard, node))
        case "embedCard":
            return _parse_embed_card(cast(schema.EmbedCard, node))
        case "extension":
            return blocks.Extension(raw=dict(node))
        case "bodiedExtension":
            return blocks.BodiedExtension(raw=dict(node))
        case "syncBlock":
            return blocks.SyncBlock(raw=dict(node))
        case "bodiedSyncBlock":
            return blocks.BodiedSyncBlock(raw=dict(node))
        case _:
            return blocks.Extension(raw=dict(node))


# ── Block parsers ─────────────────────────────────────────────────────


def _extract_block_marks(
    marks: list[dict[str, Any]],
) -> tuple[str | None, int | None]:
    alignment = indentation = None
    for mark in marks:
        if mark["type"] == "alignment":
            alignment = mark["attrs"]["align"]
        elif mark["type"] == "indentation":
            indentation = mark["attrs"]["level"]
    return alignment, indentation


def _parse_paragraph(node: schema.Paragraph) -> blocks.Paragraph:
    alignment, indentation = _extract_block_marks(node.get("marks", []))
    return blocks.Paragraph(
        children=_parse_inlines(node.get("content", [])),
        alignment=alignment,
        indentation=indentation,
    )


def _parse_heading(node: schema.Heading) -> blocks.Heading:
    level = cast(Literal[1, 2, 3, 4, 5, 6], node["attrs"]["level"])
    alignment, indentation = _extract_block_marks(node.get("marks", []))
    return blocks.Heading(
        level=level,
        children=_parse_inlines(node.get("content", [])),
        alignment=alignment,
        indentation=indentation,
    )


def _parse_code_block(node: schema.CodeBlock) -> blocks.CodeBlock:
    attrs = node.get("attrs")
    language = attrs.get("language") if attrs else None
    code = "".join(c["text"] for c in node.get("content", []) if c["type"] == "text")
    return blocks.CodeBlock(code=code, language=language)


def _parse_blockquote(node: schema.Blockquote) -> blocks.BlockQuote:
    return blocks.BlockQuote(children=_parse_blocks(node["content"]))


def _parse_bullet_list(node: schema.BulletList) -> blocks.BulletList:
    return blocks.BulletList(items=[_parse_list_item(item) for item in node["content"]])


def _parse_ordered_list(node: schema.OrderedList) -> blocks.OrderedList:
    attrs = node.get("attrs")
    start = attrs.get("order", 1) if attrs else 1
    return blocks.OrderedList(
        items=[_parse_list_item(item) for item in node["content"]],
        start=start,
    )


def _parse_list_item(node: schema.ListItem) -> blocks.ListItem:
    return blocks.ListItem(children=_parse_blocks(node["content"]))


def _parse_task_list(node: schema.TaskList) -> blocks.TaskList:
    items: list[blocks.TaskItem] = []
    for item in node["content"]:
        attrs = item["attrs"]
        items.append(
            blocks.TaskItem(
                children=_parse_inlines(item.get("content", [])),
                local_id=attrs["localId"],
                state=attrs["state"],
            )
        )
    return blocks.TaskList(items=items)


def _parse_decision_list(node: schema.DecisionList) -> blocks.DecisionList:
    items: list[blocks.DecisionItem] = []
    for item in node["content"]:
        attrs = item["attrs"]
        items.append(
            blocks.DecisionItem(
                children=_parse_inlines(item.get("content", [])),
                local_id=attrs["localId"],
                state=attrs["state"],
            )
        )
    return blocks.DecisionList(items=items)


def _parse_panel(node: schema.Panel) -> blocks.Panel:
    attrs = node.get("attrs", {})
    return blocks.Panel(
        children=_parse_blocks(node["content"]),
        panel_type=attrs["panelType"],
        panel_icon=attrs.get("panelIcon"),
        panel_icon_id=attrs.get("panelIconId"),
        panel_icon_text=attrs.get("panelIconText"),
        panel_color=attrs.get("panelColor"),
    )


def _parse_expand(node: schema.Expand) -> blocks.Expand:
    attrs = node.get("attrs", {})
    return blocks.Expand(
        children=_parse_blocks(node["content"]),
        title=attrs.get("title"),
    )


def _parse_nested_expand(node: schema.NestedExpand) -> blocks.NestedExpand:
    attrs = node.get("attrs", {})
    return blocks.NestedExpand(
        children=_parse_blocks(node["content"]),
        title=attrs.get("title"),
    )


def _parse_layout_section(node: schema.LayoutSection) -> blocks.LayoutSection:
    columns: list[blocks.LayoutColumn] = []
    for col in node["content"]:
        attrs = col.get("attrs", {})
        columns.append(
            blocks.LayoutColumn(
                children=_parse_blocks(col["content"]),
                width=attrs.get("width"),
            )
        )
    return blocks.LayoutSection(columns=columns)


def _parse_media(node: schema.Media) -> blocks.Media:
    attrs = node["attrs"]
    return blocks.Media(
        media_type=attrs["type"],
        url=attrs.get("url"),
        id=attrs.get("id"),
        collection=attrs.get("collection"),
        alt=attrs.get("alt"),
        width=attrs.get("width"),
        height=attrs.get("height"),
    )


def _parse_media_single(node: schema.MediaSingle) -> blocks.MediaSingle:
    attrs = node.get("attrs", {})
    media_node = node["content"][0]
    return blocks.MediaSingle(
        media=_parse_media(media_node),
        layout=attrs.get("layout"),
        width=attrs.get("width"),
        width_type=attrs.get("widthType"),
    )


def _parse_media_group(node: schema.MediaGroup) -> blocks.MediaGroup:
    return blocks.MediaGroup(
        media_list=[_parse_media(m) for m in node["content"]],
    )


def _parse_block_card(node: schema.BlockCard) -> blocks.BlockCard:
    attrs = node.get("attrs", {})
    return blocks.BlockCard(url=attrs.get("url"), data=attrs.get("data"))


def _parse_embed_card(node: schema.EmbedCard) -> blocks.EmbedCard:
    attrs = node["attrs"]
    return blocks.EmbedCard(
        url=attrs["url"],
        layout=attrs["layout"],
        width=attrs.get("width"),
        original_width=attrs.get("originalWidth"),
        original_height=attrs.get("originalHeight"),
    )


def _parse_table(node: schema.Table) -> blocks.Table:
    rows = node["content"]
    attrs = node.get("attrs", {})
    display_mode: str | None = attrs.get("displayMode")
    is_number_column_enabled: bool | None = attrs.get("isNumberColumnEnabled")
    layout: str | None = attrs.get("layout")
    width: float | None = attrs.get("width")

    if not rows:
        return blocks.Table(
            head=[], body=[],
            display_mode=display_mode,
            is_number_column_enabled=is_number_column_enabled,
            layout=layout, width=width,
        )

    num_rows = len(rows)
    num_cols = 0
    for row in rows:
        cols = 0
        for cell in row["content"]:
            cell_attrs = cell.get("attrs", {})
            cols += cell_attrs.get("colspan", 1)
        num_cols = max(num_cols, cols)

    grid: list[list[blocks.TableCell]] = [
        [blocks.TableCell(children=[]) for _ in range(num_cols)]
        for _ in range(num_rows)
    ]
    occupied: list[list[bool]] = [[False] * num_cols for _ in range(num_rows)]

    for r, row in enumerate(rows):
        col = 0
        for cell in row["content"]:
            while col < num_cols and occupied[r][col]:
                col += 1
            if col >= num_cols:
                break
            cell_attrs = cell.get("attrs", {})
            cs = cell_attrs.get("colspan", 1)
            rs = cell_attrs.get("rowspan", 1)
            parsed = _parse_table_cell(cell)
            grid[r][col] = parsed
            for dr in range(rs):
                for dc in range(cs):
                    if r + dr < num_rows and col + dc < num_cols:
                        occupied[r + dr][col + dc] = True
            col += cs

    cells_row0 = rows[0]["content"]
    is_header = bool(cells_row0 and cells_row0[0]["type"] == "tableHeader")
    head = grid[0] if is_header else []
    body = grid[1:] if is_header else grid
    return blocks.Table(
        head=head, body=body,
        display_mode=display_mode,
        is_number_column_enabled=is_number_column_enabled,
        layout=layout, width=width,
    )


def _parse_table_cell(
    node: schema.TableCell | schema.TableHeader,
) -> blocks.TableCell:
    attrs = node.get("attrs", {})
    cls = blocks.TableHeader if node["type"] == "tableHeader" else blocks.TableCell
    return cls(
        children=_parse_blocks(node["content"]),
        colspan=attrs.get("colspan"),
        rowspan=attrs.get("rowspan"),
        col_width=attrs.get("colwidth"),
        background=attrs.get("background"),
    )


# ── Inline dispatch ───────────────────────────────────────────────────


def _parse_inlines(nodes: list[schema.Inline]) -> list[inlines.Inline]:
    result: list[inlines.Inline] = []
    for node in nodes:
        result.extend(_parse_inline(node))
    return _merge_adjacent(result)


_MERGEABLE = (inlines.Strong, inlines.Emphasis, inlines.Strikethrough, inlines.Underline)


def _merge_adjacent(nodes: list[inlines.Inline]) -> list[inlines.Inline]:
    if len(nodes) < 2:
        return nodes
    result: list[inlines.Inline] = [nodes[0]]
    for node in nodes[1:]:
        prev = result[-1]
        if (
            type(prev) is type(node)
            and isinstance(prev, _MERGEABLE)
            and isinstance(node, _MERGEABLE)
        ):
            prev.children.extend(node.children)
        else:
            result.append(node)
    return result


def _parse_inline(node: schema.Inline) -> list[inlines.Inline]:
    t = node["type"]
    match t:
        case "text":
            return _parse_text(cast(schema.Text, node))
        case "hardBreak":
            return [inlines.HardBreak()]
        case "mention":
            return _parse_mention(cast(schema.Mention, node))
        case "emoji":
            return _parse_emoji(cast(schema.Emoji, node))
        case "date":
            return _parse_date(cast(schema.Date, node))
        case "status":
            return _parse_status(cast(schema.Status, node))
        case "inlineCard":
            return _parse_inline_card(cast(schema.InlineCard, node))
        case "placeholder":
            return _parse_placeholder(cast(schema.Placeholder, node))
        case "mediaInline":
            return _parse_media_inline(cast(schema.MediaInline, node))
        case "inlineExtension":
            return [inlines.InlineExtension(raw=dict(node))]
        case _:
            return [inlines.InlineExtension(raw=dict(node))]


# ── Inline parsers ────────────────────────────────────────────────────


def _parse_text(node: schema.Text) -> list[inlines.Inline]:
    text = node["text"]
    if not text:
        return []
    marks = node.get("marks", [])
    if not marks:
        return [inlines.Text(text=text)]
    return _apply_marks(text, marks)


def _parse_mention(node: schema.Mention) -> list[inlines.Inline]:
    attrs = node["attrs"]
    return [
        inlines.Mention(
            id=attrs["id"],
            text=attrs.get("text"),
            access_level=attrs.get("accessLevel"),
            user_type=attrs.get("userType"),
        )
    ]


def _parse_emoji(node: schema.Emoji) -> list[inlines.Inline]:
    attrs = node["attrs"]
    return [
        inlines.Emoji(
            short_name=attrs["shortName"],
            text=attrs.get("text"),
            id=attrs.get("id"),
        )
    ]


def _parse_date(node: schema.Date) -> list[inlines.Inline]:
    return [inlines.Date(timestamp=node["attrs"]["timestamp"])]


def _parse_status(node: schema.Status) -> list[inlines.Inline]:
    attrs = node["attrs"]
    return [
        inlines.Status(
            text=attrs["text"],
            color=attrs["color"],
            style=attrs.get("style"),
        )
    ]


def _parse_inline_card(node: schema.InlineCard) -> list[inlines.Inline]:
    attrs = node["attrs"]
    return [inlines.InlineCard(url=attrs.get("url"), data=attrs.get("data"))]


def _parse_placeholder(node: schema.Placeholder) -> list[inlines.Inline]:
    return [inlines.Placeholder(text=node["attrs"]["text"])]


def _parse_media_inline(node: schema.MediaInline) -> list[inlines.Inline]:
    attrs = node["attrs"]
    mi = inlines.MediaInline(
        id=attrs.get("id"),
        collection=attrs.get("collection"),
        media_type=attrs.get("type", "file"),
        alt=attrs.get("alt"),
        width=attrs.get("width"),
        height=attrs.get("height"),
    )
    result: list[inlines.Inline] = [mi]
    return result


# ── Mark application ──────────────────────────────────────────────────


def _apply_marks(text: str, marks: list[schema.Mark]) -> list[inlines.Inline]:
    marks = sorted(marks, key=lambda m: schema.MARK_ORDER.get(m.get("type", ""), 99))
    return _wrap_marks(text, marks, 0)


def _wrap_marks(
    text: str, marks: list[schema.Mark], index: int
) -> list[inlines.Inline]:
    if index >= len(marks):
        return [inlines.Text(text=text)]

    mark = marks[index]
    t = mark.get("type", "")

    match t:
        case "code":
            return [inlines.CodeSpan(code=text)]
        case "link":
            attrs = mark.get("attrs", {})
            href = attrs.get("href", "")
            title = attrs.get("title")
            return [
                inlines.Link(
                    url=href,
                    children=_wrap_marks(text, marks, index + 1),
                    title=title,
                )
            ]
        case "strong":
            return [inlines.Strong(children=_wrap_marks(text, marks, index + 1))]
        case "em":
            return [inlines.Emphasis(children=_wrap_marks(text, marks, index + 1))]
        case "strike":
            return [
                inlines.Strikethrough(children=_wrap_marks(text, marks, index + 1))
            ]
        case "underline":
            return [inlines.Underline(children=_wrap_marks(text, marks, index + 1))]
        case "textColor":
            color = mark.get("attrs", {}).get("color", "")
            return [
                inlines.TextColor(
                    color=color, children=_wrap_marks(text, marks, index + 1)
                )
            ]
        case "backgroundColor":
            color = mark.get("attrs", {}).get("color", "")
            return [
                inlines.BackgroundColor(
                    color=color, children=_wrap_marks(text, marks, index + 1)
                )
            ]
        case "subsup":
            sub_type = mark.get("attrs", {}).get("type", "sub")
            return [
                inlines.SubSup(
                    type=sub_type, children=_wrap_marks(text, marks, index + 1)
                )
            ]
        case "annotation":
            ann_id = mark.get("attrs", {}).get("id", "")
            return [
                inlines.Annotation(
                    id=ann_id, children=_wrap_marks(text, marks, index + 1)
                )
            ]
        case _:
            return _wrap_marks(text, marks, index + 1)
