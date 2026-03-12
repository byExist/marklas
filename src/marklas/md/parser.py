"""Markdown → Union AST parsing."""

from __future__ import annotations

import json
import re
import textwrap
from collections.abc import Sequence
from typing import Any, Literal, Required, TypedDict, cast

import mistune

from marklas.nodes import blocks, inlines


# ── Token ────────────────────────────────────────────────────────────


class Token(TypedDict, total=False):
    type: Required[str]
    raw: str
    children: list[Token]
    attrs: dict[str, Any]
    style: str
    tight: bool
    bullet: str
    annotated: bool


_KNOWN_BLOCK_TYPES = frozenset(
    {
        # mistune
        "paragraph",
        "heading",
        "block_code",
        "block_quote",
        "thematic_break",
        "list",
        "table",
        "block_html",
        "blank_line",
        "block_text",
        "list_item",
        # annotation
        "panel",
        "expand",
        "nestedExpand",
        "taskList",
        "decisionList",
        "layoutSection",
        "layoutColumn",
        "mediaSingle",
        "mediaGroup",
        "blockCard",
        "embedCard",
        "extension",
        "bodiedExtension",
        "syncBlock",
        "bodiedSyncBlock",
    }
)


# ── Tokenizer ────────────────────────────────────────────────────────

_tokenize = mistune.create_markdown(
    renderer="ast",
    plugins=["table", "strikethrough", "task_lists"],
)
_inline_parser = _tokenize.inline


# ── Entry point ──────────────────────────────────────────────────────


def parse(markdown: str) -> blocks.Document:
    tokens = cast(list[Token], _tokenize(markdown))
    return blocks.Document(children=_parse_doc_children(tokens))


# ── Annotation matching ─────────────────────────────────────────────

_ADF_COMMENT_RE = re.compile(r"<!--\s*(/?)adf:(\w+)\s*(.*?)-->", re.DOTALL)
_ADF_COMMENT_SPLIT_RE = re.compile(r"(<!--\s*/?adf:\w+\s*.*?-->)")


def _parse_adf_comment(raw: str) -> tuple[bool, str, dict[str, Any]] | None:
    """Return (closing, tag, attrs) if ADF comment, else None."""
    m = _ADF_COMMENT_RE.fullmatch(raw.strip())
    if not m:
        return None
    closing, tag, attr_str = m.groups()
    try:
        attrs: dict[str, Any] = json.loads(attr_str) if attr_str.strip() else {}
    except json.JSONDecodeError:
        return None
    return bool(closing), tag, attrs


def _normalize_block_annotation(
    tag: str, attrs: dict[str, Any], inner: list[Token]
) -> Token:
    """Normalize an annotated block token so its children match the standard structure.

    For paragraph/heading, mistune produces block-level children (e.g. a paragraph
    token wrapping inlines). This unwraps them to inline children so downstream
    parsers see the same structure as non-annotated tokens.
    """
    match tag:
        case "paragraph":
            # inner = [{"type": "paragraph", "children": [inlines...]}]
            # → children = [inlines...]
            children = _unwrap_inner_inlines(inner)
            return Token(type="paragraph", attrs=attrs, children=children)
        case "heading":
            # level은 inner heading에서 가져오고, annotation attrs와 병합
            inner_attrs = _extract_inner_attrs(inner)
            merged_attrs = {**inner_attrs, **attrs}
            children = _unwrap_inner_inlines(inner)
            return Token(type="heading", attrs=merged_attrs, children=children)
        case _:
            return Token(type=tag, attrs=attrs, children=inner, annotated=True)


def _extract_inner_attrs(inner: list[Token]) -> dict[str, Any]:
    """Extract attrs from the first block token (e.g. heading's level)."""
    if inner:
        return inner[0].get("attrs", {})
    return {}


def _unwrap_inner_inlines(inner: list[Token]) -> list[Token]:
    """Extract inline children from a single-block wrapper.

    When `<!-- adf:paragraph -->text<!-- /adf:paragraph -->` is tokenized,
    inner = [{"type": "paragraph", "children": [inline tokens...]}].
    This extracts the inline tokens from the first block.
    """
    if len(inner) == 1 and inner[0]["type"] in ("paragraph", "heading"):
        return inner[0].get("children", [])
    # Collect inline children, skipping non-content blocks like blank_line
    result: list[Token] = []
    for tok in inner:
        if tok["type"] in ("paragraph", "heading", "block_text"):
            result.extend(tok.get("children", []))
        elif tok["type"] == "blank_line":
            continue
    return result


def _match_block_annotations(tokens: list[Token]) -> list[Token]:
    """Match block-level `<!-- adf:tag -->...<!-- /adf:tag -->` pairs."""
    stack: list[tuple[str, dict[str, Any], list[Token]]] = []
    result: list[Token] = []

    for token in tokens:
        target = stack[-1][2] if stack else result

        if token["type"] == "block_html":
            raw = token.get("raw", "")
            parsed = _parse_adf_comment(raw)
            if parsed:
                closing, tag, attrs = parsed
                if not closing:
                    stack.append((tag, attrs, []))
                else:
                    if stack and stack[-1][0] == tag:
                        stag, sattrs, inner = stack.pop()
                        merged = _normalize_block_annotation(stag, sattrs, inner)
                        (stack[-1][2] if stack else result).append(merged)
                continue
            inline_children = _split_block_html(raw)
            if inline_children is not None:
                target.append(Token(type="paragraph", children=inline_children))
                continue

        target.append(token)

    while stack:
        _, _, inner = stack.pop()
        (stack[-1][2] if stack else result).extend(inner)

    return result


def _split_block_html(raw: str) -> list[Token] | None:
    """Split a block_html containing inline annotations into matched inline tokens."""
    stripped = raw.strip()
    if "<!-- adf:" not in stripped:
        return None

    parts = _ADF_COMMENT_SPLIT_RE.split(stripped)
    synthetic_tokens: list[Token] = []
    for part in parts:
        if not part:
            continue
        parsed = _parse_adf_comment(part)
        if parsed:
            synthetic_tokens.append(Token(type="inline_html", raw=part))
        else:
            state = _inline_parser.state_cls(env={})
            state.src = part
            synthetic_tokens.extend(cast(list[Token], _inline_parser.parse(state)))

    if not synthetic_tokens:
        return None

    return _match_inline_annotations(synthetic_tokens)


