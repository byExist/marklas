"""Block-level dispatch and per-node builders.

Public entry: `dispatch_blocks(tokens)`. The dispatcher is generator-shaped
and yields `ast.Node` for every input token that maps to a block-level AST
node. Container parsers narrow the stream to their schema with
`ir.collect` + a `TypeGuard` predicate.

This module is organized into three layers:

1. **Dispatch** — `dispatch_blocks` walks normalized tokens, threads
   pending mark/table-meta state attached by previous metadata tokens,
   and routes each token to a builder via `match`.

2. **Builders** — one per AST node type. Builders for HTML-extension
   blocks (Panel, Expand, MediaSingle, …) consume `HtmlPaired.inner`,
   which is a list of raw mistune tokens carried across pairing; they
   re-normalize and re-dispatch as needed.

3. **Cell sub-system** — at the bottom of the file. Table cells are a
   different beast because mistune tokenizes their entire content as
   inline (no block_html), so we need a parallel grouping/promotion
   pipeline that maps inline_html paired groups back to block-level
   nodes.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from typing import Any, cast

from marklas import ast

from .cell import group_inline_html as _group_cell_inline_html, parse_cell_content
from .inline import (
    inline_mark_from,
    parse_inlines,
    parse_normalized_inlines,
    reparse_text_inlines,
)
from .ir import (
    HtmlPaired,
    HtmlVoid,
    Token,
    collect,
    is_blockquote,
    is_bodied_sync,
    is_caption,
    is_expand,
    is_list_item,
    is_nested_expand,
    is_non_nestable,
    is_panel,
)
from .normalize import (
    find_paired_close,
    attach_marks,
    block_html_to_inline,
    get_params,
    inline_content_text,
    media_border_marks,
    normalize_blocks,
    normalize_inlines,
    parse_block_marks,
    parse_tag,
)


# Matches HTML <br> in any of its case/whitespace variants. Used to undo the
# renderer's "<code>...<br>...</code>" encoding of newlines inside table cells.
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)


# ── Dispatch ──────────────────────────────────────────────────────────────────


def dispatch_blocks(
    tokens: list[Token], *, list_item: bool = False
) -> Iterator[ast.Node]:
    """Walk normalized block tokens and yield AST nodes.

    Threads two pieces of pending state across the iteration:
    - `<div adf="marks" params="...">` → attached as marks on the next block
    - `<div adf="table" params="...">` → attached as layout meta on the next
      table

    `list_item=True` enables the mistune `block_text` → `Paragraph` rule that
    only applies inside list items.
    """
    pending_marks: list[ast.Mark] = []
    pending_table_meta: dict[str, Any] | None = None
    for token in tokens:
        # Metadata sentinels (HtmlVoid with adf="marks"/"table")
        if isinstance(token, HtmlVoid):
            if token.adf_type == "marks":
                pending_marks = parse_block_marks(get_params(token.attrs))
                continue
            if token.adf_type == "table":
                pending_table_meta = get_params(token.attrs)
                continue

        # list_item only: mistune emits block_text for tight list items
        if list_item and isinstance(token, dict) and token.get("type") == "block_text":
            children = token.get("children", [])
            # Mirror _build_paragraph's "&nbsp;" → empty paragraph rule so
            # list items with an originally-empty paragraph round-trip
            # back to one instead of "text &nbsp;".
            if (
                len(children) == 1
                and children[0].get("type") == "text"
                and children[0].get("raw", "") in ("\xa0", "&nbsp;")
            ):
                yield ast.Paragraph(content=[])
            else:
                yield ast.Paragraph(content=parse_inlines(children))
            continue

        sub_tokens: list[Token]
        if isinstance(token, dict) and token.get("type") == "list":
            sub_tokens = list(_split_mixed_list_token(token))
        else:
            sub_tokens = [token]

        for sub in sub_tokens:
            node = _build_block(sub, table_meta=pending_table_meta)
            if isinstance(sub, dict) and sub.get("type") == "table":
                pending_table_meta = None  # consumed

            if node is not None:
                attach_marks(node, pending_marks)
                pending_marks = []
                yield node


def _build_block(
    token: Token, *, table_meta: dict[str, Any] | None = None
) -> ast.Node | None:
    """Single-token dispatcher."""
    match token:
        case HtmlPaired():
            return _build_html_paired(token)
        case HtmlVoid():
            return build_html_void(token)
        case dict() as raw:
            return _build_mistune_block(raw, table_meta=table_meta)
        case _:
            return None


# ── HTML extension builders (paired) ──────────────────────────────────────────


def _build_html_paired(token: HtmlPaired) -> ast.Node | None:
    match token.adf_type:
        case "panel":
            return _build_panel(token.attrs, token.inner)
        case "expand" | "nestedExpand":
            return _build_expand(token.adf_type, token.attrs, token.inner)
        case "mediaSingle":
            return build_media_single(token.attrs, token.inner)
        case "mediaGroup":
            return build_media_group(token.attrs, token.inner)
        case "layoutSection":
            return _build_layout_section(token.attrs, token.inner)
        case "decisionList":
            return build_decision_list(token.attrs, block_html_to_inline(token.inner))
        case "taskList":
            return build_task_list(token.attrs, block_html_to_inline(token.inner))
        case "blockCard" | "embedCard":
            return build_block_card(token.adf_type, token.attrs)
        case "extension" | "bodiedExtension" | "syncBlock" | "bodiedSyncBlock":
            # Normally void, but `nested-table` arrives paired with a visual
            # `<table>` inner. The inner is cosmetic — `attrs.params` carries
            # the original ADF.
            return build_html_void(HtmlVoid(tag=token.tag, attrs=token.attrs))
        case "":
            # Plain HTML element (no `adf=` attribute). Currently only
            # `<p></p>` matters: the renderer uses it to encode an empty
            # paragraph (the &nbsp; alternative would render as visible
            # text). Recover it as ast.Paragraph(content=[]).
            if token.tag == "p":
                p = ast.Paragraph(content=parse_normalized_inlines(token.inner))
                block_marks = parse_block_marks(get_params(token.attrs))
                if block_marks:
                    p.marks = block_marks
                return p
            return None
        case _:
            return None


def build_html_void(token: HtmlVoid) -> ast.Node | None:
    """Self-contained data elements that encode an entire ADF node in attrs."""
    match token.adf_type:
        case "extension":
            return _build_extension(token.attrs)
        case "bodiedExtension":
            return _build_bodied_extension(token.attrs)
        case "syncBlock":
            return _build_sync_block(token.attrs)
        case "bodiedSyncBlock":
            return _build_bodied_sync_block(token.attrs)
        case "unknownBlock":
            return _build_unknown_block(token.attrs)
        case _:
            return None


# ── Mistune-native block builders ─────────────────────────────────────────────


def _build_mistune_block(
    token: dict[str, Any], *, table_meta: dict[str, Any] | None = None
) -> ast.Node | None:
    t = token.get("type", "")
    match t:
        case "paragraph":
            return _build_paragraph(token)
        case "image":
            return _build_image(token)
        case "heading":
            return _build_heading(token)
        case "block_code":
            return _build_codeblock(token)
        case "block_quote":
            return _build_blockquote(token)
        case "list":
            return _build_list(token)
        case "thematic_break":
            return ast.Rule()
        case "table":
            return _build_table(token, table_meta)
        case _:
            return None


def _build_paragraph(token: dict[str, Any]) -> ast.Paragraph:
    children = token.get("children", [])
    if len(children) == 1 and children[0].get("type") == "text":
        raw = children[0].get("raw", "")
        if raw in ("\xa0", "&nbsp;"):
            return ast.Paragraph(content=[])
    return ast.Paragraph(content=parse_inlines(children))


def _build_heading(token: dict[str, Any]) -> ast.Heading:
    level = token.get("attrs", {}).get("level", 1)
    children = token.get("children", [])
    return ast.Heading(level=level, content=parse_inlines(children))


def _build_codeblock(token: dict[str, Any]) -> ast.CodeBlock:
    raw = token.get("raw", "")
    if raw.endswith("\n"):
        raw = raw[:-1]
    info = token.get("attrs", {}).get("info", "")
    language = info.split()[0] if info else None
    content = [ast.Text(text=raw)] if raw else []
    return ast.CodeBlock(language=language, content=content)


def _build_blockquote(token: dict[str, Any]) -> ast.Blockquote:
    children = token.get("children", [])
    return ast.Blockquote(
        content=collect(dispatch_blocks(normalize_blocks(children)), is_blockquote)
    )


def _split_mixed_list_token(token: dict[str, Any]) -> list[dict[str, Any]]:
    """Split a mistune `list` whose children mix task and non-task items.

    mistune merges adjacent same-marker lists into one (e.g. `- [ ]` task
    items followed by `- ` bullet items become a single `list` token with
    `task_list_item` + `list_item` children). Walk the children, group
    consecutive ones of the same kind, and emit one cloned list token per
    group. Non-item children (`{"type": "list"}` sub-lists, etc.) stay
    with the current group.
    """
    children = token.get("children", [])
    if not children:
        return [token]

    def kind(c: dict[str, Any]) -> str | None:
        t = c.get("type")
        if t == "task_list_item":
            return "task"
        if t == "list_item":
            return "plain"
        return None

    has_task = any(kind(c) == "task" for c in children)
    has_plain = any(kind(c) == "plain" for c in children)
    if not (has_task and has_plain):
        return [token]

    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_kind: str | None = None
    for c in children:
        k = kind(c)
        if k is None or k == current_kind:
            current.append(c)
            continue
        if current_kind is not None:
            groups.append(current)
            current = []
        current_kind = k
        current.append(c)
    if current:
        groups.append(current)

    return [{**token, "children": g} for g in groups]


def _build_list(
    token: dict[str, Any],
) -> ast.BulletList | ast.OrderedList | ast.TaskList:
    attrs = token.get("attrs", {})
    ordered = attrs.get("ordered", False)
    children = token.get("children", [])

    is_task = any(c.get("type") == "task_list_item" for c in children)
    if is_task:
        items: list[ast.TaskListContent] = []
        for child in children:
            if child.get("type") == "task_list_item":
                # mistune nests a sub-list under its parent <li>, but ADF
                # expresses a nested taskList as a sibling. Pull the nested
                # list out and append it as a sibling to match the canonical
                # `taskList > [...items, nested-taskList]` shape.
                sub_lists = [
                    c for c in child.get("children", []) if c.get("type") == "list"
                ]
                if sub_lists:
                    trimmed = dict(child)
                    trimmed["children"] = [
                        c for c in child.get("children", []) if c.get("type") != "list"
                    ]
                    items.append(_build_task_item_dispatch(trimmed))
                    for sub in sub_lists:
                        nested = _build_list(sub)
                        if isinstance(nested, ast.TaskList):
                            items.append(nested)
                else:
                    items.append(_build_task_item_dispatch(child))
            elif child.get("type") == "list":
                nested = _build_list(child)
                if isinstance(nested, ast.TaskList):
                    items.append(nested)
        return ast.TaskList(content=items)

    list_items = [_build_list_item(c) for c in children if c.get("type") == "list_item"]

    if ordered:
        # Mirror the ADF parser's normalization: order=1 is the implicit
        # default, so collapse it to None for symmetry across the two
        # parse paths. (ADF render then omits the attrs envelope entirely.)
        order = attrs.get("start", 1)
        return ast.OrderedList(content=list_items, order=order if order != 1 else None)
    return ast.BulletList(content=list_items)


def _build_list_item(token: dict[str, Any]) -> ast.ListItem:
    children = token.get("children", [])
    return ast.ListItem(
        content=collect(
            dispatch_blocks(normalize_blocks(children), list_item=True),
            is_list_item,
        )
    )


def _is_block_task_item(token: dict[str, Any]) -> bool:
    """BlockTaskItem if 2+ non-blank block children."""
    children = token.get("children", [])
    non_blank = [c for c in children if c.get("type") != "blank_line"]
    return len(non_blank) > 1


def _build_task_item_dispatch(
    token: dict[str, Any],
) -> ast.TaskItem | ast.BlockTaskItem:
    if _is_block_task_item(token):
        return _build_block_task_item(token)
    return _build_task_item(token)


def _build_task_item(token: dict[str, Any]) -> ast.TaskItem:
    checked = token.get("attrs", {}).get("checked", False)
    state = "DONE" if checked else "TODO"
    inlines: list[ast.Inline] = []
    for child in token.get("children", []):
        if child.get("type") in ("block_text", "paragraph"):
            inlines.extend(parse_inlines(child.get("children", [])))
    return ast.TaskItem(state=state, content=inlines)


def _build_block_task_item(token: dict[str, Any]) -> ast.BlockTaskItem:
    checked = token.get("attrs", {}).get("checked", False)
    state = "DONE" if checked else "TODO"
    content: list[ast.BlockTaskItemContent] = []
    for child in token.get("children", []):
        t = child.get("type", "")
        if t == "blank_line":
            continue
        if t == "block_text":
            content.append(
                ast.Paragraph(content=parse_inlines(child.get("children", [])))
            )
        else:
            node = _build_mistune_block(child)
            if isinstance(node, (ast.Paragraph, ast.Extension)):
                content.append(node)
    return ast.BlockTaskItem(state=state, content=content)


def _build_image(token: dict[str, Any]) -> ast.MediaSingle:
    """`![alt](url)` (solo paragraph) → MediaSingle > Media(type="external")."""
    attrs = token.get("attrs", {})
    url = attrs.get("url", "") or attrs.get("src", "")
    alt = attrs.get("alt", "")
    if not alt:
        children = token.get("children", [])
        alt = "".join(c.get("raw", "") for c in children if c.get("type") == "text")
    return ast.MediaSingle(
        content=[ast.Media(type="external", url=url, alt=alt or None)],
    )


# ── HTML extension builders (block-level) ─────────────────────────────────────


def _build_panel(attrs: Mapping[str, str], inner: list[Token]) -> ast.Panel:
    p = get_params(attrs)
    return ast.Panel(
        panel_type=p.get("panelType", "info"),
        content=collect(dispatch_blocks(normalize_blocks(inner)), is_panel),
        panel_icon=p.get("panelIcon"),
        panel_icon_id=p.get("panelIconId"),
        panel_icon_text=p.get("panelIconText"),
        panel_color=p.get("panelColor"),
    )


def _build_expand(
    adf_type: str, attrs: Mapping[str, str], inner: list[Token]
) -> ast.Expand | ast.NestedExpand:
    p = get_params(attrs)
    normalized = normalize_blocks(inner)
    block_title, content_tokens = extract_summary(normalized)
    title = block_title or p.get("title")
    if adf_type == "nestedExpand":
        return ast.NestedExpand(
            content=collect(dispatch_blocks(content_tokens), is_nested_expand),
            title=title,
        )
    return ast.Expand(
        content=collect(dispatch_blocks(content_tokens), is_expand),
        title=title,
    )


def extract_summary(
    tokens: Sequence[Token],
) -> tuple[str | None, list[Token]]:
    """Find first `<summary>...</summary>` in a token stream.

    Block-context tokens are already normalized; `<summary>` arrives as an
    `HtmlPaired` with the title as its single text-inner token. The cell
    sub-system passes a raw inline_html stream; we still need to find the
    paired `<summary>` there.

    Returns `(title, tokens_without_summary)`.
    """
    token_list = list(tokens)
    for i, token in enumerate(token_list):
        if isinstance(token, HtmlPaired) and token.tag == "summary":
            title_parts = [t.get("raw", "") for t in token.inner if isinstance(t, dict)]
            title = "".join(title_parts)
            return title or None, token_list[:i] + token_list[i + 1 :]
        if isinstance(token, dict) and token.get("type") == "inline_html":
            tag, _, closing = parse_tag(token.get("raw", ""))
            if tag == "summary" and not closing:
                close_idx = find_paired_close(
                    token_list, i + 1, "summary", token_type="inline_html"
                )
                if close_idx is not None:
                    inner_dicts = [
                        t for t in token_list[i + 1 : close_idx] if isinstance(t, dict)
                    ]
                    title = inline_content_text(inner_dicts)
                    return (
                        title or None,
                        token_list[:i] + token_list[close_idx + 1 :],
                    )
    return None, token_list


def build_decision_list(
    _attrs: Mapping[str, str], inline_tokens: list[dict[str, Any]]
) -> ast.DecisionList:
    """Parse decisionList from a flat inline_html/text token stream.

    Block-level and cell-level callers both produce inline tokens
    (block-level path flattens block_html via `block_html_to_inline`), so a
    single implementation suffices.
    """
    items: list[ast.DecisionItem] = []
    for group in _group_cell_inline_html(inline_tokens):
        if isinstance(group, list) or not group.get("_paired"):
            continue
        if group["tag"] != "li":
            continue
        li_params = get_params(group["attrs"])
        items.append(
            ast.DecisionItem(
                state=li_params.get("state", ""),
                content=parse_inlines(reparse_text_inlines(group["inner"])),
            )
        )
    return ast.DecisionList(content=items)


def build_task_list(
    _attrs: Mapping[str, str], inline_tokens: list[dict[str, Any]]
) -> ast.TaskList:
    items: list[ast.TaskListContent] = []
    for group in _group_cell_inline_html(inline_tokens):
        if isinstance(group, list) or not group.get("_paired"):
            continue
        if group["tag"] != "li":
            continue
        li_params = get_params(group["attrs"])
        state = li_params.get("state", "TODO")
        # The renderer embeds a sibling nested taskList inside its preceding
        # li so the cell HTML stays well-formed (`<li>…<ul>…</ul></li>`).
        # Lift those nested taskLists back out as sibling TaskListContent
        # entries so the ADF mirrors `taskList > [items, nested-taskList]`.
        sub_lists, plain_inner = _split_nested_task_lists(group["inner"])
        items.append(
            ast.TaskItem(
                state="DONE" if state == "DONE" else "TODO",
                content=parse_inlines(reparse_text_inlines(plain_inner)),
            )
        )
        for sub_inner in sub_lists:
            items.append(build_task_list({}, sub_inner))
    return ast.TaskList(content=items)


def _split_nested_task_lists(
    tokens: list[dict[str, Any]],
) -> tuple[list[list[dict[str, Any]]], list[dict[str, Any]]]:
    """Split a li's inner token stream into (nested taskList inner-token lists, remaining tokens)."""
    sub_lists: list[list[dict[str, Any]]] = []
    cleaned: list[dict[str, Any]] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.get("type") == "inline_html":
            raw = t.get("raw", "")
            tag, attrs, closing = parse_tag(raw)
            if not closing and tag == "ul" and attrs.get("adf") == "taskList":
                close_idx = find_paired_close(
                    tokens, i + 1, "ul", token_type="inline_html"
                )
                if close_idx is not None:
                    sub_lists.append(tokens[i + 1 : close_idx])
                    i = close_idx + 1
                    continue
        cleaned.append(t)
        i += 1
    return sub_lists, cleaned


