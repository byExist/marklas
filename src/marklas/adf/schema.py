from __future__ import annotations

from typing import Any, Literal, NotRequired, TypeAlias, TypedDict

# ── Marks ──────────────────────────────────────────────────────────────


class Strong(TypedDict):
    type: Literal["strong"]


class Em(TypedDict):
    type: Literal["em"]


class Strike(TypedDict):
    type: Literal["strike"]


class Code(TypedDict):
    type: Literal["code"]


class _LinkAttrs(TypedDict):
    href: str
    title: NotRequired[str]
    id: NotRequired[str]
    collection: NotRequired[str]
    occurrenceKey: NotRequired[str]


class Link(TypedDict):
    type: Literal["link"]
    attrs: _LinkAttrs


class Underline(TypedDict):
    type: Literal["underline"]


class _TextColorAttrs(TypedDict):
    color: str


class TextColor(TypedDict):
    type: Literal["textColor"]
    attrs: _TextColorAttrs


class _SubSupAttrs(TypedDict):
    type: Literal["sub", "sup"]


class SubSup(TypedDict):
    type: Literal["subsup"]
    attrs: _SubSupAttrs


class _BackgroundColorAttrs(TypedDict):
    color: str


class BackgroundColor(TypedDict):
    type: Literal["backgroundColor"]
    attrs: _BackgroundColorAttrs


class _AnnotationAttrs(TypedDict):
    id: str
    annotationType: NotRequired[str]


class AnnotationMark(TypedDict):
    type: Literal["annotation"]
    attrs: _AnnotationAttrs


Mark: TypeAlias = (
    Strong
    | Em
    | Strike
    | Code
    | Link
    | Underline
    | TextColor
    | SubSup
    | BackgroundColor
    | AnnotationMark
)


# ── Inline Nodes ───────────────────────────────────────────────────────


class Text(TypedDict):
    type: Literal["text"]
    text: str
    marks: NotRequired[list[Mark]]


class HardBreak(TypedDict):
    type: Literal["hardBreak"]


class _MentionAttrs(TypedDict):
    id: str
    text: NotRequired[str]
    localId: NotRequired[str]
    userType: NotRequired[str]
    accessLevel: NotRequired[str]


class Mention(TypedDict):
    type: Literal["mention"]
    attrs: _MentionAttrs


class _EmojiAttrs(TypedDict):
    shortName: str
    id: NotRequired[str]
    text: NotRequired[str]
    localId: NotRequired[str]


class Emoji(TypedDict):
    type: Literal["emoji"]
    attrs: _EmojiAttrs


class _DateAttrs(TypedDict):
    timestamp: str
    localId: NotRequired[str]


class Date(TypedDict):
    type: Literal["date"]
    attrs: _DateAttrs


class _StatusAttrs(TypedDict):
    text: str
    color: str
    style: NotRequired[str]
    localId: NotRequired[str]


class Status(TypedDict):
    type: Literal["status"]
    attrs: _StatusAttrs


class _InlineCardAttrs(TypedDict, total=False):
    url: str
    data: dict[str, Any]


class InlineCard(TypedDict):
    type: Literal["inlineCard"]
    attrs: _InlineCardAttrs


class _PlaceholderAttrs(TypedDict):
    text: str
    localId: NotRequired[str]


class Placeholder(TypedDict):
    type: Literal["placeholder"]
    attrs: _PlaceholderAttrs


class _ExtensionAttrs(TypedDict):
    extensionType: str
    extensionKey: str
    parameters: NotRequired[Any]
    text: NotRequired[str]
    layout: NotRequired[str]
    localId: NotRequired[str]


class InlineExtension(TypedDict):
    type: Literal["inlineExtension"]
    attrs: _ExtensionAttrs


class _MediaInlineAttrs(TypedDict):
    id: str
    collection: str
    type: NotRequired[str]
    alt: NotRequired[str]
    occurrenceKey: NotRequired[str]
    width: NotRequired[int]
    height: NotRequired[int]
    localId: NotRequired[str]