def _trim_annotation_children(children: list[Token]) -> list[Token]:
    """Strip leading/trailing whitespace from annotation children.

    Inline annotations are rendered with spaces between the comment and content
    (e.g. ``<!-- adf:tag --> content <!-- /adf:tag -->``) for Markdown viewer
    compatibility. This removes those padding spaces during parsing.
    """
    if not children:
        return children
    result = list(children)
    # trim leading
    if result and result[0]["type"] == "text":
        stripped = result[0].get("raw", "").lstrip()
        if stripped:
            result[0] = Token(type="text", raw=stripped)
        else:
            result = result[1:]
    # trim trailing
    if result and result[-1]["type"] == "text":
        stripped = result[-1].get("raw", "").rstrip()
        if stripped:
            result[-1] = Token(type="text", raw=stripped)
        else:
            result = result[:-1]
    return result


def _match_inline_annotations(tokens: list[Token]) -> list[Token]:
    """Match inline-level `<!-- adf:tag -->...<!-- /adf:tag -->` pairs."""
    stack: list[tuple[str, dict[str, Any], list[Token]]] = []
    result: list[Token] = []

    for token in tokens:
        target = stack[-1][2] if stack else result

        if token["type"] == "inline_html":
            parsed = _parse_adf_comment(token.get("raw", ""))
            if parsed:
                closing, tag, attrs = parsed
                if not closing:
                    stack.append((tag, attrs, []))
                else:
                    if stack and stack[-1][0] == tag:
                        stag, sattrs, inner = stack.pop()
                        merged = Token(
                            type=stag,
                            attrs=sattrs,
                            children=_trim_annotation_children(inner),
                            annotated=True,
                        )
                        (stack[-1][2] if stack else result).append(merged)
                continue
            continue

        target.append(token)

    while stack:
        _, _, inner = stack.pop()
        (stack[-1][2] if stack else result).extend(inner)

    return result


def _match_cell_annotations(tokens: list[Token]) -> list[Token]:
    """Match cell-level annotation pairs (same logic, different context)."""
    stack: list[tuple[str, dict[str, Any], list[Token]]] = []
    result: list[Token] = []

    for tok in tokens:
        target = stack[-1][2] if stack else result

        if tok["type"] == "inline_html":
            parsed = _parse_adf_comment(tok.get("raw", ""))
            if parsed:
                closing, tag, attrs = parsed
                if not closing:
                    stack.append((tag, attrs, []))
                else:
                    if stack and stack[-1][0] == tag:
                        stag, sattrs, inner = stack.pop()
                        merged = Token(
                            type=stag,
                            attrs=sattrs,
                            children=_trim_annotation_children(inner),
                            annotated=True,
                        )
                        (stack[-1][2] if stack else result).append(merged)
                continue

        target.append(tok)

    while stack:
        _, _, inner = stack.pop()
        (stack[-1][2] if stack else result).extend(inner)

    return result


# ── Document children ───────────────────────────────────────────────


def _parse_doc_children(tokens: list[Token]) -> list[blocks.DocChild]:
    matched = _match_block_annotations(tokens)
    result: list[blocks.DocChild] = []
    for token in matched:
        node = _parse_doc_child(token)
        if node is not None:
            result.append(node)
    return result


def _parse_doc_child(token: Token) -> blocks.DocChild | None:
    match token["type"]:
        case "paragraph":
            return _parse_paragraph(token)
        case "heading":
            return _parse_heading(token)
        case "block_code":
            return _parse_code_block(token)
        case "block_quote":
            return _parse_blockquote(token)
        case "thematic_break":
            return _parse_thematic_break()
        case "list":
            return _parse_list(token)
        case "table":
            return _parse_table(token)
        case "panel":
            return _parse_panel(token)
        case "expand":
            return _parse_expand(token)
        case "taskList":
            return _parse_task_list(token)
        case "decisionList":
            return _parse_decision_list(token)
        case "layoutSection":
            return _parse_layout_section(token)
        case "mediaSingle":
            return _parse_media_single(token)
        case "mediaGroup":
            return _parse_media_group(token)
        case "blockCard":
            return _parse_block_card(token)
        case "embedCard":
            return _parse_embed_card(token)
        case "extension":
            return _parse_extension(token)
        case "bodiedExtension":
            return _parse_bodied_extension(token)
        case "syncBlock":
            return _parse_sync_block(token)
        case "bodiedSyncBlock":
            return _parse_bodied_sync_block(token)
        case known if known in _KNOWN_BLOCK_TYPES:
            return None
        case _:
            raise ValueError(f"unexpected doc token type: {token['type']}")


# ── BlockQuote children ─────────────────────────────────────────────


def _parse_blockquote_children(tokens: list[Token]) -> list[blocks.BlockQuoteChild]:
    matched = _match_block_annotations(tokens)
    result: list[blocks.BlockQuoteChild] = []
    for token in matched:
        node = _parse_blockquote_child(token)
        if node is not None:
            result.append(node)
    return result


def _parse_blockquote_child(token: Token) -> blocks.BlockQuoteChild | None:
    match token["type"]:
        case "paragraph":
            return _parse_paragraph(token)
        case "list":
            return _parse_list(token)
        case "block_code":
            return _parse_code_block(token)
        case "mediaSingle":
            return _parse_media_single(token)
        case "mediaGroup":
            return _parse_media_group(token)
        case "extension":
            return _parse_extension(token)
        case known if known in _KNOWN_BLOCK_TYPES:
            return None
        case _:
            raise ValueError(f"unexpected blockquote token type: {token['type']}")


# ── ListItem children ───────────────────────────────────────────────


def _parse_listitem_children(
    item_token: Token, tight: bool
) -> list[blocks.ListItemChild]:
    """Special handling for block_text (tight lists) and block_html
    (inline annotations).
    """
    matched = _match_block_annotations(item_token.get("children", []))
    result: list[blocks.ListItemChild] = []
    for child in matched:
        if child.get("annotated"):
            node = _parse_listitem_child(child)
            if node is not None:
                result.append(node)
            continue
        match child["type"]:
            case "block_text":
                inls = _parse_inlines(child.get("children", []))
                result.append(blocks.Paragraph(children=inls))
            case "block_html":
                inline_children = _split_block_html(child.get("raw", ""))
                if inline_children is not None:
                    inls = _parse_inlines(inline_children)
                    if inls:
                        result.append(blocks.Paragraph(children=inls))
            case _:
                node = _parse_listitem_child(child)
                if node is not None:
                    result.append(node)
    return result