def build_media_single(attrs: Mapping[str, str], inner: list[Token]) -> ast.MediaSingle:
    p = get_params(attrs)
    content: list[ast.Media | ast.Caption] = []
    for token in inner:
        if not isinstance(token, dict) or token.get("type") != "paragraph":
            continue
        children = token.get("children", [])
        normalized = normalize_inlines(children)
        for item in normalized:
            if isinstance(item, HtmlPaired):
                _collect_media_items(item, content)
    # MediaSingle node-level link → linkHref/linkTitle params (rendered by
    # `_render_media_single`); distinct from a link on the leaf media child.
    marks: list[ast.LinkMark] = []
    if "linkHref" in p:
        marks.append(ast.LinkMark(href=p["linkHref"], title=p.get("linkTitle")))
    return ast.MediaSingle(
        content=content,
        width=p.get("width"),
        layout=p.get("layout"),
        width_type=p.get("widthType"),
        marks=marks,
    )


def _collect_media_items(
    item: HtmlPaired,
    out: list[ast.Media | ast.Caption],
    outer_marks: tuple[ast.LinkMark | ast.AnnotationMark, ...] = (),
) -> None:
    """Walk a mediaSingle's inner items, attaching wrapping inline marks.

    Media with marks arrives nested inside one or more inline-mark
    wrappers (``<span adf="annotation">…</span>`` for AnnotationMark,
    ``<a adf="link" href=…>…</a>`` for LinkMark). Unwrap them and accumulate
    the marks onto the leaf media node.
    """
    if item.adf_type == "media":
        media = _build_media(item.attrs)
        if outer_marks:
            # outer_marks is outermost-first, but the renderer wraps the first
            # mark innermost — reverse to restore the original marks order.
            media.marks = [*media.marks, *reversed(outer_marks)]
        out.append(media)
        return
    if item.adf_type == "caption":
        caption_inlines = collect(parse_normalized_inlines(item.inner), is_caption)
        out.append(ast.Caption(content=caption_inlines))
        return
    wrapping = _media_wrapping_mark(item)
    if wrapping is None:
        return
    for sub in item.inner:
        if isinstance(sub, HtmlPaired):
            _collect_media_items(sub, out, (*outer_marks, wrapping))