class MediaInline(TypedDict):
    type: Literal["mediaInline"]
    attrs: _MediaInlineAttrs


Inline: TypeAlias = (
    Text
    | HardBreak
    | Mention
    | Emoji
    | Date
    | Status
    | InlineCard
    | Placeholder
    | InlineExtension
    | MediaInline
)


# ── Block Nodes ────────────────────────────────────────────────────────


class _LocalIdAttrs(TypedDict, total=False):
    localId: str


class Paragraph(TypedDict):
    type: Literal["paragraph"]
    content: NotRequired[list[Inline]]
    attrs: NotRequired[_LocalIdAttrs]
    marks: NotRequired[list[dict[str, Any]]]


class _HeadingAttrs(TypedDict):
    level: int
    localId: NotRequired[str]


class Heading(TypedDict):
    type: Literal["heading"]
    attrs: _HeadingAttrs
    content: NotRequired[list[Inline]]
    marks: NotRequired[list[dict[str, Any]]]


class _CodeBlockAttrs(TypedDict, total=False):
    language: str
    localId: str


class CodeBlock(TypedDict):
    type: Literal["codeBlock"]
    content: NotRequired[list[Inline]]
    attrs: NotRequired[_CodeBlockAttrs]


class Blockquote(TypedDict):
    type: Literal["blockquote"]
    content: list[Block]
    attrs: NotRequired[_LocalIdAttrs]


class ListItem(TypedDict):
    type: Literal["listItem"]
    content: list[Block]
    attrs: NotRequired[_LocalIdAttrs]


class BulletList(TypedDict):
    type: Literal["bulletList"]
    content: list[ListItem]
    attrs: NotRequired[_LocalIdAttrs]


class _OrderedListAttrs(TypedDict, total=False):
    order: int
    localId: str


class OrderedList(TypedDict):
    type: Literal["orderedList"]
    content: list[ListItem]
    attrs: NotRequired[_OrderedListAttrs]


class _TaskItemAttrs(TypedDict):
    localId: str
    state: str


class TaskItem(TypedDict):
    type: Literal["taskItem"]
    attrs: _TaskItemAttrs
    content: NotRequired[list[Inline]]


class _TaskListAttrs(TypedDict):
    localId: str


class TaskList(TypedDict):
    type: Literal["taskList"]
    attrs: _TaskListAttrs
    content: list[TaskItem]


class Rule(TypedDict):
    type: Literal["rule"]


class _TableCellAttrs(TypedDict, total=False):
    colspan: int
    rowspan: int
    background: str
    colwidth: list[int]


class TableCell(TypedDict):
    type: Literal["tableCell"]
    content: list[Block]
    attrs: NotRequired[_TableCellAttrs]


class TableHeader(TypedDict):
    type: Literal["tableHeader"]
    content: list[Block]
    attrs: NotRequired[_TableCellAttrs]


class TableRow(TypedDict):
    type: Literal["tableRow"]
    content: list[TableCell | TableHeader]


class _TableAttrs(TypedDict, total=False):
    layout: str
    isNumberColumnEnabled: bool
    localId: str
    width: int
    displayMode: str


class Table(TypedDict):
    type: Literal["table"]
    content: list[TableRow]
    attrs: NotRequired[_TableAttrs]


class _MediaAttrs(TypedDict):
    type: str
    url: NotRequired[str]
    id: NotRequired[str]
    collection: NotRequired[str]
    alt: NotRequired[str]
    width: NotRequired[int]
    height: NotRequired[int]
    localId: NotRequired[str]


class Media(TypedDict):
    type: Literal["media"]
    attrs: _MediaAttrs


class _MediaSingleAttrs(TypedDict, total=False):
    layout: str
    width: float
    widthType: str
    localId: str


class MediaSingle(TypedDict):
    type: Literal["mediaSingle"]
    content: list[Media]
    attrs: NotRequired[_MediaSingleAttrs]


class MediaGroup(TypedDict):
    type: Literal["mediaGroup"]
    content: list[Media]


