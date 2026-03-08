"""Union AST → Markdown rendering. Difference-set nodes use annotation + fallback."""

from __future__ import annotations

import json
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from marklas.nodes import blocks, inlines

_annotate_ctx: ContextVar[bool] = ContextVar("annotate", default=True)


# ── Public API ───────────────────────────────────────────────────────


def render(doc: blocks.Document, *, annotate: bool = True) -> str:
    token = _annotate_ctx.set(annotate)
    try:
        parts = [_render_block(child) for child in doc.children]
        return "\n\n".join(parts) + "\n" if parts else ""
    finally:
        _annotate_ctx.reset(token)


# ── Annotation helpers ───────────────────────────────────────────────


def _to_tag(node: object) -> str:
    name = type(node).__name__
    return name[0].lower() + name[1:]


def _filter_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _annotate_block(node: object, content: str, **attrs: Any) -> str:
    if not _annotate_ctx.get():
        return content
    tag = _to_tag(node)
    filtered = {k: v for k, v in attrs.items() if v is not None}
    attr_json = f" {json.dumps(filtered, ensure_ascii=False)}" if filtered else ""
    return f"<!-- adf:{tag}{attr_json} -->\n{content}\n<!-- /adf:{tag} -->"


def _annotate_inline(node: object, content: str, **attrs: Any) -> str:
    if not _annotate_ctx.get():
        return content
    tag = _to_tag(node)
    filtered = {k: v for k, v in attrs.items() if v is not None}
    attr_json = f" {json.dumps(filtered, ensure_ascii=False)}" if filtered else ""
    return f"<!-- adf:{tag}{attr_json} -->{content}<!-- /adf:{tag} -->"


# ── Block dispatch ───────────────────────────────────────────────────


def _render_block(node: blocks.Block) -> str:
    match node:
        # Intersection
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
        # Difference-set — Annotated
        case blocks.Panel():
            return _render_panel(node)
        case blocks.Expand():
            return _render_expand(node)
        case blocks.NestedExpand():
            return _render_expand(node)
        case blocks.TaskList():
            return _render_task_list(node)
        case blocks.DecisionList():
            return _render_decision_list(node)
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
        # Difference-set — Placeholder-only
        case blocks.Extension() | blocks.BodiedExtension() \
           | blocks.SyncBlock() | blocks.BodiedSyncBlock():
            return f"`\u2699 Confluence macro`"
        case _:
            return ""


# ── Block renderers ──────────────────────────────────────────────────


def _render_paragraph(node: blocks.Paragraph) -> str:
    content = _render_inlines(node.children)
    if node.alignment or node.indentation:
        return _annotate_block(
            node, content, align=node.alignment, indentation=node.indentation,
        )
    return content


def _render_heading(node: blocks.Heading) -> str:
    content = "#" * node.level + " " + _render_inlines(node.children)
    if node.alignment or node.indentation:
        return _annotate_block(
            node, content, align=node.alignment, indentation=node.indentation,
        )
    return content


def _render_code_block(node: blocks.CodeBlock) -> str:
    lang = node.language or ""
    return f"```{lang}\n{node.code}\n```"


def _render_blockquote(node: blocks.BlockQuote) -> str:
    inner = "\n\n".join(_render_block(c) for c in node.children)
    return "\n".join(f"> {line}" if line else ">" for line in inner.split("\n"))


def _render_bullet_list(node: blocks.BulletList) -> str:
    items: list[str] = []
    for item in node.items:
        if item.checked is not None:
            marker = "- [x] " if item.checked else "- [ ] "
        else:
            marker = "- "
        body = _render_list_item_body(item.children, node.tight)
        items.append(marker + body)
    sep = "\n\n" if not node.tight else "\n"
    return sep.join(items)


def _render_ordered_list(node: blocks.OrderedList) -> str:
    items: list[str] = []
    for i, item in enumerate(node.items):
        num = node.start + i
        body = _render_list_item_body(item.children, node.tight)
        items.append(f"{num}. {body}")
    sep = "\n\n" if not node.tight else "\n"
    return sep.join(items)


def _render_list_item_body(children: list[blocks.Block], tight: bool) -> str:
    if tight and len(children) == 1 and isinstance(children[0], blocks.Paragraph):
        return _render_inlines(children[0].children)
    parts: list[str] = []
    for child in children:
        rendered = _render_block(child)
        parts.append(rendered)
    body = "\n\n".join(parts)
    # Indent lines after the first by 4 spaces
    lines = body.split("\n")
    if len(lines) > 1:
        return lines[0] + "\n" + "\n".join("    " + l if l else "" for l in lines[1:])
    return body