def _media_wrapping_mark(
    item: HtmlPaired,
) -> ast.LinkMark | ast.AnnotationMark | None:
    """Extract the ADF mark from an HTML element that wraps a media node.

    Reuses the shared `inline_mark_from` recognizer; media accepts only the
    link/annotation wrappers, so anything else is ignored here.
    """
    mark = inline_mark_from(item.tag, item.adf_type, item.attrs)
    if isinstance(mark, (ast.LinkMark, ast.AnnotationMark)):
        return mark
    return None


def _build_media(attrs: Mapping[str, str]) -> ast.Media:
    p = get_params(attrs)
    media = ast.Media(
        type=p.get("type", "file"),
        id=p.get("id"),
        alt=p.get("alt"),
        collection=p.get("collection"),
        height=p.get("height"),
        width=p.get("width"),
        url=p.get("url"),
    )
    border_marks = media_border_marks(p)
    if border_marks:
        media.marks = border_marks
    return media


def build_media_group(_attrs: Mapping[str, str], inner: list[Token]) -> ast.MediaGroup:
    collected: list[ast.Media | ast.Caption] = []
    for token in inner:
        if not isinstance(token, dict) or token.get("type") != "paragraph":
            continue
        for item in normalize_inlines(token.get("children", [])):
            if isinstance(item, HtmlPaired):
                _collect_media_items(item, collected)
    medias = [m for m in collected if isinstance(m, ast.Media)]
    return ast.MediaGroup(content=medias)


