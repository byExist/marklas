from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict


# ── Marks ──────────────────────────────────────────────────────────────


class StrongMark(TypedDict):
    type: Literal["strong"]


class EmMark(TypedDict):
    type: Literal["em"]


class StrikeMark(TypedDict):
    type: Literal["strike"]


class CodeMark(TypedDict):
    type: Literal["code"]


class LinkAttrs(TypedDict):
    href: str
    title: NotRequired[str]
    id: NotRequired[str]
    collection: NotRequired[str]
    occurrenceKey: NotRequired[str]


class LinkMark(TypedDict):
    type: Literal["link"]
    attrs: LinkAttrs


class UnderlineMark(TypedDict):
    type: Literal["underline"]


class TextColorAttrs(TypedDict):
    color: str


class TextColorMark(TypedDict):
    type: Literal["textColor"]
    attrs: TextColorAttrs


class SubSupAttrs(TypedDict):
    type: Literal["sub", "sup"]


class SubSupMark(TypedDict):
    type: Literal["subsup"]
    attrs: SubSupAttrs


class BackgroundColorAttrs(TypedDict):
    color: str


class BackgroundColorMark(TypedDict):
    type: Literal["backgroundColor"]
    attrs: BackgroundColorAttrs


type Mark = (
    StrongMark
    | EmMark
    | StrikeMark
    | CodeMark
    | LinkMark
    | UnderlineMark
    | TextColorMark
    | SubSupMark
    | BackgroundColorMark
)


# ── Inline Nodes ───────────────────────────────────────────────────────


class TextNode(TypedDict):
    type: Literal["text"]
    text: str
    marks: NotRequired[list[Mark]]


class HardBreakNode(TypedDict):
    type: Literal["hardBreak"]


class MentionAttrs(TypedDict):
    id: str
    text: NotRequired[str]
    localId: NotRequired[str]
    userType: NotRequired[str]
    accessLevel: NotRequired[str]


class MentionNode(TypedDict):
    type: Literal["mention"]
    attrs: MentionAttrs


class EmojiAttrs(TypedDict):
    shortName: str
    id: NotRequired[str]
    text: NotRequired[str]
    localId: NotRequired[str]


class EmojiNode(TypedDict):
    type: Literal["emoji"]
    attrs: EmojiAttrs


class DateAttrs(TypedDict):
    timestamp: str
    localId: NotRequired[str]


class DateNode(TypedDict):
    type: Literal["date"]
    attrs: DateAttrs


class StatusAttrs(TypedDict):
    text: str
    color: str
    style: NotRequired[str]
    localId: NotRequired[str]


class StatusNode(TypedDict):
    type: Literal["status"]
    attrs: StatusAttrs


class InlineCardAttrs(TypedDict, total=False):
    url: str
    data: dict[str, Any]


class InlineCardNode(TypedDict):
    type: Literal["inlineCard"]
    attrs: InlineCardAttrs


type InlineNode = (
    TextNode
    | HardBreakNode
    | MentionNode
    | EmojiNode
    | DateNode
    | StatusNode
    | InlineCardNode
)


# ── Block Nodes ────────────────────────────────────────────────────────


class LocalIdAttrs(TypedDict, total=False):
    localId: str


class ParagraphNode(TypedDict):
    type: Literal["paragraph"]
    content: list[InlineNode]
    attrs: NotRequired[LocalIdAttrs]


class HeadingAttrs(TypedDict):
    level: int
    localId: NotRequired[str]


class HeadingNode(TypedDict):
    type: Literal["heading"]
    attrs: HeadingAttrs
    content: list[InlineNode]


class CodeBlockAttrs(TypedDict, total=False):
    language: str
    localId: str


class CodeBlockNode(TypedDict):
    type: Literal["codeBlock"]
    content: list[InlineNode]
    attrs: NotRequired[CodeBlockAttrs]


class BlockquoteNode(TypedDict):
    type: Literal["blockquote"]
    content: list[BlockNode]
    attrs: NotRequired[LocalIdAttrs]


class ListItemNode(TypedDict):
    type: Literal["listItem"]
    content: list[BlockNode]
    attrs: NotRequired[LocalIdAttrs]


class BulletListNode(TypedDict):
    type: Literal["bulletList"]
    content: list[ListItemNode]
    attrs: NotRequired[LocalIdAttrs]


class OrderedListAttrs(TypedDict, total=False):
    order: int
    localId: str


class OrderedListNode(TypedDict):
    type: Literal["orderedList"]
    content: list[ListItemNode]
    attrs: NotRequired[OrderedListAttrs]


class TaskItemAttrs(TypedDict):
    localId: str
    state: str


class TaskItemNode(TypedDict):
    type: Literal["taskItem"]
    attrs: TaskItemAttrs
    content: list[InlineNode]


class TaskListAttrs(TypedDict):
    localId: str


