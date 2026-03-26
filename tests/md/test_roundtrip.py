"""MD roundtrip tests: AST → MD → AST.

Verifies that rendering to MD and parsing back produces equivalent AST.
"""

from __future__ import annotations

from marklas.md.parser import parse
from marklas.md.renderer import render
from marklas.ast import (
    AlignmentMark,
    AnnotationMark,
    BlockCard,
    Blockquote,
    BulletList,
    CodeBlock,
    CodeMark,
    Date,
    DocContent,
    DecisionItem,
    DecisionList,
    Doc,
    EmbedCard,
    Emoji,
    EmMark,
    Expand,
    Extension,
    HardBreak,
    Heading,
    IndentationMark,
    InlineCard,
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


# ── Helpers ──────────────────────────────────────────────────────────────────


def _rt(doc: Doc) -> Doc:
    """Roundtrip: render to MD, parse back."""
    return parse(render(doc))


def _rt1(node: DocContent) -> DocContent:
    """Roundtrip a single block node, return first content node."""
    doc = Doc(content=[node])
    return _rt(doc).content[0]


# ── Block nodes ──────────────────────────────────────────────────────────────


class TestBlocks:
    def test_paragraph(self):
        node = _rt1(Paragraph(content=[Text(text="hello")]))
        assert isinstance(node, Paragraph)
        first = node.content[0]
        assert isinstance(first, Text)
        assert first.text == "hello"

    def test_paragraph_empty(self):
        node = _rt1(Paragraph())
        assert isinstance(node, Paragraph)
        assert len(node.content) == 0

    def test_heading(self):
        for level in (1, 2, 3, 4, 5, 6):
            node = _rt1(Heading(level=level, content=[Text(text="title")]))
            assert isinstance(node, Heading)
            assert node.level == level

    def test_code_block(self):
        node = _rt1(CodeBlock(language="python", content=[Text(text="x = 1")]))
        assert isinstance(node, CodeBlock)
        assert node.language == "python"
        assert node.content[0].text == "x = 1"

    def test_code_block_no_language(self):
        node = _rt1(CodeBlock(content=[Text(text="code")]))
        assert isinstance(node, CodeBlock)
        assert node.language is None

    def test_blockquote(self):
        node = _rt1(Blockquote(content=[Paragraph(content=[Text(text="quote")])]))
        assert isinstance(node, Blockquote)
        inner = node.content[0]
        assert isinstance(inner, Paragraph)

    def test_bullet_list(self):
        node = _rt1(
            BulletList(
                content=[
                    ListItem(content=[Paragraph(content=[Text(text="a")])]),
                    ListItem(content=[Paragraph(content=[Text(text="b")])]),
                ]
            )
        )
        assert isinstance(node, BulletList)
        assert len(node.content) == 2

    def test_ordered_list(self):
        node = _rt1(
            OrderedList(
                order=3,
                content=[
                    ListItem(content=[Paragraph(content=[Text(text="item")])]),
                ],
            )
        )
        assert isinstance(node, OrderedList)
        assert node.order == 3

    def test_rule(self):
        node = _rt1(Rule())
        assert isinstance(node, Rule)

    def test_empty_paragraph_between_headings(self):
        doc = _rt(
            Doc(
                content=[
                    Heading(level=1, content=[Text(text="A")]),
                    Paragraph(),
                    Heading(level=2, content=[Text(text="B")]),
                ]
            )
        )
        assert len(doc.content) == 3
        assert isinstance(doc.content[1], Paragraph)

    def test_deep_nesting(self):
        """Expand > Panel > BulletList > CodeBlock."""
        node = _rt1(
            Expand(
                title="Deep",
                content=[
                    Panel(
                        panel_type="info",
                        content=[
                            BulletList(
                                content=[
                                    ListItem(
                                        content=[
                                            Paragraph(content=[Text(text="item")]),
                                            CodeBlock(
                                                language="python",
                                                content=[Text(text="x = 1")],
                                            ),
                                        ]
                                    )
                                ]
                            )
                        ],
                    )
                ],
            )
        )
        assert isinstance(node, Expand)

    def test_unicode_korean(self):
        node = _rt1(Paragraph(content=[Text(text="한글 테스트입니다")]))
        assert isinstance(node, Paragraph)
        first = node.content[0]
        assert isinstance(first, Text)
        assert first.text == "한글 테스트입니다"

    def test_unicode_emoji_in_text(self):
        node = _rt1(Paragraph(content=[Text(text="🎉 축하합니다 🎊")]))
        assert isinstance(node, Paragraph)
        first = node.content[0]
        assert isinstance(first, Text)
        assert "🎉" in first.text


# ── Inline marks ─────────────────────────────────────────────────────────────


class TestInlineMarks:
    def test_strong(self):
        node = _rt1(Paragraph(content=[Text(text="bold", marks=[StrongMark()])]))
        assert isinstance(node, Paragraph)
        first = node.content[0]
        assert isinstance(first, Text)
        assert any(isinstance(m, StrongMark) for m in first.marks)

    def test_em(self):
        node = _rt1(Paragraph(content=[Text(text="italic", marks=[EmMark()])]))
        assert isinstance(node, Paragraph)
        first = node.content[0]
        assert isinstance(first, Text)
        assert any(isinstance(m, EmMark) for m in first.marks)

    def test_strike(self):
        node = _rt1(Paragraph(content=[Text(text="strike", marks=[StrikeMark()])]))
        assert isinstance(node, Paragraph)
        first = node.content[0]
        assert isinstance(first, Text)
        assert any(isinstance(m, StrikeMark) for m in first.marks)

    def test_code(self):
        node = _rt1(Paragraph(content=[Text(text="code", marks=[CodeMark()])]))
        assert isinstance(node, Paragraph)
        first = node.content[0]
        assert isinstance(first, Text)
        assert any(isinstance(m, CodeMark) for m in first.marks)

    def test_link(self):
        mark = LinkMark(href="https://example.com", title="t")
        node = _rt1(Paragraph(content=[Text(text="link", marks=[mark])]))
        assert isinstance(node, Paragraph)
        first = node.content[0]
        assert isinstance(first, Text)
        link = next(m for m in first.marks if isinstance(m, LinkMark))
        assert link.href == "https://example.com"
        assert link.title == "t"

    def test_underline(self):
        node = _rt1(Paragraph(content=[Text(text="u", marks=[UnderlineMark()])]))
        assert isinstance(node, Paragraph)
        first = node.content[0]
        assert isinstance(first, Text)
        assert any(isinstance(m, UnderlineMark) for m in first.marks)

    def test_text_color(self):
        node = _rt1(
            Paragraph(content=[Text(text="red", marks=[TextColorMark(color="#f00")])])
        )
        assert isinstance(node, Paragraph)
        first = node.content[0]
        assert isinstance(first, Text)
        tc = next(m for m in first.marks if isinstance(m, TextColorMark))
        assert tc.color == "#f00"

    def test_annotation(self):
        mark = AnnotationMark(id="a1", annotation_type="inlineComment")
        node = _rt1(Paragraph(content=[Text(text="noted", marks=[mark])]))
        assert isinstance(node, Paragraph)
        first = node.content[0]
        assert isinstance(first, Text)
        ann = next(m for m in first.marks if isinstance(m, AnnotationMark))
        assert ann.id == "a1"

    def test_two_marks_strong_em(self):
        node = _rt1(Paragraph(content=[Text(text="x", marks=[StrongMark(), EmMark()])]))
        assert isinstance(node, Paragraph)
        first = node.content[0]
        assert isinstance(first, Text)
        assert len(first.marks) == 2

    def test_two_marks_link_strong(self):
        node = _rt1(
            Paragraph(
                content=[
                    Text(
                        text="x",
                        marks=[LinkMark(href="https://example.com"), StrongMark()],
                    )
                ]
            )
        )
        assert isinstance(node, Paragraph)
        first = node.content[0]
        assert isinstance(first, Text)
        assert any(isinstance(m, LinkMark) for m in first.marks)
        assert any(isinstance(m, StrongMark) for m in first.marks)

    def test_three_marks(self):
        node = _rt1(
            Paragraph(
                content=[Text(text="x", marks=[StrongMark(), EmMark(), StrikeMark()])]
            )
        )
        assert isinstance(node, Paragraph)
        first = node.content[0]
        assert isinstance(first, Text)
        assert len(first.marks) == 3


# ── Inline nodes ─────────────────────────────────────────────────────────────


class TestInlineNodes:
    def test_hard_break(self):
        node = _rt1(Paragraph(content=[Text(text="a"), HardBreak(), Text(text="b")]))
        assert isinstance(node, Paragraph)
        assert any(isinstance(c, HardBreak) for c in node.content)

    def test_mention(self):
        node = _rt1(Paragraph(content=[Mention(id="u1", text="@John")]))
        assert isinstance(node, Paragraph)
        m = node.content[0]
        assert isinstance(m, Mention)
        assert m.id == "u1"

    def test_emoji(self):
        node = _rt1(
            Paragraph(content=[Emoji(short_name=":smile:", id="1f604", text="😄")])
        )
        assert isinstance(node, Paragraph)
        e = node.content[0]
        assert isinstance(e, Emoji)
        assert e.short_name == ":smile:"

    def test_date(self):
        node = _rt1(Paragraph(content=[Date(timestamp="1700000000000")]))
        assert isinstance(node, Paragraph)
        d = node.content[0]
        assert isinstance(d, Date)
        assert d.timestamp == "1700000000000"

    def test_status(self):
        node = _rt1(Paragraph(content=[Status(text="DONE", color="green")]))
        assert isinstance(node, Paragraph)
        s = node.content[0]
        assert isinstance(s, Status)
        assert s.text == "DONE"

    def test_inline_card(self):
        node = _rt1(Paragraph(content=[InlineCard(url="https://example.com")]))
        assert isinstance(node, Paragraph)
        ic = node.content[0]
        assert isinstance(ic, InlineCard)
        assert ic.url == "https://example.com"

    def test_placeholder(self):
        node = _rt1(Paragraph(content=[Placeholder(text="Enter name")]))
        assert isinstance(node, Paragraph)
        p = node.content[0]
        assert isinstance(p, Placeholder)
        assert p.text == "Enter name"

    def test_media_inline(self):
        node = _rt1(
            Paragraph(
                content=[
                    MediaInline(id="f1", collection="uploads", type="file"),
                ]
            )
        )
        assert isinstance(node, Paragraph)
        mi = node.content[0]
        assert isinstance(mi, MediaInline)
        assert mi.id == "f1"

    def test_special_chars_in_text(self):
        for char in ["*", "_", "[", "]", "`", "\\", "<", ">", "#", "~"]:
            node = _rt1(Paragraph(content=[Text(text=f"before {char} after")]))
            assert isinstance(node, Paragraph)
            full_text = "".join(c.text for c in node.content if isinstance(c, Text))
            assert char in full_text, f"char {char!r} not in {full_text!r}"

    def test_pipe_in_table_cell(self):
        node = _rt1(
            Table(
                content=[
                    TableRow(
                        content=[
                            TableHeader(content=[Paragraph(content=[Text(text="H")])]),
                        ]
                    ),
                    TableRow(
                        content=[
                            TableCell(
                                content=[Paragraph(content=[Text(text="a | b")])]
                            ),
                        ]
                    ),
                ]
            )
        )
        assert isinstance(node, Table)


# ── Block HTML nodes ─────────────────────────────────────────────────────────


class TestBlockHTML:
    def test_panel(self):
        node = _rt1(
            Panel(
                panel_type="info",
                content=[Paragraph(content=[Text(text="note")])],
            )
        )
        assert isinstance(node, Panel)
        assert node.panel_type == "info"

    def test_panel_empty(self):
        node = _rt1(Panel(panel_type="info", content=[Paragraph()]))
        assert isinstance(node, Panel)

    def test_expand(self):
        node = _rt1(
            Expand(
                title="Details",
                content=[Paragraph(content=[Text(text="body")])],
            )
        )
        assert isinstance(node, Expand)
        assert node.title == "Details"

    def test_expand_empty(self):
        node = _rt1(Expand(content=[Paragraph()]))
        assert isinstance(node, Expand)

    def test_decision_list(self):
        node = _rt1(
            DecisionList(
                content=[
                    DecisionItem(state="DECIDED", content=[Text(text="yes")]),
                ]
            )
        )
        assert isinstance(node, DecisionList)
        item = node.content[0]
        assert isinstance(item, DecisionItem)
        assert item.state == "DECIDED"

    def test_block_card(self):
        node = _rt1(BlockCard(url="https://example.com"))
        assert isinstance(node, BlockCard)
        assert node.url == "https://example.com"

    def test_embed_card(self):
        node = _rt1(EmbedCard(url="https://yt.com", layout="wide"))
        assert isinstance(node, EmbedCard)
        assert node.url == "https://yt.com"

    def test_layout_section(self):
        node = _rt1(
            LayoutSection(
                content=[
                    LayoutColumn(
                        width=50, content=[Paragraph(content=[Text(text="left")])]
                    ),
                    LayoutColumn(
                        width=50, content=[Paragraph(content=[Text(text="right")])]
                    ),
                ]
            )
        )
        assert isinstance(node, LayoutSection)
        assert len(node.content) == 2


# ── Media ────────────────────────────────────────────────────────────────────


class TestMedia:
    def test_media_single(self):
        node = _rt1(
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

    def test_media_group(self):
        node = _rt1(
            MediaGroup(
                content=[
                    Media(type="file", id="a", collection="c"),
                    Media(type="file", id="b", collection="c"),
                ]
            )
        )
        assert isinstance(node, MediaGroup)
        assert len(node.content) == 2


# ── TaskList ─────────────────────────────────────────────────────────────────


class TestTaskList:
    def test_task_list(self):
        node = _rt1(
            TaskList(
                content=[
                    TaskItem(state="TODO", content=[Text(text="todo")]),
                    TaskItem(state="DONE", content=[Text(text="done")]),
                ]
            )
        )
        assert isinstance(node, TaskList)
        item0 = node.content[0]
        assert isinstance(item0, TaskItem)
        assert item0.state == "TODO"
        item1 = node.content[1]
        assert isinstance(item1, TaskItem)
        assert item1.state == "DONE"


# ── Table ────────────────────────────────────────────────────────────────────


class TestTable:
    def test_simple_table(self):
        node = _rt1(
            Table(
                content=[
                    TableRow(
                        content=[
                            TableHeader(content=[Paragraph(content=[Text(text="H")])]),
                        ]
                    ),
                    TableRow(
                        content=[
                            TableCell(content=[Paragraph(content=[Text(text="D")])]),
                        ]
                    ),
                ]
            )
        )
        assert isinstance(node, Table)
        assert len(node.content) == 2


# ── Extension / Data ─────────────────────────────────────────────────────────


class TestExtension:
    def test_extension(self):
        node = _rt1(
            Extension(
                extension_key="macro",
                extension_type="com.atlassian",
                parameters={"key": "val"},
            )
        )
        assert isinstance(node, Extension)
        assert node.extension_key == "macro"
        assert node.parameters == {"key": "val"}

    def test_sync_block(self):
        node = _rt1(SyncBlock(resource_id="r1"))
        assert isinstance(node, SyncBlock)
        assert node.resource_id == "r1"


# ── Block marks ──────────────────────────────────────────────────────────────


class TestBlockMarks:
    def test_alignment(self):
        node = _rt1(
            Paragraph(
                content=[Text(text="centered")],
                marks=[AlignmentMark(align="center")],
            )
        )
        assert isinstance(node, Paragraph)
        assert any(isinstance(m, AlignmentMark) for m in node.marks)

    def test_indentation(self):
        node = _rt1(
            Paragraph(
                content=[Text(text="indented")],
                marks=[IndentationMark(level=2)],
            )
        )
        assert isinstance(node, Paragraph)
        mark = next(m for m in node.marks if isinstance(m, IndentationMark))
        assert mark.level == 2
