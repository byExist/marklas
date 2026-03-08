"""MD renderer 테스트: AST → Markdown"""

from __future__ import annotations

import json

from marklas.md.renderer import render
from marklas.nodes import blocks, inlines


# ── 교집합 블록 렌더링 ───────────────────────────────────────────────


def test_paragraph():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.Text(text="hello world")])]
    )
    assert render(doc) == "hello world\n"


def test_heading_levels():
    for level in (1, 2, 3, 4, 5, 6):
        doc = blocks.Document(
            children=[
                blocks.Heading(level=level, children=[inlines.Text(text="title")])
            ]
        )
        assert render(doc) == f"{'#' * level} title\n"


def test_code_block_with_language():
    doc = blocks.Document(
        children=[blocks.CodeBlock(code="print(1)", language="python")]
    )
    assert render(doc) == "```python\nprint(1)\n```\n"


def test_code_block_without_language():
    doc = blocks.Document(children=[blocks.CodeBlock(code="hello")])
    assert render(doc) == "```\nhello\n```\n"


def test_blockquote():
    doc = blocks.Document(
        children=[
            blocks.BlockQuote(
                children=[blocks.Paragraph(children=[inlines.Text(text="quoted")])]
            )
        ]
    )
    assert render(doc) == "> quoted\n"


def test_blockquote_multiblock():
    doc = blocks.Document(
        children=[
            blocks.BlockQuote(
                children=[
                    blocks.Paragraph(children=[inlines.Text(text="a")]),
                    blocks.Paragraph(children=[inlines.Text(text="b")]),
                ]
            )
        ]
    )
    assert render(doc) == "> a\n>\n> b\n"


def test_bullet_list():
    doc = blocks.Document(
        children=[
            blocks.BulletList(
                items=[
                    blocks.ListItem(
                        children=[blocks.Paragraph(children=[inlines.Text(text="a")])]
                    ),
                    blocks.ListItem(
                        children=[blocks.Paragraph(children=[inlines.Text(text="b")])]
                    ),
                ]
            )
        ]
    )
    assert render(doc) == "- a\n- b\n"


def test_ordered_list():
    doc = blocks.Document(
        children=[
            blocks.OrderedList(
                items=[
                    blocks.ListItem(
                        children=[blocks.Paragraph(children=[inlines.Text(text="a")])]
                    ),
                    blocks.ListItem(
                        children=[blocks.Paragraph(children=[inlines.Text(text="b")])]
                    ),
                ],
                start=3,
            )
        ]
    )
    assert render(doc) == "3. a\n4. b\n"


def test_bullet_list_with_checkbox():
    doc = blocks.Document(
        children=[
            blocks.BulletList(
                items=[
                    blocks.ListItem(
                        children=[
                            blocks.Paragraph(children=[inlines.Text(text="done")])
                        ],
                        checked=True,
                    ),
                    blocks.ListItem(
                        children=[
                            blocks.Paragraph(children=[inlines.Text(text="todo")])
                        ],
                        checked=False,
                    ),
                ]
            )
        ]
    )
    assert render(doc) == "- [x] done\n- [ ] todo\n"


def test_thematic_break():
    doc = blocks.Document(children=[blocks.ThematicBreak()])
    assert render(doc) == "---\n"


def test_multiple_blocks():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(children=[inlines.Text(text="a")]),
            blocks.Paragraph(children=[inlines.Text(text="b")]),
        ]
    )
    assert render(doc) == "a\n\nb\n"


def test_empty_document():
    doc = blocks.Document(children=[])
    assert render(doc) == ""


# ── 교집합 인라인 렌더링 ─────────────────────────────────────────────


def test_strong():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Strong(children=[inlines.Text(text="bold")])]
            )
        ]
    )
    assert render(doc) == "**bold**\n"


def test_emphasis():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Emphasis(children=[inlines.Text(text="italic")])]
            )
        ]
    )
    assert render(doc) == "*italic*\n"


def test_strikethrough():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Strikethrough(children=[inlines.Text(text="deleted")])
                ]
            )
        ]
    )
    assert render(doc) == "~~deleted~~\n"


