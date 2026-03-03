from typing import Any

from marklas.nodes import blocks, inlines
from marklas.adf.parser import parse

# ── Block parsers ─────────────────────────────────────────────────────


def test_empty_doc():
    doc = parse({"type": "doc", "version": 1, "content": []})
    assert doc.children == []


def test_paragraph():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "hello"},
                    ],
                },
            ],
        }
    )
    assert doc.children == [blocks.Paragraph(children=[inlines.Text(text="hello")])]


def test_empty_paragraph():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": []},
            ],
        }
    )
    assert doc.children == [blocks.Paragraph(children=[])]


def test_heading_levels():
    for level in (1, 2, 3, 4, 5, 6):
        doc = parse(
            {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "heading",
                        "attrs": {"level": level},
                        "content": [
                            {"type": "text", "text": f"H{level}"},
                        ],
                    },
                ],
            }
        )
        assert doc.children == [
            blocks.Heading(level=level, children=[inlines.Text(text=f"H{level}")])
        ]


def test_code_block_with_language():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "codeBlock",
                    "attrs": {"language": "python"},
                    "content": [
                        {"type": "text", "text": "print('hi')"},
                    ],
                },
            ],
        }
    )
    assert doc.children == [blocks.CodeBlock(code="print('hi')", language="python")]


def test_code_block_no_language():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "codeBlock",
                    "content": [
                        {"type": "text", "text": "code"},
                    ],
                },
            ],
        }
    )
    assert doc.children == [blocks.CodeBlock(code="code", language=None)]


def test_code_block_multiple_text_nodes():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "codeBlock",
                    "content": [
                        {"type": "text", "text": "line1\n"},
                        {"type": "text", "text": "line2"},
                    ],
                },
            ],
        }
    )
    assert doc.children == [blocks.CodeBlock(code="line1\nline2")]


def test_blockquote():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "blockquote",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": "quoted"},
                            ],
                        },
                    ],
                },
            ],
        }
    )
    assert doc.children == [
        blocks.BlockQuote(
            children=[
                blocks.Paragraph(children=[inlines.Text(text="quoted")]),
            ]
        )
    ]


def test_bullet_list():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "a"}],
                                },
                            ],
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "b"}],
                                },
                            ],
                        },
                    ],
                },
            ],
        }
    )
    assert doc.children == [
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


def test_ordered_list_with_start():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
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
                                },
                            ],
                        },
                    ],
                },
            ],
        }
    )
    result = doc.children[0]
    assert isinstance(result, blocks.OrderedList)
    assert result.start == 3


def test_thematic_break():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "rule"},
            ],
        }
    )
    assert doc.children == [blocks.ThematicBreak()]


def test_table_header_body():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
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
                                            "content": [{"type": "text", "text": "H1"}],
                                        },
                                    ],
                                },
                                {
                                    "type": "tableHeader",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [{"type": "text", "text": "H2"}],
                                        },
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
                                            "content": [{"type": "text", "text": "A"}],
                                        },
                                    ],
                                },
                                {
                                    "type": "tableCell",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [{"type": "text", "text": "B"}],
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
        }
    )
    result = doc.children[0]
    assert isinstance(result, blocks.Table)
    assert result.head == [
        blocks.TableCell(children=[blocks.Paragraph(children=[inlines.Text(text="H1")])]),
        blocks.TableCell(children=[blocks.Paragraph(children=[inlines.Text(text="H2")])]),
    ]
    assert result.body == [
        [
            blocks.TableCell(children=[blocks.Paragraph(children=[inlines.Text(text="A")])]),
            blocks.TableCell(children=[blocks.Paragraph(children=[inlines.Text(text="B")])]),
        ]
    ]