def _parse_listitem_child(token: Token) -> blocks.ListItemChild | None:
    match token["type"]:
        case "paragraph" | "block_text":
            return _parse_paragraph(token)
        case "list":
            return _parse_list(token)
        case "block_code":
            return _parse_code_block(token)
        case "mediaSingle":
            return _parse_media_single(token)
        case "extension":
            return _parse_extension(token)
        case "taskList":
            return _parse_task_list(token)
        case known if known in _KNOWN_BLOCK_TYPES:
            return None
        case _:
            raise ValueError(f"unexpected listitem token type: {token['type']}")


# ── Panel children ──────────────────────────────────────────────────


def _parse_panel_children(tokens: list[Token]) -> list[blocks.PanelChild]:
    matched = _match_block_annotations(tokens)
    result: list[blocks.PanelChild] = []
    for token in matched:
        node = _parse_panel_child(token)
        if node is not None:
            result.append(node)
    return result


def _parse_panel_child(token: Token) -> blocks.PanelChild | None:
    match token["type"]:
        case "paragraph":
            return _parse_paragraph(token)
        case "heading":
            return _parse_heading(token)
        case "list":
            return _parse_list(token)
        case "block_code":
            return _parse_code_block(token)
        case "taskList":
            return _parse_task_list(token)
        case "decisionList":
            return _parse_decision_list(token)
        case "thematic_break":
            return _parse_thematic_break()
        case "mediaSingle":
            return _parse_media_single(token)
        case "mediaGroup":
            return _parse_media_group(token)
        case "blockCard":
            return _parse_block_card(token)
        case "extension":
            return _parse_extension(token)
        case known if known in _KNOWN_BLOCK_TYPES:
            return None
        case _:
            raise ValueError(f"unexpected panel token type: {token['type']}")


# ── Expand children ─────────────────────────────────────────────────


def _parse_expand_children(tokens: list[Token]) -> list[blocks.ExpandChild]:
    matched = _match_block_annotations(tokens)
    result: list[blocks.ExpandChild] = []
    for token in matched:
        node = _parse_expand_child(token)
        if node is not None:
            result.append(node)
    return result


def _parse_expand_child(token: Token) -> blocks.ExpandChild | None:
    match token["type"]:
        case "paragraph":
            return _parse_paragraph(token)
        case "heading":
            return _parse_heading(token)
        case "list":
            return _parse_list(token)
        case "block_code":
            return _parse_code_block(token)
        case "block_quote":
            return _parse_blockquote(token)
        case "table":
            return _parse_table(token)
        case "taskList":
            return _parse_task_list(token)
        case "decisionList":
            return _parse_decision_list(token)
        case "thematic_break":
            return _parse_thematic_break()
        case "mediaSingle":
            return _parse_media_single(token)
        case "mediaGroup":
            return _parse_media_group(token)
        case "panel":
            return _parse_panel(token)
        case "nestedExpand":
            return _parse_nested_expand(token)
        case "blockCard":
            return _parse_block_card(token)
        case "embedCard":
            return _parse_embed_card(token)
        case "extension":
            return _parse_extension(token)
        case "bodiedExtension":
            return _parse_bodied_extension(token)
        case known if known in _KNOWN_BLOCK_TYPES:
            return None
        case _:
            raise ValueError(f"unexpected expand token type: {token['type']}")


# ── NestedExpand children ───────────────────────────────────────────


def _parse_nested_expand_children(
    tokens: list[Token],
) -> list[blocks.NestedExpandChild]:
    matched = _match_block_annotations(tokens)
    result: list[blocks.NestedExpandChild] = []
    for token in matched:
        node = _parse_nested_expand_child(token)
        if node is not None:
            result.append(node)
    return result


def _parse_nested_expand_child(token: Token) -> blocks.NestedExpandChild | None:
    match token["type"]:
        case "paragraph":
            return _parse_paragraph(token)
        case "heading":
            return _parse_heading(token)
        case "list":
            return _parse_list(token)
        case "block_code":
            return _parse_code_block(token)
        case "block_quote":
            return _parse_blockquote(token)
        case "taskList":
            return _parse_task_list(token)
        case "decisionList":
            return _parse_decision_list(token)
        case "thematic_break":
            return _parse_thematic_break()
        case "mediaSingle":
            return _parse_media_single(token)
        case "mediaGroup":
            return _parse_media_group(token)
        case "panel":
            return _parse_panel(token)
        case "extension":
            return _parse_extension(token)
        case known if known in _KNOWN_BLOCK_TYPES:
            return None
        case _:
            raise ValueError(f"unexpected nestedExpand token type: {token['type']}")


# ── TableCell children ──────────────────────────────────────────────


def _parse_tablecell_children(tokens: list[Token]) -> list[blocks.TableCellChild]:
    """Normalize cell inline tokens via _normalize_cell_tokens, then dispatch."""
    normalized = _normalize_cell_tokens(tokens)
    result: list[blocks.TableCellChild] = []
    for token in normalized:
        node = _parse_tablecell_child(token)
        if node is not None:
            result.append(node)
    return result


def _parse_tablecell_child(token: Token) -> blocks.TableCellChild | None:
    match token["type"]:
        case "paragraph":
            return _parse_paragraph(token)
        case "heading":
            return _parse_heading(token)
        case "list":
            return _parse_list(token)
        case "block_code":
            return _parse_code_block(token)
        case "block_quote":
            return _parse_blockquote(token)
        case "taskList":
            return _parse_task_list(token)
        case "decisionList":
            return _parse_decision_list(token)
        case "thematic_break":
            return _parse_thematic_break()
        case "mediaSingle":
            return _parse_media_single(token)
        case "mediaGroup":
            return _parse_media_group(token)
        case "panel":
            return _parse_panel(token)
        case "nestedExpand":
            return _parse_nested_expand(token)
        case "blockCard":
            return _parse_block_card(token)
        case "embedCard":
            return _parse_embed_card(token)
        case "extension":
            return _parse_extension(token)
        case known if known in _KNOWN_BLOCK_TYPES:
            return None
        case _:
            raise ValueError(f"unexpected tableCell token type: {token['type']}")


# ── Shared block parsers (intersection) ─────────────────────────────


def _parse_paragraph(token: Token) -> blocks.Paragraph:
    """Parse paragraph — attrs may carry alignment/indentation from cell annotations."""
    attrs = token.get("attrs", {})
    children = _parse_inlines(token.get("children", []))
    return blocks.Paragraph(
        children=children,
        alignment=attrs.get("align"),
        indentation=attrs.get("indentation"),
    )