def test_link():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Link(
                        url="https://example.com", children=[inlines.Text(text="click")]
                    )
                ]
            )
        ]
    )
    assert render(doc) == "[click](https://example.com)\n"


def test_link_with_title():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Link(
                        url="https://example.com",
                        children=[inlines.Text(text="click")],
                        title="hint",
                    )
                ]
            )
        ]
    )
    assert render(doc) == '[click](https://example.com "hint")\n'


def test_image():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Image(url="https://img.png", alt="photo")]
            )
        ]
    )
    assert render(doc) == "![photo](https://img.png)\n"


def test_image_with_title():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Image(url="https://img.png", alt="photo", title="cap")
                ]
            )
        ]
    )
    assert render(doc) == '![photo](https://img.png "cap")\n'


def test_code_span():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.CodeSpan(code="x=1")])]
    )
    assert render(doc) == "`x=1`\n"


def test_code_span_with_backtick():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.CodeSpan(code="a`b")])]
    )
    assert render(doc) == "`` a`b ``\n"


def test_hard_break():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Text(text="a"),
                    inlines.HardBreak(),
                    inlines.Text(text="b"),
                ]
            )
        ]
    )
    assert render(doc) == "a\\\nb\n"


def test_soft_break():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Text(text="a"),
                    inlines.SoftBreak(),
                    inlines.Text(text="b"),
                ]
            )
        ]
    )
    assert render(doc) == "a\nb\n"


def test_nested_marks():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Strong(
                        children=[
                            inlines.Emphasis(children=[inlines.Text(text="both")])
                        ]
                    )
                ]
            )
        ]
    )
    assert render(doc) == "***both***\n"


def test_mark_space_handling():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Strong(
                        children=[
                            inlines.Text(text=" hello "),
                        ]
                    )
                ]
            )
        ]
    )
    assert render(doc) == " **hello** \n"


# ── Table ────────────────────────────────────────────────────────────


def test_table_basic():
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableCell(
                        children=[blocks.Paragraph(children=[inlines.Text(text="A")])]
                    ),
                    blocks.TableCell(
                        children=[blocks.Paragraph(children=[inlines.Text(text="B")])]
                    ),
                ],
                body=[
                    [
                        blocks.TableCell(
                            children=[
                                blocks.Paragraph(children=[inlines.Text(text="1")])
                            ]
                        ),
                        blocks.TableCell(
                            children=[
                                blocks.Paragraph(children=[inlines.Text(text="2")])
                            ]
                        ),
                    ],
                ],
            )
        ]
    )
    expected = (
        "| <!-- adf:paragraph -->A<!-- /adf:paragraph -->"
        " | <!-- adf:paragraph -->B<!-- /adf:paragraph --> |\n"
        "| --- | --- |\n"
        "| <!-- adf:paragraph -->1<!-- /adf:paragraph -->"
        " | <!-- adf:paragraph -->2<!-- /adf:paragraph --> |\n"
    )
    assert render(doc) == expected


def test_table_with_alignment():
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableCell(
                        children=[blocks.Paragraph(children=[inlines.Text(text="L")])]
                    ),
                    blocks.TableCell(
                        children=[blocks.Paragraph(children=[inlines.Text(text="C")])]
                    ),
                    blocks.TableCell(
                        children=[blocks.Paragraph(children=[inlines.Text(text="R")])]
                    ),
                ],
                body=[],
                alignments=["left", "center", "right"],
            )
        ]
    )
    expected = (
        "| <!-- adf:paragraph -->L<!-- /adf:paragraph -->"
        " | <!-- adf:paragraph -->C<!-- /adf:paragraph -->"
        " | <!-- adf:paragraph -->R<!-- /adf:paragraph --> |\n"
        "| :--- | :---: | ---: |\n"
    )
    assert render(doc) == expected


