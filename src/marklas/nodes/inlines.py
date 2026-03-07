from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from marklas.nodes.base import Node


@dataclass
class Inline(Node):
    pass


# --- Intersection ---


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


# --- Difference-set: Annotated inlines ---


@dataclass
class Mention(Inline):
    id: str
    text: str | None = None
    access_level: str | None = None
    user_type: str | None = None


@dataclass
class Emoji(Inline):
    short_name: str
    text: str | None = None
    id: str | None = None


@dataclass
class Date(Inline):
    timestamp: str


@dataclass
class Status(Inline):
    text: str
    color: str
    style: str | None = None


@dataclass
class InlineCard(Inline):
    url: str | None = None
    data: dict[str, Any] | None = None


@dataclass
class MediaInline(Inline):
    id: str | None = None
    collection: str | None = None
    media_type: str = "file"
    alt: str | None = None
    width: int | None = None
    height: int | None = None


# --- Difference-set: Wrapping marks ---


@dataclass
class Underline(Inline):
    children: list[Inline]


@dataclass
class TextColor(Inline):
    color: str
    children: list[Inline]


@dataclass
class BackgroundColor(Inline):
    color: str
    children: list[Inline]


@dataclass
class SubSup(Inline):
    type: str  # sub, sup
    children: list[Inline]


@dataclass
class Annotation(Inline):
    id: str
    children: list[Inline]
    annotation_type: str = "inlineComment"


# --- Difference-set: Placeholder-only ---


@dataclass
class Placeholder(Inline):
    text: str


@dataclass
class InlineExtension(Inline):
    raw: dict[str, Any]
