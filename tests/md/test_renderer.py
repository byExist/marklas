"""Markdown renderer tests."""

from __future__ import annotations

from typing import Literal

import pytest

from marklas.ast import DocContent
from marklas.ast import (
    AlignmentMark,
    AnnotationMark,
    BackgroundColorMark,
    BlockCard,
    BlockTaskItem,
    Blockquote,
    BodiedExtension,
    BorderMark,
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
    NestedExpand,
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
from marklas.md.renderer import render


def _render(*blocks: DocContent) -> str:
    """Shortcut: wrap blocks in Doc and render."""
    return render(Doc(content=list(blocks)))


# ── Paragraph ──────────────────────────────────────────────────────────────────


class TestParagraph:
    def test_simple(self):
        assert _render(Paragraph(content=[Text(text="hello")])) == "hello\n"

    def test_empty(self):
        assert _render(Paragraph(content=[])) == "&nbsp;\n"

    def test_with_alignment_mark(self):
        result = _render(
            Paragraph(
                content=[Text(text="centered")],
                marks=[AlignmentMark(align="center")],
            )
        )
        assert '<div adf="marks"' in result
        assert '"align":"center"' in result
        assert "centered" in result

    def test_with_data_consumer_mark(self):
        result = _render(
            Paragraph(
                content=[Text(text="data")],
                marks=[DataConsumerMark(sources=["src-1", "src-2"])],
            )
        )
        assert '<div adf="marks"' in result
        assert '"dataConsumerSources"' in result
        assert "src-1" in result


# ── Heading ────────────────────────────────────────────────────────────────────


class TestHeading:
    @pytest.mark.parametrize("level", [1, 2, 3, 4, 5, 6])
    def test_levels(self, level: Literal[1, 2, 3, 4, 5, 6]):
        result = _render(Heading(level=level, content=[Text(text="Title")]))
        assert result == f"{'#' * level} Title\n"

    def test_with_indentation_mark(self):
        result = _render(
            Heading(
                level=2,
                content=[Text(text="Indented")],
                marks=[IndentationMark(level=2)],
            )
        )
        assert '<div adf="marks"' in result
        assert '"indent":2' in result
        assert "## Indented" in result


# ── CodeBlock ──────────────────────────────────────────────────────────────────


class TestCodeBlock:
    def test_with_language(self):
        result = _render(CodeBlock(language="python", content=[Text(text="x = 1")]))
        assert result == "```python\nx = 1\n```\n"

    def test_without_language(self):
        result = _render(CodeBlock(content=[Text(text="raw code")]))
        assert result == "```\nraw code\n```\n"

    def test_with_backticks_in_code(self):
        result = _render(CodeBlock(content=[Text(text="use ```backticks```")]))
        assert result.startswith("````")

    def test_with_breakout_mark(self):
        result = _render(
            CodeBlock(
                language="js",
                content=[Text(text="code")],
                marks=[BreakoutMark(mode="wide")],
            )
        )
        assert '<div adf="marks"' in result
        assert '"breakoutMode":"wide"' in result


# ── Blockquote ─────────────────────────────────────────────────────────────────


class TestBlockquote:
    def test_simple(self):
        result = _render(Blockquote(content=[Paragraph(content=[Text(text="quote")])]))
        assert result == "> quote\n"

    def test_multiline(self):
        result = _render(
            Blockquote(
                content=[
                    Paragraph(content=[Text(text="line 1")]),
                    Paragraph(content=[Text(text="line 2")]),
                ]
            )
        )
        assert "> line 1\n>\n> line 2\n" == result


# ── Lists ──────────────────────────────────────────────────────────────────────


class TestBulletList:
    def test_simple(self):
        result = _render(
            BulletList(
                content=[
                    ListItem(content=[Paragraph(content=[Text(text="a")])]),
                    ListItem(content=[Paragraph(content=[Text(text="b")])]),
                ]
            )
        )
        assert result == "- a\n- b\n"

    def test_nested(self):
        result = _render(
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
                                    ),
                                ]
                            ),
                        ]
                    ),
                ]
            )
        )
        assert "- parent" in result
        assert "  - child" in result