def test_table_no_header():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "table",
                    "content": [
                        {
                            "type": "tableRow",
                            "content": [
                                {
                                    "type": "tableCell",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [{"type": "text", "text": "A"}],
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
        }
    )
    result = doc.children[0]
    assert isinstance(result, blocks.Table)
    assert result.head == []
    assert len(result.body) == 1


def test_table_cell_block_structure_preserved():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
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
                                            "content": [
                                                {"type": "text", "text": "Col"}
                                            ],
                                        },
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
                                            "content": [
                                                {"type": "text", "text": "before"}
                                            ],
                                        },
                                        {
                                            "type": "codeBlock",
                                            "content": [
                                                {"type": "text", "text": "print(1)"}
                                            ],
                                            "attrs": {"language": "python"},
                                        },
                                        {
                                            "type": "bulletList",
                                            "content": [
                                                {
                                                    "type": "listItem",
                                                    "content": [
                                                        {
                                                            "type": "paragraph",
                                                            "content": [
                                                                {
                                                                    "type": "text",
                                                                    "text": "item",
                                                                }
                                                            ],
                                                        },
                                                    ],
                                                },
                                            ],
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
        }
    )
    table = doc.children[0]
    assert isinstance(table, blocks.Table)
    cell = table.body[0][0]
    assert cell.children == [
        blocks.Paragraph(children=[inlines.Text(text="before")]),
        blocks.CodeBlock(code="print(1)", language="python"),
        blocks.BulletList(
            items=[
                blocks.ListItem(
                    children=[blocks.Paragraph(children=[inlines.Text(text="item")])]
                )
            ]
        ),
    ]


def test_table_cell_hard_break_preserved():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
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
                                            "content": [
                                                {"type": "text", "text": "Col"},
                                            ],
                                        },
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
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": "first",
                                                    "marks": [{"type": "strong"}],
                                                },
                                                {"type": "hardBreak"},
                                                {
                                                    "type": "text",
                                                    "text": "second",
                                                    "marks": [{"type": "strong"}],
                                                },
                                            ],
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
        }
    )
    table = doc.children[0]
    assert isinstance(table, blocks.Table)
    cell = table.body[0][0]
    assert cell.children == [
        blocks.Paragraph(
            children=[
                inlines.Strong(children=[inlines.Text(text="first")]),
                inlines.HardBreak(),
                inlines.Strong(children=[inlines.Text(text="second")]),
            ]
        ),
    ]


def _make_cell(text: str, type: str = "tableCell", **attrs: int) -> dict[str, Any]:
    cell: dict[str, Any] = {
        "type": type,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }
    if attrs:
        cell["attrs"] = attrs
    return cell


def _make_table(*rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "table",
                "content": [{"type": "tableRow", "content": cells} for cells in rows],
            }
        ],
    }


def test_table_colspan():
    doc = parse(
        _make_table(
            [
                _make_cell("H1", "tableHeader"),
                _make_cell("H2", "tableHeader"),
                _make_cell("H3", "tableHeader"),
            ],
            [
                _make_cell("A", colspan=2),
                _make_cell("B"),
            ],
        )
    )
    table = doc.children[0]
    assert isinstance(table, blocks.Table)
    assert len(table.head) == 3
    assert len(table.body) == 1
    row = table.body[0]
    assert len(row) == 3
    assert row[0].children == [blocks.Paragraph(children=[inlines.Text(text="A")])]
    assert row[1].children == []
    assert row[2].children == [blocks.Paragraph(children=[inlines.Text(text="B")])]


def test_table_rowspan():
    doc = parse(
        _make_table(
            [
                _make_cell("H1", "tableHeader"),
                _make_cell("H2", "tableHeader"),
            ],
            [
                _make_cell("A", rowspan=2),
                _make_cell("B"),
            ],
            [
                _make_cell("C"),
            ],
        )
    )
    table = doc.children[0]
    assert isinstance(table, blocks.Table)
    assert len(table.body) == 2
    row0 = table.body[0]
    assert len(row0) == 2
    assert row0[0].children == [blocks.Paragraph(children=[inlines.Text(text="A")])]
    assert row0[1].children == [blocks.Paragraph(children=[inlines.Text(text="B")])]
    row1 = table.body[1]
    assert len(row1) == 2
    assert row1[0].children == []
    assert row1[1].children == [blocks.Paragraph(children=[inlines.Text(text="C")])]


