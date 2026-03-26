"""Markdown parser tests."""

from __future__ import annotations

from marklas.ast import DocContent
from marklas.ast import (
    AlignmentMark,
    AnnotationMark,
    BackgroundColorMark,
    BlockCard,
    Blockquote,
    BreakoutMark,
    BulletList,
    Caption,
    CodeBlock,
    CodeMark,
    DataConsumerMark,
    Date,
    DecisionItem,
    DecisionList,
    Doc,
    EmbedCard,
    EmMark,
    Emoji,
    Expand,
    Extension,
    HardBreak,
    Heading,
    IndentationMark,
    InlineCard,
    InlineExtension,
    LayoutColumn,
    LayoutSection,
    LinkMark,
    ListItem,
    Media,
    MediaGroup,
    MediaInline,
    MediaSingle,
    Mention,
    OrderedList,
    Panel,
    Paragraph,
    Placeholder,
    Rule,
    Status,
    StrikeMark,
    StrongMark,
    SubSupMark,
    SyncBlock,
    Table,
    TableCell,
    TableHeader,
    TableRow,
    TaskItem,
    TaskList,
    Text,
    TextColorMark,
    UnderlineMark,
)
from marklas.md.parser import parse
from marklas.md.renderer import render


def _roundtrip(doc: Doc) -> Doc:
    return parse(render(doc))


def _rt_block(node: DocContent) -> DocContent:
    """Roundtrip a single block node and return the restored node."""
    doc = Doc(content=[node])
    return _roundtrip(doc).content[0]


# ── Paragraph ──────────────────────────────────────────────────────────────────


class TestParagraph:
    def test_simple(self):
        node = _rt_block(Paragraph(content=[Text(text="hello")]))
        assert isinstance(node, Paragraph)
        first = node.content[0]
        assert isinstance(first, Text)
        assert first.text == "hello"

    def test_empty(self):
        node = _rt_block(Paragraph(content=[]))
        assert isinstance(node, Paragraph)
        assert node.content == []

    def test_with_alignment_mark(self):
        node = _rt_block(
            Paragraph(
                content=[Text(text="centered")],
                marks=[AlignmentMark(align="center")],
            )
        )
        assert isinstance(node, Paragraph)
        assert isinstance(node, Paragraph)
        assert any(isinstance(m, AlignmentMark) for m in node.marks)

    def test_with_data_consumer_mark(self):
        node = _rt_block(
            Paragraph(
                content=[Text(text="data")],
                marks=[DataConsumerMark(sources=["src-1"])],
            )
        )
        assert isinstance(node, Paragraph)
        assert any(isinstance(m, DataConsumerMark) for m in node.marks)


# ── Heading ────────────────────────────────────────────────────────────────────


class TestHeading:
    def test_levels(self):
        for level in (1, 2, 3, 4, 5, 6):
            node = _rt_block(Heading(level=level, content=[Text(text="T")]))
            assert isinstance(node, Heading)
            assert node.level == level

    def test_with_indentation_mark(self):
        node = _rt_block(
            Heading(
                level=2,
                content=[Text(text="Indented")],
                marks=[IndentationMark(level=2)],
            )
        )
        assert isinstance(node, Heading)
        assert any(isinstance(m, IndentationMark) for m in node.marks)


# ── CodeBlock ──────────────────────────────────────────────────────────────────


class TestCodeBlock:
    def test_with_language(self):
        node = _rt_block(CodeBlock(language="python", content=[Text(text="x = 1")]))
        assert isinstance(node, CodeBlock)
        assert node.language == "python"
        first = node.content[0]
        assert isinstance(first, Text)
        assert first.text == "x = 1"

    def test_without_language(self):
        node = _rt_block(CodeBlock(content=[Text(text="raw")]))
        assert isinstance(node, CodeBlock)
        assert node.language is None

    def test_with_breakout_mark(self):
        node = _rt_block(
            CodeBlock(
                language="js",
                content=[Text(text="code")],
                marks=[BreakoutMark(mode="wide")],
            )
        )
        assert isinstance(node, CodeBlock)
        assert any(isinstance(m, BreakoutMark) for m in node.marks)