def _parse_heading(token: Token) -> blocks.Heading:
    """Parse heading — attrs may carry alignment/indentation from cell annotations."""
    attrs = token.get("attrs", {})
    level = attrs["level"]
    children = _parse_inlines(token.get("children", []))
    return blocks.Heading(
        level=level,
        children=children,
        alignment=attrs.get("align"),
        indentation=attrs.get("indentation"),
    )


def _parse_code_block(token: Token) -> blocks.CodeBlock:
    code = token.get("raw", "")
    if code.endswith("\n"):
        code = code[:-1]
    code = textwrap.dedent(code)
    info = token.get("attrs", {}).get("info", "")
    language = info or None
    return blocks.CodeBlock(code=code, language=language)


def _parse_blockquote(token: Token) -> blocks.BlockQuote:
    children = _parse_blockquote_children(token.get("children", []))
    return blocks.BlockQuote(children=children)


def _parse_thematic_break() -> blocks.ThematicBreak:
    return blocks.ThematicBreak()


def _parse_list(token: Token) -> blocks.BulletList | blocks.OrderedList:
    attrs = token.get("attrs", {})
    ordered = attrs["ordered"]
    tight = token.get("tight", True)
    items: list[blocks.ListItem] = []
    start = 1

    if ordered:
        start_val = attrs.get("start")
        if start_val is not None:
            start = start_val

    for child_tok in token.get("children", []):
        if child_tok["type"] not in ("list_item", "task_list_item"):
            continue
        item_children = _parse_listitem_children(child_tok, tight)
        checked = child_tok.get("attrs", {}).get("checked")
        items.append(blocks.ListItem(children=item_children, checked=checked))

    if ordered:
        return blocks.OrderedList(items=items, start=start, tight=tight)
    return blocks.BulletList(items=items, tight=tight)


def _parse_table(token: Token) -> blocks.Table:
    """Parse table — handles both plain and annotated (displayMode, layout, etc.)."""
    if token.get("annotated"):
        attrs = token.get("attrs", {})
        inner = _parse_doc_children(token.get("children", []))
        if inner and isinstance(inner[0], blocks.Table):
            t = inner[0]
            t.display_mode = attrs.get("displayMode")
            t.is_number_column_enabled = attrs.get("isNumberColumnEnabled")
            t.layout = attrs.get("layout")
            t.width = attrs.get("width")
            _apply_cell_attrs(t, attrs.get("cells"))
            return t
        return inner[0] if inner else blocks.Paragraph(children=[])  # type: ignore[return-value]

    head: list[blocks.TableCell] = []
    body: list[list[blocks.TableCell]] = []
    alignments: list[Literal["left", "center", "right"] | None] = []
    for child_tok in token.get("children", []):
        if child_tok["type"] == "table_head":
            for cell_tok in child_tok.get("children", []):
                align = cell_tok.get("attrs", {}).get("align")
                alignments.append(align)
                cell_children = _parse_tablecell_children(
                    cell_tok.get("children", []),
                )
                head.append(blocks.TableHeader(children=cell_children))
        elif child_tok["type"] == "table_body":
            for row_tok in child_tok.get("children", []):
                row: list[blocks.TableCell] = []
                for cell_tok in row_tok.get("children", []):
                    cell_children = _parse_tablecell_children(
                        cell_tok.get("children", []),
                    )
                    row.append(blocks.TableCell(children=cell_children))
                body.append(row)

    if head and all(
        not cell.children
        or (
            len(cell.children) == 1
            and isinstance(cell.children[0], blocks.Paragraph)
            and len(cell.children[0].children) == 1
            and isinstance(cell.children[0].children[0], inlines.Text)
            and not cell.children[0].children[0].text.strip()
        )
        for cell in head
    ):
        head = []

    return blocks.Table(head=head, body=body, alignments=alignments)


# ── Shared block parsers (annotation-only) ──────────────────────────


def _parse_panel(token: Token) -> blocks.Panel:
    attrs = token.get("attrs", {})
    inner = _parse_panel_children(token.get("children", []))
    children = cast(list[blocks.PanelChild], _unwrap_blockquote(inner))
    return blocks.Panel(
        children=children,
        panel_type=attrs.get("panelType", "info"),
        panel_icon=attrs.get("panelIcon"),
        panel_icon_id=attrs.get("panelIconId"),
        panel_icon_text=attrs.get("panelIconText"),
        panel_color=attrs.get("panelColor"),
    )


def _parse_expand(token: Token) -> blocks.Expand:
    attrs = token.get("attrs", {})
    inner = _parse_expand_children(token.get("children", []))
    children = cast(list[blocks.ExpandChild], _unwrap_blockquote(inner))
    return blocks.Expand(children=children, title=attrs.get("title"))


def _parse_nested_expand(token: Token) -> blocks.NestedExpand:
    attrs = token.get("attrs", {})
    inner = _parse_nested_expand_children(token.get("children", []))
    children = cast(list[blocks.NestedExpandChild], _unwrap_blockquote(inner))
    return blocks.NestedExpand(children=children, title=attrs.get("title"))


def _parse_task_list(token: Token) -> blocks.TaskList:
    inner = _parse_doc_children(token.get("children", []))
    items = _extract_task_items(inner)
    return blocks.TaskList(items=items)


def _parse_decision_list(token: Token) -> blocks.DecisionList:
    inner = _parse_doc_children(token.get("children", []))
    items = _extract_decision_items(inner)
    return blocks.DecisionList(items=items)


def _parse_layout_section(token: Token) -> blocks.LayoutSection:
    matched = _match_block_annotations(token.get("children", []))
    columns: list[blocks.LayoutColumn] = []
    for child in matched:
        if child["type"] == "layoutColumn":
            columns.append(_parse_layout_column(child))
    return blocks.LayoutSection(columns=columns)


def _parse_layout_column(token: Token) -> blocks.LayoutColumn:
    attrs = token.get("attrs", {})
    children = _parse_layoutcolumn_children(token.get("children", []))
    return blocks.LayoutColumn(children=children, width=attrs.get("width"))


def _parse_layoutcolumn_children(
    tokens: list[Token],
) -> list[blocks.LayoutColumnChild]:
    matched = _match_block_annotations(tokens)
    result: list[blocks.LayoutColumnChild] = []
    for token in matched:
        node = _parse_layoutcolumn_child(token)
        if node is not None:
            result.append(node)
    return result