def _build_layout_section(
    _attrs: Mapping[str, str], inner: list[Token]
) -> ast.LayoutSection:
    columns: list[ast.LayoutColumn] = []
    for block in normalize_blocks(inner):
        if isinstance(block, HtmlPaired) and block.adf_type == "layoutColumn":
            columns.append(_build_layout_column(block.attrs, block.inner))
    return ast.LayoutSection(content=columns)


def _build_layout_column(
    attrs: Mapping[str, str], inner: list[Token]
) -> ast.LayoutColumn:
    p = get_params(attrs)
    from .ir import is_block

    return ast.LayoutColumn(
        width=p.get("width", 0),
        content=collect(dispatch_blocks(normalize_blocks(inner)), is_block),
    )


def build_block_card(
    adf_type: str, attrs: Mapping[str, str]
) -> ast.BlockCard | ast.EmbedCard:
    p = get_params(attrs)
    if adf_type == "embedCard":
        return ast.EmbedCard(
            url=p.get("url", ""),
            layout=p.get("layout", "center"),
            width=p.get("width"),
            original_height=p.get("originalHeight"),
            original_width=p.get("originalWidth"),
        )
    return ast.BlockCard(
        url=p.get("url"),
        layout=p.get("layout"),
        width=p.get("width"),
        data=p.get("data"),
        datasource=p.get("datasource"),
    )


