from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from marklas.ast.base import Node
from marklas.ast.inlines import InlineNode


@dataclass
class BlockNode(Node):
    pass


@dataclass
class Document(Node):
    children: list[BlockNode]


@dataclass
class Paragraph(BlockNode):
    children: list[InlineNode]


@dataclass
class Heading(BlockNode):
    level: Literal[1, 2, 3, 4, 5, 6]
    children: list[InlineNode]


@dataclass
class CodeBlock(BlockNode):
    code: str
    language: str | None = None


@dataclass
class BlockQuote(BlockNode):
    children: list[BlockNode]


@dataclass
class ThematicBreak(BlockNode):
    pass


@dataclass
class ListItem(BlockNode):
    children: list[BlockNode]
    checked: bool | None = None


@dataclass
class BulletList(BlockNode):
    items: list[ListItem]
    tight: bool = True


@dataclass
class OrderedList(BlockNode):
    items: list[ListItem]
    start: int = 1
    tight: bool = True


@dataclass
class TableCell(Node):
    children: list[InlineNode]


@dataclass
class Table(BlockNode):
    head: list[TableCell]
    body: list[list[TableCell]]
    alignments: list[Literal["left", "center", "right"] | None] = field(default_factory=list[Literal["left", "center", "right"] | None])
