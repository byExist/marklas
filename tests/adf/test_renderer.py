"""ADF renderer tests — AST → ADF JSON."""

from __future__ import annotations

from typing import Any

from marklas.adf.renderer import render
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
    Mark,
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


def _r(doc: Doc) -> list[dict[str, Any]]:
    """Render and return content array."""
    return render(doc)["content"]


def _r1(doc: Doc) -> dict[str, Any]:
    """Render and return first content node."""
    return _r(doc)[0]


# ── Marks ────────────────────────────────────────────────────────────────────


class TestMarks:
    def test_strong(self):
        result = _r1(
            Doc(content=[Paragraph(content=[Text(text="b", marks=[StrongMark()])])])
        )
        text = result["content"][0]
        assert text["marks"] == [{"type": "strong"}]

    def test_em(self):
        result = _r1(
            Doc(content=[Paragraph(content=[Text(text="i", marks=[EmMark()])])])
        )
        assert result["content"][0]["marks"] == [{"type": "em"}]

    def test_strike(self):
        result = _r1(
            Doc(content=[Paragraph(content=[Text(text="s", marks=[StrikeMark()])])])
        )
        assert result["content"][0]["marks"] == [{"type": "strike"}]

    def test_code(self):
        result = _r1(
            Doc(content=[Paragraph(content=[Text(text="c", marks=[CodeMark()])])])
        )
        assert result["content"][0]["marks"] == [{"type": "code"}]

    def test_underline(self):
        result = _r1(
            Doc(content=[Paragraph(content=[Text(text="u", marks=[UnderlineMark()])])])
        )
        assert result["content"][0]["marks"] == [{"type": "underline"}]

    def test_link(self):
        mark = LinkMark(href="https://example.com", title="t")
        result = _r1(
            Doc(content=[Paragraph(content=[Text(text="link", marks=[mark])])])
        )
        assert result["content"][0]["marks"] == [
            {"type": "link", "attrs": {"href": "https://example.com", "title": "t"}}
        ]

    def test_link_no_title(self):
        mark = LinkMark(href="https://example.com")
        result = _r1(
            Doc(content=[Paragraph(content=[Text(text="link", marks=[mark])])])
        )
        assert result["content"][0]["marks"] == [
            {"type": "link", "attrs": {"href": "https://example.com"}}
        ]

    def test_text_color(self):
        result = _r1(
            Doc(
                content=[
                    Paragraph(
                        content=[Text(text="r", marks=[TextColorMark(color="#f00")])]
                    )
                ]
            )
        )
        assert result["content"][0]["marks"] == [
            {"type": "textColor", "attrs": {"color": "#f00"}}
        ]

    def test_background_color(self):
        result = _r1(
            Doc(
                content=[
                    Paragraph(
                        content=[
                            Text(text="bg", marks=[BackgroundColorMark(color="#0f0")])
                        ]
                    )
                ]
            )
        )
        assert result["content"][0]["marks"] == [
            {"type": "backgroundColor", "attrs": {"color": "#0f0"}}
        ]

    def test_subsup(self):
        result = _r1(
            Doc(
                content=[
                    Paragraph(content=[Text(text="2", marks=[SubSupMark(type="sup")])])
                ]
            )
        )
        assert result["content"][0]["marks"] == [
            {"type": "subsup", "attrs": {"type": "sup"}}
        ]

    def test_annotation(self):
        mark = AnnotationMark(id="a1", annotation_type="inlineComment")
        result = _r1(Doc(content=[Paragraph(content=[Text(text="x", marks=[mark])])]))
        assert result["content"][0]["marks"] == [
            {
                "type": "annotation",
                "attrs": {"id": "a1", "annotationType": "inlineComment"},
            }
        ]

    def test_multiple_marks_preserve_order(self):
        marks: list[Mark] = [
            StrongMark(),
            EmMark(),
            LinkMark(href="u"),
        ]
        result = _r1(Doc(content=[Paragraph(content=[Text(text="x", marks=marks)])]))
        types = [m["type"] for m in result["content"][0]["marks"]]
        assert types == ["strong", "em", "link"]

    def test_alignment_mark(self):
        result = _r1(
            Doc(
                content=[
                    Paragraph(
                        content=[Text(text="c")], marks=[AlignmentMark(align="center")]
                    )
                ]
            )
        )
        assert result["marks"] == [{"type": "alignment", "attrs": {"align": "center"}}]

    def test_indentation_mark(self):
        result = _r1(
            Doc(
                content=[
                    Paragraph(
                        content=[Text(text="i")], marks=[IndentationMark(level=2)]
                    )
                ]
            )
        )
        assert result["marks"] == [{"type": "indentation", "attrs": {"level": 2}}]

    def test_breakout_mark(self):
        result = _r1(
            Doc(
                content=[
                    CodeBlock(
                        content=[Text(text="x")], marks=[BreakoutMark(mode="wide")]
                    )
                ]
            )
        )
        assert result["marks"] == [{"type": "breakout", "attrs": {"mode": "wide"}}]

    def test_data_consumer_mark(self):
        result = _r1(
            Doc(
                content=[
                    Paragraph(
                        content=[Text(text="x")],
                        marks=[DataConsumerMark(sources=["s1"])],
                    )
                ]
            )
        )
        assert result["marks"] == [
            {"type": "dataConsumer", "attrs": {"sources": ["s1"]}}
        ]

    def test_border_mark(self):
        media = Media(
            type="file",
            id="m1",
            collection="c",
            marks=[BorderMark(size=1, color="#c0")],
        )
        result = render(Doc(content=[MediaSingle(content=[media])]))["content"][0][
            "content"
        ][0]
        assert result["marks"] == [
            {"type": "border", "attrs": {"size": 1, "color": "#c0"}}
        ]


