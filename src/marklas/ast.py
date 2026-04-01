from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field, fields
from typing import Any, Literal, TypeAlias, TypeVar, Union, overload


# ── Base ──────────────────────────────────────────────────────────────────────


@dataclass
class Node:
    pass


@dataclass
class Mark:
    pass


# ── Marks ─────────────────────────────────────────────────────────────────────


@dataclass
class AlignmentMark(Mark):
    align: Literal["center", "end"]


@dataclass
class AnnotationMark(Mark):
    id: str
    annotation_type: Literal["inlineComment"] = "inlineComment"


@dataclass
class BackgroundColorMark(Mark):
    color: str


@dataclass
class BorderMark(Mark):
    size: int
    color: str


@dataclass
class BreakoutMark(Mark):
    mode: Literal["wide", "full-width"]
    width: int | None = None


@dataclass
class CodeMark(Mark):
    pass


@dataclass
class DataConsumerMark(Mark):
    sources: list[str]


@dataclass
class EmMark(Mark):
    pass


# @dataclass
# class FragmentMark(Mark):
#     name: str | None = None


@dataclass
class IndentationMark(Mark):
    level: int


@dataclass
class LinkMark(Mark):
    href: str
    title: str | None = None
    # id: str | None = None  # Atlassian internal link ID
    # collection: str | None = None  # media collection reference
    # occurrence_key: str | None = None  # embed tracking


@dataclass
class StrikeMark(Mark):
    pass


@dataclass
class StrongMark(Mark):
    pass


@dataclass
class SubSupMark(Mark):
    type: Literal["sub", "sup"]


@dataclass
class TextColorMark(Mark):
    color: str


@dataclass
class UnderlineMark(Mark):
    pass


# ── Inline Nodes ──────────────────────────────────────────────────────────────


@dataclass
class Text(Node):
    text: str
    marks: Sequence[Mark] = field(default_factory=list[Mark])


@dataclass
class HardBreak(Node):
    # text: str | None = None  # always "\n", injected by ADF renderer
    pass


@dataclass
class Mention(Node):
    id: str
    text: str | None = None
    access_level: str | None = None
    user_type: Literal["DEFAULT", "SPECIAL", "APP"] | None = None


@dataclass
class Emoji(Node):
    short_name: str
    id: str | None = None
    text: str | None = None


@dataclass
class Date(Node):
    timestamp: str


@dataclass
class Status(Node):
    text: str
    color: Literal["neutral", "purple", "blue", "red", "yellow", "green"]
    style: str | None = None


@dataclass
class InlineCard(Node):
    url: str | None = None
    data: dict[str, Any] | None = None


@dataclass
class Placeholder(Node):
    text: str


@dataclass
class MediaInline(Node):
    id: str
    collection: str
    type: Literal["link", "file", "image"] | None = None
    alt: str | None = None
    # occurrence_key: str | None = None  # embed tracking
    width: int | None = None
    height: int | None = None
    data: dict[str, Any] | None = None
    marks: Sequence[LinkMark | AnnotationMark | BorderMark] = field(
        default_factory=list[LinkMark | AnnotationMark | BorderMark]
    )


@dataclass
class InlineExtension(Node):
    extension_key: str
    extension_type: str
    parameters: dict[str, Any] | None = None
    text: str | None = None
    marks: Sequence[Mark] = field(default_factory=list[Mark])


# ── Inline Type Aliases ───────────────────────────────────────────────────────

Inline: TypeAlias = Union[
    Text,
    HardBreak,
    Mention,
    Emoji,
    Date,
    Status,
    InlineCard,
    Placeholder,
    MediaInline,
    InlineExtension,
]

CaptionContent: TypeAlias = Union[
    Text,
    HardBreak,
    Mention,
    Emoji,
    Date,
    Status,
    InlineCard,
    Placeholder,
]


# ── Block Nodes ───────────────────────────────────────────────────────────────


@dataclass
class Rule(Node):
    pass


@dataclass
class CodeBlock(Node):
    language: str | None = None
    # unique_id: str | None = None
    content: Sequence[Text] = field(default_factory=list[Text])
    marks: Sequence[BreakoutMark] = field(default_factory=list[BreakoutMark])


@dataclass
class Caption(Node):
    content: Sequence[CaptionContent] = field(default_factory=list[CaptionContent])


@dataclass
class Media(Node):
    type: Literal["link", "file", "external"]
    id: str | None = None
    alt: str | None = None
    collection: str | None = None
    height: int | None = None
    # occurrence_key: str | None = None  # embed tracking
    width: int | None = None
    url: str | None = None
    marks: Sequence[LinkMark | AnnotationMark | BorderMark] = field(
        default_factory=list[LinkMark | AnnotationMark | BorderMark]
    )


