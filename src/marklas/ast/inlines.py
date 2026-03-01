from __future__ import annotations

from dataclasses import dataclass

from marklas.ast.base import Node


@dataclass
class Inline(Node):
    pass


@dataclass
class Text(Inline):
    text: str


@dataclass
class Strong(Inline):
    children: list[Inline]


@dataclass
class Emphasis(Inline):
    children: list[Inline]


@dataclass
class Strikethrough(Inline):
    children: list[Inline]


@dataclass
class Link(Inline):
    url: str
    children: list[Inline]
    title: str | None = None


@dataclass
class Image(Inline):
    url: str
    alt: str = ""
    title: str | None = None


@dataclass
class CodeSpan(Inline):
    code: str


@dataclass
class HardBreak(Inline):
    pass


@dataclass
class SoftBreak(Inline):
    pass