# ── Block nodes ──────────────────────────────────────────────────────────────


class TestBlocks:
    def test_paragraph(self):
        result = _r1(Doc(content=[Paragraph(content=[Text(text="hello")])]))
        assert result == {
            "type": "paragraph",
            "content": [{"type": "text", "text": "hello"}],
        }

    def test_paragraph_empty(self):
        result = _r1(Doc(content=[Paragraph()]))
        assert result == {"type": "paragraph"}

    def test_heading(self):
        result = _r1(Doc(content=[Heading(level=2, content=[Text(text="title")])]))
        assert result["type"] == "heading"
        assert result["attrs"] == {"level": 2}

    def test_code_block(self):
        result = _r1(
            Doc(content=[CodeBlock(language="python", content=[Text(text="x = 1")])])
        )
        assert result["type"] == "codeBlock"
        assert result["attrs"] == {"language": "python"}
        assert result["content"] == [{"type": "text", "text": "x = 1"}]

    def test_code_block_no_language(self):
        result = _r1(Doc(content=[CodeBlock(content=[Text(text="code")])]))
        assert "attrs" not in result

    def test_blockquote(self):
        result = _r1(
            Doc(content=[Blockquote(content=[Paragraph(content=[Text(text="quote")])])])
        )
        assert result["type"] == "blockquote"
        assert result["content"][0]["type"] == "paragraph"

    def test_bullet_list(self):
        result = _r1(
            Doc(
                content=[
                    BulletList(
                        content=[
                            ListItem(content=[Paragraph(content=[Text(text="item")])])
                        ]
                    )
                ]
            )
        )
        assert result["type"] == "bulletList"
        assert result["content"][0]["type"] == "listItem"

    def test_ordered_list(self):
        result = _r1(
            Doc(
                content=[
                    OrderedList(
                        content=[
                            ListItem(content=[Paragraph(content=[Text(text="item")])])
                        ],
                        order=3,
                    )
                ]
            )
        )
        assert result["type"] == "orderedList"
        assert result["attrs"] == {"order": 3}

    def test_ordered_list_no_order(self):
        result = _r1(
            Doc(
                content=[
                    OrderedList(
                        content=[
                            ListItem(content=[Paragraph(content=[Text(text="item")])])
                        ]
                    )
                ]
            )
        )
        assert "attrs" not in result

    def test_rule(self):
        result = _r1(Doc(content=[Rule()]))
        assert result == {"type": "rule"}

    def test_panel(self):
        result = _r1(
            Doc(
                content=[
                    Panel(
                        panel_type="info",
                        content=[Paragraph(content=[Text(text="note")])],
                        panel_color="#eef",
                    )
                ]
            )
        )
        assert result["type"] == "panel"
        assert result["attrs"]["panelType"] == "info"
        assert result["attrs"]["panelColor"] == "#eef"

    def test_expand(self):
        result = _r1(
            Doc(
                content=[
                    Expand(
                        title="Details",
                        content=[Paragraph(content=[Text(text="body")])],
                    )
                ]
            )
        )
        assert result["type"] == "expand"
        assert result["attrs"] == {"title": "Details"}

    def test_nested_expand(self):
        result = _r1(
            Doc(
                content=[
                    Expand(
                        content=[
                            NestedExpand(
                                title="Inner",
                                content=[Paragraph(content=[Text(text="nested")])],
                            )
                        ]
                    )
                ]
            )
        )
        inner = result["content"][0]
        assert inner["type"] == "nestedExpand"
        assert inner["attrs"] == {"title": "Inner"}