def test_table_colspan_and_rowspan():
    doc = parse(
        _make_table(
            [
                _make_cell("H1", "tableHeader"),
                _make_cell("H2", "tableHeader"),
                _make_cell("H3", "tableHeader"),
            ],
            [
                _make_cell("A", colspan=2, rowspan=2),
                _make_cell("B"),
            ],
            [
                _make_cell("C"),
            ],
        )
    )
    table = doc.children[0]
    assert isinstance(table, blocks.Table)
    assert len(table.body) == 2
    row0 = table.body[0]
    assert len(row0) == 3
    assert row0[0].children == [blocks.Paragraph(children=[inlines.Text(text="A")])]
    assert row0[1].children == []
    assert row0[2].children == [blocks.Paragraph(children=[inlines.Text(text="B")])]
    row1 = table.body[1]
    assert len(row1) == 3
    assert row1[0].children == []
    assert row1[1].children == []
    assert row1[2].children == [blocks.Paragraph(children=[inlines.Text(text="C")])]


def test_task_list():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "taskList",
                    "attrs": {"localId": "1"},
                    "content": [
                        {
                            "type": "taskItem",
                            "attrs": {"localId": "a", "state": "DONE"},
                            "content": [
                                {"type": "text", "text": "done"},
                            ],
                        },
                        {
                            "type": "taskItem",
                            "attrs": {"localId": "b", "state": "TODO"},
                            "content": [
                                {"type": "text", "text": "todo"},
                            ],
                        },
                    ],
                },
            ],
        }
    )
    result = doc.children[0]
    assert isinstance(result, blocks.BulletList)
    assert result.items[0].checked is True
    assert result.items[1].checked is False


def test_decision_list():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "decisionList",
                    "attrs": {"localId": "1"},
                    "content": [
                        {
                            "type": "decisionItem",
                            "attrs": {"localId": "a", "state": "DECIDED"},
                            "content": [
                                {"type": "text", "text": "yes"},
                            ],
                        },
                    ],
                },
            ],
        }
    )
    result = doc.children[0]
    assert isinstance(result, blocks.BulletList)
    assert result.items[0].checked is True


def test_panel_fallback():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "panel",
                    "attrs": {"panelType": "info"},
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "info"}],
                        },
                    ],
                },
            ],
        }
    )
    assert doc.children == [
        blocks.BlockQuote(
            children=[
                blocks.Paragraph(children=[inlines.Text(text="info")]),
            ]
        )
    ]


def test_expand_with_title():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "expand",
                    "attrs": {"title": "Details"},
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "body"}],
                        },
                    ],
                },
            ],
        }
    )
    result = doc.children[0]
    assert isinstance(result, blocks.BlockQuote)
    assert result.children[0] == blocks.Paragraph(
        children=[inlines.Text(text="Details")]
    )
    assert result.children[1] == blocks.Paragraph(children=[inlines.Text(text="body")])


def test_expand_no_title():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "expand",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "body"}],
                        },
                    ],
                },
            ],
        }
    )
    result = doc.children[0]
    assert isinstance(result, blocks.BlockQuote)
    assert len(result.children) == 1


def test_nested_expand():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "nestedExpand",
                    "attrs": {"title": "Nested"},
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "inner"}],
                        },
                    ],
                },
            ],
        }
    )
    result = doc.children[0]
    assert isinstance(result, blocks.BlockQuote)
    assert result.children[0] == blocks.Paragraph(
        children=[inlines.Text(text="Nested")]
    )


def test_layout_section_flatten():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "layoutSection",
                    "content": [
                        {
                            "type": "layoutColumn",
                            "attrs": {"width": 50},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "col1"}],
                                },
                            ],
                        },
                        {
                            "type": "layoutColumn",
                            "attrs": {"width": 50},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "col2"}],
                                },
                            ],
                        },
                    ],
                },
            ],
        }
    )
    assert doc.children == [
        blocks.Paragraph(children=[inlines.Text(text="col1")]),
        blocks.Paragraph(children=[inlines.Text(text="col2")]),
    ]


def test_media_single_external():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "mediaSingle",
                    "content": [
                        {
                            "type": "media",
                            "attrs": {
                                "type": "external",
                                "url": "https://img.png",
                                "alt": "photo",
                            },
                        },
                    ],
                },
            ],
        }
    )
    assert doc.children == [
        blocks.Paragraph(children=[inlines.Image(url="https://img.png", alt="photo")])
    ]