def test_table_cell_hardbreak():
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableCell(
                        children=[
                            blocks.Paragraph(
                                children=[
                                    inlines.Text(text="a"),
                                    inlines.HardBreak(),
                                    inlines.Text(text="b"),
                                ]
                            )
                        ]
                    ),
                ],
                body=[],
            )
        ]
    )
    expected = "| <!-- adf:paragraph -->a<br>b<!-- /adf:paragraph --> |\n| --- |\n"
    assert render(doc) == expected


def test_table_cell_multi_paragraph():
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableCell(
                        children=[
                            blocks.Paragraph(children=[inlines.Text(text="first")]),
                            blocks.Paragraph(children=[inlines.Text(text="second")]),
                        ]
                    ),
                ],
                body=[],
            )
        ]
    )
    expected = (
        "| <!-- adf:paragraph -->first<!-- /adf:paragraph -->"
        "<!-- adf:paragraph -->second<!-- /adf:paragraph --> |\n"
        "| --- |\n"
    )
    assert render(doc) == expected


def test_table_cell_non_paragraph_blocks():
    """리스트가 테이블 셀에서 HTML <ul>/<ol>로 렌더링."""
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableCell(
                        children=[
                            blocks.BulletList(
                                items=[
                                    blocks.ListItem(
                                        children=[
                                            blocks.Paragraph(
                                                children=[inlines.Text(text="item1")]
                                            ),
                                        ]
                                    ),
                                    blocks.ListItem(
                                        children=[
                                            blocks.Paragraph(
                                                children=[inlines.Text(text="item2")]
                                            ),
                                        ]
                                    ),
                                ]
                            ),
                        ]
                    ),
                ],
                body=[],
            )
        ]
    )
    result = render(doc)
    assert (
        "<!-- adf:bulletList --><ul><li><!-- adf:paragraph -->item1<!-- /adf:paragraph --></li><li><!-- adf:paragraph -->item2<!-- /adf:paragraph --></li></ul><!-- /adf:bulletList -->"
        in result
    )


def test_table_cell_block_with_hardbreak():
    """비-Paragraph 블록 내 HardBreak가 고아 \\가 아닌 <br>로 변환."""
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableCell(
                        children=[
                            blocks.BlockQuote(
                                children=[
                                    blocks.Paragraph(
                                        children=[
                                            inlines.Text(text="a"),
                                            inlines.HardBreak(),
                                            inlines.Text(text="b"),
                                        ]
                                    )
                                ]
                            ),
                        ]
                    ),
                ],
                body=[],
            )
        ]
    )
    result = render(doc)
    # HardBreak가 <br>로 변환, 고아 \ 없어야 함
    assert "\\ " not in result
    assert (
        "<blockquote><!-- adf:paragraph -->a<br>b<!-- /adf:paragraph --></blockquote>"
        in result
    )


def test_table_with_attrs():
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableCell(
                        children=[blocks.Paragraph(children=[inlines.Text(text="H")])],
                        colspan=2,
                    ),
                ],
                body=[],
                layout="default",
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:table" in result
    assert "<!-- /adf:table -->" in result
    assert '"layout": "default"' in result
    assert '"colspan": 2' in result


# ── 차집합 블록 annotation ───────────────────────────────────────────