def _parse_layoutcolumn_child(token: Token) -> blocks.LayoutColumnChild | None:
    match token["type"]:
        case "paragraph":
            return _parse_paragraph(token)
        case "heading":
            return _parse_heading(token)
        case "list":
            return _parse_list(token)
        case "block_code":
            return _parse_code_block(token)
        case "block_quote":
            return _parse_blockquote(token)
        case "table":
            return _parse_table(token)
        case "taskList":
            return _parse_task_list(token)
        case "decisionList":
            return _parse_decision_list(token)
        case "thematic_break":
            return _parse_thematic_break()
        case "mediaSingle":
            return _parse_media_single(token)
        case "mediaGroup":
            return _parse_media_group(token)
        case "panel":
            return _parse_panel(token)
        case "expand":
            return _parse_expand(token)
        case "blockCard":
            return _parse_block_card(token)
        case "embedCard":
            return _parse_embed_card(token)
        case "extension":
            return _parse_extension(token)
        case "bodiedExtension":
            return _parse_bodied_extension(token)
        case known if known in _KNOWN_BLOCK_TYPES:
            return None
        case _:
            raise ValueError(f"unexpected layoutColumn token type: {token['type']}")


def _parse_media_single(token: Token) -> blocks.MediaSingle:
    attrs = token.get("attrs", {})
    media = _build_media(attrs.get("media", {}))
    return blocks.MediaSingle(
        media=media,
        layout=attrs.get("layout"),
        width=attrs.get("width"),
        width_type=attrs.get("widthType"),
    )


def _parse_media_group(token: Token) -> blocks.MediaGroup:
    attrs = token.get("attrs", {})
    media_list = [_build_media(m) for m in attrs.get("mediaList", [])]
    return blocks.MediaGroup(media_list=media_list)


def _parse_block_card(token: Token) -> blocks.BlockCard:
    attrs = token.get("attrs", {})
    return blocks.BlockCard(url=attrs.get("url"), data=attrs.get("data"))


def _parse_embed_card(token: Token) -> blocks.EmbedCard:
    attrs = token.get("attrs", {})
    return blocks.EmbedCard(
        url=attrs.get("url", ""),
        layout=attrs.get("layout", ""),
        width=attrs.get("width"),
        original_width=attrs.get("originalWidth"),
        original_height=attrs.get("originalHeight"),
    )


def _parse_extension(token: Token) -> blocks.Extension:
    return blocks.Extension(raw=token.get("attrs", {}))


def _parse_bodied_extension(token: Token) -> blocks.BodiedExtension:
    return blocks.BodiedExtension(raw=token.get("attrs", {}))


def _parse_sync_block(token: Token) -> blocks.SyncBlock:
    return blocks.SyncBlock(raw=token.get("attrs", {}))


def _parse_bodied_sync_block(token: Token) -> blocks.BodiedSyncBlock:
    return blocks.BodiedSyncBlock(raw=token.get("attrs", {}))


# ── Table cell normalization ────────────────────────────────────────

_HTML_CELL_BLOCK_MAP: dict[str, str] = {
    "blockquote": "block_quote",
    "h1": "heading",
    "h2": "heading",
    "h3": "heading",
    "h4": "heading",
    "h5": "heading",
    "h6": "heading",
    "ul": "list",
    "ol": "list",
    "code": "block_code",
}

_HTML_CELL_VOID_MAP: dict[str, str] = {
    "hr": "thematic_break",
}


def _normalize_cell_tokens(tokens: list[Token]) -> list[Token]:
    """Convert table cell inline tokens to standard block-level tokens.

    Pipeline: annotation matching → HTML block recognition → <br> splitting
    → inline grouping into paragraphs.

    Produces tokens in standard MistuneType format so that
    ``_parse_tablecell_children()`` can handle them directly, eliminating
    the need for separate cell parsers.

    Conversions:
        <h1>...<h6>      → Token(type="heading", attrs={"level": N})
        <blockquote>      → Token(type="block_quote", children=[normalized...])
        <ul>/<ol>         → Token(type="list", children=[list_items...])
        <code>            → Token(type="block_code", raw=...)
        <hr>              → Token(type="thematic_break")
        <br>              → block separator (splits into separate blocks)
        <br/>             → Token(type="linebreak") (preserved as hardBreak)
        remaining inlines → Token(type="paragraph", children=[...])
    """
    matched = _match_html_cell_blocks(_match_cell_annotations(tokens))
    result: list[Token] = []
    loose: list[Token] = []

    def _flush_loose() -> None:
        if not loose:
            return
        result.append(Token(type="paragraph", children=list(loose)))
        loose.clear()

    for tok in matched:
        if tok.get("annotated"):
            tag = tok["type"]
            if tag in _CELL_BLOCK_TAGS:
                _flush_loose()
                block_tok = _cell_annotation_to_block(tok)
                result.append(block_tok)
            else:
                loose.append(tok)
        else:
            classified = _classify_br(tok)
            if classified["type"] == "block_separator":
                _flush_loose()
            else:
                loose.append(classified)

    _flush_loose()
    return result


# ── Inline parsing ──────────────────────────────────────────────────


def _parse_inlines(tokens: list[Token]) -> list[inlines.Inline]:
    matched = _match_inline_annotations(tokens)
    result: list[inlines.Inline] = []
    for token in matched:
        node = _parse_inline(token)
        if node is not None:
            if (
                isinstance(node, inlines.Text)
                and result
                and isinstance(result[-1], inlines.Text)
            ):
                result[-1] = inlines.Text(text=result[-1].text + node.text)
            else:
                result.append(node)
    return result


def _parse_inline(token: Token) -> inlines.Inline | None:
    match token["type"]:
        case "text":
            return _parse_text(token)
        case "strong":
            return _parse_strong(token)
        case "emphasis":
            return _parse_emphasis(token)
        case "strikethrough":
            return _parse_strikethrough(token)
        case "link":
            return _parse_link(token)
        case "image":
            return _parse_image(token)
        case "codespan":
            return _parse_codespan(token)
        case "linebreak":
            return _parse_linebreak(token)
        case "softbreak":
            return _parse_softbreak(token)
        case "mention":
            return _parse_mention(token)
        case "emoji":
            return _parse_emoji(token)
        case "date":
            return _parse_date(token)
        case "status":
            return _parse_status(token)
        case "inlineCard":
            return _parse_inline_card(token)
        case "mediaInline":
            return _parse_media_inline(token)
        case "underline":
            return _parse_underline(token)
        case "textColor":
            return _parse_text_color(token)
        case "backgroundColor":
            return _parse_background_color(token)
        case "subSup":
            return _parse_subsup(token)
        case "annotation":
            return _parse_annotation(token)
        case "placeholder":
            return _parse_placeholder(token)
        case "inlineExtension":
            return _parse_inline_extension(token)
        case _:
            raise ValueError(f"unexpected inline token type: {token['type']}")


