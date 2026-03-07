from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

from marklas.nodes.base import Node
from marklas.nodes.inlines import Inline


@dataclass
class Block(Node):
    pass


# --- Intersection ---


@dataclass
class Document(Node):
    children: list[Block]


@dataclass
class Paragraph(Block):
    children: list[Inline]
    alignment: str | None = None  # center, end
    indentation: int | None = None


@dataclass
class Heading(Block):
    level: Literal[1, 2, 3, 4, 5, 6]
    children: list[Inline]
    alignment: str | None = None
    indentation: int | None = None


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
    children: list[Block]
    colspan: int | None = None
    rowspan: int | None = None
    col_width: list[int] | None = None
    background: str | None = None


@dataclass
class TableHeader(TableCell):
    pass


@dataclass
class Table(Block):
    head: list[TableCell]
    body: list[list[TableCell]]
    alignments: list[Literal["left", "center", "right"] | None] = field(
        default_factory=list[Literal["left", "center", "right"] | None]
    )
    display_mode: str | None = None
    is_number_column_enabled: bool | None = None
    layout: str | None = None
    width: float | None = None


# --- Difference-set: Annotated blocks ---


@dataclass
class Panel(Block):
    children: list[Block]
    panel_type: str  # info, note, tip, warning, error, success, custom
    panel_icon: str | None = None
    panel_icon_id: str | None = None
    panel_icon_text: str | None = None
    panel_color: str | None = None


@dataclass
class Expand(Block):
    children: list[Block]
    title: str | None = None


@dataclass
class NestedExpand(Block):
    children: list[Block]
    title: str | None = None


@dataclass
class TaskItem(Node):
    children: list[Inline]
    state: str  # TODO, DONE
    local_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class TaskList(Block):
    items: list[TaskItem]


@dataclass
class DecisionItem(Node):
    children: list[Inline]
    state: str
    local_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class DecisionList(Block):
    items: list[DecisionItem]


# Note: width is required in the ADF schema, but may be absent in
# annotation comments during MD restoration, so it's optional in the AST.
# ADF renderer uses equal distribution (100/len(columns)) when None.
# Inherits Block for type compatibility since it appears temporarily
# inside _pair_block_annotations(list[Block]) during parsing.
@dataclass
class LayoutColumn(Block):
    children: list[Block]
    width: float | None = None


@dataclass
class LayoutSection(Block):
    columns: list[LayoutColumn]


@dataclass
class Media(Node):
    media_type: str  # file, external
    url: str | None = None
    id: str | None = None
    collection: str | None = None
    alt: str | None = None
    width: int | None = None
    height: int | None = None


# Note: ADF mediaSingle.content is a list but always contains exactly one Media.
# Additional content like captions is not currently supported (only content[0] is preserved on roundtrip).
@dataclass
class MediaSingle(Block):
    media: Media
    layout: str | None = None
    width: float | None = None
    width_type: str | None = None


@dataclass
class MediaGroup(Block):
    media_list: list[Media]


@dataclass
class BlockCard(Block):
    url: str | None = None
    data: dict[str, Any] | None = None


@dataclass
class EmbedCard(Block):
    url: str
    layout: str
    width: float | None = None
    original_width: int | None = None
    original_height: int | None = None


# --- Difference-set: Placeholder-only ---


@dataclass
class Extension(Block):
    raw: dict[str, Any]


@dataclass
class BodiedExtension(Block):
    raw: dict[str, Any]


@dataclass
class SyncBlock(Block):
    raw: dict[str, Any]


@dataclass
class BodiedSyncBlock(Block):
    raw: dict[str, Any]
