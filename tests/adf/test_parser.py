"""ADF parser tests — ADF JSON → AST."""

from __future__ import annotations

from typing import Any

from marklas.adf.parser import parse
from marklas.ast import (
    AlignmentMark,
    AnnotationMark,
    BackgroundColorMark,
    BlockCard,
    BlockTaskItem,
    Blockquote,
    BodiedExtension,
    BodiedSyncBlock,
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
    Emoji,
    EmMark,
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


def _p(content: list[dict[str, Any]]) -> Doc:
    """Parse a doc with given content."""
    return parse({"type": "doc", "version": 1, "content": content})


def _p1(content: list[dict[str, Any]]) -> object:
    """Parse and return first content node."""
    return _p(content).content[0]


# ── Marks ────────────────────────────────────────────────────────────────────


class TestMarks:
    def test_strong(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "b", "marks": [{"type": "strong"}]}
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        text = node.content[0]
        assert isinstance(text, Text)
        assert text.marks == [StrongMark()]

    def test_em(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "i", "marks": [{"type": "em"}]}
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        text = node.content[0]
        assert isinstance(text, Text)
        assert text.marks == [EmMark()]

    def test_strike(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "s", "marks": [{"type": "strike"}]}
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        text = node.content[0]
        assert isinstance(text, Text)
        assert text.marks == [StrikeMark()]

    def test_code(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "c", "marks": [{"type": "code"}]}
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        text = node.content[0]
        assert isinstance(text, Text)
        assert text.marks == [CodeMark()]

    def test_underline(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "u", "marks": [{"type": "underline"}]}
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        text = node.content[0]
        assert isinstance(text, Text)
        assert text.marks == [UnderlineMark()]

    def test_link(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "link",
                            "marks": [
                                {
                                    "type": "link",
                                    "attrs": {
                                        "href": "https://example.com",
                                        "title": "t",
                                    },
                                }
                            ],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        text = node.content[0]
        assert isinstance(text, Text)
        assert text.marks == [LinkMark(href="https://example.com", title="t")]

    def test_text_color(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "r",
                            "marks": [
                                {"type": "textColor", "attrs": {"color": "#f00"}}
                            ],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        text = node.content[0]
        assert isinstance(text, Text)
        assert text.marks == [TextColorMark(color="#f00")]

    def test_background_color(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "bg",
                            "marks": [
                                {"type": "backgroundColor", "attrs": {"color": "#0f0"}}
                            ],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        text = node.content[0]
        assert isinstance(text, Text)
        assert text.marks == [BackgroundColorMark(color="#0f0")]

    def test_subsup(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "2",
                            "marks": [{"type": "subsup", "attrs": {"type": "sup"}}],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        text = node.content[0]
        assert isinstance(text, Text)
        assert text.marks == [SubSupMark(type="sup")]

    def test_annotation(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "x",
                            "marks": [
                                {
                                    "type": "annotation",
                                    "attrs": {
                                        "id": "a1",
                                        "annotationType": "inlineComment",
                                    },
                                }
                            ],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        text = node.content[0]
        assert isinstance(text, Text)
        assert text.marks == [AnnotationMark(id="a1", annotation_type="inlineComment")]

    def test_multiple_marks(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "x",
                            "marks": [
                                {"type": "strong"},
                                {"type": "em"},
                                {"type": "link", "attrs": {"href": "u"}},
                            ],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        text = node.content[0]
        assert isinstance(text, Text)
        assert len(text.marks) == 3

    def test_alignment_mark(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "c"}],
                    "marks": [{"type": "alignment", "attrs": {"align": "center"}}],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        assert node.marks == [AlignmentMark(align="center")]

    def test_indentation_mark(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "i"}],
                    "marks": [{"type": "indentation", "attrs": {"level": 2}}],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        assert node.marks == [IndentationMark(level=2)]

    def test_breakout_mark(self):
        node = _p1(
            [
                {
                    "type": "codeBlock",
                    "content": [{"type": "text", "text": "x"}],
                    "marks": [{"type": "breakout", "attrs": {"mode": "wide"}}],
                }
            ]
        )
        assert isinstance(node, CodeBlock)
        assert node.marks == [BreakoutMark(mode="wide")]

    def test_data_consumer_mark(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "x"}],
                    "marks": [{"type": "dataConsumer", "attrs": {"sources": ["s1"]}}],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        assert node.marks == [DataConsumerMark(sources=["s1"])]

    def test_border_mark(self):
        node = _p1(
            [
                {
                    "type": "mediaSingle",
                    "content": [
                        {
                            "type": "media",
                            "attrs": {"type": "file", "id": "m1", "collection": "c"},
                            "marks": [
                                {"type": "border", "attrs": {"size": 1, "color": "#c0"}}
                            ],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, MediaSingle)
        media = node.content[0]
        assert isinstance(media, Media)
        assert media.marks == [BorderMark(size=1, color="#c0")]


# ── Block nodes ──────────────────────────────────────────────────────────────


class TestBlocks:
    def test_paragraph(self):
        node = _p1(
            [{"type": "paragraph", "content": [{"type": "text", "text": "hello"}]}]
        )
        assert isinstance(node, Paragraph)
        text = node.content[0]
        assert isinstance(text, Text)
        assert text.text == "hello"

    def test_paragraph_empty(self):
        node = _p1([{"type": "paragraph"}])
        assert isinstance(node, Paragraph)
        assert len(node.content) == 0

    def test_heading(self):
        node = _p1(
            [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "title"}],
                }
            ]
        )
        assert isinstance(node, Heading)
        assert node.level == 2

    def test_code_block(self):
        node = _p1(
            [
                {
                    "type": "codeBlock",
                    "attrs": {"language": "python"},
                    "content": [{"type": "text", "text": "x = 1"}],
                }
            ]
        )
        assert isinstance(node, CodeBlock)
        assert node.language == "python"
        assert node.content[0].text == "x = 1"

    def test_code_block_no_language(self):
        node = _p1(
            [{"type": "codeBlock", "content": [{"type": "text", "text": "code"}]}]
        )
        assert isinstance(node, CodeBlock)
        assert node.language is None

    def test_blockquote(self):
        node = _p1(
            [
                {
                    "type": "blockquote",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "q"}],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Blockquote)
        assert isinstance(node.content[0], Paragraph)

    def test_bullet_list(self):
        node = _p1(
            [
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "item"}],
                                }
                            ],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, BulletList)
        assert isinstance(node.content[0], ListItem)

    def test_ordered_list(self):
        node = _p1(
            [
                {
                    "type": "orderedList",
                    "attrs": {"order": 3},
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "item"}],
                                }
                            ],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, OrderedList)
        assert node.order == 3

    def test_rule(self):
        node = _p1([{"type": "rule"}])
        assert isinstance(node, Rule)

    def test_panel(self):
        node = _p1(
            [
                {
                    "type": "panel",
                    "attrs": {"panelType": "info", "panelColor": "#eef"},
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "note"}],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Panel)
        assert node.panel_type == "info"
        assert node.panel_color == "#eef"

    def test_expand(self):
        node = _p1(
            [
                {
                    "type": "expand",
                    "attrs": {"title": "Details"},
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "body"}],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Expand)
        assert node.title == "Details"

    def test_nested_expand(self):
        node = _p1(
            [
                {
                    "type": "expand",
                    "content": [
                        {
                            "type": "nestedExpand",
                            "attrs": {"title": "Inner"},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "n"}],
                                }
                            ],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Expand)
        inner = node.content[0]
        assert isinstance(inner, NestedExpand)
        assert inner.title == "Inner"