# ── Data element builders (self-contained void) ───────────────────────────────


def _build_extension(attrs: Mapping[str, str]) -> ast.Extension:
    p = get_params(attrs)
    return ast.Extension(
        extension_key=p.get("extensionKey", ""),
        extension_type=p.get("extensionType", ""),
        parameters=p.get("parameters"),
        text=p.get("text"),
        layout=p.get("layout"),
    )


def _build_bodied_extension(attrs: Mapping[str, str]) -> ast.BodiedExtension:
    p = get_params(attrs)
    return ast.BodiedExtension(
        extension_key=p.get("extensionKey", ""),
        extension_type=p.get("extensionType", ""),
        content=collect(_adf_dict_nodes(p.get("content", [])), is_non_nestable),
        parameters=p.get("parameters"),
        text=p.get("text"),
        layout=p.get("layout"),
    )


def _build_sync_block(attrs: Mapping[str, str]) -> ast.SyncBlock:
    p = get_params(attrs)
    return ast.SyncBlock(resource_id=p.get("resourceId", ""))


def _build_bodied_sync_block(attrs: Mapping[str, str]) -> ast.BodiedSyncBlock:
    p = get_params(attrs)
    return ast.BodiedSyncBlock(
        resource_id=p.get("resourceId", ""),
        content=collect(_adf_dict_nodes(p.get("content", [])), is_bodied_sync),
    )


