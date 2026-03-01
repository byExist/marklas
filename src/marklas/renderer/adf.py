from __future__ import annotations

from uuid import uuid4

from marklas import schema
from marklas.ast import blocks, inlines

# ── Mark ordering ────────────────────────────────────────────────────
# ADF 권장 순서: link > strong > em > strike > code
_MARK_ORDER = {"link": 0, "strong": 1, "em": 2, "strike": 3, "code": 4}


def _sort_marks(marks: list[schema.Mark]) -> list[schema.Mark]:
    return sorted(marks, key=lambda m: _MARK_ORDER.get(m["type"], 99))


# ── Public API ───────────────────────────────────────────────────────


def render(doc: blocks.Document) -> schema.Doc:
    content: list[schema.Block] = []
    for child in doc.children:
        block = _render_block(child)
        if block is not None:
            content.append(block)
    return schema.Doc(type="doc", version=1, content=content)


# ── Block dispatch ───────────────────────────────────────────────────


def _render_block(node: blocks.Block) -> schema.Block | None:
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
            return schema.Rule(type="rule")
        case blocks.BulletList():
            return _render_bullet_list(node)
        case blocks.OrderedList():
            return _render_ordered_list(node)
        case blocks.Table():
            return _render_table(node)
        case _:
            return None


# ── Block renderers ──────────────────────────────────────────────────


def _render_paragraph(node: blocks.Paragraph) -> schema.Block:
    # children이 Image 1개만이면 mediaSingle으로 변환
    if len(node.children) == 1 and isinstance(node.children[0], inlines.Image):
        img = node.children[0]
        media: schema.Media = {
            "type": "media",
            "attrs": {"type": "external", "url": img.url},
        }
        return {"type": "mediaSingle", "content": [media]}

    content = _render_inlines(node.children)
    return schema.Paragraph(type="paragraph", content=content)


def _render_heading(node: blocks.Heading) -> schema.Heading:
    return schema.Heading(
        type="heading",
        attrs={"level": node.level},
        content=_render_inlines(node.children),
    )


def _render_code_block(node: blocks.CodeBlock) -> schema.CodeBlock:
    content: list[schema.Inline] = [schema.Text(type="text", text=node.code)]
    if node.language is not None:
        return schema.CodeBlock(
            type="codeBlock",
            content=content,
            attrs={"language": node.language},
        )
    return schema.CodeBlock(type="codeBlock", content=content)


def _render_blockquote(node: blocks.BlockQuote) -> schema.Blockquote:
    content: list[schema.Block] = []
    for child in node.children:
        block = _render_block(child)
        if block is not None:
            content.append(block)
    return schema.Blockquote(type="blockquote", content=content)


def _render_bullet_list(node: blocks.BulletList) -> schema.BulletList | schema.TaskList:
    # checked 항목이 있으면 taskList
    has_task = any(item.checked is not None for item in node.items)
    if has_task:
        return _render_task_list(node)
    items = [_render_list_item(item) for item in node.items]
    return schema.BulletList(type="bulletList", content=items)


def _render_task_list(node: blocks.BulletList) -> schema.TaskList:
    task_items: list[schema.TaskItem] = []
    for item in node.items:
        state = "DONE" if item.checked else "TODO"
        content = _render_inlines_from_blocks(item.children)
        task_items.append(
            schema.TaskItem(
                type="taskItem",
                attrs={"localId": str(uuid4()), "state": state},
                content=content,
            )
        )
    return schema.TaskList(
        type="taskList",
        attrs={"localId": str(uuid4())},
        content=task_items,
    )


def _render_ordered_list(node: blocks.OrderedList) -> schema.OrderedList:
    items = [_render_list_item(item) for item in node.items]
    if node.start != 1:
        return schema.OrderedList(
            type="orderedList",
            content=items,
            attrs={"order": node.start},
        )
    return schema.OrderedList(type="orderedList", content=items)


def _render_list_item(item: blocks.ListItem) -> schema.ListItem:
    content: list[schema.Block] = []
    for child in item.children:
        block = _render_block(child)
        if block is not None:
            content.append(block)
    return schema.ListItem(type="listItem", content=content)


