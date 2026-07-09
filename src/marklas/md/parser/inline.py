"""Inline-level dispatch and per-node builders.

Public entry: `parse_inlines(tokens)`. The pipeline is

    raw mistune tokens
        → normalize_inlines (pair up inline_html, recognize <br>)
        → _flatten (dispatch each normalized token, accumulating marks)
        → list[ast.Inline]

Dispatch is `match` over the IR. There are exactly two sources of inline
content:

- raw mistune tokens (text, strong, em, link, codespan, softbreak,
  linebreak, …)  — unchanged dicts pass through to `_build_raw_inline`.
- HTML extensions (`<span adf="mention">`, `<u adf="underline">`, …) —
  HtmlPaired/HtmlVoid objects produced by `normalize_inlines` flow to
  `_build_paired_inline` / a HardBreak shortcut.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from marklas import ast

from .ir import HtmlPaired, HtmlVoid, Token
from .normalize import get_params, inline_parser, media_border_marks, normalize_inlines


# Reuse the package-level mistune instance's inline parser so the same set
# of plugins (strikethrough, task_lists, …) applies — instantiating a bare
# InlineParser misses those and silently loses marks like strike.
_INLINE_PARSER = inline_parser


# ── Public entry ──────────────────────────────────────────────────────────────


def parse_inlines(tokens: list[dict[str, Any]]) -> list[ast.Inline]:
    """Convert a list of raw mistune inline tokens to AST Inline nodes."""
    return _flatten(normalize_inlines(tokens), [])


def reparse_text_inlines(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Re-run text tokens through mistune's inline parser.

    When the block-level parser emits a `block_html` chunk (e.g. a
    `<li adf="decisionItem">...**bold**...</li>` jammed onto one line),
    mistune skips inline parsing for its contents, so markdown marks
    (`**bold**`, `*em*`, ``​`code`​``, links, …) survive as
    literal characters in a single text token. This helper re-tokenizes
    each text run so the downstream pipeline sees structured strong/em/
    codespan/link nodes again. Non-text tokens (inline_html, …) pass
    through untouched.
    """
    out: list[dict[str, Any]] = []
    for t in tokens:
        if t.get("type") == "text":
            raw = t.get("raw", "")
            if raw:
                out.extend(_INLINE_PARSER(raw, {}))
        else:
            out.append(t)
    return out


def parse_normalized_inlines(tokens: list[Token]) -> list[ast.Inline]:
    """Build AST Inline nodes from an already-normalized inline token stream."""
    return _flatten(tokens, [])


# ── Helpers ───────────────────────────────────────────────────────────────────


def inline_text(tokens: list[Token]) -> str:
    """Concatenate textual content from a normalized inline token list.

    Used by paired-HTML builders that flatten inner content to a single
    string (mention, emoji, status, etc.).
    """
    parts: list[str] = []
    for t in tokens:
        if isinstance(t, HtmlPaired):
            parts.append(inline_text(t.inner))
        elif isinstance(t, dict):
            parts.append(t.get("raw", ""))
    return "".join(parts)


def _flatten(tokens: list[Token], parent_marks: list[ast.Mark]) -> list[ast.Inline]:
    """Walk normalized inline tokens, accumulating marks down through nesting."""
    result: list[ast.Inline] = []
    for token in tokens:
        match token:
            case HtmlPaired():
                result.extend(_build_paired_inline(token, parent_marks))
            case HtmlVoid(tag="br"):
                result.append(ast.HardBreak())
            case HtmlVoid():
                # Other inline voids (e.g. self-closing custom tags) — drop.
                continue
            case dict() as raw:
                result.extend(_build_raw_inline(raw, parent_marks))
    return _merge_adjacent_text(result)


def _merge_adjacent_text(inlines: list[ast.Inline]) -> list[ast.Inline]:
    """Coalesce adjacent ast.Text nodes that share the exact same marks.

    mistune emits a single inline span as multiple text tokens when it
    aborts a link/image candidate ("**[label]**" → "[" + "label]" under a
    strong mark). The fragments carry identical marks, so we stitch them
    back together — preserving the round-trip node count.
    """
    merged: list[ast.Inline] = []
    for node in inlines:
        if (
            merged
            and isinstance(node, ast.Text)
            and isinstance(prev := merged[-1], ast.Text)
            and list(prev.marks) == list(node.marks)
        ):
            prev.text += node.text
        else:
            merged.append(node)
    return merged