# ── Intersection inline parsers ─────────────────────────────────────


def _parse_text(token: Token) -> inlines.Text:
    return inlines.Text(text=token.get("raw", ""))


def _parse_strong(token: Token) -> inlines.Strong:
    return inlines.Strong(children=_parse_inlines(token.get("children", [])))


def _parse_emphasis(token: Token) -> inlines.Emphasis:
    return inlines.Emphasis(children=_parse_inlines(token.get("children", [])))


def _parse_strikethrough(token: Token) -> inlines.Strikethrough:
    return inlines.Strikethrough(children=_parse_inlines(token.get("children", [])))


def _parse_link(token: Token) -> inlines.Link:
    attrs = token.get("attrs", {})
    url = attrs.get("url") or token.get("link", "")
    title = attrs.get("title")
    return inlines.Link(
        url=url,
        children=_parse_inlines(token.get("children", [])),
        title=title,
    )


def _parse_image(token: Token) -> inlines.Image:
    attrs = token.get("attrs", {})
    url = attrs.get("url", attrs.get("src", ""))
    alt = token.get("alt", attrs.get("alt", ""))
    title = attrs.get("title")
    children = token.get("children")
    if not alt and children:
        alt_parts: list[str] = []
        for c in children:
            if c["type"] == "text":
                alt_parts.append(c.get("raw", ""))
        alt = "".join(alt_parts)
    return inlines.Image(url=url, alt=alt, title=title)


def _parse_codespan(token: Token) -> inlines.CodeSpan:
    return inlines.CodeSpan(code=token.get("raw", ""))


def _parse_linebreak(_token: Token) -> inlines.HardBreak:
    return inlines.HardBreak()


def _parse_softbreak(_token: Token) -> inlines.SoftBreak:
    return inlines.SoftBreak()


# ── Annotation-only inline parsers ─────────────────────────────────


def _parse_mention(token: Token) -> inlines.Mention:
    attrs = token.get("attrs", {})
    return inlines.Mention(
        id=attrs.get("id", ""),
        text=attrs.get("text"),
        access_level=attrs.get("accessLevel"),
        user_type=attrs.get("userType"),
    )


def _parse_emoji(token: Token) -> inlines.Emoji:
    attrs = token.get("attrs", {})
    return inlines.Emoji(
        short_name=attrs.get("shortName", ""),
        text=attrs.get("text"),
        id=attrs.get("id"),
    )


def _parse_date(token: Token) -> inlines.Date:
    attrs = token.get("attrs", {})
    return inlines.Date(timestamp=attrs.get("timestamp", ""))


def _parse_status(token: Token) -> inlines.Status:
    attrs = token.get("attrs", {})
    return inlines.Status(
        text=attrs.get("text", ""),
        color=attrs.get("color", ""),
        style=attrs.get("style"),
    )


def _parse_inline_card(token: Token) -> inlines.InlineCard:
    attrs = token.get("attrs", {})
    url = attrs.get("url")
    if not url:
        inner = _parse_inlines(token.get("children", []))
        for child in inner:
            if isinstance(child, inlines.Link):
                url = child.url
                break
    return inlines.InlineCard(url=url, data=attrs.get("data"))


def _parse_media_inline(token: Token) -> inlines.MediaInline:
    attrs = token.get("attrs", {})
    return inlines.MediaInline(
        id=attrs.get("id"),
        collection=attrs.get("collection"),
        media_type=attrs.get("mediaType", "file"),
        alt=attrs.get("alt"),
        width=attrs.get("width"),
        height=attrs.get("height"),
    )


def _parse_underline(token: Token) -> inlines.Underline:
    return inlines.Underline(children=_parse_inlines(token.get("children", [])))


def _parse_text_color(token: Token) -> inlines.TextColor:
    attrs = token.get("attrs", {})
    return inlines.TextColor(
        color=attrs.get("color", ""),
        children=_parse_inlines(token.get("children", [])),
    )


def _parse_background_color(token: Token) -> inlines.BackgroundColor:
    attrs = token.get("attrs", {})
    return inlines.BackgroundColor(
        color=attrs.get("color", ""),
        children=_parse_inlines(token.get("children", [])),
    )


def _parse_subsup(token: Token) -> inlines.SubSup:
    attrs = token.get("attrs", {})
    return inlines.SubSup(
        type=attrs.get("type", "sub"),
        children=_parse_inlines(token.get("children", [])),
    )


def _parse_annotation(token: Token) -> inlines.Annotation:
    attrs = token.get("attrs", {})
    return inlines.Annotation(
        id=attrs.get("id", ""),
        children=_parse_inlines(token.get("children", [])),
        annotation_type=attrs.get("annotationType", "inlineComment"),
    )


def _parse_placeholder(token: Token) -> inlines.Placeholder:
    inner = _parse_inlines(token.get("children", []))
    text = ""
    for child in inner:
        if isinstance(child, inlines.Text):
            text += child.text
    return inlines.Placeholder(text=text)


def _parse_inline_extension(token: Token) -> inlines.InlineExtension:
    return inlines.InlineExtension(raw=token.get("attrs", {}))


# ── Helpers ─────────────────────────────────────────────────────────


def _build_media(d: dict[str, Any]) -> blocks.Media:
    return blocks.Media(
        media_type=d.get("mediaType", "file"),
        url=d.get("url"),
        id=d.get("id"),
        collection=d.get("collection"),
        alt=d.get("alt"),
        width=d.get("width"),
        height=d.get("height"),
    )


def _unwrap_blockquote(inner: Sequence[blocks.Block]) -> list[blocks.Block]:
    """If inner is a single BlockQuote, unwrap its children."""
    if len(inner) == 1 and isinstance(inner[0], blocks.BlockQuote):
        return list(inner[0].children)
    return list(inner)


def _flatten_inlines(block_nodes: Sequence[blocks.Block]) -> list[inlines.Inline]:
    """Extract inlines from a list of blocks (typically single Paragraph)."""
    result: list[inlines.Inline] = []
    for b in block_nodes:
        if isinstance(b, blocks.Paragraph):
            result.extend(b.children)
    return result


