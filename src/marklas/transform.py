from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import fields, replace
from typing import Any, Protocol, TypeVar, cast

from marklas.ast import Node


_N = TypeVar("_N", bound=Node)
_N_contra = TypeVar("_N_contra", bound=Node, contravariant=True)


class _Visitor(Protocol[_N_contra]):
    """A callable that rewrites a single node type."""

    def __call__(self, node: _N_contra) -> Node | list[Node] | None: ...


def _transform_seq(
    items: Sequence[Any],
    visitor: _Visitor[Node],
) -> tuple[list[Any], bool]:
    new_list: list[Any] = []
    for item in items:
        if not isinstance(item, Node):
            new_list.append(item)
            continue
        transformed = _transform(item, visitor)
        match visitor(transformed):
            case None:
                new_list.append(transformed)
            case [*nodes]:
                new_list.extend(nodes)
            case node:
                new_list.append(node)
    changed = len(new_list) != len(items) or any(
        a is not b for a, b in zip(new_list, items)
    )
    return new_list, changed


def _transform(node: Node, visitor: _Visitor[Node]) -> Node:
    updates: dict[str, Any] = {}
    for f in fields(node):
        value: Any = getattr(node, f.name)
        if not isinstance(value, Sequence) or isinstance(value, str):
            continue
        new_list, changed = _transform_seq(cast(Sequence[Any], value), visitor)
        if changed:
            updates[f.name] = new_list
    if not updates:
        return node
    return replace(node, **updates)


class Transformer:
    """Registry of typed visitors for bottom-up AST rewriting.

    Register handlers for specific node types with :meth:`register`.
    Multiple handlers can be registered for the same type — they are
    tried in registration order, and the first non-``None`` result wins.

    Return ``None`` to skip (pass to the next handler or leave unchanged),
    a ``Node`` to replace, or a ``list[Node]`` to splice.

    Nodes returned by a handler are **not** revisited — only the original
    tree is traversed.

    Usage::

        t = Transformer()

        @t.register(CodeBlock)
        def _(node: CodeBlock) -> list[Node] | None:
            if node.language == "mermaid":
                return [Paragraph(...), Expand(...)]
            return None

        @t.register(Media)
        def _(node: Media) -> Media | None:
            if node.type == "external":
                return Media(type="file", id=upload(node.url))
            return None

        new_doc = t(doc)
    """

    def __init__(self) -> None:
        self._handlers: dict[type[Node], list[_Visitor[Any]]] = {}

    def register(self, node_type: type[_N]) -> Callable[[_Visitor[_N]], _Visitor[_N]]:
        """Decorator to register a visitor for *node_type*."""

        def decorator(fn: _Visitor[_N]) -> _Visitor[_N]:
            self._handlers.setdefault(node_type, []).append(fn)
            return fn

        return decorator

    def __call__(self, node: Node) -> Node:
        return _transform(node, self._dispatch)

    def _dispatch(self, node: Node) -> Node | list[Node] | None:
        handlers = self._handlers.get(type(node))
        if not handlers:
            return None
        for handler in handlers:
            if (result := handler(node)) is not None:
                return result
        return None