# ── Media ────────────────────────────────────────────────────────────────────


class TestMedia:
    def test_media_single(self):
        node = _p1(
            [
                {
                    "type": "mediaSingle",
                    "attrs": {"layout": "center", "width": 600},
                    "content": [
                        {
                            "type": "media",
                            "attrs": {
                                "type": "file",
                                "id": "abc",
                                "collection": "uploads",
                            },
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, MediaSingle)
        assert node.layout == "center"
        media = node.content[0]
        assert isinstance(media, Media)
        assert media.id == "abc"

    def test_media_single_with_caption(self):
        node = _p1(
            [
                {
                    "type": "mediaSingle",
                    "content": [
                        {
                            "type": "media",
                            "attrs": {"type": "file", "id": "abc", "collection": "c"},
                        },
                        {
                            "type": "caption",
                            "content": [{"type": "text", "text": "cap"}],
                        },
                    ],
                }
            ]
        )
        assert isinstance(node, MediaSingle)
        caption = node.content[1]
        assert isinstance(caption, Caption)
        first = caption.content[0]
        assert isinstance(first, Text)
        assert first.text == "cap"

    def test_media_group(self):
        node = _p1(
            [
                {
                    "type": "mediaGroup",
                    "content": [
                        {
                            "type": "media",
                            "attrs": {"type": "file", "id": "a", "collection": "c"},
                        },
                        {
                            "type": "media",
                            "attrs": {"type": "file", "id": "b", "collection": "c"},
                        },
                    ],
                }
            ]
        )
        assert isinstance(node, MediaGroup)
        assert len(node.content) == 2


# ── Cards ────────────────────────────────────────────────────────────────────


class TestCards:
    def test_block_card(self):
        node = _p1([{"type": "blockCard", "attrs": {"url": "https://example.com"}}])
        assert isinstance(node, BlockCard)
        assert node.url == "https://example.com"

    def test_embed_card(self):
        node = _p1(
            [
                {
                    "type": "embedCard",
                    "attrs": {"url": "https://yt.com", "layout": "wide"},
                }
            ]
        )
        assert isinstance(node, EmbedCard)
        assert node.url == "https://yt.com"
        assert node.layout == "wide"

    def test_inline_card(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "inlineCard", "attrs": {"url": "https://example.com"}}
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        card = node.content[0]
        assert isinstance(card, InlineCard)
        assert card.url == "https://example.com"


# ── TaskList / DecisionList ──────────────────────────────────────────────────


class TestTaskDecision:
    def test_task_list(self):
        node = _p1(
            [
                {
                    "type": "taskList",
                    "attrs": {"localId": "tl1"},
                    "content": [
                        {
                            "type": "taskItem",
                            "attrs": {"localId": "t1", "state": "TODO"},
                            "content": [{"type": "text", "text": "todo"}],
                        },
                        {
                            "type": "taskItem",
                            "attrs": {"localId": "t2", "state": "DONE"},
                            "content": [{"type": "text", "text": "done"}],
                        },
                    ],
                }
            ]
        )
        assert isinstance(node, TaskList)
        item0 = node.content[0]
        assert isinstance(item0, TaskItem)
        assert item0.state == "TODO"
        item1 = node.content[1]
        assert isinstance(item1, TaskItem)
        assert item1.state == "DONE"

    def test_block_task_item(self):
        node = _p1(
            [
                {
                    "type": "taskList",
                    "attrs": {"localId": "tl1"},
                    "content": [
                        {
                            "type": "blockTaskItem",
                            "attrs": {"localId": "bt1", "state": "TODO"},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "first"}],
                                },
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "second"}],
                                },
                            ],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, TaskList)
        item = node.content[0]
        assert isinstance(item, BlockTaskItem)
        assert len(item.content) == 2

    def test_decision_list(self):
        node = _p1(
            [
                {
                    "type": "decisionList",
                    "attrs": {"localId": "dl1"},
                    "content": [
                        {
                            "type": "decisionItem",
                            "attrs": {"localId": "d1", "state": "DECIDED"},
                            "content": [{"type": "text", "text": "yes"}],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, DecisionList)
        item = node.content[0]
        assert isinstance(item, DecisionItem)
        assert item.state == "DECIDED"


# ── Layout ───────────────────────────────────────────────────────────────────


class TestLayout:
    def test_layout_section(self):
        node = _p1(
            [
                {
                    "type": "layoutSection",
                    "content": [
                        {
                            "type": "layoutColumn",
                            "attrs": {"width": 50},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "left"}],
                                }
                            ],
                        },
                        {
                            "type": "layoutColumn",
                            "attrs": {"width": 50},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "right"}],
                                }
                            ],
                        },
                    ],
                }
            ]
        )
        assert isinstance(node, LayoutSection)
        assert len(node.content) == 2
        col = node.content[0]
        assert isinstance(col, LayoutColumn)
        assert col.width == 50