@dataclass
class MediaSingle(Node):
    content: Sequence[Media | Caption] = field(default_factory=list[Media | Caption])
    width: float | None = None
    layout: (
        Literal[
            "wide",
            "full-width",
            "center",
            "wrap-right",
            "wrap-left",
            "align-end",
            "align-start",
        ]
        | None
    ) = None
    width_type: Literal["percentage", "pixel"] | None = None
    marks: Sequence[LinkMark] = field(default_factory=list[LinkMark])


@dataclass
class MediaGroup(Node):
    content: Sequence[Media]


@dataclass
class Paragraph(Node):
    content: Sequence[Inline] = field(default_factory=list[Inline])
    marks: Sequence[Mark] = field(default_factory=list[Mark])


@dataclass
class Heading(Node):
    level: Literal[1, 2, 3, 4, 5, 6]
    content: Sequence[Inline] = field(default_factory=list[Inline])
    marks: Sequence[Mark] = field(default_factory=list[Mark])


@dataclass
class Blockquote(Node):
    content: Sequence[BlockquoteContent]


@dataclass
class ListItem(Node):
    content: Sequence[ListItemContent]


@dataclass
class BulletList(Node):
    content: Sequence[ListItem]


@dataclass
class OrderedList(Node):
    content: Sequence[ListItem]
    order: int | None = None


@dataclass
class TableCell(Node):
    content: Sequence[TableCellContent]
    colspan: int | None = None
    rowspan: int | None = None
    colwidth: list[int] | None = None
    background: str | None = None


@dataclass
class TableHeader(TableCell):
    pass


@dataclass
class TableRow(Node):
    content: Sequence[TableCell | TableHeader]


@dataclass
class Table(Node):
    content: Sequence[TableRow]
    display_mode: Literal["default", "fixed"] | None = None
    is_number_column_enabled: bool | None = None
    layout: (
        Literal["wide", "full-width", "center", "align-end", "align-start", "default"]
        | None
    ) = None
    width: float | None = None
    # marks: Sequence[FragmentMark] — FragmentMark itself is commented out


@dataclass
class Panel(Node):
    panel_type: Literal["info", "note", "tip", "warning", "error", "success", "custom"]
    content: Sequence[PanelContent]
    panel_icon: str | None = None
    panel_icon_id: str | None = None
    panel_icon_text: str | None = None
    panel_color: str | None = None


@dataclass
class NestedExpand(Node):
    content: Sequence[NestedExpandContent]
    title: str | None = None


@dataclass
class Expand(Node):
    content: Sequence[ExpandContent]
    title: str | None = None
    marks: Sequence[BreakoutMark] = field(default_factory=list[BreakoutMark])


@dataclass
class TaskItem(Node):
    state: Literal["TODO", "DONE"]
    content: Sequence[Inline] = field(default_factory=list[Inline])


@dataclass
class BlockTaskItem(Node):
    state: Literal["TODO", "DONE"]
    content: Sequence[BlockTaskItemContent]


@dataclass
class TaskList(Node):
    content: Sequence[TaskListContent]


@dataclass
class DecisionItem(Node):
    state: str
    content: Sequence[Inline] = field(default_factory=list[Inline])


@dataclass
class DecisionList(Node):
    content: Sequence[DecisionItem]


@dataclass
class LayoutColumn(Node):
    width: float
    content: Sequence[BlockContent]


@dataclass
class LayoutSection(Node):
    content: Sequence[LayoutColumn]
    marks: Sequence[BreakoutMark] = field(default_factory=list[BreakoutMark])


@dataclass
class BlockCard(Node):
    url: str | None = None
    datasource: dict[str, Any] | None = None
    width: float | None = None
    layout: (
        Literal[
            "wide",
            "full-width",
            "center",
            "wrap-right",
            "wrap-left",
            "align-end",
            "align-start",
        ]
        | None
    ) = None
    data: dict[str, Any] | None = None


@dataclass
class EmbedCard(Node):
    url: str
    layout: Literal[
        "wide",
        "full-width",
        "center",
        "wrap-right",
        "wrap-left",
        "align-end",
        "align-start",
    ]
    width: float | None = None
    original_height: int | None = None
    original_width: int | None = None


@dataclass
class Extension(Node):
    extension_key: str
    extension_type: str
    parameters: dict[str, Any] | None = None
    text: str | None = None
    layout: Literal["wide", "full-width", "default"] | None = None
    marks: Sequence[Mark] = field(default_factory=list[Mark])


@dataclass
class BodiedExtension(Node):
    extension_key: str
    extension_type: str
    content: Sequence[NonNestableBlockContent]
    parameters: dict[str, Any] | None = None
    text: str | None = None
    layout: Literal["wide", "full-width", "default"] | None = None
    marks: Sequence[Mark] = field(default_factory=list[Mark])