def test_panel():
    doc = blocks.Document(
        children=[
            blocks.Panel(
                panel_type="info",
                children=[blocks.Paragraph(children=[inlines.Text(text="note")])],
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:panel" in result
    assert '"panelType": "info"' in result
    assert "\nnote\n" in result
    assert "<!-- /adf:panel -->" in result


def test_panel_with_all_attrs():
    doc = blocks.Document(
        children=[
            blocks.Panel(
                panel_type="custom",
                panel_icon=":star:",
                panel_icon_id="icon-1",
                panel_icon_text="Star",
                panel_color="#ff0",
                children=[blocks.Paragraph(children=[inlines.Text(text="x")])],
            )
        ]
    )
    result = render(doc)
    assert '"panelIcon": ":star:"' in result
    assert '"panelIconId": "icon-1"' in result
    assert '"panelIconText": "Star"' in result
    assert '"panelColor": "#ff0"' in result


def test_expand():
    doc = blocks.Document(
        children=[
            blocks.Expand(
                title="Details",
                children=[blocks.Paragraph(children=[inlines.Text(text="content")])],
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:expand" in result
    assert '"title": "Details"' in result
    assert "\ncontent\n" in result
    assert "<!-- /adf:expand -->" in result


def test_nested_expand():
    doc = blocks.Document(
        children=[
            blocks.NestedExpand(
                title="Inner",
                children=[
                    blocks.Paragraph(children=[inlines.Text(text="inner content")])
                ],
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:nestedExpand" in result
    assert "<!-- /adf:nestedExpand -->" in result


def test_task_list():
    doc = blocks.Document(
        children=[
            blocks.TaskList(
                items=[
                    blocks.TaskItem(
                        children=[inlines.Text(text="done task")],
                        state="DONE",
                        local_id="t1",
                    ),
                    blocks.TaskItem(
                        children=[inlines.Text(text="todo task")],
                        state="TODO",
                        local_id="t2",
                    ),
                ]
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:taskList -->" in result
    assert "- [x] done task" in result
    assert "- [ ] todo task" in result
    assert "<!-- /adf:taskList -->" in result


def test_decision_list():
    doc = blocks.Document(
        children=[
            blocks.DecisionList(
                items=[
                    blocks.DecisionItem(
                        children=[inlines.Text(text="decided")],
                        state="DECIDED",
                        local_id="d1",
                    ),
                    blocks.DecisionItem(
                        children=[inlines.Text(text="pending")], state="", local_id="d2"
                    ),
                ]
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:decisionList -->" in result
    assert "- [x] decided" in result
    assert "- [ ] pending" in result


def test_layout_section():
    doc = blocks.Document(
        children=[
            blocks.LayoutSection(
                columns=[
                    blocks.LayoutColumn(
                        children=[
                            blocks.Paragraph(children=[inlines.Text(text="col1")])
                        ],
                        width=50.0,
                    ),
                    blocks.LayoutColumn(
                        children=[
                            blocks.Paragraph(children=[inlines.Text(text="col2")])
                        ],
                        width=50.0,
                    ),
                ]
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:layoutSection -->" in result
    assert "<!-- adf:layoutColumn" in result
    assert "col1" in result
    assert "col2" in result
    assert '"width": 50.0' in result


def test_media_single_external():
    doc = blocks.Document(
        children=[
            blocks.MediaSingle(
                media=blocks.Media(media_type="external", url="https://img.png"),
                layout="center",
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:mediaSingle" in result
    assert "![](https://img.png)" in result
    assert '"layout": "center"' in result


def test_media_single_file():
    doc = blocks.Document(
        children=[
            blocks.MediaSingle(
                media=blocks.Media(media_type="file", id="file-1", collection="c"),
            )
        ]
    )
    result = render(doc)
    assert "`\U0001f4ce attachment`" in result


def test_media_group():
    doc = blocks.Document(
        children=[
            blocks.MediaGroup(
                media_list=[
                    blocks.Media(media_type="external", url="https://a.png"),
                    blocks.Media(media_type="file", id="f-1", collection="c"),
                ]
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:mediaGroup" in result
    assert "![](https://a.png)" in result
    assert "`\U0001f4ce attachment`" in result


def test_block_card_with_url():
    doc = blocks.Document(children=[blocks.BlockCard(url="https://example.com")])
    result = render(doc)
    assert "<!-- adf:blockCard" in result
    assert "[https://example.com](https://example.com)" in result


def test_block_card_with_data():
    doc = blocks.Document(children=[blocks.BlockCard(data={"name": "card"})])
    result = render(doc)
    assert "`\U0001f517 card link`" in result


def test_embed_card():
    doc = blocks.Document(
        children=[blocks.EmbedCard(url="https://embed.com", layout="wide", width=80.0)]
    )
    result = render(doc)
    assert "<!-- adf:embedCard" in result
    assert "[https://embed.com](https://embed.com)" in result
    assert '"width": 80.0' in result


# ── Placeholder 전용 ─────────────────────────────────────────────────


def test_extension_placeholder():
    doc = blocks.Document(
        children=[blocks.Extension(raw={"type": "extension", "attrs": {}})]
    )
    assert render(doc) == "`\u2699 Confluence macro`\n"


def test_bodied_extension_placeholder():
    doc = blocks.Document(
        children=[blocks.BodiedExtension(raw={"type": "bodiedExtension", "attrs": {}})]
    )
    assert render(doc) == "`\u2699 Confluence macro`\n"


def test_sync_block_placeholder():
    doc = blocks.Document(
        children=[blocks.SyncBlock(raw={"type": "syncBlock", "attrs": {}})]
    )
    assert render(doc) == "`\u2699 Confluence macro`\n"


def test_bodied_sync_block_placeholder():
    doc = blocks.Document(
        children=[blocks.BodiedSyncBlock(raw={"type": "bodiedSyncBlock", "attrs": {}})]
    )
    assert render(doc) == "`\u2699 Confluence macro`\n"


def test_placeholder_inline():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Text(text="before"),
                    inlines.Placeholder(text="Type something"),
                    inlines.Text(text="after"),
                ]
            )
        ]
    )
    assert render(doc) == "beforeafter\n"


def test_inline_extension_placeholder():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.InlineExtension(
                        raw={"type": "inlineExtension", "attrs": {}}
                    )
                ]
            )
        ]
    )
    assert render(doc) == "`\u2699 Confluence macro`\n"


# ── 차집합 인라인 annotation ─────────────────────────────────────────


def test_mention():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Mention(id="user-1", text="@Alice", user_type="DEFAULT")
                ]
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:mention" in result
    assert "`@Alice`" in result
    assert '"id": "user-1"' in result
    assert "<!-- /adf:mention -->" in result


def test_mention_without_text():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.Mention(id="user-2")])]
    )
    result = render(doc)
    assert "`@user-2`" in result


def test_emoji():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Emoji(short_name="smile", text="\U0001f604")]
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:emoji" in result
    assert "\U0001f604" in result
    assert '"shortName": "smile"' in result


def test_emoji_without_text():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.Emoji(short_name="thumbsup")])]
    )
    result = render(doc)
    assert ":thumbsup:" in result


def test_date():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.Date(timestamp="1609459200000")])]
    )
    result = render(doc)
    assert "<!-- adf:date" in result
    assert "`2021-01-01`" in result
    assert '"timestamp": "1609459200000"' in result


def test_status():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Status(text="In Progress", color="blue", style="bold")
                ]
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:status" in result
    assert "`In Progress`" in result
    assert '"color": "blue"' in result
    assert '"localId"' not in result


def test_inline_card_url():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(children=[inlines.InlineCard(url="https://example.com")])
        ]
    )
    result = render(doc)
    assert "<!-- adf:inlineCard" in result
    assert "[https://example.com](https://example.com)" in result