def _extract_task_items(
    inner: Sequence[blocks.Block],
) -> list[blocks.TaskItem]:
    """Extract TaskItems from bullet list rendered inside annotation."""
    items: list[blocks.TaskItem] = []
    for block in inner:
        if isinstance(block, blocks.BulletList):
            for li in block.items:
                state = "DONE" if li.checked else "TODO"
                inls = _flatten_inlines(li.children)
                items.append(blocks.TaskItem(children=inls, state=state))
        elif isinstance(block, blocks.Paragraph):
            state, inls = _check_task_prefix(block.children)
            items.append(blocks.TaskItem(children=inls, state=state))
    return items


def _extract_decision_items(
    inner: Sequence[blocks.Block],
) -> list[blocks.DecisionItem]:
    """Extract DecisionItems from bullet list rendered inside annotation."""
    items: list[blocks.DecisionItem] = []
    for block in inner:
        if isinstance(block, blocks.BulletList):
            for li in block.items:
                state = "DECIDED" if li.checked else ""
                inls = _flatten_inlines(li.children)
                items.append(blocks.DecisionItem(children=inls, state=state))
        elif isinstance(block, blocks.Paragraph):
            state, inls = _check_decision_prefix(block.children)
            items.append(blocks.DecisionItem(children=inls, state=state))
    return items


def _check_task_prefix(
    nodes: list[inlines.Inline],
) -> tuple[str, list[inlines.Inline]]:
    """Check for [x]/[ ] prefix in inline nodes."""
    if nodes and isinstance(nodes[0], inlines.Text):
        text = nodes[0].text
        if text.startswith("[x] "):
            rest = text[4:]
            new_nodes = ([inlines.Text(text=rest)] if rest else []) + list(nodes[1:])
            return "DONE", new_nodes
        elif text.startswith("[ ] "):
            rest = text[4:]
            new_nodes = ([inlines.Text(text=rest)] if rest else []) + list(nodes[1:])
            return "TODO", new_nodes
    return "TODO", list(nodes)


def _check_decision_prefix(
    nodes: list[inlines.Inline],
) -> tuple[str, list[inlines.Inline]]:
    """Check for [x]/[ ] prefix in inline nodes for decisions."""
    if nodes and isinstance(nodes[0], inlines.Text):
        text = nodes[0].text
        if text.startswith("[x] "):
            rest = text[4:]
            new_nodes = ([inlines.Text(text=rest)] if rest else []) + list(nodes[1:])
            return "DECIDED", new_nodes
        elif text.startswith("[ ] "):
            rest = text[4:]
            new_nodes = ([inlines.Text(text=rest)] if rest else []) + list(nodes[1:])
            return "", new_nodes
    return "", list(nodes)


def _apply_cell_attrs(table: blocks.Table, cell_attrs: list[list[Any]] | None) -> None:
    """Apply compact cell attrs to table cells."""
    if not cell_attrs:
        return
    all_rows = [table.head, *table.body]
    for row_idx, row_attr in enumerate(cell_attrs):
        if row_idx >= len(all_rows):
            break
        row = all_rows[row_idx]
        for col_idx, attr in enumerate(row_attr):
            if col_idx >= len(row):
                break
            cell = row[col_idx]
            if attr is None:
                continue
            if isinstance(attr, list):
                cell.col_width = attr
            elif isinstance(attr, dict):
                d = cast(dict[str, Any], attr)
                if d.get("colspan"):
                    cell.colspan = d["colspan"]
                if d.get("rowspan"):
                    cell.rowspan = d["rowspan"]
                if d.get("colwidth"):
                    cell.col_width = d["colwidth"]
                if d.get("background"):
                    cell.background = d["background"]
                if d.get("header"):
                    header = blocks.TableHeader(
                        children=cell.children,
                        colspan=cell.colspan,
                        rowspan=cell.rowspan,
                        col_width=cell.col_width,
                        background=cell.background,
                    )
                    row[col_idx] = header


_CELL_BLOCK_TAGS = frozenset(
    {
        "paragraph",
        "block_code",
        "codeBlock",
        "block_quote",
        "heading",
        "thematic_break",
        "list",
        "panel",
        "expand",
        "nestedExpand",
        "taskList",
        "decisionList",
        "mediaSingle",
        "mediaGroup",
        "blockCard",
        "embedCard",
        "extension",
        "bodiedExtension",
        "syncBlock",
        "bodiedSyncBlock",
    }
)


def _match_html_cell_blocks(tokens: list[Token]) -> list[Token]:
    """Match HTML open/close tag pairs for known block types into annotated-style tokens."""
    result: list[Token] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.get("annotated"):
            result.append(tok)
            i += 1
            continue
        if tok["type"] == "inline_html":
            raw = tok.get("raw", "")
            tag = _extract_html_open_tag(raw)
            if tag and tag in _HTML_CELL_VOID_MAP:
                result.append(
                    Token(
                        type=_HTML_CELL_VOID_MAP[tag],
                        attrs={},
                        children=[],
                        annotated=True,
                    )
                )
                i += 1
                continue
            if tag and tag in _HTML_CELL_BLOCK_MAP:
                close_idx = _find_html_close_idx(tokens, i + 1, tag)
                if close_idx is not None:
                    attrs: dict[str, Any] = {}
                    block_type = _HTML_CELL_BLOCK_MAP[tag]
                    if block_type == "heading":
                        attrs["level"] = int(tag[1])
                    elif block_type == "list":
                        attrs["ordered"] = tag == "ol"
                        start = _extract_html_attr(raw, "start")
                        if start is not None:
                            attrs["start"] = int(start)
                    result.append(
                        Token(
                            type=block_type,
                            attrs=attrs,
                            children=tokens[i + 1 : close_idx],
                            annotated=True,
                        )
                    )
                    i = close_idx + 1
                    continue
        result.append(tok)
        i += 1
    return result