@dataclass
class SyncBlock(Node):
    resource_id: str
    marks: Sequence[BreakoutMark] = field(default_factory=list[BreakoutMark])


@dataclass
class BodiedSyncBlock(Node):
    resource_id: str
    content: Sequence[BodiedSyncBlockContent]
    marks: Sequence[BreakoutMark] = field(default_factory=list[BreakoutMark])


@dataclass
class Doc(Node):
    content: Sequence[DocContent]
    version: int = 1


# ── Block Content Type Aliases ────────────────────────────────────────────────

BlockquoteContent: TypeAlias = Union[
    Paragraph,
    OrderedList,
    BulletList,
    CodeBlock,
    MediaSingle,
    MediaGroup,
    Extension,
]

ListItemContent: TypeAlias = Union[
    Paragraph,
    BulletList,
    OrderedList,
    TaskList,
    MediaSingle,
    CodeBlock,
    Extension,
]

PanelContent: TypeAlias = Union[
    Paragraph,
    Heading,
    BulletList,
    OrderedList,
    BlockCard,
    MediaGroup,
    MediaSingle,
    CodeBlock,
    TaskList,
    Rule,
    DecisionList,
    Extension,
]

TableCellContent: TypeAlias = Union[
    Paragraph,
    Panel,
    Blockquote,
    OrderedList,
    BulletList,
    Rule,
    Heading,
    CodeBlock,
    MediaSingle,
    MediaGroup,
    DecisionList,
    TaskList,
    BlockCard,
    EmbedCard,
    Extension,
    NestedExpand,
]

NestedExpandContent: TypeAlias = Union[
    Paragraph,
    Heading,
    MediaSingle,
    MediaGroup,
    CodeBlock,
    BulletList,
    OrderedList,
    TaskList,
    DecisionList,
    Rule,
    Panel,
    Blockquote,
    Extension,
]

ExpandContent: TypeAlias = Union[
    Paragraph,
    Panel,
    Blockquote,
    OrderedList,
    BulletList,
    Rule,
    Heading,
    CodeBlock,
    MediaGroup,
    MediaSingle,
    DecisionList,
    TaskList,
    Table,
    BlockCard,
    EmbedCard,
    Extension,
    NestedExpand,
]

BlockTaskItemContent: TypeAlias = Union[Paragraph, Extension]

TaskListContent: TypeAlias = Union[TaskItem, BlockTaskItem, TaskList]

NonNestableBlockContent: TypeAlias = Union[
    Paragraph,
    Panel,
    Blockquote,
    OrderedList,
    BulletList,
    Rule,
    Heading,
    CodeBlock,
    MediaGroup,
    MediaSingle,
    DecisionList,
    TaskList,
    Table,
    BlockCard,
    EmbedCard,
    Extension,
]

BlockContent: TypeAlias = Union[
    Paragraph,
    Heading,
    CodeBlock,
    BulletList,
    OrderedList,
    Blockquote,
    Table,
    Panel,
    Expand,
    Rule,
    MediaSingle,
    MediaGroup,
    BlockCard,
    EmbedCard,
    TaskList,
    DecisionList,
    Extension,
    BodiedExtension,
]

BodiedSyncBlockContent: TypeAlias = Union[
    Paragraph,
    BlockCard,
    Blockquote,
    BulletList,
    CodeBlock,
    DecisionList,
    EmbedCard,
    Expand,
    Heading,
    LayoutSection,
    MediaGroup,
    MediaSingle,
    OrderedList,
    Panel,
    Rule,
    Table,
    TaskList,
]

DocContent: TypeAlias = Union[
    Paragraph,
    Heading,
    CodeBlock,
    BulletList,
    OrderedList,
    Blockquote,
    Table,
    Panel,
    Expand,
    Rule,
    MediaSingle,
    MediaGroup,
    BlockCard,
    EmbedCard,
    TaskList,
    DecisionList,
    LayoutSection,
    Extension,
    BodiedExtension,
    SyncBlock,
    BodiedSyncBlock,
]


# ── Tree walk ────────────────────────────────────────────────────────────────


_N = TypeVar("_N", bound=Node)


def _walk(node: Node, node_type: type[Node] | None) -> Iterator[Node]:
    for f in fields(node):
        value: Any = getattr(node, f.name)
        if not isinstance(value, Sequence) or isinstance(value, str):
            continue
        for child in value:  # type: ignore
            if not isinstance(child, Node):
                continue
            if node_type is None or isinstance(child, node_type):
                yield child
            yield from _walk(child, node_type)


@overload
def walk(node: Node) -> Iterator[Node]: ...
@overload
def walk(node: Node, node_type: type[_N]) -> Iterator[_N]: ...


def walk(node: Node, node_type: type[Node] | None = None) -> Iterator[Node]:
    """Yield all descendant nodes from *node*, optionally filtered by *node_type*."""
    yield from _walk(node, node_type)
