"""Token normalization — the parser's first non-trivial stage.

mistune emits a flat list of token dicts. We do two things here:

1. **Parse HTML tags and pair up open/close** so that
   `<aside adf="panel">...</aside>` becomes a single `HtmlPaired` IR node
   carrying its inner tokens, and self-contained / void tags become
   `HtmlVoid`.
2. **Keep mistune's own block tokens (paragraph, heading, list, …)
   untouched** as opaque dicts. They are the boundary with mistune — the
   builders in block.py / inline.py read them by their `type` key.

Two contexts share the same paired-matching algorithm:
- `normalize_blocks` — top-level / nested block_html streams
- `normalize_inlines` — inline_html streams inside paragraph children,
  emphasis, links, cell content, etc.

The paired-matching primitive is `find_paired_close`, parameterized over
`token_type`.

Note: mistune's table cell mixes inline_html with text/strong/em/link.
Cell-context grouping is more involved (it pairs inline_html and also
splits inline runs from block-promotable groups); that lives in block.py
under cell handling, but reuses `find_paired_close` from here.
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import mistune

from marklas import ast
from marklas.md import blockmark_keys as keys

from .ir import HtmlPaired, HtmlVoid, Token


# ── Tokenize ──────────────────────────────────────────────────────────────────


# Make a container's open/close tag line — or a whole-line empty self-contained
# element (``<div adf="table" …></div>``) or one-line ``<summary>`` — its own
# single-line block_html. Otherwise CommonMark rule 6 lets the tag swallow
# everything up to the next blank line, so a blank-line-free container (or a
# marker ``<div></div>`` jammed against the block it annotates) collapses into
# one opaque token and the following content is lost. Separating them lets the
# rest parse in place, matching the renderer's blank-line form the pairing logic
# already handles. The self-contained branch requires an empty inner (``></``)
# so content-bearing one-liners (``<ul adf="decisionList"><li>…</li></ul>``)
# stay opaque for the inline re-split path.
_ADF_CONTAINER_TAGS = r"details|aside|section|figure|div|ul"
_ADF_TAG_LINE = (
    r"^ {0,3}(?:"
    rf"<(?:{_ADF_CONTAINER_TAGS})\b[^\n>]*></(?:{_ADF_CONTAINER_TAGS})>"
    rf"|</?(?:{_ADF_CONTAINER_TAGS})\b[^\n>]*>"
    r"|<summary>[^\n]*</summary>"
    r"|</?summary>"
    r")[ \t]*\n"
)


def _parse_adf_tag_line(_block: Any, m: re.Match[str], state: Any) -> int:
    state.append_token({"type": "block_html", "raw": m.group(0)})
    return m.end()


def _adf_containers(md: mistune.Markdown) -> None:
    """mistune plugin: register the `adf_tag_line` rule.

    Inserted before `raw_html` so it wins position ties. Top-level rules only:
    these tags map to nodes (panel, expand, …) reachable only via the top-level
    HTML-pairing path — lists/blockquotes can't validly hold them, cells use a
    separate path.
    """
    md.block.register(
        "adf_tag_line", _ADF_TAG_LINE, _parse_adf_tag_line, before="raw_html"
    )


_md = mistune.create_markdown(
    renderer="ast",
    plugins=["table", "strikethrough", "task_lists", _adf_containers],
)

# Public alias of `_md.inline` for builders that need to re-tokenize raw
# block_html inner text (e.g. `<li adf="decisionItem">**bold**</li>` —
# mistune skips inline parsing for block_html, so marks like strong/em/
# strike survive as literal characters and must be re-parsed).
inline_parser = _md.inline


def tokenize(md: str) -> list[dict[str, Any]]:
    """Run mistune in AST mode and assert the expected shape."""
    result = _md(md)
    if not isinstance(result, list):
        raise TypeError(
            "mistune AST renderer must return a list of token dicts; "
            f"got {type(result).__name__}"
        )
    return result


# ── HTML tag parsing ──────────────────────────────────────────────────────────


_TAG_RE = re.compile(
    r"<(/?)(\w+)"
    r"((?:\s+[\w-]+(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'))?)*)"
    r"\s*/?>",
    re.DOTALL,
)
_ATTR_RE = re.compile(r"""([\w-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'))?""")


def parse_tag(raw: str) -> tuple[str, dict[str, str], bool]:
    """Parse `<tag attr=value ...>` → (tag_name, attrs, is_closing)."""
    m = _TAG_RE.match(raw.strip())
    if not m:
        return ("", {}, False)
    closing = bool(m.group(1))
    tag = m.group(2).lower()
    attr_str = m.group(3) or ""
    attrs: dict[str, str] = {}
    for am in _ATTR_RE.finditer(attr_str):
        key = am.group(1)
        value = (
            am.group(2)
            if am.group(2) is not None
            else (am.group(3) if am.group(3) is not None else "")
        )
        # In a table cell the renderer escapes "|" to "\\|" so the pipe
        # doesn't terminate the cell. mistune unescapes that for plain
        # text but not for inline_html attribute values, leaving "\\|"
        # inside something like params='{"cxhtml":"a\\|b"}' — which then
        # fails JSON parsing. Restore the literal pipe here.
        value = value.replace("\\|", "|")
        attrs[key] = value
    return (tag, attrs, closing)


def parse_params(raw: str) -> dict[str, Any]:
    """Unescape HTML attribute + JSON-parse the `params="..."` attr."""
    unescaped = html.unescape(raw)
    try:
        return json.loads(unescaped)
    except (json.JSONDecodeError, ValueError):
        return {}


def has_adf(attrs: Mapping[str, str]) -> bool:
    return "adf" in attrs


def get_params(attrs: Mapping[str, str]) -> dict[str, Any]:
    return parse_params(attrs.get("params", "{}"))


def inline_content_text(tokens: list[dict[str, Any]]) -> str:
    """Concatenate `raw` from a flat list of text-ish tokens."""
    return "".join(t.get("raw", "") for t in tokens)


# ── Paired matching ───────────────────────────────────────────────────────────


def find_paired_close(
    tokens: Sequence[Token], start: int, tag: str, *, token_type: str
) -> int | None:
    """Find the index of the matching </tag> for an open <tag> in `tokens`.

    Tracks nesting depth, ignoring tokens of other types and self-contained
    tokens whose raw already contains </tag>. Non-dict tokens (already
    normalized HtmlPaired/HtmlVoid) are skipped — paired matching only
    operates on raw mistune tokens of the requested `token_type`.

    Used uniformly for `block_html`, `inline_html`, and re-tokenized HTML
    streams (see `split_html_string`).
    """
    depth = 1
    for i in range(start, len(tokens)):
        token = tokens[i]
        if not isinstance(token, dict):
            continue
        if token.get("type") != token_type:
            continue
        raw = token.get("raw", "").strip()
        t, _, closing = parse_tag(raw)
        if t != tag:
            continue
        if closing:
            depth -= 1
            if depth == 0:
                return i
        elif f"</{tag}>" in raw:
            continue  # self-contained: neither open nor close
        else:
            depth += 1
    return None


def split_html_string(raw: str) -> list[dict[str, Any]]:
    """Re-tokenize a raw HTML string into inline_html and text tokens.

    Needed because mistune merges multiple `<li ...>...</li>` segments into
    a single `block_html` raw string. After splitting, the same paired
    matching that handles cell content can pair `<li>`/`</li>` correctly.
    """
    result: list[dict[str, Any]] = []
    pos = 0
    for m in _TAG_RE.finditer(raw):
        if m.start() > pos:
            result.append({"type": "text", "raw": raw[pos : m.start()]})
        result.append({"type": "inline_html", "raw": m.group(0)})
        pos = m.end()
    if pos < len(raw):
        result.append({"type": "text", "raw": raw[pos:]})
    return result


def block_html_to_inline(tokens: list[Token]) -> list[dict[str, Any]]:
    """Flatten block_html tokens' raw strings into inline_html/text tokens.

    Dataclass tokens (HtmlPaired/HtmlVoid) pass through silently; we only
    re-split raw block_html dicts, recovering li-level structure from a
    single block_html that mistune emitted by jamming all `<li>` siblings
    on one line.
    """
    inline: list[dict[str, Any]] = []
    for t in tokens:
        if isinstance(t, dict) and t.get("type") == "block_html":
            inline.extend(split_html_string(t.get("raw", "").strip()))
    return inline


# ── Normalize: block-level ────────────────────────────────────────────────────


def normalize_blocks(tokens: Sequence[Token]) -> list[Token]:
    """Pair block_html into HtmlPaired/HtmlVoid; pass other tokens through.

    Idempotent: pre-normalized HtmlPaired/HtmlVoid pass through unchanged,
    so callers can blindly normalize whether the input came straight from
    mistune or from a previous normalization pass (e.g. builders that
    receive an `HtmlPaired.inner` of mixed raw/IR tokens).

    Drops blank_line. Promotes solo-image paragraphs to a bare image token
    so that the dispatcher can build a top-level MediaSingle from
    `![alt](url)`.

    `<div adf="marks">` and `<div adf="table">` metadata tokens are emitted
    as HtmlVoid; the block dispatcher consumes them as pending state that
    attaches to the next regular block.
    """
    result: list[Token] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if isinstance(token, (HtmlPaired, HtmlVoid)):
            result.append(token)
            i += 1
            continue
        t = token.get("type", "")

        if t == "blank_line":
            i += 1
            continue

        if t == "block_html":
            raw = token.get("raw", "").strip()
            tag, attrs, closing = parse_tag(raw)

            if closing:
                i += 1
                continue

            # Self-contained: <tag ...></tag>
            if f"</{tag}>" in raw:
                if has_adf(attrs):
                    result.append(HtmlVoid(tag=tag, attrs=attrs))
                elif tag == "summary":
                    # <summary>title</summary> is part of the marklas convention
                    # for expand/nestedExpand titles. It has no adf= attr but
                    # we must preserve its text content for the builder.
                    m = re.match(r"<summary[^>]*>(.*?)</summary>", raw, re.DOTALL)
                    title = m.group(1) if m else ""
                    result.append(
                        HtmlPaired(
                            tag="summary",
                            attrs=attrs,
                            inner=[{"type": "text", "raw": title}],
                        )
                    )
                elif tag == "p":
                    # The renderer encodes an empty ADF paragraph as `<p></p>`
                    # (a blank line would just dissolve, "&nbsp;" would render
                    # as visible text). Promote it to a paired token so the
                    # block dispatcher can rebuild ast.Paragraph(content=[]).
                    m = re.match(r"<p[^>]*>(.*?)</p>", raw, re.DOTALL)
                    inner_text = m.group(1) if m else ""
                    inner_tokens: list[Token] = (
                        [{"type": "text", "raw": inner_text}] if inner_text else []
                    )
                    result.append(HtmlPaired(tag="p", attrs=attrs, inner=inner_tokens))
                i += 1
                continue

            if not has_adf(attrs):
                # adf-less raw HTML at the top level: not part of our convention
                i += 1
                continue

            close_idx = find_paired_close(tokens, i + 1, tag, token_type="block_html")
            if close_idx is not None:
                # Inner is kept as raw mistune tokens. Builders that need a
                # normalized stream call `normalize_blocks` themselves (it is
                # idempotent for already-normalized Token lists). Keeping
                # raw form preserves cases mistune merges into a single
                # block_html, e.g. multiple `<li adf="...">...</li>` rendered
                # on one line inside `<ul adf="decisionList">`.
                inner: list[Token] = list(tokens[i + 1 : close_idx])
                result.append(HtmlPaired(tag=tag, attrs=attrs, inner=inner))
                i = close_idx + 1
                continue

            i += 1
            continue

        # Solo-image paragraph → bare image (so dispatcher treats it as a
        # block-level MediaSingle rather than a paragraph wrapping inline)
        if t == "paragraph":
            children = token.get("children", [])
            if len(children) == 1 and children[0].get("type") == "image":
                result.append(children[0])
                i += 1
                continue

        result.append(token)
        i += 1

    return result


# ── Normalize: inline-level ───────────────────────────────────────────────────


def normalize_inlines(tokens: list[dict[str, Any]]) -> list[Token]:
    """Recursively pair inline_html tokens at every nesting level.

    - inline_html pairs → HtmlPaired
    - raw `<br>` / `<br/>` → HtmlVoid(tag="br")  (hard break sentinel)
    - adf-less HTML other than `<br>` → removed
    - tokens with children (strong, emphasis, link, etc.) → children normalized
    - other tokens → pass through

    After this pass, no raw inline_html open/close tokens remain anywhere in
    the tree; inline builders can assume the tree is fully normalized.
    """
    result: list[Token] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token.get("type") == "inline_html":
            raw = token.get("raw", "")
            tag, attrs, closing = parse_tag(raw)

            if not closing and tag == "br":
                # Raw <br> / <br/> is a hard line break.
                result.append(HtmlVoid(tag="br", attrs=attrs))
                i += 1
                continue

            if closing or not has_adf(attrs):
                i += 1
                continue

            close_idx = find_paired_close(tokens, i + 1, tag, token_type="inline_html")
            if close_idx is not None:
                inner = normalize_inlines(tokens[i + 1 : close_idx])
                result.append(HtmlPaired(tag=tag, attrs=attrs, inner=inner))
                i = close_idx + 1
                continue

            i += 1
            continue

        if "children" in token:
            result.append({**token, "children": normalize_inlines(token["children"])})
        else:
            result.append(token)
        i += 1

    return result


# ── Mark helpers ──────────────────────────────────────────────────────────────


def attach_marks(node: ast.Node, marks: list[ast.Mark]) -> None:
    """Append marks to a node's `marks` field if it has one."""
    if hasattr(node, "marks") and marks:
        setattr(node, "marks", list(getattr(node, "marks")) + marks)


def parse_block_marks(params: dict[str, Any]) -> list[ast.Mark]:
    """Convert a `<div adf="marks" params="...">` params dict into AST marks."""
    marks: list[ast.Mark] = []
    if keys.ALIGN in params:
        marks.append(ast.AlignmentMark(align=params[keys.ALIGN]))
    if keys.INDENT in params:
        marks.append(ast.IndentationMark(level=params[keys.INDENT]))
    if keys.BREAKOUT_MODE in params:
        marks.append(
            ast.BreakoutMark(
                mode=params[keys.BREAKOUT_MODE],
                width=params.get(keys.BREAKOUT_WIDTH),
            )
        )
    if keys.DATA_CONSUMER_SOURCES in params:
        marks.append(ast.DataConsumerMark(sources=params[keys.DATA_CONSUMER_SOURCES]))
    if keys.BORDER_SIZE in params:
        marks.append(
            ast.BorderMark(
                size=params[keys.BORDER_SIZE],
                color=params.get(keys.BORDER_COLOR, ""),
            )
        )
    if keys.FONT_SIZE in params:
        marks.append(ast.FontSizeMark(size=params[keys.FONT_SIZE]))
    if keys.UNKNOWN_MARKS in params:
        for um in params[keys.UNKNOWN_MARKS]:
            marks.append(
                ast.UnknownMark(type=um.get("type", ""), attrs=um.get("attrs"))
            )
    return marks


def media_border_marks(params: dict[str, Any]) -> list[ast.BorderMark]:
    """Recover the BorderMark folded into a media node's own params.

    Shared by `_build_media` (Media) and `_build_media_inline` (MediaInline):
    both encode border as borderSize/borderColor in the media span's params.
    """
    return [m for m in parse_block_marks(params) if isinstance(m, ast.BorderMark)]