class TestOrderedList:
    def test_simple(self):
        result = _render(
            OrderedList(
                content=[
                    ListItem(content=[Paragraph(content=[Text(text="a")])]),
                    ListItem(content=[Paragraph(content=[Text(text="b")])]),
                ]
            )
        )
        assert result == "1. a\n2. b\n"

    def test_custom_start(self):
        result = _render(
            OrderedList(
                order=3,
                content=[
                    ListItem(content=[Paragraph(content=[Text(text="item")])]),
                ],
            )
        )
        assert result == "3. item\n"


# ── Rule ───────────────────────────────────────────────────────────────────────


class TestRule:
    def test_simple(self):
        assert _render(Rule()) == "---\n"


# ── TaskList ───────────────────────────────────────────────────────────────────


class TestTaskList:
    def test_simple(self):
        result = _render(
            TaskList(
                content=[
                    TaskItem(state="DONE", content=[Text(text="done")]),
                    TaskItem(state="TODO", content=[Text(text="todo")]),
                ]
            )
        )
        assert "- [x] done" in result
        assert "- [ ] todo" in result

    def test_block_task_item(self):
        result = _render(
            TaskList(
                content=[
                    BlockTaskItem(
                        state="TODO",
                        content=[
                            Paragraph(content=[Text(text="first")]),
                            Paragraph(content=[Text(text="second")]),
                        ],
                    ),
                ]
            )
        )
        assert "- [ ] first" in result
        assert "second" in result


# ── Inline Marks ───────────────────────────────────────────────────────────────


class TestMarks:
    def test_strong(self):
        result = _render(Paragraph(content=[Text(text="bold", marks=[StrongMark()])]))
        assert "**bold**" in result

    def test_em(self):
        result = _render(Paragraph(content=[Text(text="italic", marks=[EmMark()])]))
        assert "*italic*" in result

    def test_strike(self):
        result = _render(
            Paragraph(content=[Text(text="deleted", marks=[StrikeMark()])])
        )
        assert "~~deleted~~" in result

    def test_code(self):
        result = _render(Paragraph(content=[Text(text="x = 1", marks=[CodeMark()])]))
        assert "`x = 1`" in result

    def test_link(self):
        result = _render(
            Paragraph(
                content=[
                    Text(text="click", marks=[LinkMark(href="https://example.com")])
                ]
            )
        )
        assert "[click](https://example.com)" in result

    def test_link_with_title(self):
        result = _render(
            Paragraph(
                content=[
                    Text(
                        text="click",
                        marks=[LinkMark(href="https://example.com", title="Example")],
                    )
                ]
            )
        )
        assert '[click](https://example.com "Example")' in result

    def test_underline(self):
        result = _render(
            Paragraph(content=[Text(text="underlined", marks=[UnderlineMark()])])
        )
        assert '<u adf="underline">underlined</u>' in result

    def test_text_color(self):
        result = _render(
            Paragraph(
                content=[Text(text="red", marks=[TextColorMark(color="#ff0000")])]
            )
        )
        assert 'adf="textColor"' in result
        assert "#ff0000" in result

    def test_subsup(self):
        result = _render(
            Paragraph(content=[Text(text="2", marks=[SubSupMark(type="sup")])])
        )
        assert '<sup adf="subSup">2</sup>' in result

    def test_annotation(self):
        result = _render(
            Paragraph(
                content=[
                    Text(
                        text="annotated",
                        marks=[
                            AnnotationMark(id="ann-1", annotation_type="inlineComment")
                        ],
                    )
                ]
            )
        )
        assert '<mark adf="annotation"' in result
        assert "annotated" in result
        assert '"id":"ann-1"' in result

    def test_background_color(self):
        result = _render(
            Paragraph(
                content=[
                    Text(
                        text="highlighted", marks=[BackgroundColorMark(color="#ffff00")]
                    )
                ]
            )
        )
        assert 'adf="bgColor"' in result
        assert "#ffff00" in result

    def test_combined_strong_em(self):
        result = _render(
            Paragraph(content=[Text(text="both", marks=[StrongMark(), EmMark()])])
        )
        assert "***both***" in result

    def test_flanking_spaces(self):
        result = _render(
            Paragraph(content=[Text(text=" hello ", marks=[StrongMark()])])
        )
        assert " **hello** " in result

    def test_code_with_backticks(self):
        result = _render(Paragraph(content=[Text(text="a`b", marks=[CodeMark()])]))
        assert "`` a`b ``" in result or "``a`b``" in result


# ── Inline HTML Nodes ──────────────────────────────────────────────────────────