def _build_unknown_block(attrs: Mapping[str, str]) -> ast.UnknownBlock:
    return ast.UnknownBlock(raw=get_params(attrs))


def _adf_dict_nodes(nodes: list[Any]) -> list[ast.Node]:
    """Convert raw ADF JSON node dicts into AST nodes via the ADF parser.

    BodiedExtension/BodiedSyncBlock serialize their entire content as ADF
    JSON inside the `params` attribute. Without conversion the AST would
    hold bare dicts, which the renderer cannot consume.
    """
    if not nodes:
        return []
    from marklas.adf import parser as _adf_parser  # lazy to avoid cycles

    fake_doc: dict[str, Any] = {"type": "doc", "version": 1, "content": nodes}
    return list(_adf_parser.parse(fake_doc).content)


# ── Table ─────────────────────────────────────────────────────────────────────


def _build_table(token: dict[str, Any], meta: dict[str, Any] | None) -> ast.Table:
    children = token.get("children", [])
    head_token = None
    body_rows: list[dict[str, Any]] = []
    for child in children:
        if child.get("type") == "table_head":
            head_token = child
        elif child.get("type") == "table_body":
            body_rows = child.get("children", [])

    header_mode = (meta or {}).get("header", "row")
    rows: list[ast.TableRow] = []

    if head_token:
        head_cells = head_token.get("children", [])
        if header_mode in ("row", "both"):
            rows.append(_build_table_row(head_cells, header=True))

    for row_token in body_rows:
        row_cells = row_token.get("children", [])
        first_col_header = header_mode in ("column", "both")
        rows.append(_build_table_row(row_cells, first_col_header=first_col_header))

    m = meta or {}
    raw_colwidths = m.get("colwidths")
    colwidths: list[float] | None = (
        [float(w) for w in cast(list[Any], raw_colwidths)]
        if isinstance(raw_colwidths, list)
        else None
    )
    table = ast.Table(
        content=rows,
        layout=m.get("layout"),
        display_mode=m.get("displayMode"),
        is_number_column_enabled=m.get("isNumberColumnEnabled"),
        width=m.get("width"),
        colwidths=colwidths,
    )
    _sparsify_rows(table)
    return table