def _render_table(node: blocks.Table) -> schema.Table:
    rows: list[schema.TableRow] = []

    # head → tableHeader
    if node.head:
        header_cells: list[schema.TableCell | schema.TableHeader] = []
        for cell in node.head:
            cell_content = _render_inlines(cell.children)
            header_cells.append(
                schema.TableHeader(
                    type="tableHeader",
                    content=[schema.Paragraph(type="paragraph", content=cell_content)],
                )
            )
        rows.append(schema.TableRow(type="tableRow", content=header_cells))

    # body → tableCell
    for row in node.body:
        body_cells: list[schema.TableCell | schema.TableHeader] = []
        for cell in row:
            cell_content = _render_inlines(cell.children)
            body_cells.append(
                schema.TableCell(
                    type="tableCell",
                    content=[schema.Paragraph(type="paragraph", content=cell_content)],
                )
            )
        rows.append(schema.TableRow(type="tableRow", content=body_cells))

    return schema.Table(type="table", content=rows)


# ── Inline rendering ─────────────────────────────────────────────────


def _render_inlines(nodes: list[inlines.Inline]) -> list[schema.Inline]:
    result: list[schema.Inline] = []
    for node in nodes:
        result.extend(_flatten_inline(node, []))
    return result


def _render_inlines_from_blocks(
    block_nodes: list[blocks.Block],
) -> list[schema.Inline]:
    """ListItem의 children(블록 리스트)에서 인라인을 추출한다. taskItem content용."""
    result: list[schema.Inline] = []
    for block in block_nodes:
        if isinstance(block, blocks.Paragraph):
            result.extend(_render_inlines(block.children))
    return result


def _flatten_inline(node: inlines.Inline, marks: list[schema.Mark]) -> list[schema.Inline]:
    match node:
        case inlines.Text():
            if not node.text:
                return []
            text: schema.Text = schema.Text(type="text", text=node.text)
            if marks:
                text["marks"] = _sort_marks(marks)
            return [text]

        case inlines.Strong():
            new_marks: list[schema.Mark] = [*marks, schema.Strong(type="strong")]
            result: list[schema.Inline] = []
            for child in node.children:
                result.extend(_flatten_inline(child, new_marks))
            return result

        case inlines.Emphasis():
            new_marks: list[schema.Mark] = [*marks, schema.Em(type="em")]
            result: list[schema.Inline] = []
            for child in node.children:
                result.extend(_flatten_inline(child, new_marks))
            return result

        case inlines.Strikethrough():
            new_marks: list[schema.Mark] = [*marks, schema.Strike(type="strike")]
            result: list[schema.Inline] = []
            for child in node.children:
                result.extend(_flatten_inline(child, new_marks))
            return result

        case inlines.Link():
            link_mark: schema.Link = {"type": "link", "attrs": {"href": node.url}}
            if node.title:
                link_mark["attrs"]["title"] = node.title
            new_marks: list[schema.Mark] = [*marks, link_mark]
            result: list[schema.Inline] = []
            for child in node.children:
                result.extend(_flatten_inline(child, new_marks))
            return result

        case inlines.CodeSpan():
            text = schema.Text(type="text", text=node.code)
            new_marks: list[schema.Mark] = [*marks, schema.Code(type="code")]
            text["marks"] = _sort_marks(new_marks)
            return [text]

        case inlines.HardBreak():
            return [schema.HardBreak(type="hardBreak")]

        case inlines.SoftBreak():
            return [schema.Text(type="text", text=" ")]

        case inlines.Image():
            # 인라인 위치의 Image → link mark + alt 텍스트로 fallback
            link_mark: schema.Link = {"type": "link", "attrs": {"href": node.url}}
            if node.title:
                link_mark["attrs"]["title"] = node.title
            new_marks: list[schema.Mark] = [*marks, link_mark]
            alt_text = node.alt or node.url
            text = schema.Text(type="text", text=alt_text)
            text["marks"] = _sort_marks(new_marks)
            return [text]

        case _:
            return []