class TestInlineNodes:
    def test_mention(self):
        result = _render(Paragraph(content=[Mention(id="user-1", text="@John")]))
        assert 'adf="mention"' in result
        assert "@John" in result

    def test_mention_no_text(self):
        result = _render(Paragraph(content=[Mention(id="user-1")]))
        assert "@user-1" in result

    def test_emoji(self):
        result = _render(
            Paragraph(content=[Emoji(short_name=":smile:", id="1f604", text="😄")])
        )
        assert 'adf="emoji"' in result
        assert "😄" in result

    def test_date(self):
        result = _render(Paragraph(content=[Date(timestamp="1711324800000")]))
        assert 'adf="date"' in result
        assert 'datetime="1711324800000"' in result
        assert "2024-03-2" in result  # date varies by timezone offset

    def test_status(self):
        result = _render(Paragraph(content=[Status(text="IN PROGRESS", color="blue")]))
        assert 'adf="status"' in result
        assert "IN PROGRESS" in result

    def test_inline_card(self):
        result = _render(Paragraph(content=[InlineCard(url="https://example.com")]))
        assert 'adf="inlineCard"' in result
        assert 'href="https://example.com"' in result

    def test_placeholder(self):
        result = _render(Paragraph(content=[Placeholder(text="Type here")]))
        assert 'adf="placeholder"' in result
        assert "Type here" in result

    def test_hard_break(self):
        result = _render(
            Paragraph(content=[Text(text="line1"), HardBreak(), Text(text="line2")])
        )
        assert "line1\\\nline2" in result

    def test_media_inline(self):
        result = _render(
            Paragraph(
                content=[MediaInline(id="file-1", collection="uploads", type="file")]
            )
        )
        assert 'adf="mediaInline"' in result
        assert "📎" in result
        assert '"id":"file-1"' in result

    def test_media_inline_with_border_mark(self):
        result = _render(
            Paragraph(
                content=[
                    MediaInline(
                        id="file-1",
                        collection="uploads",
                        marks=[BorderMark(size=1, color="#c0c0c0")],
                    )
                ]
            )
        )
        assert '"borderSize":1' in result
        assert '"borderColor":"#c0c0c0"' in result

    def test_inline_extension(self):
        result = _render(
            Paragraph(
                content=[
                    InlineExtension(
                        extension_key="my-ext", extension_type="com.example"
                    )
                ]
            )
        )
        assert 'adf="inlineExtension"' in result
        assert "my-ext" in result


# ── HTML Fallback Blocks ───────────────────────────────────────────────────────


class TestPanel:
    def test_simple(self):
        result = _render(
            Panel(
                panel_type="info",
                content=[Paragraph(content=[Text(text="note")])],
            )
        )
        assert '<aside adf="panel"' in result
        assert '"panelType":"info"' in result
        assert "note" in result
        assert "</aside>" in result


class TestExpand:
    def test_with_title(self):
        result = _render(
            Expand(
                title="Details",
                content=[Paragraph(content=[Text(text="body")])],
            )
        )
        assert '<details adf="expand"' in result
        assert "<summary>Details</summary>" in result
        assert "body" in result

    def test_without_title(self):
        result = _render(Expand(content=[Paragraph(content=[Text(text="body")])]))
        assert "<summary>" not in result


class TestNestedExpand:
    def test_simple(self):
        result = _render(
            Table(
                content=[
                    TableRow(
                        content=[
                            TableHeader(
                                content=[
                                    NestedExpand(
                                        title="More",
                                        content=[
                                            Paragraph(content=[Text(text="hidden")])
                                        ],
                                    )
                                ]
                            ),
                        ]
                    ),
                    TableRow(
                        content=[
                            TableCell(content=[Paragraph(content=[Text(text="x")])])
                        ],
                    ),
                ]
            )
        )
        assert 'adf="nestedExpand"' in result
        assert "<summary>More</summary>" in result
        assert "hidden" in result


class TestDecisionList:
    def test_simple(self):
        result = _render(
            DecisionList(
                content=[
                    DecisionItem(state="DECIDED", content=[Text(text="yes")]),
                ]
            )
        )
        assert 'adf="decisionList"' in result
        assert 'adf="decisionItem"' in result
        assert "yes" in result


# ── Media ──────────────────────────────────────────────────────────────────────