class _PanelAttrs(TypedDict):
    panelType: str
    localId: NotRequired[str]
    panelColor: NotRequired[str]
    panelIcon: NotRequired[str]
    panelIconId: NotRequired[str]
    panelIconText: NotRequired[str]


class Panel(TypedDict):
    type: Literal["panel"]
    attrs: _PanelAttrs
    content: list[Block]


class _ExpandAttrs(TypedDict, total=False):
    title: str
    localId: str


class Expand(TypedDict):
    type: Literal["expand"]
    content: list[Block]
    attrs: NotRequired[_ExpandAttrs]


class _NestedExpandAttrs(TypedDict, total=False):
    title: str
    localId: str


class NestedExpand(TypedDict):
    type: Literal["nestedExpand"]
    content: list[Block]
    attrs: _NestedExpandAttrs


class _LayoutColumnAttrs(TypedDict):
    width: float
    localId: NotRequired[str]


class LayoutColumn(TypedDict):
    type: Literal["layoutColumn"]
    attrs: _LayoutColumnAttrs
    content: list[Block]


class LayoutSection(TypedDict):
    type: Literal["layoutSection"]
    content: list[LayoutColumn]
    attrs: NotRequired[_LocalIdAttrs]


class _DecisionItemAttrs(TypedDict):
    localId: str
    state: str


class DecisionItem(TypedDict):
    type: Literal["decisionItem"]
    attrs: _DecisionItemAttrs
    content: NotRequired[list[Inline]]


class _DecisionListAttrs(TypedDict):
    localId: str


class DecisionList(TypedDict):
    type: Literal["decisionList"]
    attrs: _DecisionListAttrs
    content: list[DecisionItem]


class _BlockCardAttrs(TypedDict, total=False):
    url: str
    data: dict[str, Any]
    localId: str


class BlockCard(TypedDict):
    type: Literal["blockCard"]
    attrs: _BlockCardAttrs


class _EmbedCardAttrs(TypedDict):
    url: str
    layout: str
    originalWidth: NotRequired[int]
    originalHeight: NotRequired[int]
    width: NotRequired[float]
    localId: NotRequired[str]


class EmbedCard(TypedDict):
    type: Literal["embedCard"]
    attrs: _EmbedCardAttrs


class Extension(TypedDict):
    type: Literal["extension"]
    attrs: _ExtensionAttrs


class BodiedExtension(TypedDict):
    type: Literal["bodiedExtension"]
    attrs: _ExtensionAttrs
    content: list[Block]


class _SyncBlockAttrs(TypedDict):
    resourceId: str
    localId: str


class SyncBlock(TypedDict):
    type: Literal["syncBlock"]
    attrs: _SyncBlockAttrs


class BodiedSyncBlock(TypedDict):
    type: Literal["bodiedSyncBlock"]
    attrs: _SyncBlockAttrs
    content: list[Block]


Block: TypeAlias = (
    Paragraph
    | Heading
    | CodeBlock
    | Blockquote
    | BulletList
    | OrderedList
    | TaskList
    | Rule
    | Table
    | MediaSingle
    | MediaGroup
    | Panel
    | Expand
    | NestedExpand
    | LayoutSection
    | DecisionList
    | BlockCard
    | EmbedCard
    | Extension
    | BodiedExtension
    | SyncBlock
    | BodiedSyncBlock
)


# ── Document ───────────────────────────────────────────────────────────


class Doc(TypedDict):
    type: Literal["doc"]
    version: int
    content: list[Block]


# ── Mark ordering ─────────────────────────────────────────────────────
# code must be last since it terminates recursion (returns CodeSpan).
# This ordering is shared by both the parser and the renderer.

MARK_ORDER: dict[str, int] = {
    "link": 0,
    "strong": 1,
    "em": 2,
    "strike": 3,
    "underline": 4,
    "textColor": 5,
    "backgroundColor": 6,
    "subsup": 7,
    "annotation": 8,
    "code": 9,
}
