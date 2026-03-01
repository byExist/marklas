from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, cast

from marklas import adf
from marklas.ast import blocks, inlines


def parse(doc: adf.Doc) -> blocks.Document:
    return blocks.Document(children=_parse_blocks(doc["content"]))


# ── Block dispatch ────────────────────────────────────────────────────


def _parse_blocks(nodes: list[adf.Block]) -> list[blocks.Block]:
    result: list[blocks.Block] = []
    for node in nodes:
        parsed = _parse_block(node)
        if parsed is not None:
            if isinstance(parsed, list):
                result.extend(parsed)
            else:
                result.append(parsed)
    return result


def _parse_block(
    node: adf.Block,
) -> blocks.Block | list[blocks.Block] | None:
    t = node["type"]
    match t:
        case "paragraph":
            return _parse_paragraph(cast(adf.Paragraph, node))
        case "heading":
            return _parse_heading(cast(adf.Heading, node))
        case "codeBlock":
            return _parse_code_block(cast(adf.CodeBlock, node))
        case "blockquote":
            return _parse_blockquote(cast(adf.Blockquote, node))
        case "bulletList":
            return _parse_bullet_list(cast(adf.BulletList, node))
        case "orderedList":
            return _parse_ordered_list(cast(adf.OrderedList, node))
        case "taskList":
            return _parse_task_list(cast(adf.TaskList, node))
        case "decisionList":
            return _parse_decision_list(cast(adf.DecisionList, node))
        case "rule":
            return blocks.ThematicBreak()
        case "table":
            return _parse_table(cast(adf.Table, node))
        case "mediaSingle":
            return _parse_media_single(cast(adf.MediaSingle, node))
        case "mediaGroup":
            return _parse_media_group(cast(adf.MediaGroup, node))
        case "panel":
            return _parse_panel(cast(adf.Panel, node))
        case "expand":
            return _parse_expand(cast(adf.Expand, node))
        case "nestedExpand":
            return _parse_expand(cast(adf.Expand, node))
        case "layoutSection":
            return _parse_layout_section(cast(adf.LayoutSection, node))
        case "blockCard":
            return _parse_block_card(cast(adf.BlockCard, node))
        case "embedCard":
            return _parse_embed_card(cast(adf.EmbedCard, node))
        case _:
            return blocks.Paragraph(children=[inlines.Text(text=f"[{t}]")])


# ── Block parsers ─────────────────────────────────────────────────────


def _parse_paragraph(node: adf.Paragraph) -> blocks.Paragraph:
    return blocks.Paragraph(children=_parse_inlines(node["content"]))


def _parse_heading(node: adf.Heading) -> blocks.Heading:
    level = cast(Literal[1, 2, 3, 4, 5, 6], node["attrs"]["level"])
    return blocks.Heading(level=level, children=_parse_inlines(node["content"]))


def _parse_code_block(node: adf.CodeBlock) -> blocks.CodeBlock:
    attrs = node.get("attrs")
    language = attrs.get("language") if attrs else None
    code = "".join(c["text"] for c in node["content"] if c["type"] == "text")
    return blocks.CodeBlock(code=code, language=language)


def _parse_blockquote(node: adf.Blockquote) -> blocks.BlockQuote:
    return blocks.BlockQuote(children=_parse_blocks(node["content"]))


def _parse_bullet_list(node: adf.BulletList) -> blocks.BulletList:
    return blocks.BulletList(items=[_parse_list_item(item) for item in node["content"]])


def _parse_ordered_list(node: adf.OrderedList) -> blocks.OrderedList:
    attrs = node.get("attrs")
    start = attrs.get("order", 1) if attrs else 1
    return blocks.OrderedList(
        items=[_parse_list_item(item) for item in node["content"]],
        start=start,
    )


def _parse_list_item(node: adf.ListItem) -> blocks.ListItem:
    return blocks.ListItem(children=_parse_blocks(node["content"]))


def _parse_task_list(node: adf.TaskList) -> blocks.BulletList:
    items: list[blocks.ListItem] = []
    for item in node["content"]:
        checked = item["attrs"]["state"] == "DONE"
        children = _parse_inlines(item["content"])
        items.append(
            blocks.ListItem(
                children=[blocks.Paragraph(children=children)] if children else [],
                checked=checked,
            )
        )
    return blocks.BulletList(items=items)


def _parse_decision_list(node: adf.DecisionList) -> blocks.BulletList:
    items: list[blocks.ListItem] = []
    for item in node["content"]:
        checked = item["attrs"]["state"] == "DECIDED"
        children = _parse_inlines(item["content"])
        items.append(
            blocks.ListItem(
                children=[blocks.Paragraph(children=children)] if children else [],
                checked=checked,
            )
        )
    return blocks.BulletList(items=items)


def _parse_table(node: adf.Table) -> blocks.Table:
    head: list[blocks.TableCell] = []
    body: list[list[blocks.TableCell]] = []
    for i, row in enumerate(node["content"]):
        cells = row["content"]
        if i == 0 and cells and cells[0]["type"] == "tableHeader":
            head = [_parse_table_cell(c) for c in cells]
        else:
            body.append([_parse_table_cell(c) for c in cells])
    return blocks.Table(head=head, body=body)


def _parse_table_cell(
    node: adf.TableCell | adf.TableHeader,
) -> blocks.TableCell:
    result: list[inlines.Inline] = []
    for block in node["content"]:
        if block["type"] == "paragraph":
            result.extend(_parse_inlines(cast(adf.Paragraph, block)["content"]))
    return blocks.TableCell(children=result)


def _parse_media_single(node: adf.MediaSingle) -> blocks.Paragraph:
    for media in node["content"]:
        inline = _media_to_inline(media)
        if inline is not None:
            return blocks.Paragraph(children=[inline])
    return blocks.Paragraph(children=[])