# ── Raw mistune token dispatch ────────────────────────────────────────────────


def _build_raw_inline(
    token: dict[str, Any], parent_marks: list[ast.Mark]
) -> list[ast.Inline]:
    """Dispatch a raw mistune inline token by its `type`.

    `token.children` (when present) was already normalized by the recursive
    pass in `normalize_inlines`, so it is a list[Token] that flows straight
    into `_flatten` — re-normalizing would crash on the dataclass entries.
    """
    t = token.get("type", "")
    match t:
        case "strong":
            return _flatten(
                token.get("children", []),
                [*parent_marks, ast.StrongMark()],
            )
        case "emphasis":
            return _flatten(
                token.get("children", []),
                [*parent_marks, ast.EmMark()],
            )
        case "strikethrough":
            return _flatten(
                token.get("children", []),
                [*parent_marks, ast.StrikeMark()],
            )
        case "codespan":
            return [
                ast.Text(
                    text=token.get("raw", ""),
                    marks=[*parent_marks, ast.CodeMark()],
                )
            ]
        case "link":
            link_attrs = token.get("attrs", {})
            href = link_attrs.get("url", "") or link_attrs.get("link", "")
            title = link_attrs.get("title")
            return _flatten(
                token.get("children", []),
                [*parent_marks, ast.LinkMark(href=href, title=title)],
            )
        case "text":
            text = token.get("raw", "")
            if parent_marks:
                return [ast.Text(text=text, marks=list(parent_marks))]
            return [ast.Text(text=text)]
        case "softbreak":
            if parent_marks:
                return [ast.Text(text=" ", marks=list(parent_marks))]
            return [ast.Text(text=" ")]
        case "linebreak":
            return [ast.HardBreak()]
        case _:
            children = token.get("children", [])
            if children:
                return _flatten(children, parent_marks)
            return []


# ── Paired HTML extension dispatch ────────────────────────────────────────────


def _build_paired_inline(
    token: HtmlPaired, parent_marks: list[ast.Mark]
) -> list[ast.Inline]:
    """Dispatch a paired HTML extension at inline level."""
    content = inline_text(token.inner)
    match token.adf_type:
        case "mention":
            return [_build_mention(token.attrs, content)]
        case "emoji":
            return [_build_emoji(token.attrs, content)]
        case "date":
            return [_build_date(token.attrs)]
        case "status":
            return [_build_status(token.attrs, content)]
        case "inlineCard":
            return [_build_inline_card(token.attrs)]
        case "placeholder":
            return [_build_placeholder(content)]
        case "mediaInline":
            return [_build_media_inline(token.attrs)]
        case "inlineExtension":
            return [_build_inline_extension(token.attrs)]
        case "unknownInline":
            return [_build_unknown_inline(token.attrs)]
        case (
            "underline"
            | "textColor"
            | "bgColor"
            | "subSup"
            | "annotation"
            | "unknownMark"
            | "link"
        ):
            return _apply_html_mark(
                token.tag, token.adf_type, token.attrs, token.inner, parent_marks
            )
        case _:
            # Unknown adf type at inline level — emit the text content with
            # any ambient marks so we don't lose user-visible characters.
            text = ast.Text(text=content)
            if parent_marks:
                text.marks = list(parent_marks)
            return [text]