# ── Media ────────────────────────────────────────────────────────────────────


class TestMedia:
    def test_media_single(self):
        result = _r1(
            Doc(
                content=[
                    MediaSingle(
                        layout="center",
                        width=600,
                        content=[Media(type="file", id="abc", collection="uploads")],
                    )
                ]
            )
        )
        assert result["type"] == "mediaSingle"
        assert result["attrs"]["layout"] == "center"
        media = result["content"][0]
        assert media["attrs"]["id"] == "abc"

    def test_media_single_with_caption(self):
        result = _r1(
            Doc(
                content=[
                    MediaSingle(
                        content=[
                            Media(type="file", id="abc", collection="uploads"),
                            Caption(content=[Text(text="caption text")]),
                        ]
                    )
                ]
            )
        )
        assert result["content"][1]["type"] == "caption"
        assert result["content"][1]["content"][0]["text"] == "caption text"

    def test_media_group(self):
        result = _r1(
            Doc(
                content=[
                    MediaGroup(
                        content=[
                            Media(type="file", id="a", collection="c"),
                            Media(type="file", id="b", collection="c"),
                        ]
                    )
                ]
            )
        )
        assert result["type"] == "mediaGroup"
        assert len(result["content"]) == 2


# ── Cards ────────────────────────────────────────────────────────────────────


class TestCards:
    def test_block_card(self):
        result = _r1(Doc(content=[BlockCard(url="https://example.com")]))
        assert result["type"] == "blockCard"
        assert result["attrs"]["url"] == "https://example.com"

    def test_embed_card(self):
        result = _r1(Doc(content=[EmbedCard(url="https://yt.com", layout="wide")]))
        assert result["type"] == "embedCard"
        assert result["attrs"]["url"] == "https://yt.com"
        assert result["attrs"]["layout"] == "wide"

    def test_inline_card(self):
        result = _r1(
            Doc(content=[Paragraph(content=[InlineCard(url="https://example.com")])])
        )
        card = result["content"][0]
        assert card["type"] == "inlineCard"
        assert card["attrs"]["url"] == "https://example.com"


# ── TaskList / DecisionList ──────────────────────────────────────────────────


