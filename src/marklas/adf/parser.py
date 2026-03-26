"""ADF JSON → AST parser."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, cast

from marklas import ast


# ── Entry point ──────────────────────────────────────────────────────────────


def parse(doc: dict[str, Any]) -> ast.Doc:
    """Convert ADF JSON dict to AST Doc."""
    return ast.Doc(
        content=_parse_doc_children(doc.get("content", [])),
        version=doc.get("version", 1),
    )


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_attrs(node: dict[str, Any]) -> dict[str, Any]:
    return node.get("attrs", {})


def _parse_children(nodes: list[dict[str, Any]]) -> list[ast.Node]:
    return [n for node in nodes if (n := _parse_block(node)) is not None]


def _parse_mark(mark: dict[str, Any]) -> ast.Mark | None:
    attrs = mark.get("attrs", {})
    match mark.get("type"):
        case "strong":
            return ast.StrongMark()
        case "em":
            return ast.EmMark()
        case "strike":
            return ast.StrikeMark()
        case "code":
            return ast.CodeMark()
        case "underline":
            return ast.UnderlineMark()
        case "link":
            return ast.LinkMark(href=attrs.get("href", ""), title=attrs.get("title"))
        case "textColor":
            return ast.TextColorMark(color=attrs.get("color", ""))
        case "backgroundColor":
            return ast.BackgroundColorMark(color=attrs.get("color", ""))
        case "subsup":
            return ast.SubSupMark(type=attrs.get("type", "sub"))
        case "annotation":
            return ast.AnnotationMark(
                id=attrs.get("id", ""),
                annotation_type=attrs.get("annotationType", "inlineComment"),
            )
        case "alignment":
            return ast.AlignmentMark(align=attrs.get("align", "center"))
        case "indentation":
            return ast.IndentationMark(level=attrs.get("level", 1))
        case "breakout":
            return ast.BreakoutMark(
                mode=attrs.get("mode", "wide"), width=attrs.get("width")
            )
        case "dataConsumer":
            return ast.DataConsumerMark(sources=attrs.get("sources", []))
        case "border":
            return ast.BorderMark(
                size=attrs.get("size", 1), color=attrs.get("color", "")
            )
        case "fragment":
            return None  # lossy: editor runtime metadata
        case _:
            msg = f"Unknown mark type: {mark.get('type')}"
            raise ValueError(msg)


def _parse_marks(marks: list[dict[str, Any]]) -> list[ast.Mark]:
    return [m for raw in marks if (m := _parse_mark(raw)) is not None]


# ── Block dispatch ───────────────────────────────────────────────────────────


def _parse_doc_children(nodes: list[dict[str, Any]]) -> list[ast.DocContent]:
    return cast(
        list[ast.DocContent],
        [n for node in nodes if (n := _parse_block(node)) is not None],
    )


def _parse_block(node: dict[str, Any]) -> ast.Node | None:
    match node.get("type"):
        case "paragraph":
            return _parse_paragraph(node)
        case "heading":
            return _parse_heading(node)
        case "codeBlock":
            return _parse_code_block(node)
        case "blockquote":
            return _parse_blockquote(node)
        case "bulletList":
            return _parse_bullet_list(node)
        case "orderedList":
            return _parse_ordered_list(node)
        case "rule":
            return _parse_rule()
        case "table":
            return _parse_table(node)
        case "panel":
            return _parse_panel(node)
        case "expand":
            return _parse_expand(node)
        case "nestedExpand":
            return _parse_nested_expand(node)
        case "mediaSingle":
            return _parse_media_single(node)
        case "mediaGroup":
            return _parse_media_group(node)
        case "blockCard":
            return _parse_block_card(node)
        case "embedCard":
            return _parse_embed_card(node)
        case "taskList":
            return _parse_task_list(node)
        case "decisionList":
            return _parse_decision_list(node)
        case "layoutSection":
            return _parse_layout_section(node)
        case "extension":
            return _parse_extension(node)
        case "bodiedExtension":
            return _parse_bodied_extension(node)
        case "syncBlock":
            return _parse_sync_block(node)
        case "bodiedSyncBlock":
            return _parse_bodied_sync_block(node)
        case _:
            return None


# ── Block parsers ────────────────────────────────────────────────────────────


def _parse_paragraph(node: dict[str, Any]) -> ast.Paragraph:
    return ast.Paragraph(
        content=_parse_inlines(node.get("content", [])),
        marks=_parse_marks(node.get("marks", [])),
    )


def _parse_heading(node: dict[str, Any]) -> ast.Heading:
    attrs = _get_attrs(node)
    return ast.Heading(
        level=attrs.get("level", 1),
        content=_parse_inlines(node.get("content", [])),
        marks=_parse_marks(node.get("marks", [])),
    )


def _parse_code_block(node: dict[str, Any]) -> ast.CodeBlock:
    attrs = _get_attrs(node)
    code = "".join(
        c["text"] for c in node.get("content", []) if c.get("type") == "text"
    )
    content = [ast.Text(text=code)] if code else []
    return ast.CodeBlock(
        language=attrs.get("language"),
        content=content,
        marks=cast(Sequence[ast.BreakoutMark], _parse_marks(node.get("marks", []))),
    )


def _parse_blockquote(node: dict[str, Any]) -> ast.Blockquote:
    return ast.Blockquote(
        content=cast(
            list[ast.BlockquoteContent], _parse_children(node.get("content", []))
        )
    )


def _parse_bullet_list(node: dict[str, Any]) -> ast.BulletList:
    return ast.BulletList(
        content=[_parse_list_item(i) for i in node.get("content", [])]
    )


def _parse_ordered_list(node: dict[str, Any]) -> ast.OrderedList:
    attrs = _get_attrs(node)
    order = attrs.get("order", 1)
    return ast.OrderedList(
        content=[_parse_list_item(i) for i in node.get("content", [])],
        order=order if order != 1 else None,
    )


def _parse_rule() -> ast.Rule:
    return ast.Rule()


def _parse_list_item(node: dict[str, Any]) -> ast.ListItem:
    return ast.ListItem(
        content=cast(
            list[ast.ListItemContent], _parse_children(node.get("content", []))
        )
    )


# ── Table ────────────────────────────────────────────────────────────────────


def _parse_table(node: dict[str, Any]) -> ast.Table:
    attrs = _get_attrs(node)
    return ast.Table(
        content=[_parse_table_row(r) for r in node.get("content", [])],
        display_mode=attrs.get("displayMode"),
        is_number_column_enabled=attrs.get("isNumberColumnEnabled"),
        layout=attrs.get("layout"),
        width=attrs.get("width"),
    )


def _parse_table_row(node: dict[str, Any]) -> ast.TableRow:
    return ast.TableRow(content=[_parse_table_cell(c) for c in node.get("content", [])])


def _parse_table_cell(node: dict[str, Any]) -> ast.TableCell | ast.TableHeader:
    attrs = _get_attrs(node)
    cls = ast.TableHeader if node.get("type") == "tableHeader" else ast.TableCell
    return cls(
        content=cast(
            list[ast.TableCellContent], _parse_children(node.get("content", []))
        ),
        colspan=attrs.get("colspan"),
        rowspan=attrs.get("rowspan"),
        colwidth=attrs.get("colwidth"),
        background=attrs.get("background"),
    )


# ── Block HTML parsers ───────────────────────────────────────────────────────


def _parse_panel(node: dict[str, Any]) -> ast.Panel:
    attrs = _get_attrs(node)
    return ast.Panel(
        panel_type=attrs.get("panelType", "info"),
        content=cast(list[ast.PanelContent], _parse_children(node.get("content", []))),
        panel_icon=attrs.get("panelIcon"),
        panel_icon_id=attrs.get("panelIconId"),
        panel_icon_text=attrs.get("panelIconText"),
        panel_color=attrs.get("panelColor"),
    )


def _parse_expand(node: dict[str, Any]) -> ast.Expand:
    attrs = _get_attrs(node)
    return ast.Expand(
        content=cast(list[ast.ExpandContent], _parse_children(node.get("content", []))),
        title=attrs.get("title"),
        marks=cast(Sequence[ast.BreakoutMark], _parse_marks(node.get("marks", []))),
    )


def _parse_nested_expand(node: dict[str, Any]) -> ast.NestedExpand:
    attrs = _get_attrs(node)
    return ast.NestedExpand(
        content=cast(
            list[ast.NestedExpandContent], _parse_children(node.get("content", []))
        ),
        title=attrs.get("title"),
    )


def _parse_media_single(node: dict[str, Any]) -> ast.MediaSingle:
    attrs = _get_attrs(node)
    content: list[ast.Media | ast.Caption] = []
    for child in node.get("content", []):
        if child.get("type") == "media":
            content.append(_parse_media(child))
        elif child.get("type") == "caption":
            content.append(_parse_caption(child))
    return ast.MediaSingle(
        content=content,
        layout=attrs.get("layout"),
        width=attrs.get("width"),
        width_type=attrs.get("widthType"),
        marks=cast(Sequence[ast.LinkMark], _parse_marks(node.get("marks", []))),
    )


def _parse_media(node: dict[str, Any]) -> ast.Media:
    attrs = _get_attrs(node)
    return ast.Media(
        type=attrs.get("type", "file"),
        id=attrs.get("id"),
        collection=attrs.get("collection"),
        alt=attrs.get("alt"),
        width=attrs.get("width"),
        height=attrs.get("height"),
        url=attrs.get("url"),
        marks=cast(
            Sequence[ast.LinkMark | ast.AnnotationMark | ast.BorderMark],
            _parse_marks(node.get("marks", [])),
        ),
    )


def _parse_caption(node: dict[str, Any]) -> ast.Caption:
    return ast.Caption(
        content=cast(list[ast.CaptionContent], _parse_inlines(node.get("content", [])))
    )


def _parse_media_group(node: dict[str, Any]) -> ast.MediaGroup:
    return ast.MediaGroup(content=[_parse_media(m) for m in node.get("content", [])])


def _parse_block_card(node: dict[str, Any]) -> ast.BlockCard:
    attrs = _get_attrs(node)
    return ast.BlockCard(
        url=attrs.get("url"),
        datasource=attrs.get("datasource"),
        width=attrs.get("width"),
        layout=attrs.get("layout"),
        data=attrs.get("data"),
    )


def _parse_embed_card(node: dict[str, Any]) -> ast.EmbedCard:
    attrs = _get_attrs(node)
    return ast.EmbedCard(
        url=attrs.get("url", ""),
        layout=attrs.get("layout", "center"),
        width=attrs.get("width"),
        original_height=attrs.get("originalHeight"),
        original_width=attrs.get("originalWidth"),
    )


def _parse_task_list(node: dict[str, Any]) -> ast.TaskList:
    items: list[ast.TaskItem | ast.BlockTaskItem | ast.TaskList] = []
    for child in node.get("content", []):
        match child.get("type"):
            case "taskList":
                items.append(_parse_task_list(child))
            case "taskItem":
                items.append(_parse_task_item(child))
            case "blockTaskItem":
                items.append(_parse_task_item(child))
            case _:
                msg = f"Unknown taskList child: {child.get('type')}"
                raise ValueError(msg)
    return ast.TaskList(content=items)


def _parse_task_item(node: dict[str, Any]) -> ast.TaskItem | ast.BlockTaskItem:
    attrs = _get_attrs(node)
    state = attrs.get("state", "TODO")
    content = node.get("content", [])

    # blockTaskItem or taskItem with block children → BlockTaskItem
    if node.get("type") == "blockTaskItem" or (
        content
        and content[0].get("type")
        not in (
            "text",
            "hardBreak",
            "mention",
            "emoji",
            "date",
            "status",
            "inlineCard",
            "placeholder",
            "mediaInline",
            "inlineExtension",
        )
    ):
        return ast.BlockTaskItem(
            state=state,
            content=cast(list[ast.BlockTaskItemContent], _parse_children(content)),
        )

    return ast.TaskItem(
        state=state,
        content=_parse_inlines(content),
    )


def _parse_decision_list(node: dict[str, Any]) -> ast.DecisionList:
    return ast.DecisionList(
        content=[_parse_decision_item(i) for i in node.get("content", [])],
    )


def _parse_decision_item(node: dict[str, Any]) -> ast.DecisionItem:
    attrs = _get_attrs(node)
    return ast.DecisionItem(
        state=attrs.get("state", "DECIDED"),
        content=_parse_inlines(node.get("content", [])),
    )


def _parse_layout_section(node: dict[str, Any]) -> ast.LayoutSection:
    return ast.LayoutSection(
        content=[_parse_layout_column(c) for c in node.get("content", [])],
        marks=cast(Sequence[ast.BreakoutMark], _parse_marks(node.get("marks", []))),
    )


def _parse_layout_column(node: dict[str, Any]) -> ast.LayoutColumn:
    attrs = _get_attrs(node)
    return ast.LayoutColumn(
        width=attrs.get("width", 50),
        content=cast(list[ast.BlockContent], _parse_children(node.get("content", []))),
    )


def _parse_extension(node: dict[str, Any]) -> ast.Extension:
    attrs = _get_attrs(node)
    return ast.Extension(
        extension_key=attrs.get("extensionKey", ""),
        extension_type=attrs.get("extensionType", ""),
        parameters=attrs.get("parameters"),
        text=attrs.get("text"),
        layout=attrs.get("layout"),
        marks=_parse_marks(node.get("marks", [])),
    )


def _parse_bodied_extension(node: dict[str, Any]) -> ast.BodiedExtension:
    attrs = _get_attrs(node)
    return ast.BodiedExtension(
        extension_key=attrs.get("extensionKey", ""),
        extension_type=attrs.get("extensionType", ""),
        content=cast(
            list[ast.NonNestableBlockContent], _parse_children(node.get("content", []))
        ),
        parameters=attrs.get("parameters"),
        text=attrs.get("text"),
        layout=attrs.get("layout"),
        marks=_parse_marks(node.get("marks", [])),
    )


def _parse_sync_block(node: dict[str, Any]) -> ast.SyncBlock:
    attrs = _get_attrs(node)
    return ast.SyncBlock(
        resource_id=attrs.get("resourceId", ""),
        marks=cast(Sequence[ast.BreakoutMark], _parse_marks(node.get("marks", []))),
    )


def _parse_bodied_sync_block(node: dict[str, Any]) -> ast.BodiedSyncBlock:
    attrs = _get_attrs(node)
    return ast.BodiedSyncBlock(
        resource_id=attrs.get("resourceId", ""),
        content=cast(
            list[ast.BodiedSyncBlockContent], _parse_children(node.get("content", []))
        ),
        marks=cast(Sequence[ast.BreakoutMark], _parse_marks(node.get("marks", []))),
    )


# ── Inline dispatch ──────────────────────────────────────────────────────────


_SURROGATE_RE = re.compile(
    r"\\u([Dd][89AaBb][0-9A-Fa-f]{2})\\u([Dd][CcDdEeFf][0-9A-Fa-f]{2})"
)


def _resolve_emoji_text(text: str | None, emoji_id: str | None) -> str | None:
    """Decode surrogate pair literals (e.g. '\\uD83D\\uDDD3') to actual unicode."""
    if text and "\\u" in text:

        def _replace(m: re.Match[str]) -> str:
            high = int(m.group(1), 16)
            low = int(m.group(2), 16)
            code_point = 0x10000 + (high - 0xD800) * 0x400 + (low - 0xDC00)
            return chr(code_point)

        decoded = _SURROGATE_RE.sub(_replace, text)
        if decoded != text:
            return decoded
    if text:
        return text
    if emoji_id:
        return chr(int(emoji_id, 16))
    return None


def _parse_inlines(nodes: list[dict[str, Any]]) -> list[ast.Inline]:
    return [n for node in nodes if (n := _parse_inline(node)) is not None]


def _parse_inline(node: dict[str, Any]) -> ast.Inline | None:
    match node.get("type"):
        case "text":
            return _parse_text(node)
        case "hardBreak":
            return _parse_hard_break()
        case "mention":
            return _parse_mention(node)
        case "emoji":
            return _parse_emoji(node)
        case "date":
            return _parse_date(node)
        case "status":
            return _parse_status(node)
        case "inlineCard":
            return _parse_inline_card(node)
        case "placeholder":
            return _parse_placeholder(node)
        case "mediaInline":
            return _parse_media_inline(node)
        case "inlineExtension":
            return _parse_inline_extension(node)
        case _:
            return None


# ── Inline parsers ───────────────────────────────────────────────────────────


def _parse_text(node: dict[str, Any]) -> ast.Text:
    return ast.Text(
        text=node.get("text", ""),
        marks=_parse_marks(node.get("marks", [])),
    )


def _parse_hard_break() -> ast.HardBreak:
    return ast.HardBreak()


def _parse_mention(node: dict[str, Any]) -> ast.Mention:
    attrs = _get_attrs(node)
    return ast.Mention(
        id=attrs.get("id", ""),
        text=attrs.get("text"),
        access_level=attrs.get("accessLevel"),
        user_type=attrs.get("userType"),
    )


def _parse_emoji(node: dict[str, Any]) -> ast.Emoji:
    attrs = _get_attrs(node)
    emoji_id = attrs.get("id")
    text = _resolve_emoji_text(attrs.get("text"), emoji_id)
    return ast.Emoji(
        short_name=attrs.get("shortName", ""),
        id=emoji_id,
        text=text,
    )


def _parse_date(node: dict[str, Any]) -> ast.Date:
    return ast.Date(timestamp=_get_attrs(node).get("timestamp", ""))


def _parse_status(node: dict[str, Any]) -> ast.Status:
    attrs = _get_attrs(node)
    return ast.Status(
        text=attrs.get("text", ""),
        color=attrs.get("color", "neutral"),
        style=attrs.get("style"),
    )


def _parse_inline_card(node: dict[str, Any]) -> ast.InlineCard:
    attrs = _get_attrs(node)
    return ast.InlineCard(url=attrs.get("url"), data=attrs.get("data"))


def _parse_placeholder(node: dict[str, Any]) -> ast.Placeholder:
    return ast.Placeholder(text=_get_attrs(node).get("text", ""))


def _parse_media_inline(node: dict[str, Any]) -> ast.MediaInline:
    attrs = _get_attrs(node)
    return ast.MediaInline(
        id=attrs.get("id", ""),
        collection=attrs.get("collection", ""),
        type=attrs.get("type"),
        alt=attrs.get("alt"),
        width=attrs.get("width"),
        height=attrs.get("height"),
        data=attrs.get("data"),
        marks=cast(
            Sequence[ast.LinkMark | ast.AnnotationMark | ast.BorderMark],
            _parse_marks(node.get("marks", [])),
        ),
    )


def _parse_inline_extension(node: dict[str, Any]) -> ast.InlineExtension:
    attrs = _get_attrs(node)
    return ast.InlineExtension(
        extension_key=attrs.get("extensionKey", ""),
        extension_type=attrs.get("extensionType", ""),
        parameters=attrs.get("parameters"),
        text=attrs.get("text"),
        marks=_parse_marks(node.get("marks", [])),
    )