# ── Table ────────────────────────────────────────────────────────────


def _render_table(node: blocks.Table) -> str:
    if node.head:
        col_count = len(node.head)
        head_cells = [_render_cell_blocks(cell.children) for cell in node.head]
    elif node.body:
        col_count = max(len(row) for row in node.body)
        head_cells = [""] * col_count
    else:
        return ""
    header = "| " + " | ".join(head_cells) + " |"

    # delimiter row
    delimiters: list[str] = []
    for i in range(col_count):
        align = node.alignments[i] if i < len(node.alignments) else None
        if align == "center":
            delimiters.append(":---:")
        elif align == "right":
            delimiters.append("---:")
        elif align == "left":
            delimiters.append(":---")
        else:
            delimiters.append("---")
    delimiter = "| " + " | ".join(delimiters) + " |"

    rows = [header, delimiter]
    for body_row in node.body:
        cells = [_render_cell_blocks(cell.children) for cell in body_row]
        # Pad missing cells with empty strings
        while len(cells) < col_count:
            cells.append("")
        rows.append("| " + " | ".join(cells) + " |")

    table_md = "\n".join(rows)

    # Wrap with annotation if table/cell attrs are present
    table_attr_values: list[Any] = [
        node.display_mode, node.is_number_column_enabled,
        node.layout, node.width,
    ]
    has_table_attrs = any(v is not None for v in table_attr_values)
    has_cell_attrs = any(
        cell.colspan or cell.rowspan or cell.col_width or cell.background
        or isinstance(cell, blocks.TableHeader)
        for row_cells in [node.head, *node.body]
        for cell in row_cells
    )
    if has_table_attrs or has_cell_attrs:
        table_attrs: dict[str, Any] = {}
        if node.display_mode is not None:
            table_attrs["displayMode"] = node.display_mode
        if node.is_number_column_enabled is not None:
            table_attrs["isNumberColumnEnabled"] = node.is_number_column_enabled
        if node.layout is not None:
            table_attrs["layout"] = node.layout
        if node.width is not None:
            table_attrs["width"] = node.width
        cell_attrs = _collect_cell_attrs(node)
        if cell_attrs:
            table_attrs["cells"] = cell_attrs
        return _annotate_block(node, table_md, **table_attrs)

    return table_md


def _collect_cell_attrs(node: blocks.Table) -> list[list[Any]] | None:
    """Collect compact cell attrs.

    - ``null`` — all default attributes
    - ``[colwidth]`` (list) — default cell with only colwidth
    - ``{...}`` (dict) — non-default attributes (colspan≠1, rowspan≠1, background, header)
    """
    all_rows = [node.head, *node.body]
    result: list[list[Any]] = []
    has_any = False
    for row in all_rows:
        row_attrs: list[Any] = []
        for cell in row:
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
                has_any = True
                row_attrs.append(attrs)
            elif cell.col_width:
                has_any = True
                row_attrs.append(cell.col_width)
            else:
                row_attrs.append(None)
        result.append(row_attrs)
    return result if has_any else None


def _render_cell_inlines(nodes: list[inlines.Inline]) -> str:
    return "".join(
        "<br>" if isinstance(node, inlines.HardBreak) else _render_inline(node)
        for node in nodes
    )


def _render_cell_blocks(children: list[blocks.Block]) -> str:
    parts: list[str] = []
    for child in children:
        if isinstance(child, blocks.Paragraph):
            parts.append(_render_cell_inlines(child.children))
        elif isinstance(child, blocks.CodeBlock):
            # Code block in table cell: use <code> instead of fences
            code = child.code.replace("\n", "<br>")
            parts.append(f"<code>{code}</code>")
        elif isinstance(child, (blocks.BulletList, blocks.OrderedList)):
            parts.append(_render_cell_list(child))
        else:
            rendered = _render_block(child)
            # HardBreak(\\\n) → <br> first, then remaining newlines → <br>
            rendered = rendered.replace("\\\n", "<br>").replace("\n", "<br>")
            parts.append(rendered)
    return "<br>".join(parts)


def _render_cell_list(node: blocks.BulletList | blocks.OrderedList) -> str:
    """Render lists in table cells as HTML <ul>/<ol> tags."""
    tag = "ol" if isinstance(node, blocks.OrderedList) else "ul"
    start_attr = f' start="{node.start}"' if isinstance(node, blocks.OrderedList) and node.start != 1 else ""
    items: list[str] = []
    for item in node.items:
        body = _render_cell_list_item(item.children)
        items.append(f"<li>{body}</li>")
    return f"<{tag}{start_attr}>{''.join(items)}</{tag}>"