class TestTaskDecision:
    def test_task_list(self):
        result = _r1(
            Doc(
                content=[
                    TaskList(
                        content=[
                            TaskItem(state="TODO", content=[Text(text="todo")]),
                            TaskItem(state="DONE", content=[Text(text="done")]),
                        ]
                    )
                ]
            )
        )
        assert result["type"] == "taskList"
        assert "localId" in result["attrs"]
        items = result["content"]
        assert items[0]["attrs"]["state"] == "TODO"
        assert items[1]["attrs"]["state"] == "DONE"

    def test_block_task_item(self):
        result = _r1(
            Doc(
                content=[
                    TaskList(
                        content=[
                            BlockTaskItem(
                                state="TODO",
                                content=[
                                    Paragraph(content=[Text(text="first")]),
                                    Paragraph(content=[Text(text="second")]),
                                ],
                            )
                        ]
                    )
                ]
            )
        )
        item = result["content"][0]
        assert item["type"] == "blockTaskItem"
        assert len(item["content"]) == 2

    def test_decision_list(self):
        result = _r1(
            Doc(
                content=[
                    DecisionList(
                        content=[
                            DecisionItem(state="DECIDED", content=[Text(text="yes")])
                        ]
                    )
                ]
            )
        )
        assert result["type"] == "decisionList"
        item = result["content"][0]
        assert item["type"] == "decisionItem"
        assert item["attrs"]["state"] == "DECIDED"


# ── Layout ───────────────────────────────────────────────────────────────────


class TestLayout:
    def test_layout_section(self):
        result = _r1(
            Doc(
                content=[
                    LayoutSection(
                        content=[
                            LayoutColumn(
                                width=50,
                                content=[Paragraph(content=[Text(text="left")])],
                            ),
                            LayoutColumn(
                                width=50,
                                content=[Paragraph(content=[Text(text="right")])],
                            ),
                        ]
                    )
                ]
            )
        )
        assert result["type"] == "layoutSection"
        assert len(result["content"]) == 2
        assert result["content"][0]["attrs"] == {"width": 50}


# ── Table ────────────────────────────────────────────────────────────────────


class TestTable:
    def test_simple_table(self):
        result = _r1(
            Doc(
                content=[
                    Table(
                        content=[
                            TableRow(
                                content=[
                                    TableHeader(
                                        content=[Paragraph(content=[Text(text="H")])]
                                    ),
                                ]
                            ),
                            TableRow(
                                content=[
                                    TableCell(
                                        content=[Paragraph(content=[Text(text="D")])]
                                    ),
                                ]
                            ),
                        ]
                    )
                ]
            )
        )
        assert result["type"] == "table"
        assert result["content"][0]["content"][0]["type"] == "tableHeader"
        assert result["content"][1]["content"][0]["type"] == "tableCell"

    def test_cell_attrs(self):
        result = _r1(
            Doc(
                content=[
                    Table(
                        content=[
                            TableRow(
                                content=[
                                    TableCell(
                                        content=[Paragraph(content=[Text(text="x")])],
                                        colspan=2,
                                        background="#ff0",
                                    ),
                                ]
                            )
                        ]
                    )
                ]
            )
        )
        cell = result["content"][0]["content"][0]
        assert cell["attrs"]["colspan"] == 2
        assert cell["attrs"]["background"] == "#ff0"

    def test_table_attrs(self):
        result = _r1(
            Doc(
                content=[
                    Table(
                        content=[
                            TableRow(
                                content=[
                                    TableCell(
                                        content=[Paragraph(content=[Text(text="x")])]
                                    )
                                ]
                            )
                        ],
                        layout="wide",
                    )
                ]
            )
        )
        assert result["attrs"] == {"layout": "wide"}


# ── Extension / SyncBlock ────────────────────────────────────────────────────


class TestExtension:
    def test_extension(self):
        result = _r1(
            Doc(
                content=[
                    Extension(
                        extension_key="macro",
                        extension_type="com.atlassian",
                        parameters={"key": "val"},
                    )
                ]
            )
        )
        assert result["type"] == "extension"
        assert result["attrs"]["extensionKey"] == "macro"
        assert result["attrs"]["parameters"] == {"key": "val"}

    def test_bodied_extension(self):
        result = _r1(
            Doc(
                content=[
                    BodiedExtension(
                        extension_key="macro",
                        extension_type="com.atlassian",
                        content=[Paragraph(content=[Text(text="body")])],
                    )
                ]
            )
        )
        assert result["type"] == "bodiedExtension"
        assert result["content"][0]["type"] == "paragraph"

    def test_sync_block(self):
        result = _r1(Doc(content=[SyncBlock(resource_id="r1")]))
        assert result["type"] == "syncBlock"
        assert result["attrs"] == {"resourceId": "r1"}

    def test_bodied_sync_block(self):
        result = _r1(
            Doc(
                content=[
                    BodiedSyncBlock(
                        resource_id="r1",
                        content=[Paragraph(content=[Text(text="sync")])],
                    )
                ]
            )
        )
        assert result["type"] == "bodiedSyncBlock"
        assert result["content"][0]["type"] == "paragraph"


