"""Intermediate representation and container schemas for the markdown parser.

The parser walks a stream of *tokens* through three stages — tokenize → normalize
→ build. The IR types in this module are what flows between those stages once
mistune's raw token dicts have been pair-matched into HTML extension nodes.

Two dataclasses describe every paired/void HTML extension we care about:

  HtmlPaired   — <tag attrs>...inner...</tag>
  HtmlVoid     — <tag attrs/>  or  <br>  or  <div adf="cell" params="..."></div>

Mistune's own raw token dicts (paragraph, heading, list, text, strong, ...) pass
through as plain dicts. The boundary is explicit:

  type Token = HtmlPaired | HtmlVoid | dict[str, Any]

Container schemas (DocContent, PanelContent, ...) are derived from ast.py at
import time via `typing.get_args`, then wrapped in TypeGuard predicates. This
makes ast.py the *single source of truth* for which AST node types are valid
inside which container; the parser narrows back to those unions through
isinstance, without `cast`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, TypeGuard, TypeVar, get_args

from marklas import ast

T = TypeVar("T")


# ── IR dataclasses ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class HtmlPaired:
    """Paired HTML tag with normalized inner tokens.

    `source_tokens` carries the original mistune open/close tokens when a
    paired group needs to be re-injected into an inline stream on fallback
    (cell context only — see cell.py for details).
    """

    tag: str
    attrs: Mapping[str, str]
    inner: list[Token] = field(default_factory=list["Token"])
    source_tokens: tuple[dict[str, Any], dict[str, Any]] | None = None

    @property
    def adf_type(self) -> str:
        return self.attrs.get("adf", "")


@dataclass(frozen=True, slots=True)
class HtmlVoid:
    """Self-closing or void HTML tag (no inner content).

    Covers raw `<br>`, `<hr>`, self-contained `<div adf="cell" ...></div>`
    metadata tokens, and `<div adf="extension" params="..."></div>` data
    elements that encode an entire ADF node in their attrs.
    """

    tag: str
    attrs: Mapping[str, str]
    source_token: dict[str, Any] | None = None

    @property
    def adf_type(self) -> str:
        return self.attrs.get("adf", "")


Token = HtmlPaired | HtmlVoid | dict[str, Any]


# ── Container schemas (mirror ast.py via get_args) ────────────────────────────
#
# Each container's content union (DocContent, PanelContent, …) is declared in
# ast.py. `get_args` unfolds the union at import time so we can do isinstance
# narrowing and TypeGuard predicates without duplicating the schema here.


_DOC_CONTENT = get_args(ast.DocContent)
_PANEL_CONTENT = get_args(ast.PanelContent)
_EXPAND_CONTENT = get_args(ast.ExpandContent)
_NESTED_EXPAND_CONTENT = get_args(ast.NestedExpandContent)
_BLOCKQUOTE_CONTENT = get_args(ast.BlockquoteContent)
_LIST_ITEM_CONTENT = get_args(ast.ListItemContent)
_BLOCK_CONTENT = get_args(ast.BlockContent)
_TABLE_CELL_CONTENT = get_args(ast.TableCellContent)
_NON_NESTABLE_BLOCK_CONTENT = get_args(ast.NonNestableBlockContent)
_BODIED_SYNC_BLOCK_CONTENT = get_args(ast.BodiedSyncBlockContent)
_CAPTION_CONTENT = get_args(ast.CaptionContent)


def is_doc(node: ast.Node) -> TypeGuard[ast.DocContent]:
    return isinstance(node, _DOC_CONTENT)


def is_panel(node: ast.Node) -> TypeGuard[ast.PanelContent]:
    return isinstance(node, _PANEL_CONTENT)


def is_expand(node: ast.Node) -> TypeGuard[ast.ExpandContent]:
    return isinstance(node, _EXPAND_CONTENT)


def is_nested_expand(node: ast.Node) -> TypeGuard[ast.NestedExpandContent]:
    return isinstance(node, _NESTED_EXPAND_CONTENT)


def is_blockquote(node: ast.Node) -> TypeGuard[ast.BlockquoteContent]:
    return isinstance(node, _BLOCKQUOTE_CONTENT)


def is_list_item(node: ast.Node) -> TypeGuard[ast.ListItemContent]:
    return isinstance(node, _LIST_ITEM_CONTENT)


def is_block(node: ast.Node) -> TypeGuard[ast.BlockContent]:
    return isinstance(node, _BLOCK_CONTENT)


def is_table_cell(node: ast.Node) -> TypeGuard[ast.TableCellContent]:
    return isinstance(node, _TABLE_CELL_CONTENT)


def is_non_nestable(node: ast.Node) -> TypeGuard[ast.NonNestableBlockContent]:
    return isinstance(node, _NON_NESTABLE_BLOCK_CONTENT)


def is_bodied_sync(node: ast.Node) -> TypeGuard[ast.BodiedSyncBlockContent]:
    return isinstance(node, _BODIED_SYNC_BLOCK_CONTENT)


def is_caption(node: ast.Node) -> TypeGuard[ast.CaptionContent]:
    return isinstance(node, _CAPTION_CONTENT)


def collect(
    nodes: Iterable[ast.Node | None],
    is_valid: Callable[[ast.Node], TypeGuard[T]],
) -> list[T]:
    """Collect AST nodes whose type satisfies the given schema predicate.

    Paired with a TypeGuard predicate this is the only path through which a
    generic dispatcher's `ast.Node` output is narrowed back to a specific
    container's content union — no `cast` needed.
    """
    return [n for n in nodes if n is not None and is_valid(n)]


# ── Misc constants ────────────────────────────────────────────────────────────


HEADING_LEVELS: dict[str, Literal[1, 2, 3, 4, 5, 6]] = {
    "h1": 1,
    "h2": 2,
    "h3": 3,
    "h4": 4,
    "h5": 5,
    "h6": 6,
}