def test_media_single_file():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "mediaSingle",
                    "content": [
                        {
                            "type": "media",
                            "attrs": {
                                "type": "file",
                                "id": "abc-123",
                                "collection": "uploads",
                            },
                        },
                    ],
                },
            ],
        }
    )
    assert doc.children == [
        blocks.Paragraph(children=[inlines.Text(text="[Image: abc-123]")])
    ]


def test_media_group():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "mediaGroup",
                    "content": [
                        {
                            "type": "media",
                            "attrs": {"type": "external", "url": "https://a.png"},
                        },
                        {
                            "type": "media",
                            "attrs": {"type": "external", "url": "https://b.png"},
                        },
                    ],
                },
            ],
        }
    )
    result = doc.children[0]
    assert isinstance(result, blocks.Paragraph)
    assert len(result.children) == 2
    assert isinstance(result.children[0], inlines.Image)
    assert isinstance(result.children[1], inlines.Image)


def test_block_card_with_url():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "blockCard", "attrs": {"url": "https://example.com"}},
            ],
        }
    )
    assert doc.children == [
        blocks.Paragraph(
            children=[
                inlines.Link(
                    url="https://example.com",
                    children=[inlines.Text(text="https://example.com")],
                ),
            ]
        )
    ]


def test_block_card_no_url():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "blockCard", "attrs": {"data": {"some": "data"}}},
            ],
        }
    )
    assert doc.children == [blocks.Paragraph(children=[])]


def test_embed_card_with_url():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "embedCard",
                    "attrs": {"url": "https://example.com", "layout": "center"},
                },
            ],
        }
    )
    assert doc.children == [
        blocks.Paragraph(
            children=[
                inlines.Link(
                    url="https://example.com",
                    children=[inlines.Text(text="https://example.com")],
                ),
            ]
        )
    ]


def test_embed_card_no_url():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "embedCard", "attrs": {"url": "", "layout": "center"}},
            ],
        }
    )
    assert doc.children == []


def test_unsupported_block():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "extension",
                    "attrs": {
                        "extensionType": "com.example",
                        "extensionKey": "some-key",
                    },
                },
            ],
        }
    )
    assert doc.children == [
        blocks.Paragraph(children=[inlines.Text(text="[extension]")])
    ]


# ── Inline parsers ────────────────────────────────────────────────────


def test_text():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "hello"}]},
            ],
        }
    )
    assert doc.children[0] == blocks.Paragraph(children=[inlines.Text(text="hello")])


def test_hard_break():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "a"},
                        {"type": "hardBreak"},
                        {"type": "text", "text": "b"},
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [
        inlines.Text(text="a"),
        inlines.HardBreak(),
        inlines.Text(text="b"),
    ]


def test_mention_with_text():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "mention", "attrs": {"id": "123", "text": "홍길동"}},
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [inlines.CodeSpan(code="홍길동")]


def test_mention_without_text():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "mention", "attrs": {"id": "123"}},
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [inlines.CodeSpan(code="@123")]


def test_emoji_with_text():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "emoji",
                            "attrs": {"shortName": "smile", "text": "😄"},
                        },
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [inlines.Text(text="😄")]


def test_emoji_without_text():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "emoji", "attrs": {"shortName": "smile"}},
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [inlines.Text(text=":smile:")]


def test_date():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "date", "attrs": {"timestamp": "1672531200000"}},
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [inlines.CodeSpan(code="2023-01-01")]


def test_status():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "status",
                            "attrs": {"text": "IN PROGRESS", "color": "blue"},
                        },
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [inlines.CodeSpan(code="IN PROGRESS")]


def test_inline_card_with_url():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "inlineCard", "attrs": {"url": "https://example.com"}},
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [
        inlines.Link(
            url="https://example.com",
            children=[inlines.Text(text="https://example.com")],
        )
    ]


def test_inline_card_no_url():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "inlineCard", "attrs": {}},
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == []


def test_unsupported_inline():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "placeholder", "attrs": {"text": "Type something"}},
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [inlines.Text(text="[placeholder]")]


# ── Mark parsers ──────────────────────────────────────────────────────