# ── Blockquote ─────────────────────────────────────────────────────────────────


class TestBlockquote:
    def test_simple(self):
        node = _rt_block(Blockquote(content=[Paragraph(content=[Text(text="quote")])]))
        assert isinstance(node, Blockquote)
        assert isinstance(node.content[0], Paragraph)

    def test_nested(self):
        node = _rt_block(
            Blockquote(
                content=[
                    Paragraph(content=[Text(text="a")]),
                    Paragraph(content=[Text(text="b")]),
                ]
            )
        )
        assert isinstance(node, Blockquote)
        assert len(node.content) == 2


# ── Lists ──────────────────────────────────────────────────────────────────────


class TestBulletList:
    def test_simple(self):
        node = _rt_block(
            BulletList(
                content=[
                    ListItem(content=[Paragraph(content=[Text(text="a")])]),
                    ListItem(content=[Paragraph(content=[Text(text="b")])]),
                ]
            )
        )
        assert isinstance(node, BulletList)
        assert len(node.content) == 2

    def test_nested(self):
        node = _rt_block(
            BulletList(
                content=[
                    ListItem(
                        content=[
                            Paragraph(content=[Text(text="parent")]),
                            BulletList(
                                content=[
                                    ListItem(
                                        content=[
                                            Paragraph(content=[Text(text="child")])
                                        ]
                                    )
                                ]
                            ),
                        ]
                    ),
                ]
            )
        )
        assert isinstance(node, BulletList)
        first_item = node.content[0]
        assert isinstance(first_item, ListItem)
        inner = first_item.content[1]
        assert isinstance(inner, BulletList)


class TestOrderedList:
    def test_simple(self):
        node = _rt_block(
            OrderedList(
                content=[
                    ListItem(content=[Paragraph(content=[Text(text="a")])]),
                    ListItem(content=[Paragraph(content=[Text(text="b")])]),
                ]
            )
        )
        assert isinstance(node, OrderedList)
        assert len(node.content) == 2

    def test_custom_start(self):
        node = _rt_block(
            OrderedList(
                order=3,
                content=[ListItem(content=[Paragraph(content=[Text(text="item")])])],
            )
        )
        assert isinstance(node, OrderedList)
        assert node.order == 3


# ── Rule ───────────────────────────────────────────────────────────────────────


class TestRule:
    def test_simple(self):
        node = _rt_block(Rule())
        assert isinstance(node, Rule)


# ── TaskList ───────────────────────────────────────────────────────────────────


class TestTaskList:
    def test_simple(self):
        node = _rt_block(
            TaskList(
                content=[
                    TaskItem(state="DONE", content=[Text(text="done")]),
                    TaskItem(state="TODO", content=[Text(text="todo")]),
                ]
            )
        )
        assert isinstance(node, TaskList)
        items = [c for c in node.content if isinstance(c, TaskItem)]
        assert items[0].state == "DONE"
        assert items[1].state == "TODO"


# ── Inline Marks ───────────────────────────────────────────────────────────────


