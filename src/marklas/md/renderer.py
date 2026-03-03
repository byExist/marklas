from __future__ import annotations

from marklas.nodes import blocks, inlines


def render(doc: blocks.Document) -> str:
    parts = [_render_block(child) for child in doc.children]
    return "\n\n".join(parts) + "\n" if parts else ""


# ── Block dispatch ────────────────────────────────────────────────────


def _render_block(node: blocks.Block) -> str:
    match node:
        case blocks.Paragraph():
            return _render_paragraph(node)
        case blocks.Heading():
            return _render_heading(node)
        case blocks.CodeBlock():
            return _render_code_block(node)
        case blocks.BlockQuote():
            return _render_blockquote(node)
        case blocks.BulletList():
            return _render_bullet_list(node)
        case blocks.OrderedList():
            return _render_ordered_list(node)
        case blocks.ThematicBreak():
            return "---"
        case blocks.Table():
            return _render_table(node)
        case _:
            return ""


# ── Block renderers ───────────────────────────────────────────────────


def _render_paragraph(node: blocks.Paragraph) -> str:
    return _render_inlines(node.children)


def _render_heading(node: blocks.Heading) -> str:
    prefix = "#" * node.level
    content = _render_inlines(node.children)
    return f"{prefix} {content}"


def _render_code_block(node: blocks.CodeBlock) -> str:
    fence = "````" if "```" in node.code else "```"
    lang = node.language or ""
    return f"{fence}{lang}\n{node.code}\n{fence}"


def _render_blockquote(node: blocks.BlockQuote) -> str:
    inner = "\n\n".join(_render_block(child) for child in node.children)
    lines = inner.split("\n")
    return "\n".join(f"> {line}" if line else ">" for line in lines)


def _render_bullet_list(node: blocks.BulletList) -> str:
    items = [_render_list_item(item, "- ") for item in node.items]
    sep = "\n\n" if not node.tight else "\n"
    return sep.join(items)


def _render_ordered_list(node: blocks.OrderedList) -> str:
    items: list[str] = []
    for i, item in enumerate(node.items):
        num = node.start + i
        items.append(_render_list_item(item, f"{num}. "))
    sep = "\n\n" if not node.tight else "\n"
    return sep.join(items)


def _render_list_item(item: blocks.ListItem, marker: str) -> str:
    if item.checked is True:
        marker = marker.rstrip() + " [x] "
    elif item.checked is False:
        marker = marker.rstrip() + " [ ] "

    content = "\n\n".join(_render_block(child) for child in item.children)
    lines = content.split("\n")
    indent = " " * len(marker)
    result = marker + lines[0]
    for line in lines[1:]:
        result += "\n" + (indent + line if line else "")
    return result


def _render_table(node: blocks.Table) -> str:
    if not node.head:
        return ""

    col_count = len(node.head)

    head_cells = [_render_cell_inlines(cell.children) for cell in node.head]
    header = "| " + " | ".join(head_cells) + " |"

    delimiters: list[str] = []
    for i in range(col_count):
        align = node.alignments[i] if i < len(node.alignments) else None
        match align:
            case "left":
                delimiters.append(":---")
            case "center":
                delimiters.append(":---:")
            case "right":
                delimiters.append("---:")
            case _:
                delimiters.append("---")
    delimiter = "| " + " | ".join(delimiters) + " |"

    rows: list[str] = [header, delimiter]
    for row in node.body:
        cells: list[str] = []
        for i in range(col_count):
            if i < len(row):
                cells.append(_render_cell_inlines(row[i].children))
            else:
                cells.append("")
        rows.append("| " + " | ".join(cells) + " |")

    return "\n".join(rows)


def _render_cell_inlines(nodes: list[inlines.Inline]) -> str:
    return "".join(
        "<br>" if isinstance(node, inlines.HardBreak) else _render_inline(node)
        for node in nodes
    )


# ── Inline dispatch ───────────────────────────────────────────────────


def _render_inlines(nodes: list[inlines.Inline]) -> str:
    return "".join(_render_inline(node) for node in nodes)


def _render_inline(node: inlines.Inline) -> str:
    match node:
        case inlines.Text():
            return node.text
        case inlines.Strong():
            return f"**{_render_inlines(node.children)}**"
        case inlines.Emphasis():
            return f"*{_render_inlines(node.children)}*"
        case inlines.Strikethrough():
            return f"~~{_render_inlines(node.children)}~~"
        case inlines.Link():
            return _render_link(node)
        case inlines.Image():
            return _render_image(node)
        case inlines.CodeSpan():
            return _render_code_span(node)
        case inlines.HardBreak():
            return "\\\n"
        case inlines.SoftBreak():
            return "\n"
        case _:
            return ""


# ── Inline renderers ──────────────────────────────────────────────────


def _render_link(node: inlines.Link) -> str:
    text = _render_inlines(node.children)
    if node.title:
        return f'[{text}]({node.url} "{node.title}")'
    return f"[{text}]({node.url})"


def _render_image(node: inlines.Image) -> str:
    if node.title:
        return f'![{node.alt}]({node.url} "{node.title}")'
    return f"![{node.alt}]({node.url})"


def _render_code_span(node: inlines.CodeSpan) -> str:
    if "`" in node.code:
        return f"`` {node.code} ``"
    return f"`{node.code}`"