def test_inline_card_data():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(children=[inlines.InlineCard(data={"name": "card"})])
        ]
    )
    result = render(doc)
    assert "`\U0001f517 card link`" in result


def test_media_inline():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.MediaInline(id="m-1", collection="c", media_type="file")
                ]
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:mediaInline" in result
    assert "`\U0001f4ce attachment`" in result
    assert '"id": "m-1"' in result


def test_underline():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Underline(children=[inlines.Text(text="underlined")])]
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:underline -->underlined<!-- /adf:underline -->" in result


def test_text_color():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.TextColor(
                        color="#ff0000", children=[inlines.Text(text="red")]
                    )
                ]
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:textColor" in result
    assert '"color": "#ff0000"' in result
    assert "red" in result


def test_background_color():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.BackgroundColor(
                        color="#00ff00", children=[inlines.Text(text="green")]
                    )
                ]
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:backgroundColor" in result
    assert '"color": "#00ff00"' in result


def test_subsup():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.SubSup(type="sub", children=[inlines.Text(text="2")])]
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:subSup" in result
    assert '"type": "sub"' in result


def test_annotation_inline():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Annotation(
                        id="ann-1", children=[inlines.Text(text="noted")]
                    )
                ]
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:annotation" in result
    assert '"id": "ann-1"' in result
    assert "noted" in result