def _cell_annotation_to_block(token: Token) -> Token:
    """Convert an annotated cell token into a standard block-level token.

    For most types the token is passed through as-is.
    HTML-originated blocks (heading, list, block_quote, block_code) need their
    children restructured into standard Mistune format.
    """
    tag = token["type"]
    attrs = token.get("attrs", {})
    inner = [_br_to_linebreak(t) for t in token.get("children", [])]

    match tag:
        case "paragraph":
            return Token(type="paragraph", attrs=attrs, children=inner)
        case "heading":
            level = attrs.get("level", 1)
            stripped = _strip_html_wrapper(inner, f"h{level}")
            return Token(
                type="heading", attrs={**attrs, "level": level}, children=stripped
            )
        case "block_code" | "codeBlock":
            stripped = _strip_html_wrapper(inner, "code")
            code = _inner_tokens_to_text(stripped).replace("<br>", "\n")
            return Token(
                type="block_code", raw=code, attrs={"info": attrs.get("language", "")}
            )
        case "block_quote":
            stripped = _strip_html_wrapper(inner, "blockquote")
            normalized = _normalize_cell_tokens(stripped)
            return Token(type="block_quote", children=normalized)
        case "list":
            ordered = attrs.get("ordered", False)
            html_tag = "ol" if ordered else "ul"
            stripped = _strip_html_wrapper(inner, html_tag)
            li_groups = _split_by_tag(stripped, "li")
            list_items: list[Token] = []
            for li_toks in li_groups:
                li_children = _normalize_cell_tokens(li_toks)
                list_items.append(Token(type="list_item", children=li_children))
            return Token(
                type="list",
                attrs={"ordered": ordered, "start": attrs.get("start", 1)},
                children=list_items,
                tight=True,
            )
        case "panel":
            stripped = _strip_html_wrapper(inner, "blockquote")
            normalized = _normalize_cell_tokens(stripped)
            return Token(type="panel", attrs=attrs, children=normalized, annotated=True)
        case "expand":
            stripped = _strip_html_wrapper(inner, "blockquote")
            normalized = _normalize_cell_tokens(stripped)
            return Token(
                type="expand", attrs=attrs, children=normalized, annotated=True
            )
        case "nestedExpand":
            stripped = _strip_html_wrapper(inner, "blockquote")
            normalized = _normalize_cell_tokens(stripped)
            return Token(
                type="nestedExpand", attrs=attrs, children=normalized, annotated=True
            )
        case "taskList":
            stripped = _strip_html_wrapper(inner, "ul")
            li_groups = _split_by_tag(stripped, "li")
            task_items: list[Token] = []
            for li_toks in li_groups:
                task_items.append(Token(type="paragraph", children=li_toks))
            return Token(
                type="taskList", attrs=attrs, children=task_items, annotated=True
            )
        case "decisionList":
            stripped = _strip_html_wrapper(inner, "ul")
            li_groups = _split_by_tag(stripped, "li")
            decision_items: list[Token] = []
            for li_toks in li_groups:
                decision_items.append(Token(type="paragraph", children=li_toks))
            return Token(
                type="decisionList",
                attrs=attrs,
                children=decision_items,
                annotated=True,
            )
        case _:
            return token


def _extract_html_open_tag(raw: str) -> str | None:
    """Extract tag name from an opening HTML tag, or None."""
    s = raw.strip().lower()
    if not s.startswith("<") or s.startswith("</"):
        return None
    tag = s.lstrip("<").split(">")[0].split()[0].rstrip("/")
    return tag if tag else None


_HTML_ATTR_RE = re.compile(r"""(\w+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")


def _extract_html_attr(raw: str, name: str) -> str | None:
    """Extract a named attribute value from an HTML open tag."""
    for m in _HTML_ATTR_RE.finditer(raw):
        if m.group(1).lower() == name.lower():
            return m.group(2) if m.group(2) is not None else m.group(3)
    return None


def _find_html_close_idx(tokens: list[Token], start: int, tag: str) -> int | None:
    """Find matching close tag index, handling nesting."""
    depth = 1
    for i in range(start, len(tokens)):
        tok = tokens[i]
        if tok.get("annotated"):
            continue
        if tok["type"] == "inline_html":
            raw = tok.get("raw", "").strip().lower()
            if (
                raw.startswith(f"<{tag}")
                and raw.endswith(">")
                and not raw.startswith(f"</{tag}")
            ):
                depth += 1
            elif raw == f"</{tag}>":
                depth -= 1
                if depth == 0:
                    return i
    return None


def _classify_br(tok: Token) -> Token:
    """Classify `<br>` variants: `<br>` → block separator, `<br/>` → linebreak."""
    if tok["type"] != "inline_html":
        return tok
    raw = tok.get("raw", "").strip().lower()
    if raw == "<br/>":
        return Token(type="linebreak")
    if raw == "<br>":
        return Token(type="block_separator")
    return tok


def _br_to_linebreak(tok: Token) -> Token:
    """Convert `<br/>` to linebreak inside annotated children."""
    if tok["type"] == "inline_html" and tok.get("raw", "").strip().lower() == "<br/>":
        return Token(type="linebreak")
    return tok


def _strip_html_wrapper(tokens: list[Token], tag: str) -> list[Token]:
    """Remove opening and closing HTML tags from token list."""
    start = 0
    end = len(tokens)
    if tokens and tokens[0]["type"] == "inline_html":
        raw = tokens[0].get("raw", "").strip().lower()
        if raw.startswith(f"<{tag}") and raw.endswith(">"):
            start = 1
    if end > start and tokens[end - 1]["type"] == "inline_html":
        raw = tokens[end - 1].get("raw", "").strip().lower()
        if raw == f"</{tag}>":
            end -= 1
    return tokens[start:end]


def _split_by_tag(tokens: list[Token], tag: str) -> list[list[Token]]:
    """Split tokens by <tag>...</tag> pairs, returning inner content of each."""
    groups: list[list[Token]] = []
    current: list[Token] | None = None

    for tok in tokens:
        if tok["type"] == "inline_html":
            raw = tok.get("raw", "").strip().lower()
            if (
                raw.startswith(f"<{tag}")
                and raw.endswith(">")
                and not raw.startswith(f"</{tag}")
            ):
                current = []
                continue
            elif raw == f"</{tag}>":
                if current is not None:
                    groups.append(current)
                    current = None
                continue
        if current is not None:
            current.append(tok)

    return groups


def _inner_tokens_to_text(tokens: list[Token]) -> str:
    """Extract plain text from inner tokens (for code blocks)."""
    parts: list[str] = []
    for tok in tokens:
        if tok["type"] == "text":
            parts.append(tok.get("raw", ""))
        elif tok["type"] == "linebreak":
            parts.append("<br>")
        elif tok["type"] == "inline_html":
            parts.append(tok.get("raw", "").strip())
        elif tok["type"] == "codespan":
            parts.append(tok.get("raw", ""))
        else:
            parts.append(tok.get("raw", ""))
    return "".join(parts)