def test_strong_mark():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "bold", "marks": [{"type": "strong"}]},
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [inlines.Strong(children=[inlines.Text(text="bold")])]


def test_em_mark():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "italic", "marks": [{"type": "em"}]},
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [inlines.Emphasis(children=[inlines.Text(text="italic")])]


def test_strike_mark():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "deleted",
                            "marks": [{"type": "strike"}],
                        },
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [
        inlines.Strikethrough(children=[inlines.Text(text="deleted")])
    ]


def test_code_mark():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "code", "marks": [{"type": "code"}]},
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [inlines.CodeSpan(code="code")]


def test_link_mark():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "click",
                            "marks": [
                                {
                                    "type": "link",
                                    "attrs": {"href": "https://example.com"},
                                },
                            ],
                        },
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [
        inlines.Link(url="https://example.com", children=[inlines.Text(text="click")])
    ]


def test_link_mark_with_title():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "click",
                            "marks": [
                                {
                                    "type": "link",
                                    "attrs": {
                                        "href": "https://example.com",
                                        "title": "Example",
                                    },
                                },
                            ],
                        },
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [
        inlines.Link(
            url="https://example.com",
            children=[inlines.Text(text="click")],
            title="Example",
        )
    ]


def test_nested_marks():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "bold italic",
                            "marks": [
                                {"type": "strong"},
                                {"type": "em"},
                            ],
                        },
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [
        inlines.Strong(
            children=[inlines.Emphasis(children=[inlines.Text(text="bold italic")])]
        )
    ]


def test_code_and_link_marks():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "example",
                            "marks": [
                                {"type": "code"},
                                {
                                    "type": "link",
                                    "attrs": {"href": "https://example.com"},
                                },
                            ],
                        },
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [
        inlines.Link(
            url="https://example.com",
            children=[inlines.CodeSpan(code="example")],
        ),
    ]


def test_empty_text_with_marks():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "", "marks": [{"type": "strong"}]},
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == []


def test_underline_ignored():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "underlined",
                            "marks": [{"type": "underline"}],
                        },
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [inlines.Text(text="underlined")]


def test_text_color_ignored():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "colored",
                            "marks": [
                                {"type": "textColor", "attrs": {"color": "#ff0000"}},
                            ],
                        },
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [inlines.Text(text="colored")]


def test_background_color_ignored():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "highlighted",
                            "marks": [
                                {
                                    "type": "backgroundColor",
                                    "attrs": {"color": "#ffff00"},
                                },
                            ],
                        },
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [inlines.Text(text="highlighted")]


def test_subsup_ignored():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "sup",
                            "marks": [
                                {"type": "subsup", "attrs": {"type": "sup"}},
                            ],
                        },
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [inlines.Text(text="sup")]


# ── Adjacent mark merging ────────────────────────────────────────────


def test_adjacent_strong_merged():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "hello ",
                            "marks": [{"type": "strong"}],
                        },
                        {
                            "type": "text",
                            "text": "world",
                            "marks": [{"type": "strong"}],
                        },
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [
        inlines.Strong(
            children=[inlines.Text(text="hello "), inlines.Text(text="world")]
        ),
    ]


def test_adjacent_strong_with_ignored_underline_merged():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "plain ",
                            "marks": [{"type": "strong"}],
                        },
                        {
                            "type": "text",
                            "text": "underlined",
                            "marks": [
                                {"type": "underline"},
                                {"type": "strong"},
                            ],
                        },
                        {
                            "type": "text",
                            "text": " rest",
                            "marks": [{"type": "strong"}],
                        },
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [
        inlines.Strong(
            children=[
                inlines.Text(text="plain "),
                inlines.Text(text="underlined"),
                inlines.Text(text=" rest"),
            ]
        ),
    ]


def test_different_mark_types_not_merged():
    doc = parse(
        {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "bold",
                            "marks": [{"type": "strong"}],
                        },
                        {
                            "type": "text",
                            "text": "italic",
                            "marks": [{"type": "em"}],
                        },
                    ],
                },
            ],
        }
    )
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == [
        inlines.Strong(children=[inlines.Text(text="bold")]),
        inlines.Emphasis(children=[inlines.Text(text="italic")]),
    ]