# ── Block marks ──────────────────────────────────────────────────────


def test_paragraph_alignment():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Text(text="centered")],
                alignment="center",
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:paragraph" in result
    assert '"align": "center"' in result
    assert "centered" in result


def test_heading_indentation():
    doc = blocks.Document(
        children=[
            blocks.Heading(
                level=2,
                children=[inlines.Text(text="indented")],
                indentation=1,
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:heading" in result
    assert '"indentation": 1' in result
    assert "## indented" in result


# ── 중첩 ─────────────────────────────────────────────────────────────


def test_panel_with_task_list():
    doc = blocks.Document(
        children=[
            blocks.Panel(
                panel_type="info",
                children=[
                    blocks.TaskList(
                        items=[
                            blocks.TaskItem(
                                children=[inlines.Text(text="task 1")],
                                state="DONE",
                                local_id="t1",
                            ),
                            blocks.TaskItem(
                                children=[inlines.Text(text="task 2")],
                                state="TODO",
                                local_id="t2",
                            ),
                        ]
                    )
                ],
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:panel" in result
    assert "<!-- adf:taskList -->" in result
    assert "- [x] task 1" in result
    assert "- [ ] task 2" in result


# ── _annotate_block / _annotate_inline 정확성 ────────────────────────


def test_annotate_block_no_attrs():
    doc = blocks.Document(
        children=[
            blocks.TaskList(
                items=[
                    blocks.TaskItem(
                        children=[inlines.Text(text="a")], state="TODO", local_id="t1"
                    ),
                ]
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:taskList -->" in result
    assert "<!-- /adf:taskList -->" in result


def test_annotate_inline_no_attrs():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Underline(children=[inlines.Text(text="u")])]
            )
        ]
    )
    result = render(doc)
    assert "<!-- adf:underline -->u<!-- /adf:underline -->" in result


def test_annotate_block_with_attrs_json():
    doc = blocks.Document(
        children=[
            blocks.Panel(
                panel_type="warning",
                children=[blocks.Paragraph(children=[inlines.Text(text="warn")])],
            )
        ]
    )
    result = render(doc)
    # JSON attrs가 파싱 가능한지 확인
    lines = result.split("\n")
    open_tag = lines[0]
    assert open_tag.startswith("<!-- adf:panel ")
    json_str = open_tag[len("<!-- adf:panel ") : -len(" -->")]
    attrs = json.loads(json_str)
    assert attrs["panelType"] == "warning"


def test_annotate_inline_with_attrs_json():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.TextColor(color="#abc", children=[inlines.Text(text="t")])
                ]
            )
        ]
    )
    result = render(doc)
    # 인라인 annotation JSON 파싱
    start = result.index("<!-- adf:textColor ") + len("<!-- adf:textColor ")
    end = result.index(" -->t")
    json_str = result[start:end]
    attrs = json.loads(json_str)
    assert attrs["color"] == "#abc"


# ── Headerless table ────────────────────────────────────────────────


# ── annotate=False ──────────────────────────────────────────────────


def test_annotate_false_panel():
    """annotate=False strips panel annotation, renders content only."""
    doc = blocks.Document(
        children=[
            blocks.Panel(
                panel_type="info",
                children=[blocks.Paragraph(children=[inlines.Text(text="note")])],
            )
        ]
    )
    result = render(doc, annotate=False)
    assert "<!-- adf:" not in result
    assert "note" in result


def test_annotate_false_task_list():
    """annotate=False strips taskList annotation, renders checklist only."""
    doc = blocks.Document(
        children=[
            blocks.TaskList(
                items=[
                    blocks.TaskItem(
                        children=[inlines.Text(text="done")],
                        state="DONE",
                        local_id="t1",
                    ),
                    blocks.TaskItem(
                        children=[inlines.Text(text="todo")],
                        state="TODO",
                        local_id="t2",
                    ),
                ]
            )
        ]
    )
    result = render(doc, annotate=False)
    assert "<!-- adf:" not in result
    assert "- [x] done" in result
    assert "- [ ] todo" in result


def test_annotate_false_mention():
    """annotate=False strips mention annotation, renders fallback only."""
    doc = blocks.Document(
        children=[
            blocks.Paragraph(children=[inlines.Mention(id="user-1", text="@Alice")])
        ]
    )
    result = render(doc, annotate=False)
    assert "<!-- adf:" not in result
    assert "`@Alice`" in result


def test_annotate_false_text_color():
    """annotate=False strips textColor annotation, renders text only."""
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.TextColor(
                        color="#ff0000", children=[inlines.Text(text="red")]
                    )
                ]
            )
        ]
    )
    result = render(doc, annotate=False)
    assert "<!-- adf:" not in result
    assert "red" in result


