"""Markdown → Union AST 파싱. `<!-- adf:... -->` 주석이 있으면 차집합 노드를 자동 복원."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal, cast

import mistune

from marklas.nodes import blocks, inlines

type _Alignment = Literal["left", "center", "right"] | None

# ── ADF 주석 파싱 ────────────────────────────────────────────────────

_ADF_COMMENT_RE = re.compile(r"<!--\s*(/?)adf:(\w+)\s*(.*?)-->")
_ADF_COMMENT_SPLIT_RE = re.compile(r"(<!--\s*/?adf:\w+\s*.*?-->)")


def _split_inline_adf(raw: str) -> list[inlines.Inline]:
    """block_html raw에서 인라인 ADF 주석과 텍스트를 분리."""
    parts = _ADF_COMMENT_SPLIT_RE.split(raw.strip())
    children: list[inlines.Inline] = []
    for part in parts:
        if not part:
            continue
        parsed = _parse_adf_comment(part)
        if parsed:
            closing, tag, attrs = parsed
            children.append(_AdfInlineComment(tag=tag, attrs=attrs, closing=closing))
        else:
            children.append(inlines.Text(text=part))
    return children


def _parse_adf_comment(raw: str) -> tuple[bool, str, dict[str, Any]] | None:
    """ADF 주석이면 (closing, tag, attrs) 반환, 아니면 None."""
    m = _ADF_COMMENT_RE.fullmatch(raw.strip())
    if not m:
        return None
    closing, tag, attr_str = m.groups()
    try:
        attrs: dict[str, Any] = json.loads(attr_str) if attr_str.strip() else {}
    except json.JSONDecodeError:
        return None
    return bool(closing), tag, attrs


# ── 마커 노드 ────────────────────────────────────────────────────────


@dataclass
class _AdfBlockComment(blocks.Block):
    tag: str = ""
    attrs: dict[str, Any] | None = None
    closing: bool = False


@dataclass
class _AdfInlineComment(inlines.Inline):
    tag: str = ""
    attrs: dict[str, Any] | None = None
    closing: bool = False


# ── 1단계: mistune AST 렌더러 ────────────────────────────────────────


class _ASTRenderer(mistune.BaseRenderer):
    """mistune 커스텀 렌더러: 토큰을 AST 노드로 직접 변환한다."""

    def _render_children(self, token: dict[str, Any], state: Any) -> list[Any]:
        result: list[Any] = []
        for child in token.get("children", []):
            node: Any = self.render_token(child, state)
            if node is not None:
                result.append(node)
        return result

    def _flatten_text(self, token: dict[str, Any]) -> str:
        if "raw" in token:
            return token["raw"]
        parts: list[str] = []
        for child in token.get("children", []):
            parts.append(self._flatten_text(child))
        return "".join(parts)

    def __call__(self, tokens: Any, state: Any) -> blocks.Document:  # type: ignore[override]
        children: list[blocks.Block] = []
        for tok in tokens:
            node: Any = self.render_token(tok, state)
            if node is not None:
                children.append(node)
        return blocks.Document(children=children)

    # ── Block methods ────────────────────────────────────────────────

    def paragraph(self, token: dict[str, Any], state: Any) -> blocks.Paragraph:
        return blocks.Paragraph(children=self._render_children(token, state))

    def block_text(self, token: dict[str, Any], state: Any) -> blocks.Paragraph:
        return blocks.Paragraph(children=self._render_children(token, state))

    def heading(self, token: dict[str, Any], state: Any) -> blocks.Heading:
        return blocks.Heading(
            level=token["attrs"]["level"],
            children=self._render_children(token, state),
        )

    def block_code(self, token: dict[str, Any], state: Any) -> blocks.CodeBlock:
        code = token["raw"]
        if code.endswith("\n"):
            code = code[:-1]
        attrs: dict[str, Any] = token.get("attrs") or {}
        return blocks.CodeBlock(code=code, language=attrs.get("info"))

    def block_quote(self, token: dict[str, Any], state: Any) -> blocks.BlockQuote:
        return blocks.BlockQuote(children=self._render_children(token, state))

    def thematic_break(self, token: dict[str, Any], state: Any) -> blocks.ThematicBreak:
        return blocks.ThematicBreak()

    def list(
        self, token: dict[str, Any], state: Any
    ) -> blocks.BulletList | blocks.OrderedList:
        items = self._render_children(token, state)
        tight = token.get("tight", True)
        attrs = token["attrs"]
        if attrs["ordered"]:
            return blocks.OrderedList(
                items=items, start=attrs.get("start", 1), tight=tight
            )
        return blocks.BulletList(items=items, tight=tight)

    def list_item(self, token: dict[str, Any], state: Any) -> blocks.ListItem:
        return blocks.ListItem(children=self._render_children(token, state))

    def task_list_item(self, token: dict[str, Any], state: Any) -> blocks.ListItem:
        return blocks.ListItem(
            children=self._render_children(token, state),
            checked=token["attrs"]["checked"],
        )

    def table(self, token: dict[str, Any], state: Any) -> blocks.Table:
        head: list[blocks.TableCell] = []
        body: list[list[blocks.TableCell]] = []
        alignments: list[_Alignment] = []

        for child in token.get("children", []):
            if child["type"] == "table_head":
                for cell_tok in child.get("children", []):
                    cell_inlines = self._render_children(cell_tok, state)
                    head.append(
                        blocks.TableCell(
                            children=[blocks.Paragraph(children=cell_inlines)]
                        )
                    )
                    alignments.append(cell_tok.get("attrs", {}).get("align"))
            elif child["type"] == "table_body":
                for row_tok in child.get("children", []):
                    row: list[blocks.TableCell] = []
                    for cell_tok in row_tok.get("children", []):
                        cell_inlines = self._render_children(cell_tok, state)
                        row.append(
                            blocks.TableCell(
                                children=[blocks.Paragraph(children=cell_inlines)]
                            )
                        )
                    body.append(row)

        if head and _is_empty_head(head):
            head = []
        return blocks.Table(head=head, body=body, alignments=alignments)

    def blank_line(self, token: dict[str, Any], state: Any) -> None:
        return None

    def block_html(
        self, token: dict[str, Any], state: Any
    ) -> _AdfBlockComment | blocks.Paragraph | None:
        raw = token["raw"]
        # 단일 ADF 주석 → 블록 마커
        parsed = _parse_adf_comment(raw)
        if parsed:
            closing, tag, attrs = parsed
            return _AdfBlockComment(tag=tag, attrs=attrs, closing=closing)
        # 인라인 ADF 주석이 줄 전체를 차지하면 block_html로 인식됨
        # → 인라인 children으로 분리하여 Paragraph로 래핑
        if "<!-- adf:" in raw or "<!-- /adf:" in raw:
            children = _split_inline_adf(raw)
            if children:
                return blocks.Paragraph(children=children)
        return None

    # ── Inline methods ───────────────────────────────────────────────

    def text(self, token: dict[str, Any], state: Any) -> inlines.Text:
        return inlines.Text(text=token["raw"])

    def strong(self, token: dict[str, Any], state: Any) -> inlines.Strong:
        return inlines.Strong(children=self._render_children(token, state))

    def emphasis(self, token: dict[str, Any], state: Any) -> inlines.Emphasis:
        return inlines.Emphasis(children=self._render_children(token, state))

    def strikethrough(self, token: dict[str, Any], state: Any) -> inlines.Strikethrough:
        return inlines.Strikethrough(children=self._render_children(token, state))

    def link(self, token: dict[str, Any], state: Any) -> inlines.Link:
        return inlines.Link(
            url=token["attrs"]["url"],
            children=self._render_children(token, state),
            title=token["attrs"].get("title"),
        )

    def image(self, token: dict[str, Any], state: Any) -> inlines.Image:
        return inlines.Image(
            url=token["attrs"]["url"],
            alt=self._flatten_text(token),
            title=token["attrs"].get("title"),
        )

    def codespan(self, token: dict[str, Any], state: Any) -> inlines.CodeSpan:
        return inlines.CodeSpan(code=token["raw"])

    def linebreak(self, token: dict[str, Any], state: Any) -> inlines.HardBreak:
        return inlines.HardBreak()

    def softbreak(self, token: dict[str, Any], state: Any) -> inlines.SoftBreak:
        return inlines.SoftBreak()

    def inline_html(
        self, token: dict[str, Any], state: Any
    ) -> _AdfInlineComment | None:
        parsed = _parse_adf_comment(token["raw"])
        if parsed:
            closing, tag, attrs = parsed
            return _AdfInlineComment(tag=tag, attrs=attrs, closing=closing)
        return None


_md = mistune.create_markdown(
    renderer=_ASTRenderer(),
    plugins=["table", "strikethrough", "task_lists"],
)


# ── 2단계: 주석-요소 페어링 ──────────────────────────────────────────


def _pair_block_annotations(children: list[blocks.Block]) -> list[blocks.Block]:
    result: list[blocks.Block] = []
    i = 0
    while i < len(children):
        child = children[i]
        if isinstance(child, _AdfBlockComment) and not child.closing:
            tag = child.tag
            attrs = child.attrs or {}
            inner: list[blocks.Block] = []
            i += 1
            found_closing = False
            while i < len(children):
                c = children[i]
                if isinstance(c, _AdfBlockComment) and c.closing and c.tag == tag:
                    found_closing = True
                    break
                inner.append(c)
                i += 1
            if found_closing:
                result.append(_build_block_node(tag, attrs, inner))
            else:
                result.extend(inner)
        elif isinstance(child, _AdfBlockComment) and child.closing:
            pass  # 짝 없는 닫는 주석 무시
        else:
            result.append(child)
        i += 1
    return result


def _pair_inline_annotations(
    children: list[inlines.Inline],
) -> list[inlines.Inline]:
    result: list[inlines.Inline] = []
    i = 0
    while i < len(children):
        child = children[i]
        if isinstance(child, _AdfInlineComment) and not child.closing:
            tag = child.tag
            attrs = child.attrs or {}
            inner: list[inlines.Inline] = []
            i += 1
            found_closing = False
            while i < len(children):
                c = children[i]
                if isinstance(c, _AdfInlineComment) and c.closing and c.tag == tag:
                    found_closing = True
                    break
                inner.append(c)
                i += 1
            if found_closing:
                inner = _pair_inline_annotations(inner)  # 재귀: 중첩 인라인 주석
                result.append(_build_inline_node(tag, attrs, inner))
            else:
                result.extend(inner)
        elif isinstance(child, _AdfInlineComment) and child.closing:
            pass
        else:
            match child:
                case inlines.Strong() | inlines.Emphasis() | inlines.Strikethrough() | inlines.Link():
                    child.children = _pair_inline_annotations(child.children)
                case _:
                    pass
            result.append(child)
        i += 1
    return result


def _post_process(children: list[blocks.Block]) -> list[blocks.Block]:
    children = _pair_block_annotations(children)
    for child in children:
        _apply_inline_annotations(child)
    return children


def _apply_inline_annotations(block: blocks.Block) -> None:
    """블록 내부의 인라인 주석을 재귀적으로 페어링."""
    match block:
        case blocks.Paragraph():
            block.children = _pair_inline_annotations(block.children)
        case blocks.Heading():
            block.children = _pair_inline_annotations(block.children)
        case blocks.BlockQuote():
            block.children = _post_process(block.children)
        case blocks.BulletList():
            for item in block.items:
                item.children = _post_process(item.children)
        case blocks.OrderedList():
            for item in block.items:
                item.children = _post_process(item.children)
        case blocks.Table():
            for cell in block.head:
                cell.children = _post_process(cell.children)
            for row in block.body:
                for cell in row:
                    cell.children = _post_process(cell.children)
        case _:
            pass


# ── 노드 빌더 ────────────────────────────────────────────────────────


def _build_block_node(
    tag: str, attrs: dict[str, Any], inner: list[blocks.Block]
) -> blocks.Block:
    match tag:
        case "panel":
            children = _unwrap_blockquote(inner)
            children = _post_process(children)
            return blocks.Panel(
                children=children,
                panel_type=attrs["panelType"],
                panel_icon=attrs.get("panelIcon"),
                panel_icon_id=attrs.get("panelIconId"),
                panel_icon_text=attrs.get("panelIconText"),
                panel_color=attrs.get("panelColor"),
            )

        case "expand":
            children = _unwrap_blockquote(inner)
            children = _post_process(children)
            return blocks.Expand(children=children, title=attrs.get("title"))

        case "nestedExpand":
            children = _unwrap_blockquote(inner)
            children = _post_process(children)
            return blocks.NestedExpand(children=children, title=attrs.get("title"))

        case "taskList":
            items = _parse_task_items(inner)
            return blocks.TaskList(items=items)

        case "decisionList":
            items = _parse_decision_items(inner)
            return blocks.DecisionList(items=items)

        case "layoutSection":
            inner = _pair_block_annotations(inner)
            columns = [c for c in inner if isinstance(c, blocks.LayoutColumn)]
            return blocks.LayoutSection(columns=columns)

        case "layoutColumn":
            children = _post_process(inner)
            return blocks.LayoutColumn(children=children, width=attrs.get("width"))

        case "mediaSingle":
            media = _parse_media_attrs(attrs.get("media", {}))
            return blocks.MediaSingle(
                media=media,
                layout=attrs.get("layout"),
                width=attrs.get("width"),
                width_type=attrs.get("widthType"),
            )

        case "mediaGroup":
            media_list = [
                _parse_media_attrs(m) for m in attrs.get("mediaList", [])
            ]
            return blocks.MediaGroup(media_list=media_list)

        case "blockCard":
            return blocks.BlockCard(url=attrs.get("url"), data=attrs.get("data"))

        case "embedCard":
            return blocks.EmbedCard(
                url=attrs["url"],
                layout=attrs["layout"],
                width=attrs.get("width"),
                original_width=attrs.get("originalWidth"),
                original_height=attrs.get("originalHeight"),
            )

        case "paragraph":
            para = (
                inner[0]
                if inner and isinstance(inner[0], blocks.Paragraph)
                else blocks.Paragraph(children=[])
            )
            para.alignment = attrs.get("align")
            para.indentation = attrs.get("indentation")
            return para

        case "heading":
            heading = (
                inner[0]
                if inner and isinstance(inner[0], blocks.Heading)
                else blocks.Heading(level=1, children=[])
            )
            heading.alignment = attrs.get("align")
            heading.indentation = attrs.get("indentation")
            return heading

        case "table":
            table = next((c for c in inner if isinstance(c, blocks.Table)), None)
            if table is None:
                return inner[0] if inner else blocks.Paragraph(children=[])
            table.display_mode = attrs.get("displayMode")
            table.is_number_column_enabled = attrs.get("isNumberColumnEnabled")
            table.layout = attrs.get("layout")
            table.width = attrs.get("width")
            cell_attrs_grid: list[list[dict[str, Any] | None]] | None = attrs.get(
                "cells"
            )
            if cell_attrs_grid:
                _apply_cell_attrs_grid(table, cell_attrs_grid)
            return table

        case _:
            return inner[0] if inner else blocks.Paragraph(children=[])


def _build_inline_node(
    tag: str, attrs: dict[str, Any], inner: list[inlines.Inline]
) -> inlines.Inline:
    match tag:
        # 독립 인라인 — attrs에서 복원, inner(fallback) 무시
        case "mention":
            return inlines.Mention(
                id=attrs["id"],
                text=attrs.get("text"),
                access_level=attrs.get("accessLevel"),
                user_type=attrs.get("userType"),
            )
        case "emoji":
            return inlines.Emoji(
                short_name=attrs["shortName"],
                text=attrs.get("text"),
                id=attrs.get("id"),
            )
        case "date":
            return inlines.Date(timestamp=attrs["timestamp"])
        case "status":
            return inlines.Status(
                text=attrs["text"],
                color=attrs["color"],
                style=attrs.get("style"),
            )
        case "inlineCard":
            url = attrs.get("url")
            if url is None and not attrs.get("data"):
                url = _extract_url_from_inner(inner)
            return inlines.InlineCard(url=url, data=attrs.get("data"))
        case "mediaInline":
            return inlines.MediaInline(
                id=attrs.get("id"),
                collection=attrs.get("collection"),
                media_type=attrs.get("mediaType", "file"),
                alt=attrs.get("alt"),
                width=attrs.get("width"),
                height=attrs.get("height"),
            )
        # 래핑 marks — inner를 children으로 사용
        case "underline":
            return inlines.Underline(children=inner)
        case "textColor":
            return inlines.TextColor(color=attrs["color"], children=inner)
        case "backgroundColor":
            return inlines.BackgroundColor(color=attrs["color"], children=inner)
        case "subSup":
            return inlines.SubSup(type=attrs["type"], children=inner)
        case "annotation":
            return inlines.Annotation(
                id=attrs["id"],
                children=inner,
                annotation_type=attrs.get("annotationType", "inlineComment"),
            )
        case _:
            return inlines.Text(text="")


def _is_empty_head(head: list[blocks.TableCell]) -> bool:
    """헤더 행의 모든 셀이 빈 텍스트인지 확인. headerless table 복원용."""
    for cell in head:
        for child in cell.children:
            if not isinstance(child, blocks.Paragraph):
                return False
            for inline in child.children:
                if not isinstance(inline, inlines.Text) or inline.text.strip():
                    return False
    return True


# ── 유틸리티 ─────────────────────────────────────────────────────────


_MARKDOWN_LINK_RE = re.compile(r"\[.*?\]\((.*?)\)")


def _extract_url_from_inner(inner: list[inlines.Inline]) -> str | None:
    """inner nodes에서 URL 추출. inlineCard compact format용.
    mistune은 인라인 주석 사이 텍스트를 raw Text로 처리하므로 정규식 추출 필요."""
    for node in inner:
        if isinstance(node, inlines.Link):
            return node.url
        if isinstance(node, inlines.Text):
            m = _MARKDOWN_LINK_RE.search(node.text)
            if m:
                return m.group(1)
    return None


def _unwrap_blockquote(inner: list[blocks.Block]) -> list[blocks.Block]:
    """annotation 내부의 BlockQuote를 벗겨서 children 추출."""
    if len(inner) == 1 and isinstance(inner[0], blocks.BlockQuote):
        return inner[0].children
    return inner


def _parse_media_attrs(attrs: dict[str, Any]) -> blocks.Media:
    return blocks.Media(
        media_type=attrs.get("mediaType", "file"),
        url=attrs.get("url"),
        id=attrs.get("id"),
        collection=attrs.get("collection"),
        alt=attrs.get("alt"),
        width=attrs.get("width"),
        height=attrs.get("height"),
    )


def _parse_task_items(inner: list[blocks.Block]) -> list[blocks.TaskItem]:
    items: list[blocks.TaskItem] = []
    for block in inner:
        if isinstance(block, blocks.BulletList):
            for li in block.items:
                child_inlines = _extract_inlines(li.children)
                child_inlines = _pair_inline_annotations(child_inlines)
                state = "DONE" if li.checked else "TODO"
                items.append(
                    blocks.TaskItem(
                        children=child_inlines,
                        state=state,
                    )
                )
    return items


def _parse_decision_items(inner: list[blocks.Block]) -> list[blocks.DecisionItem]:
    items: list[blocks.DecisionItem] = []
    for block in inner:
        if isinstance(block, blocks.BulletList):
            for li in block.items:
                child_inlines = _extract_inlines(li.children)
                child_inlines = _pair_inline_annotations(child_inlines)
                state = "DECIDED" if li.checked else ""
                items.append(
                    blocks.DecisionItem(
                        children=child_inlines,
                        state=state,
                    )
                )
    return items


def _extract_inlines(children: list[blocks.Block]) -> list[inlines.Inline]:
    """ListItem.children(list[Block])에서 인라인 추출."""
    result: list[inlines.Inline] = []
    for child in children:
        if isinstance(child, blocks.Paragraph):
            result.extend(child.children)
    return result


def _apply_cell_attrs_grid(
    table: blocks.Table, grid: list[list[Any]]
) -> None:
    """Compact cell attrs 적용. list=colwidth, dict=full attrs, None=기본값."""
    all_rows = [table.head, *table.body]
    for row_idx, row_attrs in enumerate(grid):
        if row_idx >= len(all_rows):
            break
        for col_idx, cell_attr in enumerate(row_attrs):
            if col_idx >= len(all_rows[row_idx]) or cell_attr is None:
                continue
            cell = all_rows[row_idx][col_idx]
            if isinstance(cell_attr, list):
                cell.col_width = cell_attr
            elif isinstance(cell_attr, dict):
                ca = cast(dict[str, Any], cell_attr)
                cell.colspan = ca.get("colspan")
                cell.rowspan = ca.get("rowspan")
                cell.col_width = ca.get("colwidth")
                cell.background = ca.get("background")
                if ca.get("header") and not isinstance(cell, blocks.TableHeader):
                    header_cell = blocks.TableHeader(
                        children=cell.children,
                        colspan=cell.colspan,
                        rowspan=cell.rowspan,
                        col_width=cell.col_width,
                        background=cell.background,
                    )
                    all_rows[row_idx][col_idx] = header_cell


# ── Public API ───────────────────────────────────────────────────────


def parse(markdown: str) -> blocks.Document:
    doc = cast(blocks.Document, _md(markdown))
    doc.children = _post_process(doc.children)
    return doc