class TaskListNode(TypedDict):
    type: Literal["taskList"]
    attrs: TaskListAttrs
    content: list[TaskItemNode]


class RuleNode(TypedDict):
    type: Literal["rule"]


class TableCellAttrs(TypedDict, total=False):
    colspan: int
    rowspan: int
    background: str
    colwidth: list[int]


class TableCellNode(TypedDict):
    type: Literal["tableCell"]
    content: list[BlockNode]
    attrs: NotRequired[TableCellAttrs]


class TableHeaderNode(TypedDict):
    type: Literal["tableHeader"]
    content: list[BlockNode]
    attrs: NotRequired[TableCellAttrs]


class TableRowNode(TypedDict):
    type: Literal["tableRow"]
    content: list[TableCellNode | TableHeaderNode]


class TableAttrs(TypedDict, total=False):
    layout: str
    isNumberColumnEnabled: bool
    localId: str
    width: int
    displayMode: str


class TableNode(TypedDict):
    type: Literal["table"]
    content: list[TableRowNode]
    attrs: NotRequired[TableAttrs]


class MediaAttrs(TypedDict):
    type: str
    url: NotRequired[str]
    id: NotRequired[str]
    collection: NotRequired[str]
    alt: NotRequired[str]
    width: NotRequired[int]
    height: NotRequired[int]
    localId: NotRequired[str]


class MediaNode(TypedDict):
    type: Literal["media"]
    attrs: MediaAttrs


class MediaSingleAttrs(TypedDict, total=False):
    layout: str
    width: float
    widthType: str
    localId: str


class MediaSingleNode(TypedDict):
    type: Literal["mediaSingle"]
    content: list[MediaNode]
    attrs: NotRequired[MediaSingleAttrs]


class MediaGroupNode(TypedDict):
    type: Literal["mediaGroup"]
    content: list[MediaNode]


class PanelAttrs(TypedDict):
    panelType: str
    localId: NotRequired[str]
    panelColor: NotRequired[str]
    panelIcon: NotRequired[str]
    panelIconId: NotRequired[str]
    panelIconText: NotRequired[str]


class PanelNode(TypedDict):
    type: Literal["panel"]
    attrs: PanelAttrs
    content: list[BlockNode]


class ExpandAttrs(TypedDict, total=False):
    title: str
    localId: str


class ExpandNode(TypedDict):
    type: Literal["expand"]
    content: list[BlockNode]
    attrs: NotRequired[ExpandAttrs]


class NestedExpandAttrs(TypedDict, total=False):
    title: str
    localId: str


class NestedExpandNode(TypedDict):
    type: Literal["nestedExpand"]
    content: list[BlockNode]
    attrs: NotRequired[NestedExpandAttrs]


class LayoutColumnAttrs(TypedDict):
    width: float
    localId: NotRequired[str]


class LayoutColumnNode(TypedDict):
    type: Literal["layoutColumn"]
    attrs: LayoutColumnAttrs
    content: list[BlockNode]


class LayoutSectionNode(TypedDict):
    type: Literal["layoutSection"]
    content: list[LayoutColumnNode]
    attrs: NotRequired[LocalIdAttrs]


class DecisionItemAttrs(TypedDict):
    localId: str
    state: str


class DecisionItemNode(TypedDict):
    type: Literal["decisionItem"]
    attrs: DecisionItemAttrs
    content: list[InlineNode]


class DecisionListAttrs(TypedDict):
    localId: str


class DecisionListNode(TypedDict):
    type: Literal["decisionList"]
    attrs: DecisionListAttrs
    content: list[DecisionItemNode]


class BlockCardAttrs(TypedDict, total=False):
    url: str
    data: dict[str, Any]
    localId: str


class BlockCardNode(TypedDict):
    type: Literal["blockCard"]
    attrs: NotRequired[BlockCardAttrs]


class EmbedCardAttrs(TypedDict):
    url: str
    layout: str
    originalWidth: NotRequired[int]
    originalHeight: NotRequired[int]
    width: NotRequired[float]
    localId: NotRequired[str]


class EmbedCardNode(TypedDict):
    type: Literal["embedCard"]
    attrs: EmbedCardAttrs


type BlockNode = (
    ParagraphNode
    | HeadingNode
    | CodeBlockNode
    | BlockquoteNode
    | BulletListNode
    | OrderedListNode
    | TaskListNode
    | RuleNode
    | TableNode
    | MediaSingleNode
    | MediaGroupNode
    | PanelNode
    | ExpandNode
    | NestedExpandNode
    | LayoutSectionNode
    | DecisionListNode
    | BlockCardNode
    | EmbedCardNode
)


# ── Document ───────────────────────────────────────────────────────────


class DocNode(TypedDict):
    type: Literal["doc"]
    version: int
    content: list[BlockNode]