class TestMarks:
    def test_strong(self):
        doc = _roundtrip(
            Doc(content=[Paragraph(content=[Text(text="bold", marks=[StrongMark()])])])
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        text = para.content[0]
        assert isinstance(text, Text)
        assert any(isinstance(m, StrongMark) for m in text.marks)

    def test_em(self):
        doc = _roundtrip(
            Doc(content=[Paragraph(content=[Text(text="italic", marks=[EmMark()])])])
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        text = para.content[0]
        assert isinstance(text, Text)
        assert any(isinstance(m, EmMark) for m in text.marks)

    def test_strike(self):
        doc = _roundtrip(
            Doc(content=[Paragraph(content=[Text(text="del", marks=[StrikeMark()])])])
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        text = para.content[0]
        assert isinstance(text, Text)
        assert any(isinstance(m, StrikeMark) for m in text.marks)

    def test_code(self):
        doc = _roundtrip(
            Doc(content=[Paragraph(content=[Text(text="x", marks=[CodeMark()])])])
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        text = para.content[0]
        assert isinstance(text, Text)
        assert any(isinstance(m, CodeMark) for m in text.marks)

    def test_link(self):
        doc = _roundtrip(
            Doc(
                content=[
                    Paragraph(
                        content=[
                            Text(text="click", marks=[LinkMark(href="https://x.com")])
                        ]
                    )
                ]
            )
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        text = para.content[0]
        assert isinstance(text, Text)
        link = next(m for m in text.marks if isinstance(m, LinkMark))
        assert link.href == "https://x.com"

    def test_underline(self):
        doc = _roundtrip(
            Doc(content=[Paragraph(content=[Text(text="u", marks=[UnderlineMark()])])])
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        text = para.content[0]
        assert isinstance(text, Text)
        assert any(isinstance(m, UnderlineMark) for m in text.marks)

    def test_text_color(self):
        doc = _roundtrip(
            Doc(
                content=[
                    Paragraph(
                        content=[Text(text="r", marks=[TextColorMark(color="#f00")])]
                    )
                ]
            )
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        text = para.content[0]
        assert isinstance(text, Text)
        mark = next(m for m in text.marks if isinstance(m, TextColorMark))
        assert mark.color == "#f00"

    def test_background_color(self):
        doc = _roundtrip(
            Doc(
                content=[
                    Paragraph(
                        content=[
                            Text(text="h", marks=[BackgroundColorMark(color="#ff0")])
                        ]
                    )
                ]
            )
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        text = para.content[0]
        assert isinstance(text, Text)
        assert any(isinstance(m, BackgroundColorMark) for m in text.marks)

    def test_subsup(self):
        doc = _roundtrip(
            Doc(
                content=[
                    Paragraph(content=[Text(text="2", marks=[SubSupMark(type="sup")])])
                ]
            )
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        text = para.content[0]
        assert isinstance(text, Text)
        mark = next(m for m in text.marks if isinstance(m, SubSupMark))
        assert mark.type == "sup"

    def test_annotation(self):
        doc = _roundtrip(
            Doc(
                content=[
                    Paragraph(
                        content=[
                            Text(
                                text="note",
                                marks=[
                                    AnnotationMark(
                                        id="a1", annotation_type="inlineComment"
                                    )
                                ],
                            )
                        ]
                    )
                ]
            )
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        text = para.content[0]
        assert isinstance(text, Text)
        mark = next(m for m in text.marks if isinstance(m, AnnotationMark))
        assert mark.id == "a1"


# ── Inline Nodes ───────────────────────────────────────────────────────────────


class TestInlineNodes:
    def test_mention(self):
        doc = _roundtrip(
            Doc(content=[Paragraph(content=[Mention(id="u1", text="John")])])
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        node = para.content[0]
        assert isinstance(node, Mention)
        assert node.id == "u1"
        assert node.text == "John"

    def test_emoji(self):
        doc = _roundtrip(
            Doc(
                content=[
                    Paragraph(
                        content=[Emoji(short_name=":smile:", id="1f604", text="😄")]
                    )
                ]
            )
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        node = para.content[0]
        assert isinstance(node, Emoji)
        assert node.short_name == ":smile:"

    def test_date(self):
        doc = _roundtrip(
            Doc(content=[Paragraph(content=[Date(timestamp="1711324800000")])])
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        node = para.content[0]
        assert isinstance(node, Date)
        assert node.timestamp == "1711324800000"

    def test_status(self):
        doc = _roundtrip(
            Doc(content=[Paragraph(content=[Status(text="OK", color="green")])])
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        node = para.content[0]
        assert isinstance(node, Status)
        assert node.text == "OK"
        assert node.color == "green"

    def test_inline_card(self):
        doc = _roundtrip(
            Doc(content=[Paragraph(content=[InlineCard(url="https://x.com")])])
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        node = para.content[0]
        assert isinstance(node, InlineCard)
        assert node.url == "https://x.com"

    def test_placeholder(self):
        doc = _roundtrip(
            Doc(content=[Paragraph(content=[Placeholder(text="Type here")])])
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        node = para.content[0]
        assert isinstance(node, Placeholder)
        assert node.text == "Type here"

    def test_hard_break(self):
        doc = _roundtrip(
            Doc(
                content=[
                    Paragraph(content=[Text(text="a"), HardBreak(), Text(text="b")])
                ]
            )
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        assert isinstance(para.content[1], HardBreak)

    def test_media_inline(self):
        doc = _roundtrip(
            Doc(
                content=[
                    Paragraph(
                        content=[
                            MediaInline(id="f1", collection="uploads", type="file")
                        ]
                    )
                ]
            )
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        node = para.content[0]
        assert isinstance(node, MediaInline)
        assert node.id == "f1"

    def test_inline_extension(self):
        doc = _roundtrip(
            Doc(
                content=[
                    Paragraph(
                        content=[InlineExtension(extension_key="k", extension_type="t")]
                    )
                ]
            )
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        node = para.content[0]
        assert isinstance(node, InlineExtension)
        assert node.extension_key == "k"


# ── Block HTML Fallback ────────────────────────────────────────────────────────


class TestPanel:
    def test_simple(self):
        node = _rt_block(
            Panel(
                panel_type="info",
                content=[Paragraph(content=[Text(text="note")])],
            )
        )
        assert isinstance(node, Panel)
        assert node.panel_type == "info"


class TestExpand:
    def test_with_title(self):
        node = _rt_block(
            Expand(
                title="Details",
                content=[Paragraph(content=[Text(text="body")])],
            )
        )
        assert isinstance(node, Expand)
        assert node.title == "Details"

    def test_without_title(self):
        node = _rt_block(Expand(content=[Paragraph(content=[Text(text="body")])]))
        assert isinstance(node, Expand)
        assert node.title is None


class TestDecisionList:
    def test_simple(self):
        node = _rt_block(
            DecisionList(
                content=[DecisionItem(state="DECIDED", content=[Text(text="yes")])]
            )
        )
        assert isinstance(node, DecisionList)
        first = node.content[0]
        assert isinstance(first, DecisionItem)
        assert first.state == "DECIDED"


# ── Media ──────────────────────────────────────────────────────────────────────


class TestMediaSingle:
    def test_simple(self):
        node = _rt_block(
            MediaSingle(
                layout="center",
                content=[Media(type="file", id="abc", collection="uploads")],
            )
        )
        assert isinstance(node, MediaSingle)
        assert node.layout == "center"
        media = node.content[0]
        assert isinstance(media, Media)
        assert media.id == "abc"

    def test_with_caption(self):
        node = _rt_block(
            MediaSingle(
                content=[
                    Media(type="file", id="abc"),
                    Caption(content=[Text(text="cap")]),
                ],
            )
        )
        assert isinstance(node, MediaSingle)
        assert len(node.content) == 2
        assert isinstance(node.content[1], Caption)


class TestMediaGroup:
    def test_simple(self):
        node = _rt_block(
            MediaGroup(content=[Media(type="file", id="a"), Media(type="file", id="b")])
        )
        assert isinstance(node, MediaGroup)
        assert len(node.content) == 2


# ── Cards ──────────────────────────────────────────────────────────────────────


class TestBlockCard:
    def test_simple(self):
        node = _rt_block(BlockCard(url="https://example.com"))
        assert isinstance(node, BlockCard)
        assert node.url == "https://example.com"


class TestEmbedCard:
    def test_simple(self):
        node = _rt_block(EmbedCard(url="https://example.com", layout="wide"))
        assert isinstance(node, EmbedCard)
        assert node.url == "https://example.com"
        assert node.layout == "wide"


# ── Extension / SyncBlock ─────────────────────────────────────────────────────


class TestExtension:
    def test_simple(self):
        node = _rt_block(Extension(extension_key="k", extension_type="t"))
        assert isinstance(node, Extension)
        assert node.extension_key == "k"


class TestSyncBlock:
    def test_simple(self):
        node = _rt_block(SyncBlock(resource_id="r1"))
        assert isinstance(node, SyncBlock)
        assert node.resource_id == "r1"


# ── Layout ─────────────────────────────────────────────────────────────────────


class TestLayoutSection:
    def test_two_columns(self):
        node = _rt_block(
            LayoutSection(
                content=[
                    LayoutColumn(
                        width=50.0,
                        content=[Paragraph(content=[Text(text="left")])],
                    ),
                    LayoutColumn(
                        width=50.0,
                        content=[Paragraph(content=[Text(text="right")])],
                    ),
                ]
            )
        )
        assert isinstance(node, LayoutSection)
        assert len(node.content) == 2
        col = node.content[0]
        assert isinstance(col, LayoutColumn)
        assert col.width == 50.0


# ── Table ──────────────────────────────────────────────────────────────────────


class TestTable:
    def test_simple(self):
        node = _rt_block(
            Table(
                content=[
                    TableRow(
                        content=[
                            TableHeader(content=[Paragraph(content=[Text(text="A")])]),
                            TableHeader(content=[Paragraph(content=[Text(text="B")])]),
                        ]
                    ),
                    TableRow(
                        content=[
                            TableCell(content=[Paragraph(content=[Text(text="1")])]),
                            TableCell(content=[Paragraph(content=[Text(text="2")])]),
                        ]
                    ),
                ]
            )
        )
        assert isinstance(node, Table)
        assert len(node.content) == 2

    def test_with_layout(self):
        node = _rt_block(
            Table(
                layout="wide",
                content=[
                    TableRow(
                        content=[
                            TableHeader(content=[Paragraph(content=[Text(text="X")])])
                        ]
                    ),
                    TableRow(
                        content=[
                            TableCell(content=[Paragraph(content=[Text(text="Y")])])
                        ]
                    ),
                ],
            )
        )
        assert isinstance(node, Table)
        assert node.layout == "wide"

    def test_colspan(self):
        node = _rt_block(
            Table(
                content=[
                    TableRow(
                        content=[
                            TableHeader(
                                content=[Paragraph(content=[Text(text="merged")])],
                                colspan=2,
                            ),
                        ]
                    ),
                    TableRow(
                        content=[
                            TableCell(content=[Paragraph(content=[Text(text="a")])]),
                            TableCell(content=[Paragraph(content=[Text(text="b")])]),
                        ]
                    ),
                ]
            )
        )
        assert isinstance(node, Table)
        first_row = node.content[0]
        assert isinstance(first_row, TableRow)
        first_cell = first_row.content[0]
        assert isinstance(first_cell, TableHeader)
        assert first_cell.colspan == 2

    def test_no_header(self):
        node = _rt_block(
            Table(
                content=[
                    TableRow(
                        content=[
                            TableCell(content=[Paragraph(content=[Text(text="A")])]),
                            TableCell(content=[Paragraph(content=[Text(text="B")])]),
                        ]
                    ),
                ]
            )
        )
        assert isinstance(node, Table)


# ── Raw MD: Solo Image ────────────────────────────────────────────────────────


class TestImage:
    def test_solo_image(self):
        doc = parse("![Cat](https://example.com/cat.png)\n")
        node = doc.content[0]
        assert isinstance(node, MediaSingle)
        media = node.content[0]
        assert isinstance(media, Media)
        assert media.type == "external"
        assert media.url == "https://example.com/cat.png"
        assert media.alt == "Cat"

    def test_inline_image_ignored(self):
        doc = parse("before ![img](url) after\n")
        node = doc.content[0]
        assert isinstance(node, Paragraph)


# ── Params Escape ──────────────────────────────────────────────────────────────


class TestParamsEscape:
    def test_ampersand_roundtrip(self):
        doc = _roundtrip(
            Doc(content=[Paragraph(content=[Status(text="A&B", color="red")])])
        )
        para = doc.content[0]
        assert isinstance(para, Paragraph)
        node = para.content[0]
        assert isinstance(node, Status)
        assert node.text == "A&B"

    def test_single_quote_roundtrip(self):
        doc = _roundtrip(
            Doc(
                content=[
                    Panel(
                        panel_type="info",
                        panel_icon="it's",
                        content=[Paragraph(content=[Text(text="x")])],
                    )
                ]
            )
        )
        node = doc.content[0]
        assert isinstance(node, Panel)
        assert node.panel_icon == "it's"
