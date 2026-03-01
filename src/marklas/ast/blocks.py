from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from marklas.ast.base import Node
from marklas.ast.inlines import Inline


@dataclass
class Block(Node):
    pass


@dataclass
class Document(Node):
    children: list[Block]


@dataclass
class Paragraph(Block):
    children: list[Inline]


@dataclass
class Heading(Block):
    level: Literal[1, 2, 3, 4, 5, 6]
    children: list[Inline]


@dataclass
class CodeBlock(Block):
    code: str
    language: str | None = None


@dataclass
class BlockQuote(Block):
    children: list[Block]


@dataclass
class ThematicBreak(Block):
    pass


@dataclass
class ListItem(Block):
    children: list[Block]
    checked: bool | None = None


@dataclass
class BulletList(Block):
    items: list[ListItem]
    tight: bool = True


@dataclass
class OrderedList(Block):
    items: list[ListItem]
    start: int = 1
    tight: bool = True


@dataclass
class TableCell(Node):
    children: list[Inline]


@dataclass
class Table(Block):
    head: list[TableCell]
    body: list[list[TableCell]]
    alignments: list[Literal["left", "center", "right"] | None] = field(
        default_factory=list[Literal["left", "center", "right"] | None]
    )