# ── Table ────────────────────────────────────────────────────────────────────


class TestTable:
    def test_simple_table(self):
        node = _p1(
            [
                {
                    "type": "table",
                    "content": [
                        {
                            "type": "tableRow",
                            "content": [
                                {
                                    "type": "tableHeader",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [{"type": "text", "text": "H"}],
                                        }
                                    ],
                                },
                            ],
                        },
                        {
                            "type": "tableRow",
                            "content": [
                                {
                                    "type": "tableCell",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [{"type": "text", "text": "D"}],
                                        }
                                    ],
                                },
                            ],
                        },
                    ],
                }
            ]
        )
        assert isinstance(node, Table)
        row0 = node.content[0]
        assert isinstance(row0, TableRow)
        assert isinstance(row0.content[0], TableHeader)
        row1 = node.content[1]
        assert isinstance(row1, TableRow)
        assert isinstance(row1.content[0], TableCell)

    def test_cell_attrs(self):
        node = _p1(
            [
                {
                    "type": "table",
                    "content": [
                        {
                            "type": "tableRow",
                            "content": [
                                {
                                    "type": "tableCell",
                                    "attrs": {"colspan": 2, "background": "#ff0"},
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [{"type": "text", "text": "x"}],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Table)
        cell = node.content[0].content[0]
        assert isinstance(cell, TableCell)
        assert cell.colspan == 2
        assert cell.background == "#ff0"

    def test_table_attrs(self):
        node = _p1(
            [
                {
                    "type": "table",
                    "attrs": {"layout": "wide"},
                    "content": [
                        {
                            "type": "tableRow",
                            "content": [
                                {
                                    "type": "tableCell",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [{"type": "text", "text": "x"}],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Table)
        assert node.layout == "wide"


# ── Extension / SyncBlock ────────────────────────────────────────────────────


class TestExtension:
    def test_extension(self):
        node = _p1(
            [
                {
                    "type": "extension",
                    "attrs": {
                        "extensionKey": "macro",
                        "extensionType": "com.atlassian",
                        "parameters": {"k": "v"},
                    },
                }
            ]
        )
        assert isinstance(node, Extension)
        assert node.extension_key == "macro"
        assert node.parameters == {"k": "v"}

    def test_bodied_extension(self):
        node = _p1(
            [
                {
                    "type": "bodiedExtension",
                    "attrs": {
                        "extensionKey": "macro",
                        "extensionType": "com.atlassian",
                    },
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "body"}],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, BodiedExtension)
        assert isinstance(node.content[0], Paragraph)

    def test_sync_block(self):
        node = _p1([{"type": "syncBlock", "attrs": {"resourceId": "r1"}}])
        assert isinstance(node, SyncBlock)
        assert node.resource_id == "r1"

    def test_bodied_sync_block(self):
        node = _p1(
            [
                {
                    "type": "bodiedSyncBlock",
                    "attrs": {"resourceId": "r1"},
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "sync"}],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, BodiedSyncBlock)
        assert isinstance(node.content[0], Paragraph)


# ── Inline nodes ─────────────────────────────────────────────────────────────


class TestInlines:
    def test_text(self):
        node = _p1(
            [{"type": "paragraph", "content": [{"type": "text", "text": "hello"}]}]
        )
        assert isinstance(node, Paragraph)
        text = node.content[0]
        assert isinstance(text, Text)
        assert text.text == "hello"

    def test_hard_break(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "a"},
                        {"type": "hardBreak"},
                        {"type": "text", "text": "b"},
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        assert isinstance(node.content[1], HardBreak)

    def test_mention(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "mention",
                            "attrs": {
                                "id": "u1",
                                "text": "@John",
                                "userType": "DEFAULT",
                            },
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        m = node.content[0]
        assert isinstance(m, Mention)
        assert m.id == "u1"
        assert m.text == "@John"
        assert m.user_type == "DEFAULT"

    def test_emoji(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "emoji",
                            "attrs": {
                                "shortName": ":smile:",
                                "id": "1f604",
                                "text": "😄",
                            },
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        e = node.content[0]
        assert isinstance(e, Emoji)
        assert e.short_name == ":smile:"
        assert e.text == "😄"

    def test_emoji_surrogate_pair(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "emoji",
                            "attrs": {
                                "shortName": ":calendar_spiral:",
                                "id": "1f5d3",
                                "text": "\\uD83D\\uDDD3",
                            },
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        e = node.content[0]
        assert isinstance(e, Emoji)
        assert e.text == "🗓"

    def test_date(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "date", "attrs": {"timestamp": "1700000000000"}}
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        d = node.content[0]
        assert isinstance(d, Date)
        assert d.timestamp == "1700000000000"

    def test_status(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "status", "attrs": {"text": "DONE", "color": "green"}}
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        s = node.content[0]
        assert isinstance(s, Status)
        assert s.text == "DONE"
        assert s.color == "green"

    def test_placeholder(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "placeholder", "attrs": {"text": "Enter name"}}
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        p = node.content[0]
        assert isinstance(p, Placeholder)
        assert p.text == "Enter name"

    def test_media_inline(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "mediaInline",
                            "attrs": {
                                "id": "f1",
                                "collection": "uploads",
                                "type": "file",
                            },
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        mi = node.content[0]
        assert isinstance(mi, MediaInline)
        assert mi.id == "f1"

    def test_inline_extension(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "inlineExtension",
                            "attrs": {
                                "extensionKey": "macro",
                                "extensionType": "com.atlassian",
                            },
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        ie = node.content[0]
        assert isinstance(ie, InlineExtension)
        assert ie.extension_key == "macro"


# ── Lossy fields dropped ─────────────────────────────────────────────────────


class TestLossyFields:
    def test_local_id_dropped(self):
        """localId should not appear on any parsed AST node."""
        node = _p1(
            [
                {
                    "type": "taskList",
                    "attrs": {"localId": "tl1"},
                    "content": [
                        {
                            "type": "taskItem",
                            "attrs": {"localId": "t1", "state": "TODO"},
                            "content": [{"type": "text", "text": "x"}],
                        }
                    ],
                }
            ]
        )
        assert isinstance(node, TaskList)
        assert not hasattr(node, "local_id")
        item = node.content[0]
        assert isinstance(item, TaskItem)
        assert not hasattr(item, "local_id")

    def test_hard_break_text_dropped(self):
        node = _p1(
            [
                {
                    "type": "paragraph",
                    "content": [{"type": "hardBreak", "attrs": {"text": "\n"}}],
                }
            ]
        )
        assert isinstance(node, Paragraph)
        hb = node.content[0]
        assert isinstance(hb, HardBreak)
        assert not hasattr(hb, "text")