def test_annotate_false_table_with_attrs():
    """annotate=False strips table attrs annotation, renders plain table."""
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableCell(
                        children=[blocks.Paragraph(children=[inlines.Text(text="H")])],
                        colspan=2,
                    ),
                ],
                body=[],
                layout="default",
            )
        ]
    )
    result = render(doc, annotate=False)
    assert "<!-- adf:" not in result
    assert "| H |" in result


def test_annotate_false_paragraph_alignment():
    """annotate=False strips paragraph alignment annotation, renders text only."""
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Text(text="centered")],
                alignment="center",
            )
        ]
    )
    result = render(doc, annotate=False)
    assert "<!-- adf:" not in result
    assert "centered" in result


def test_annotate_false_nested():
    """annotate=False strips all nested annotations."""
    doc = blocks.Document(
        children=[
            blocks.Panel(
                panel_type="info",
                children=[
                    blocks.TaskList(
                        items=[
                            blocks.TaskItem(
                                children=[inlines.Text(text="task")],
                                state="DONE",
                                local_id="t1",
                            ),
                        ]
                    )
                ],
            )
        ]
    )
    result = render(doc, annotate=False)
    assert "<!-- adf:" not in result
    assert "- [x] task" in result


def test_annotate_false_mixed_intersection_and_difference():
    """annotate=False strips annotation from difference-set inside intersection mark."""
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Strong(
                        children=[
                            inlines.TextColor(
                                color="#ff0000",
                                children=[inlines.Text(text="bold red")],
                            )
                        ]
                    )
                ]
            )
        ]
    )
    result = render(doc, annotate=False)
    assert "<!-- adf:" not in result
    assert "**bold red**" in result


def test_annotate_true_default():
    """annotate defaults to True, matching existing behavior."""
    doc = blocks.Document(
        children=[
            blocks.Panel(
                panel_type="info",
                children=[blocks.Paragraph(children=[inlines.Text(text="note")])],
            )
        ]
    )
    assert render(doc) == render(doc, annotate=True)


# ── Headerless table ────────────────────────────────────────────────


def test_headerless_table_renders_empty_header():
    """head=[]이면 빈 헤더 행을 생성하여 유효한 MD 테이블 출력."""
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[],
                body=[
                    [
                        blocks.TableCell(
                            children=[
                                blocks.Paragraph(children=[inlines.Text(text="A1")])
                            ]
                        ),
                        blocks.TableCell(
                            children=[
                                blocks.Paragraph(children=[inlines.Text(text="B1")])
                            ]
                        ),
                    ],
                    [
                        blocks.TableCell(
                            children=[
                                blocks.Paragraph(children=[inlines.Text(text="A2")])
                            ]
                        ),
                        blocks.TableCell(
                            children=[
                                blocks.Paragraph(children=[inlines.Text(text="B2")])
                            ]
                        ),
                    ],
                ],
            )
        ]
    )
    result = render(doc)
    lines = result.strip().split("\n")
    assert lines[0] == "|  |  |"
    assert lines[1] == "| --- | --- |"
    assert (
        lines[2]
        == "| <!-- adf:paragraph -->A1<!-- /adf:paragraph --> | <!-- adf:paragraph -->B1<!-- /adf:paragraph --> |"
    )
    assert (
        lines[3]
        == "| <!-- adf:paragraph -->A2<!-- /adf:paragraph --> | <!-- adf:paragraph -->B2<!-- /adf:paragraph --> |"
    )
