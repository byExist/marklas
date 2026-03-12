from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias

from marklas.nodes.base import Node


# --- Intersection ---


@dataclass
class Text(Node):
    text: str


@dataclass
class Strong(Node):
    children: list[Inline]


@dataclass
class Emphasis(Node):
    children: list[Inline]


@dataclass
class Strikethrough(Node):
    children: list[Inline]


@dataclass
class Link(Node):
    url: str
    children: list[Inline]
    title: str | None = None


@dataclass
class Image(Node):
    url: str
    alt: str = ""
    title: str | None = None


@dataclass
class CodeSpan(Node):
    code: str


@dataclass
class HardBreak(Node):
    pass


@dataclass
class SoftBreak(Node):
    pass


# --- Difference-set: Annotated inlines ---


@dataclass
class Mention(Node):
    id: str
    text: str | None = None
    access_level: str | None = None
    user_type: str | None = None


@dataclass
class Emoji(Node):
    short_name: str
    text: str | None = None
    id: str | None = None


@dataclass
class Date(Node):
    timestamp: str


@dataclass
class Status(Node):
    text: str
    color: str
    style: str | None = None


@dataclass
class InlineCard(Node):
    url: str | None = None
    data: dict[str, Any] | None = None


@dataclass
class MediaInline(Node):
    id: str | None = None
    collection: str | None = None
    media_type: str = "file"
    alt: str | None = None
    width: int | None = None
    height: int | None = None


# --- Difference-set: Wrapping marks ---


@dataclass
class Underline(Node):
    children: list[Inline]


@dataclass
class TextColor(Node):
    color: str
    children: list[Inline]


@dataclass
class BackgroundColor(Node):
    color: str
    children: list[Inline]


@dataclass
class SubSup(Node):
    type: str  # sub, sup
    children: list[Inline]


@dataclass
class Annotation(Node):
    id: str
    children: list[Inline]
    annotation_type: str = "inlineComment"


# --- Difference-set: Placeholder-only ---


@dataclass
class Placeholder(Node):
    text: str


@dataclass
class InlineExtension(Node):
    raw: dict[str, Any]


Inline: TypeAlias = (
    Text
    | Strong
    | Emphasis
    | Strikethrough
    | Link
    | Image
    | CodeSpan
    | HardBreak
    | SoftBreak
    | Mention
    | Emoji
    | Date
    | Status
    | InlineCard
    | MediaInline
    | Underline
    | TextColor
    | BackgroundColor
    | SubSup
    | Annotation
    | Placeholder
    | InlineExtension
)