def inline_mark_from(
    tag: str, adf_type: str, attrs: Mapping[str, str]
) -> ast.Mark | None:
    """Map an HTML wrapper element to the ADF Mark it encodes.

    The single "wrapper → Mark" recognizer, shared by `_apply_html_mark`
    (text/inline media) and block-media unwrapping in `block.py`.
    """
    match adf_type:
        case "underline":
            return ast.UnderlineMark()
        case "textColor":
            return ast.TextColorMark(color=get_params(attrs).get("color", ""))
        case "bgColor":
            return ast.BackgroundColorMark(color=get_params(attrs).get("color", ""))
        case "subSup":
            return ast.SubSupMark(type="sub" if tag == "sub" else "sup")
        case "annotation":
            p = get_params(attrs)
            return ast.AnnotationMark(
                id=p.get("id", ""),
                annotation_type=p.get("annotationType", "inlineComment"),
            )
        case "unknownMark":
            p = get_params(attrs)
            return ast.UnknownMark(type=p.get("type", ""), attrs=p.get("attrs"))
        case "link":
            return ast.LinkMark(href=attrs.get("href", ""), title=attrs.get("title"))
        case _:
            return None


def _attach_inline_mark(node: ast.Inline, mark: ast.Mark) -> None:
    """Append a wrapping mark to an inline node, respecting its schema.

    Text accepts any mark; MediaInline accepts only the media mark subset.
    Other inline nodes carry no marks (a wrapper around them is a no-op).
    """
    if isinstance(node, ast.Text):
        node.marks = [*node.marks, mark]
    elif isinstance(node, ast.MediaInline) and isinstance(
        mark, (ast.LinkMark, ast.AnnotationMark, ast.BorderMark)
    ):
        node.marks = [*node.marks, mark]


def _apply_html_mark(
    tag: str,
    adf_type: str,
    attrs: Mapping[str, str],
    inner: list[Token],
    parent_marks: list[ast.Mark],
) -> list[ast.Inline]:
    """Wrap inner content with an HTML-encoded mark (underline, link, ...)."""
    mark = inline_mark_from(tag, adf_type, attrs)
    if mark is None:
        content = inline_text(inner)
        text = ast.Text(text=content)
        if parent_marks:
            text.marks = list(parent_marks)
        return [text]

    inlines = _flatten(inner, parent_marks)
    for node in inlines:
        _attach_inline_mark(node, mark)
    return inlines


# ── Inline atom builders ──────────────────────────────────────────────────────


def _build_mention(attrs: Mapping[str, str], content: str) -> ast.Mention:
    p = get_params(attrs)
    return ast.Mention(
        id=p.get("id", ""),
        text=content or None,
        access_level=p.get("accessLevel"),
        user_type=p.get("userType"),
    )


def _build_emoji(attrs: Mapping[str, str], content: str) -> ast.Emoji:
    p = get_params(attrs)
    return ast.Emoji(
        short_name=p.get("shortName", ""),
        id=p.get("id"),
        text=content or None,
    )


def _build_date(attrs: Mapping[str, str]) -> ast.Date:
    return ast.Date(timestamp=attrs.get("datetime", ""))


def _build_status(attrs: Mapping[str, str], content: str) -> ast.Status:
    p = get_params(attrs)
    return ast.Status(
        text=content or p.get("text", ""),
        color=p.get("color", "neutral"),
        style=p.get("style"),
    )


def _build_inline_card(attrs: Mapping[str, str]) -> ast.InlineCard:
    p = get_params(attrs) if "params" in attrs else {}
    return ast.InlineCard(url=attrs.get("href"), data=p.get("data"))


def _build_placeholder(content: str) -> ast.Placeholder:
    return ast.Placeholder(text=content)


def _build_media_inline(attrs: Mapping[str, str]) -> ast.MediaInline:
    p = get_params(attrs)
    media = ast.MediaInline(
        id=p.get("id", ""),
        collection=p.get("collection", ""),
        type=p.get("type"),
        alt=p.get("alt"),
        width=p.get("width"),
        height=p.get("height"),
        data=p.get("data"),
    )
    border = media_border_marks(p)
    if border:
        media.marks = border
    return media


def _build_inline_extension(attrs: Mapping[str, str]) -> ast.InlineExtension:
    p = get_params(attrs)
    return ast.InlineExtension(
        extension_key=p.get("extensionKey", ""),
        extension_type=p.get("extensionType", ""),
        parameters=p.get("parameters"),
        text=p.get("text"),
    )


def _build_unknown_inline(attrs: Mapping[str, str]) -> ast.UnknownInline:
    return ast.UnknownInline(raw=get_params(attrs))