def _render_cell_list_item(children: list[blocks.Block]) -> str:
    """Render list item children as HTML. Supports nested lists."""
    parts: list[str] = []
    for child in children:
        if isinstance(child, blocks.Paragraph):
            parts.append(_render_cell_inlines(child.children))
        elif isinstance(child, (blocks.BulletList, blocks.OrderedList)):
            parts.append(_render_cell_list(child))
        else:
            rendered = _render_block(child)
            rendered = rendered.replace("\\\n", "<br>").replace("\n", "<br>")
            parts.append(rendered)
    return "<br>".join(parts)


# ── Difference-set block rendering ────────────────────────────────────


def _render_panel(node: blocks.Panel) -> str:
    inner = "\n\n".join(_render_block(c) for c in node.children)
    return _annotate_block(
        node, inner,
        panelType=node.panel_type,
        panelIcon=node.panel_icon,
        panelIconId=node.panel_icon_id,
        panelIconText=node.panel_icon_text,
        panelColor=node.panel_color,
    )


def _render_expand(node: blocks.Expand | blocks.NestedExpand) -> str:
    inner = "\n\n".join(_render_block(c) for c in node.children)
    return _annotate_block(node, inner, title=node.title)


def _render_task_list(node: blocks.TaskList) -> str:
    items: list[str] = []
    for item in node.items:
        marker = "- [x] " if item.state == "DONE" else "- [ ] "
        items.append(marker + _render_inlines(item.children))
    return _annotate_block(node, "\n".join(items))


def _render_decision_list(node: blocks.DecisionList) -> str:
    items: list[str] = []
    for item in node.items:
        marker = "- [x] " if item.state == "DECIDED" else "- [ ] "
        items.append(marker + _render_inlines(item.children))
    return _annotate_block(node, "\n".join(items))


def _render_layout_section(node: blocks.LayoutSection) -> str:
    parts: list[str] = []
    for col in node.columns:
        inner = "\n\n".join(_render_block(c) for c in col.children)
        parts.append(_annotate_block(col, inner, width=col.width))
    return _annotate_block(node, "\n\n".join(parts))


def _build_media_dict(media: blocks.Media) -> dict[str, Any]:
    """Build media attrs dict. Omits mediaType when "file" (default)."""
    d: dict[str, Any] = {}
    if media.media_type != "file":
        d["mediaType"] = media.media_type
    d.update(_filter_none({
        "id": media.id, "collection": media.collection,
        "url": media.url, "alt": media.alt,
        "width": media.width, "height": media.height,
    }))
    return d


def _render_media_single(node: blocks.MediaSingle) -> str:
    if node.media.media_type == "external" and node.media.url:
        fallback = f"![{node.media.alt or ''}]({node.media.url})"
    else:
        alt = node.media.alt or "attachment"
        fallback = f"`\U0001F4CE {alt}`"
    media = _build_media_dict(node.media)
    return _annotate_block(
        node, fallback,
        layout=node.layout, width=node.width, widthType=node.width_type, media=media,
    )


def _render_media_group(node: blocks.MediaGroup) -> str:
    fallbacks: list[str] = []
    for m in node.media_list:
        if m.media_type == "external" and m.url:
            fallbacks.append(f"![{m.alt or ''}]({m.url})")
        else:
            alt = m.alt or "attachment"
            fallbacks.append(f"`\U0001F4CE {alt}`")
    media_list = [_build_media_dict(m) for m in node.media_list]
    return _annotate_block(node, "\n".join(fallbacks), mediaList=media_list)


def _render_block_card(node: blocks.BlockCard) -> str:
    fallback = f"[{node.url}]({node.url})" if node.url else "`\U0001F517 card link`"
    return _annotate_block(node, fallback, url=node.url, data=node.data)


def _render_embed_card(node: blocks.EmbedCard) -> str:
    fallback = f"[{node.url}]({node.url})"
    return _annotate_block(
        node, fallback,
        url=node.url, layout=node.layout, width=node.width,
        originalWidth=node.original_width, originalHeight=node.original_height,
    )


# ── Inline rendering ────────────────────────────────────────────────


def _render_inlines(nodes: list[inlines.Inline]) -> str:
    return "".join(_render_inline(node) for node in nodes)