def _sparsify_rows(table: ast.Table) -> None:
    """Drop padding cells the md emitter inserted at rowspan-occupied slots.

    ADF tables are sparse — a row only lists cells whose columns it
    actually owns; columns claimed by a prior row's rowspan are absent
    from the row's content. GFM tables, on the other hand, require a
    cell at *every* column, so the md emitter pads occupied slots with
    empty cells. Reverse that padding here so the round-tripped AST
    has the same sparse shape as the source.

    This is the *dense → sparse* half of the round-trip pair with
    ``marklas.adf.parser._equalize_row_widths`` (which extends a
    trailing-cell colspan to make a sparse row reach the table's width
    on the ADF side).
    """
    rows = table.content
    num_rows = len(rows)
    if num_rows == 0:
        return
    occupied: set[tuple[int, int]] = set()
    for r, row in enumerate(rows):
        kept: list[ast.TableCell | ast.TableHeader] = []
        c = 0
        for cell in row.content:
            # md emitter pads occupied slots with empty cells; drop them
            # (advance past the column, don't keep the cell).
            if (r, c) in occupied and _is_empty_cell(cell):
                c += 1
                continue
            kept.append(cell)
            c += ast.Table.mark_cell_span(occupied, r, c, cell, num_rows)
        row.content = kept