class TestMediaSingle:
    def test_simple(self):
        result = _render(
            MediaSingle(
                layout="center",
                content=[
                    Media(type="file", id="abc-123", collection="uploads"),
                ],
            )
        )
        assert "<figure" in result
        assert 'adf="mediaSingle"' in result
        assert 'adf="media"' in result
        assert "📎" in result

    def test_with_caption(self):
        result = _render(
            MediaSingle(
                content=[
                    Media(type="file", id="abc"),
                    Caption(content=[Text(text="My caption")]),
                ],
            )
        )
        assert '<figcaption adf="caption">My caption</figcaption>' in result

    def test_media_with_border_mark(self):
        result = _render(
            MediaSingle(
                content=[
                    Media(
                        type="file",
                        id="abc",
                        marks=[BorderMark(size=2, color="#000")],
                    ),
                ],
            )
        )
        assert '"borderSize":2' in result
        assert '"borderColor":"#000"' in result


class TestMediaGroup:
    def test_simple(self):
        result = _render(
            MediaGroup(
                content=[
                    Media(type="file", id="a"),
                    Media(type="file", id="b"),
                ]
            )
        )
        assert 'adf="mediaGroup"' in result
        assert result.count('adf="media"') == 2


# ── Cards ──────────────────────────────────────────────────────────────────────


class TestBlockCard:
    def test_simple(self):
        result = _render(BlockCard(url="https://example.com"))
        assert 'adf="blockCard"' in result
        assert '"url":"https://example.com"' in result


class TestEmbedCard:
    def test_simple(self):
        result = _render(EmbedCard(url="https://example.com", layout="wide"))
        assert 'adf="embedCard"' in result
        assert '"layout":"wide"' in result


# ── Extension ──────────────────────────────────────────────────────────────────


class TestExtension:
    def test_simple(self):
        result = _render(
            Extension(extension_key="my-ext", extension_type="com.example")
        )
        assert 'adf="extension"' in result
        assert "my-ext" in result


class TestBodiedExtension:
    def test_simple(self):
        result = _render(
            BodiedExtension(
                extension_key="my-macro",
                extension_type="com.example",
                content=[Paragraph(content=[Text(text="body")])],
            )
        )
        assert 'adf="bodiedExtension"' in result
        assert '"extensionKey":"my-macro"' in result
        assert "content" in result


class TestSyncBlock:
    def test_simple(self):
        result = _render(SyncBlock(resource_id="res-1"))
        assert 'adf="syncBlock"' in result
        assert "res-1" in result


# ── Layout ─────────────────────────────────────────────────────────────────────