def _wrap_mark(content: str, delimiter: str) -> str:
    """CommonMark compliance: move spaces from inside delimiters to outside."""
    if not content:
        return content
    leading = ""
    trailing = ""
    inner = content
    if inner.startswith(" "):
        leading = " "
        inner = inner[1:]
    if inner.endswith(" "):
        trailing = " "
        inner = inner[:-1]
    if not inner:
        return content
    return f"{leading}{delimiter}{inner}{delimiter}{trailing}"


def _render_inline(node: inlines.Inline) -> str:
    match node:
        # Intersection
        case inlines.Text():
            return node.text
        case inlines.Strong():
            return _wrap_mark(_render_inlines(node.children), "**")
        case inlines.Emphasis():
            return _wrap_mark(_render_inlines(node.children), "*")
        case inlines.Strikethrough():
            return _wrap_mark(_render_inlines(node.children), "~~")
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
        # Difference-set — Annotated
        case inlines.Mention():
            return _render_mention(node)
        case inlines.Emoji():
            return _render_emoji(node)
        case inlines.Date():
            return _render_date(node)
        case inlines.Status():
            return _render_status(node)
        case inlines.InlineCard():
            return _render_inline_card(node)
        case inlines.MediaInline():
            return _render_media_inline(node)
        case inlines.Underline():
            return _render_underline(node)
        case inlines.TextColor():
            return _render_text_color(node)
        case inlines.BackgroundColor():
            return _render_background_color(node)
        case inlines.SubSup():
            return _render_subsup(node)
        case inlines.Annotation():
            return _render_annotation_inline(node)
        # Difference-set — Placeholder-only
        case inlines.Placeholder():
            return ""
        case inlines.InlineExtension():
            return f"`\u2699 inline macro`"
        case _:
            return ""


# ── Intersection inline renderers ─────────────────────────────────────


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
    code = node.code
    if "`" in code:
        return f"`` {code} ``"
    return f"`{code}`"


# ── Difference-set inline renderers ───────────────────────────────────


def _render_mention(node: inlines.Mention) -> str:
    text = node.text or f"@{node.id}"
    fallback = f"`{text}`"
    return _annotate_inline(
        node, fallback,
        id=node.id, text=node.text,
        accessLevel=node.access_level, userType=node.user_type,
    )


def _render_emoji(node: inlines.Emoji) -> str:
    fallback = node.text or f":{node.short_name}:"
    return _annotate_inline(
        node, fallback,
        shortName=node.short_name, text=node.text, id=node.id,
    )


def _render_date(node: inlines.Date) -> str:
    dt = datetime.fromtimestamp(int(node.timestamp) / 1000, tz=UTC)
    fallback = f"`{dt.strftime('%Y-%m-%d')}`"
    return _annotate_inline(node, fallback, timestamp=node.timestamp)


def _render_status(node: inlines.Status) -> str:
    fallback = f"`{node.text}`"
    return _annotate_inline(
        node, fallback,
        text=node.text, color=node.color,
        style=node.style,
    )


def _render_inline_card(node: inlines.InlineCard) -> str:
    if node.url:
        fallback = f"[{node.url}]({node.url})"
    else:
        fallback = "`\U0001F517 card link`"
    # Omit attrs when only url is present and no data (extractable from fallback link)
    if node.url and not node.data:
        return _annotate_inline(node, fallback)
    return _annotate_inline(node, fallback, url=node.url, data=node.data)


def _render_media_inline(node: inlines.MediaInline) -> str:
    alt = node.alt or "attachment"
    fallback = f"`\U0001F4CE {alt}`"
    media_type = None if node.media_type == "file" else node.media_type
    return _annotate_inline(
        node, fallback,
        id=node.id, collection=node.collection,
        mediaType=media_type, alt=node.alt,
        width=node.width, height=node.height,
    )


def _render_underline(node: inlines.Underline) -> str:
    content = _render_inlines(node.children)
    return _annotate_inline(node, content)


def _render_text_color(node: inlines.TextColor) -> str:
    content = _render_inlines(node.children)
    return _annotate_inline(node, content, color=node.color)


def _render_background_color(node: inlines.BackgroundColor) -> str:
    content = _render_inlines(node.children)
    return _annotate_inline(node, content, color=node.color)


def _render_subsup(node: inlines.SubSup) -> str:
    content = _render_inlines(node.children)
    return _annotate_inline(node, content, type=node.type)


def _render_annotation_inline(node: inlines.Annotation) -> str:
    content = _render_inlines(node.children)
    return _annotate_inline(
        node, content,
        id=node.id, annotationType=node.annotation_type,
    )