def _parse_media_group(node: adf.MediaGroup) -> blocks.Paragraph:
    result: list[inlines.Inline] = []
    for media in node["content"]:
        inline = _media_to_inline(media)
        if inline is not None:
            result.append(inline)
    return blocks.Paragraph(children=result)


def _media_to_inline(media: adf.Media) -> inlines.Inline | None:
    attrs = media["attrs"]
    media_type = attrs["type"]
    if media_type == "external":
        url = attrs.get("url", "")
        alt = attrs.get("alt", "")
        return inlines.Image(url=url, alt=alt)
    alt = attrs.get("alt") or attrs.get("id", "")
    return inlines.Text(text=f"[Image: {alt}]") if alt else None


def _parse_panel(node: adf.Panel) -> blocks.BlockQuote:
    return blocks.BlockQuote(children=_parse_blocks(node["content"]))


def _parse_expand(node: adf.Expand) -> blocks.BlockQuote:
    attrs = node.get("attrs")
    title = attrs.get("title") if attrs else None
    children = _parse_blocks(node["content"])
    if title:
        children.insert(0, blocks.Paragraph(children=[inlines.Text(text=title)]))
    return blocks.BlockQuote(children=children)


def _parse_layout_section(node: adf.LayoutSection) -> list[blocks.Block]:
    result: list[blocks.Block] = []
    for column in node["content"]:
        result.extend(_parse_blocks(column["content"]))
    return result


def _parse_block_card(node: adf.BlockCard) -> blocks.Paragraph:
    attrs = node.get("attrs")
    url = attrs.get("url") if attrs else None
    if url:
        return blocks.Paragraph(
            children=[inlines.Link(url=url, children=[inlines.Text(text=url)])]
        )
    return blocks.Paragraph(children=[])


def _parse_embed_card(node: adf.EmbedCard) -> blocks.Paragraph | None:
    url = node["attrs"]["url"]
    if not url:
        return None
    return blocks.Paragraph(
        children=[inlines.Link(url=url, children=[inlines.Text(text=url)])]
    )


# ── Inline dispatch ───────────────────────────────────────────────────


def _parse_inlines(nodes: list[adf.Inline]) -> list[inlines.Inline]:
    result: list[inlines.Inline] = []
    for node in nodes:
        result.extend(_parse_inline(node))
    return result


def _parse_inline(node: adf.Inline) -> list[inlines.Inline]:
    t = node["type"]
    match t:
        case "text":
            return _parse_text(cast(adf.Text, node))
        case "hardBreak":
            return [inlines.HardBreak()]
        case "mention":
            return _parse_mention(cast(adf.Mention, node))
        case "emoji":
            return _parse_emoji(cast(adf.Emoji, node))
        case "date":
            return _parse_date(cast(adf.Date, node))
        case "status":
            return _parse_status(cast(adf.Status, node))
        case "inlineCard":
            return _parse_inline_card(cast(adf.InlineCard, node))
        case _:
            return [inlines.Text(text=f"[{t}]")]


# ── Inline parsers ────────────────────────────────────────────────────


def _parse_text(node: adf.Text) -> list[inlines.Inline]:
    text = node["text"]
    if not text:
        return []
    marks = node.get("marks", [])
    if not marks:
        return [inlines.Text(text=text)]
    return _apply_marks(text, marks)


def _parse_mention(node: adf.Mention) -> list[inlines.Inline]:
    attrs = node["attrs"]
    text = attrs.get("text") or f"@{attrs['id']}"
    return [inlines.CodeSpan(code=text)]


def _parse_emoji(node: adf.Emoji) -> list[inlines.Inline]:
    attrs = node["attrs"]
    text = attrs.get("text") or f":{attrs['shortName']}:"
    return [inlines.Text(text=text)]


def _parse_date(node: adf.Date) -> list[inlines.Inline]:
    timestamp = node["attrs"]["timestamp"]
    dt = datetime.fromtimestamp(int(timestamp) / 1000, tz=UTC)
    return [inlines.CodeSpan(code=dt.strftime("%Y-%m-%d"))]


def _parse_status(node: adf.Status) -> list[inlines.Inline]:
    return [inlines.CodeSpan(code=node["attrs"]["text"])]


def _parse_inline_card(node: adf.InlineCard) -> list[inlines.Inline]:
    url = node["attrs"].get("url")
    if not url:
        return []
    return [inlines.Link(url=url, children=[inlines.Text(text=url)])]


# ── Mark application ──────────────────────────────────────────────────


_MARK_ORDER = {"code": 0, "link": 1, "strong": 2, "em": 3, "strike": 4}
_IGNORED_MARKS = {"underline", "textColor", "backgroundColor", "subsup"}


def _apply_marks(text: str, marks: list[adf.Mark]) -> list[inlines.Inline]:
    supported = [m for m in marks if m.get("type") not in _IGNORED_MARKS]
    supported.sort(key=lambda m: _MARK_ORDER.get(m.get("type", ""), 99))
    return _wrap_marks(text, supported, 0)


def _wrap_marks(text: str, marks: list[adf.Mark], index: int) -> list[inlines.Inline]:
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
                    url=href, children=_wrap_marks(text, marks, index + 1), title=title
                )
            ]
        case "strong":
            return [inlines.Strong(children=_wrap_marks(text, marks, index + 1))]
        case "em":
            return [inlines.Emphasis(children=_wrap_marks(text, marks, index + 1))]
        case "strike":
            return [inlines.Strikethrough(children=_wrap_marks(text, marks, index + 1))]
        case _:
            return _wrap_marks(text, marks, index + 1)