def _is_empty_cell(cell: ast.TableCell | ast.TableHeader) -> bool:
    """True if the cell has no visible content (a single empty/whitespace
    paragraph, or nothing at all)."""
    content = list(cell.content)
    if not content:
        return True
    if len(content) != 1:
        return False
    only = content[0]
    if not isinstance(only, ast.Paragraph):
        return False
    inlines = list(only.content)
    if not inlines:
        return True
    if len(inlines) == 1 and isinstance(inlines[0], ast.Text):
        return not inlines[0].text.strip()
    return False


def _build_table_row(
    cells: list[dict[str, Any]],
    *,
    header: bool = False,
    first_col_header: bool = False,
) -> ast.TableRow:
    result: list[ast.TableCell | ast.TableHeader] = []
    skip = 0
    for idx, cell_token in enumerate(cells):
        if skip > 0:
            skip -= 1
            continue

        children = cell_token.get("children", [])
        cell_meta, content_children = _extract_cell_meta(children)
        content = parse_cell_content(content_children)

        colspan = cell_meta.get("colspan")
        if colspan and colspan > 1:
            skip = colspan - 1

        # An explicit `header` flag in the cell meta overrides the table's
        # header mode (used for partial column-header tables where a cell's
        # type deviates from what mode "row"/"column"/"both" would imply).
        if "header" in cell_meta:
            is_header = bool(cell_meta["header"])
        else:
            is_header = header or (first_col_header and idx == 0)
        cls = ast.TableHeader if is_header else ast.TableCell
        result.append(
            cls(
                content=content,
                colspan=colspan,
                rowspan=cell_meta.get("rowspan"),
                background=cell_meta.get("background"),
            )
        )
    return ast.TableRow(content=result)


def _extract_cell_meta(
    children: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Strip a leading `<div adf="cell" params="...">...</div>` and return its params."""
    if not children:
        return {}, children
    first = children[0]
    if first.get("type") == "inline_html":
        raw = first.get("raw", "")
        tag, attrs, _ = parse_tag(raw)
        if tag == "div" and attrs.get("adf") == "cell":
            params = get_params(attrs)
            # Remove only the cell meta's own closing </div>. Any later
            # </div> belongs to a sibling element (embedCard, extension,
            # etc.) — stripping those breaks their paired matching and
            # they degrade to bare text on round-trip.
            remaining = list(children[1:])
            for i, c in enumerate(remaining):
                if (
                    c.get("type") == "inline_html"
                    and c.get("raw", "").strip() == "</div>"
                ):
                    del remaining[i]
                    break
            return params, remaining
    return {}, children