class TestLayoutSection:
    def test_two_columns(self):
        result = _render(
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
        assert 'adf="layoutSection"' in result
        assert 'adf="layoutColumn"' in result
        assert "left" in result
        assert "right" in result


# ── Table ──────────────────────────────────────────────────────────────────────


class TestTable:
    def test_simple_header_row(self):
        result = _render(
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
        assert "| A | B |" in result
        assert "| --- | --- |" in result
        assert "| 1 | 2 |" in result
        assert "<data" not in result  # no metadata for default

    def test_no_header(self):
        result = _render(
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
        assert '<div adf="table"' in result
        assert '"header":"none"' in result

    def test_cell_metadata(self):
        result = _render(
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
        assert '<div adf="cell"' in result
        assert '"colspan":2' in result

    def test_cell_bare_text(self):
        """Single Paragraph cell renders as bare text, not <p>."""
        result = _render(
            Table(
                content=[
                    TableRow(
                        content=[
                            TableHeader(content=[Paragraph(content=[Text(text="hi")])]),
                        ]
                    ),
                    TableRow(
                        content=[
                            TableCell(content=[Paragraph(content=[Text(text="val")])]),
                        ]
                    ),
                ]
            )
        )
        assert "| hi |" in result
        assert "<p>" not in result

    def test_cell_multi_block(self):
        """Multiple blocks in cell use HTML tags."""
        result = _render(
            Table(
                content=[
                    TableRow(
                        content=[
                            TableHeader(content=[Paragraph(content=[Text(text="h")])]),
                        ]
                    ),
                    TableRow(
                        content=[
                            TableCell(
                                content=[
                                    Paragraph(content=[Text(text="first")]),
                                    Paragraph(content=[Text(text="second")]),
                                ]
                            ),
                        ]
                    ),
                ]
            )
        )
        assert "<p>" in result

    def test_pipe_escape(self):
        result = _render(
            Table(
                content=[
                    TableRow(
                        content=[
                            TableHeader(
                                content=[Paragraph(content=[Text(text="a|b")])]
                            ),
                        ]
                    ),
                    TableRow(
                        content=[
                            TableCell(content=[Paragraph(content=[Text(text="c")])]),
                        ]
                    ),
                ]
            )
        )
        assert "a\\|b" in result


# ── MD Escape ──────────────────────────────────────────────────────────────────


class TestEscape:
    def test_special_chars(self):
        result = _render(
            Paragraph(content=[Text(text=r"hello *world* [link] `code` \backslash")])
        )
        assert "\\*world\\*" in result
        assert "\\[link\\]" in result
        assert "\\`code\\`" in result
        assert "\\\\backslash" in result


# ── Params Escape ──────────────────────────────────────────────────────────────


class TestParamsEscape:
    def test_ampersand_in_params(self):
        result = _render(
            Paragraph(
                content=[
                    Emoji(short_name=":a&b:", id="e1"),
                ]
            )
        )
        assert "&amp;" in result

    def test_single_quote_in_params(self):
        result = _render(
            Panel(
                panel_type="info",
                panel_icon="it's",
                content=[Paragraph(content=[Text(text="x")])],
            )
        )
        assert "&#39;" in result


# ── Plain mode ───────────────────────────────────────────────────────────────


def _render_plain(node: DocContent) -> str:
    return render(Doc(content=[node]), plain=True)


class TestPlainMode:
    def test_adf_params_stripped(self):
        result = _render_plain(Paragraph(content=[Mention(id="u1", text="@John")]))
        assert "adf=" not in result
        assert "params=" not in result

    def test_span_stripped(self):
        result = _render_plain(Paragraph(content=[Mention(id="u1", text="@John")]))
        assert "<span" not in result
        assert "@John" in result

    def test_time_stripped(self):
        result = _render_plain(Paragraph(content=[Date(timestamp="1700000000000")]))
        assert "<time" not in result
        assert "2023-11-14" in result

    def test_mark_stripped(self):
        result = _render_plain(
            Paragraph(content=[Text(text="noted", marks=[AnnotationMark(id="a1")])])
        )
        assert "<mark" not in result
        assert "noted" in result

    def test_div_stripped(self):
        result = _render_plain(BlockCard(url="https://example.com"))
        assert "<div" not in result
        assert "https://example.com" in result

    def test_section_stripped(self):
        result = _render_plain(
            LayoutSection(
                content=[
                    LayoutColumn(
                        width=50, content=[Paragraph(content=[Text(text="col")])]
                    ),
                ]
            )
        )
        assert "<section" not in result
        assert "col" in result

    def test_metadata_div_skipped(self):
        result = _render_plain(
            Paragraph(
                content=[Text(text="text")],
                marks=[AlignmentMark(align="center")],
            )
        )
        assert "<div" not in result

    def test_u_kept(self):
        result = _render_plain(
            Paragraph(content=[Text(text="underline", marks=[UnderlineMark()])])
        )
        assert "<u>" in result

    def test_sub_sup_kept(self):
        result = _render_plain(
            Paragraph(content=[Text(text="2", marks=[SubSupMark(type="sub")])])
        )
        assert "<sub>" in result

    def test_a_kept(self):
        result = _render_plain(
            Paragraph(content=[InlineCard(url="https://example.com")])
        )
        assert "<a" in result
        assert "https://example.com" in result

    def test_aside_kept(self):
        result = _render_plain(
            Panel(panel_type="info", content=[Paragraph(content=[Text(text="note")])])
        )
        assert "<aside>" in result

    def test_details_kept(self):
        result = _render_plain(
            Expand(title="Title", content=[Paragraph(content=[Text(text="body")])])
        )
        assert "<details>" in result
        assert "<summary>" in result

    def test_figure_kept(self):
        result = _render_plain(
            MediaSingle(content=[Media(type="file", id="abc", collection="c")])
        )
        assert "<figure>" in result

    def test_native_md_unchanged(self):
        result = _render_plain(
            Paragraph(content=[Text(text="bold", marks=[StrongMark()])])
        )
        assert "**bold**" in result

    def test_table_no_metadata(self):
        result = _render_plain(
            Table(
                layout="wide",
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
                ],
            )
        )
        assert "<div" not in result
        assert "| H |" in result
