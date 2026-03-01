from __future__ import annotations

from dataclasses import dataclass

from marklas.ast.base import Node


@dataclass
class InlineNode(Node):
    pass


@dataclass
class Text(InlineNode):
    text: str


@dataclass
class Strong(InlineNode):
    children: list[InlineNode]


@dataclass
class Emphasis(InlineNode):
    children: list[InlineNode]


@dataclass
class Strikethrough(InlineNode):
    children: list[InlineNode]


@dataclass
class Link(InlineNode):
    url: str
    children: list[InlineNode]
    title: str | None = None


@dataclass
class Image(InlineNode):
    url: str
    alt: str = ""
    title: str | None = None


@dataclass
class CodeSpan(InlineNode):
    code: str


@dataclass
class HardBreak(InlineNode):
    pass


@dataclass
class SoftBreak(InlineNode):
    pass