# ── Inline nodes ─────────────────────────────────────────────────────────────


class TestInlines:
    def test_text(self):
        result = _r1(Doc(content=[Paragraph(content=[Text(text="hello")])]))
        assert result["content"] == [{"type": "text", "text": "hello"}]

    def test_hard_break(self):
        result = _r1(
            Doc(
                content=[
                    Paragraph(content=[Text(text="a"), HardBreak(), Text(text="b")])
                ]
            )
        )
        assert result["content"][1] == {"type": "hardBreak", "attrs": {"text": "\n"}}

    def test_mention(self):
        result = _r1(
            Doc(
                content=[
                    Paragraph(
                        content=[Mention(id="u1", text="@John", user_type="DEFAULT")]
                    )
                ]
            )
        )
        node = result["content"][0]
        assert node["type"] == "mention"
        assert node["attrs"]["id"] == "u1"
        assert node["attrs"]["text"] == "@John"
        assert node["attrs"]["userType"] == "DEFAULT"

    def test_emoji(self):
        result = _r1(
            Doc(
                content=[
                    Paragraph(content=[Emoji(short_name=":smile:", id="e1", text="😊")])
                ]
            )
        )
        node = result["content"][0]
        assert node["attrs"]["shortName"] == ":smile:"

    def test_date(self):
        result = _r1(
            Doc(content=[Paragraph(content=[Date(timestamp="1700000000000")])])
        )
        assert result["content"][0]["attrs"] == {"timestamp": "1700000000000"}

    def test_status(self):
        result = _r1(
            Doc(content=[Paragraph(content=[Status(text="DONE", color="green")])])
        )
        node = result["content"][0]
        assert node["attrs"]["text"] == "DONE"
        assert node["attrs"]["color"] == "green"

    def test_placeholder(self):
        result = _r1(Doc(content=[Paragraph(content=[Placeholder(text="Enter name")])]))
        assert result["content"][0]["attrs"] == {"text": "Enter name"}

    def test_media_inline(self):
        result = _r1(
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
        node = result["content"][0]
        assert node["type"] == "mediaInline"
        assert node["attrs"]["id"] == "f1"

    def test_inline_extension(self):
        result = _r1(
            Doc(
                content=[
                    Paragraph(
                        content=[
                            InlineExtension(
                                extension_key="macro",
                                extension_type="com.atlassian",
                            )
                        ]
                    )
                ]
            )
        )
        node = result["content"][0]
        assert node["type"] == "inlineExtension"
        assert node["attrs"]["extensionKey"] == "macro"


# ── Lossy field regeneration ─────────────────────────────────────────────────


class TestLossyFields:
    def test_local_id_generated_for_task_list(self):
        result = _r1(
            Doc(
                content=[
                    TaskList(content=[TaskItem(state="TODO", content=[Text(text="x")])])
                ]
            )
        )
        assert "localId" in result["attrs"]
        assert "localId" in result["content"][0]["attrs"]

    def test_local_id_generated_for_decision_list(self):
        result = _r1(
            Doc(
                content=[
                    DecisionList(
                        content=[
                            DecisionItem(state="DECIDED", content=[Text(text="x")])
                        ]
                    )
                ]
            )
        )
        assert "localId" in result["attrs"]
        assert "localId" in result["content"][0]["attrs"]

    def test_hard_break_text_injected(self):
        result = _r1(Doc(content=[Paragraph(content=[HardBreak()])]))
        assert result["content"][0]["attrs"]["text"] == "\n"
