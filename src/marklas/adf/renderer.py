"""AST → ADF JSON renderer."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import uuid4

from marklas import ast


# ── Entry point ──────────────────────────────────────────────────────────────


def render(doc: ast.Doc) -> dict[str, Any]:
    """Convert AST Doc to ADF JSON dict."""
    return {
        "type": "doc",
        "version": doc.version,
        "content": _render_children(doc.content, _render_block),
    }


# ── Helpers ──────────────────────────────────────────────────────────────────


def _render_children(
    nodes: Sequence[ast.Node],
    render_fn: Any,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in nodes:
        rendered = render_fn(node)
        if rendered is not None:
            result.append(rendered)
    return result


def _local_id() -> str:
    return str(uuid4())


def _omit_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _with_marks(result: dict[str, Any], marks: Sequence[ast.Mark]) -> dict[str, Any]:
    """Attach marks to a node dict if any exist."""
    if marks:
        result["marks"] = _render_marks(marks)
    return result


# ── Mark rendering ───────────────────────────────────────────────────────────


def _render_mark(mark: ast.Mark) -> dict[str, Any]:
    match mark:
        case ast.StrongMark():
            return {"type": "strong"}
        case ast.EmMark():
            return {"type": "em"}
        case ast.StrikeMark():
            return {"type": "strike"}
        case ast.CodeMark():
            return {"type": "code"}
        case ast.UnderlineMark():
            return {"type": "underline"}
        case ast.LinkMark():
            attrs: dict[str, Any] = {"href": mark.href}
            if mark.title is not None:
                attrs["title"] = mark.title
            return {"type": "link", "attrs": attrs}
        case ast.TextColorMark():
            return {"type": "textColor", "attrs": {"color": mark.color}}
        case ast.BackgroundColorMark():
            return {"type": "backgroundColor", "attrs": {"color": mark.color}}
        case ast.SubSupMark():
            return {"type": "subsup", "attrs": {"type": mark.type}}
        case ast.AnnotationMark():
            return {
                "type": "annotation",
                "attrs": {
                    "id": mark.id,
                    "annotationType": mark.annotation_type,
                },
            }
        case ast.AlignmentMark():
            return {"type": "alignment", "attrs": {"align": mark.align}}
        case ast.IndentationMark():
            return {"type": "indentation", "attrs": {"level": mark.level}}
        case ast.BreakoutMark():
            return {
                "type": "breakout",
                "attrs": _omit_none({"mode": mark.mode, "width": mark.width}),
            }
        case ast.DataConsumerMark():
            return {"type": "dataConsumer", "attrs": {"sources": mark.sources}}
        case ast.BorderMark():
            return {"type": "border", "attrs": {"size": mark.size, "color": mark.color}}
        case _:
            msg = f"Unknown mark type: {type(mark)}"
            raise ValueError(msg)


def _render_marks(marks: Sequence[ast.Mark]) -> list[dict[str, Any]]:
    return [_render_mark(m) for m in marks]


# ── Block dispatch ───────────────────────────────────────────────────────────


def _render_block(node: ast.Node) -> dict[str, Any] | None:
    """Dispatch a block node. Accepts Node because it serves multiple content contexts."""
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
        case ast.MediaSingle():
            return _render_media_single(node)
        case ast.MediaGroup():
            return _render_media_group(node)
        case ast.BlockCard():
            return _render_block_card(node)
        case ast.EmbedCard():
            return _render_embed_card(node)
        case ast.TaskList():
            return _render_task_list(node)
        case ast.DecisionList():
            return _render_decision_list(node)
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
            msg = f"Unknown block node: {type(node)}"
            raise ValueError(msg)


# ── Block renderers ──────────────────────────────────────────────────────────


def _render_paragraph(node: ast.Paragraph) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "paragraph"}
    content = _render_inlines(node.content)
    if content:
        result["content"] = content
    return _with_marks(result, node.marks)


def _render_heading(node: ast.Heading) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "heading",
        "attrs": {"level": node.level},
        "content": _render_inlines(node.content),
    }
    return _with_marks(result, node.marks)


def _render_code_block(node: ast.CodeBlock) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "codeBlock"}
    attrs: dict[str, Any] = {}
    if node.language is not None:
        attrs["language"] = node.language
    if attrs:
        result["attrs"] = attrs
    if node.content:
        text = "".join(t.text for t in node.content)
        if text:
            result["content"] = [{"type": "text", "text": text}]
    return _with_marks(result, node.marks)


def _render_blockquote(node: ast.Blockquote) -> dict[str, Any]:
    return {
        "type": "blockquote",
        "content": _render_children(node.content, _render_block),
    }


def _render_bullet_list(node: ast.BulletList) -> dict[str, Any]:
    return {
        "type": "bulletList",
        "content": [_render_list_item(i) for i in node.content],
    }


def _render_ordered_list(node: ast.OrderedList) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "orderedList",
        "content": [_render_list_item(i) for i in node.content],
    }
    if node.order is not None and node.order != 1:
        result["attrs"] = {"order": node.order}
    return result


def _render_rule() -> dict[str, Any]:
    return {"type": "rule"}


def _render_list_item(node: ast.ListItem) -> dict[str, Any]:
    return {
        "type": "listItem",
        "content": _render_children(node.content, _render_block),
    }


# ── Table ────────────────────────────────────────────────────────────────────


def _render_table(node: ast.Table) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "table",
        "content": [_render_table_row(r) for r in node.content],
    }
    attrs = _omit_none(
        {
            "displayMode": node.display_mode,
            "isNumberColumnEnabled": node.is_number_column_enabled,
            "layout": node.layout,
            "width": node.width,
        }
    )
    if attrs:
        result["attrs"] = attrs
    return result


def _render_table_row(node: ast.TableRow) -> dict[str, Any]:
    return {
        "type": "tableRow",
        "content": [_render_table_cell(c) for c in node.content],
    }


def _render_table_cell(node: ast.TableCell | ast.TableHeader) -> dict[str, Any]:
    cell_type = "tableHeader" if isinstance(node, ast.TableHeader) else "tableCell"
    result: dict[str, Any] = {
        "type": cell_type,
        "content": _render_children(node.content, _render_block),
    }
    attrs = _omit_none(
        {
            "colspan": node.colspan,
            "rowspan": node.rowspan,
            "colwidth": node.colwidth,
            "background": node.background,
        }
    )
    if attrs:
        result["attrs"] = attrs
    return result


# ── Block HTML renderers ────────────────────────────────────────────────────


def _render_panel(node: ast.Panel) -> dict[str, Any]:
    attrs = _omit_none(
        {
            "panelType": node.panel_type,
            "panelIcon": node.panel_icon,
            "panelIconId": node.panel_icon_id,
            "panelIconText": node.panel_icon_text,
            "panelColor": node.panel_color,
        }
    )
    return {
        "type": "panel",
        "attrs": attrs,
        "content": _render_children(node.content, _render_block),
    }


def _render_expand(node: ast.Expand) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "expand",
        "content": _render_children(node.content, _render_block),
    }
    if node.title:
        result["attrs"] = {"title": node.title}
    return _with_marks(result, node.marks)


def _render_nested_expand(node: ast.NestedExpand) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "nestedExpand",
        "attrs": {},
        "content": _render_children(node.content, _render_block),
    }
    if node.title:
        result["attrs"]["title"] = node.title
    return result


def _render_media_single(node: ast.MediaSingle) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    for child in node.content:
        if isinstance(child, ast.Media):
            content.append(_render_media(child))
        else:
            content.append(_render_caption(child))
    result: dict[str, Any] = {"type": "mediaSingle", "content": content}
    attrs = _omit_none(
        {
            "layout": node.layout,
            "width": node.width,
            "widthType": node.width_type,
        }
    )
    if attrs:
        result["attrs"] = attrs
    return _with_marks(result, node.marks)


def _render_media(node: ast.Media) -> dict[str, Any]:
    attrs = _omit_none(
        {
            "type": node.type,
            "id": node.id,
            "collection": node.collection,
            "alt": node.alt,
            "width": node.width,
            "height": node.height,
            "url": node.url,
        }
    )
    result: dict[str, Any] = {"type": "media", "attrs": attrs}
    return _with_marks(result, node.marks)


def _render_caption(node: ast.Caption) -> dict[str, Any]:
    return {"type": "caption", "content": _render_inlines(node.content)}


def _render_media_group(node: ast.MediaGroup) -> dict[str, Any]:
    return {"type": "mediaGroup", "content": [_render_media(m) for m in node.content]}


def _render_block_card(node: ast.BlockCard) -> dict[str, Any]:
    attrs = _omit_none(
        {
            "url": node.url,
            "data": node.data,
            "datasource": node.datasource,
            "width": node.width,
            "layout": node.layout,
        }
    )
    return {"type": "blockCard", "attrs": attrs}


def _render_embed_card(node: ast.EmbedCard) -> dict[str, Any]:
    attrs = _omit_none(
        {
            "url": node.url,
            "layout": node.layout,
            "width": node.width,
            "originalHeight": node.original_height,
            "originalWidth": node.original_width,
        }
    )
    return {"type": "embedCard", "attrs": attrs}


def _render_task_list(node: ast.TaskList) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for child in node.content:
        if isinstance(child, ast.TaskList):
            items.append(_render_task_list(child))
        else:
            items.append(_render_task_item(child))
    return {
        "type": "taskList",
        "attrs": {"localId": _local_id()},
        "content": items,
    }


def _render_task_item(node: ast.TaskItem | ast.BlockTaskItem) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "taskItem" if isinstance(node, ast.TaskItem) else "blockTaskItem",
        "attrs": {"localId": _local_id(), "state": node.state},
    }
    if isinstance(node, ast.TaskItem):
        content = _render_inlines(node.content)
    else:
        content = _render_children(node.content, _render_block)
    if content:
        result["content"] = content
    return result


def _render_decision_list(node: ast.DecisionList) -> dict[str, Any]:
    return {
        "type": "decisionList",
        "attrs": {"localId": _local_id()},
        "content": [_render_decision_item(i) for i in node.content],
    }


def _render_decision_item(node: ast.DecisionItem) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "decisionItem",
        "attrs": {"localId": _local_id(), "state": node.state},
    }
    content = _render_inlines(node.content)
    if content:
        result["content"] = content
    return result


def _render_layout_section(node: ast.LayoutSection) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "layoutSection",
        "content": [_render_layout_column(c) for c in node.content],
    }
    return _with_marks(result, node.marks)


def _render_layout_column(node: ast.LayoutColumn) -> dict[str, Any]:
    return {
        "type": "layoutColumn",
        "attrs": {"width": node.width},
        "content": _render_children(node.content, _render_block),
    }


def _render_extension(node: ast.Extension) -> dict[str, Any]:
    attrs = _omit_none(
        {
            "extensionKey": node.extension_key,
            "extensionType": node.extension_type,
            "parameters": node.parameters,
            "text": node.text,
            "layout": node.layout,
        }
    )
    result: dict[str, Any] = {"type": "extension", "attrs": attrs}
    return _with_marks(result, node.marks)


def _render_bodied_extension(node: ast.BodiedExtension) -> dict[str, Any]:
    attrs = _omit_none(
        {
            "extensionKey": node.extension_key,
            "extensionType": node.extension_type,
            "parameters": node.parameters,
            "text": node.text,
            "layout": node.layout,
        }
    )
    result: dict[str, Any] = {
        "type": "bodiedExtension",
        "attrs": attrs,
        "content": _render_children(node.content, _render_block),
    }
    return _with_marks(result, node.marks)


def _render_sync_block(node: ast.SyncBlock) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "syncBlock",
        "attrs": {"resourceId": node.resource_id},
    }
    return _with_marks(result, node.marks)


def _render_bodied_sync_block(node: ast.BodiedSyncBlock) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "bodiedSyncBlock",
        "attrs": {"resourceId": node.resource_id},
        "content": _render_children(node.content, _render_block),
    }
    return _with_marks(result, node.marks)


# ── Inline dispatch ──────────────────────────────────────────────────────────


def _render_inline(node: ast.Inline) -> dict[str, Any]:
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
            msg = f"Unknown inline node: {type(node)}"
            raise ValueError(msg)


def _render_inlines(nodes: Sequence[ast.Inline]) -> list[dict[str, Any]]:
    return [_render_inline(n) for n in nodes]


# ── Inline renderers ────────────────────────────────────────────────────────


def _render_text(node: ast.Text) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "text", "text": node.text}
    return _with_marks(result, node.marks)


def _render_hard_break() -> dict[str, Any]:
    return {"type": "hardBreak", "attrs": {"text": "\n"}}


def _render_mention(node: ast.Mention) -> dict[str, Any]:
    attrs = _omit_none(
        {
            "id": node.id,
            "text": node.text,
            "accessLevel": node.access_level,
            "userType": node.user_type,
        }
    )
    return {"type": "mention", "attrs": attrs}


def _render_emoji(node: ast.Emoji) -> dict[str, Any]:
    attrs = _omit_none(
        {
            "shortName": node.short_name,
            "text": node.text,
            "id": node.id,
        }
    )
    return {"type": "emoji", "attrs": attrs}


def _render_date(node: ast.Date) -> dict[str, Any]:
    return {"type": "date", "attrs": {"timestamp": node.timestamp}}


def _render_status(node: ast.Status) -> dict[str, Any]:
    attrs = _omit_none(
        {
            "text": node.text,
            "color": node.color,
            "style": node.style,
        }
    )
    return {"type": "status", "attrs": attrs}


def _render_inline_card(node: ast.InlineCard) -> dict[str, Any]:
    attrs = _omit_none({"url": node.url, "data": node.data})
    return {"type": "inlineCard", "attrs": attrs}


def _render_placeholder(node: ast.Placeholder) -> dict[str, Any]:
    return {"type": "placeholder", "attrs": {"text": node.text}}


def _render_media_inline(node: ast.MediaInline) -> dict[str, Any]:
    attrs = _omit_none(
        {
            "id": node.id,
            "collection": node.collection,
            "type": node.type,
            "alt": node.alt,
            "width": node.width,
            "height": node.height,
            "data": node.data,
        }
    )
    result: dict[str, Any] = {"type": "mediaInline", "attrs": attrs}
    return _with_marks(result, node.marks)


def _render_inline_extension(node: ast.InlineExtension) -> dict[str, Any]:
    attrs = _omit_none(
        {
            "extensionKey": node.extension_key,
            "extensionType": node.extension_type,
            "parameters": node.parameters,
            "text": node.text,
        }
    )
    result: dict[str, Any] = {"type": "inlineExtension", "attrs": attrs}
    return _with_marks(result, node.marks)
