from marklas.nodes import blocks, inlines
from marklas.md.renderer import render

# ── Block renderers ───────────────────────────────────────────────────


def test_empty_doc():
    assert render(blocks.Document(children=[])) == ""


def test_paragraph():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.Text(text="Hello")])]
    )
    assert render(doc) == "Hello\n"


def test_empty_paragraph():
    doc = blocks.Document(children=[blocks.Paragraph(children=[])])
    assert render(doc) == "\n"


def test_heading_levels():
    for level in (1, 2, 3, 4, 5, 6):
        doc = blocks.Document(
            children=[
                blocks.Heading(level=level, children=[inlines.Text(text="Title")])
            ]
        )
        expected = "#" * level + " Title\n"
        assert render(doc) == expected


def test_code_block_with_language():
    doc = blocks.Document(
        children=[blocks.CodeBlock(code="print('hi')", language="python")]
    )
    assert render(doc) == "```python\nprint('hi')\n```\n"


def test_code_block_no_language():
    doc = blocks.Document(children=[blocks.CodeBlock(code="hello")])
    assert render(doc) == "```\nhello\n```\n"


def test_code_block_with_backticks():
    doc = blocks.Document(children=[blocks.CodeBlock(code="```\nfoo\n```")])
    assert render(doc) == "````\n```\nfoo\n```\n````\n"


def test_blockquote():
    doc = blocks.Document(
        children=[
            blocks.BlockQuote(
                children=[blocks.Paragraph(children=[inlines.Text(text="quoted")])]
            )
        ]
    )
    assert render(doc) == "> quoted\n"


def test_nested_blockquote():
    doc = blocks.Document(
        children=[
            blocks.BlockQuote(
                children=[
                    blocks.BlockQuote(
                        children=[
                            blocks.Paragraph(children=[inlines.Text(text="deep")])
                        ]
                    )
                ]
            )
        ]
    )
    assert render(doc) == "> > deep\n"


def test_bullet_list_tight():
    doc = blocks.Document(
        children=[
            blocks.BulletList(
                tight=True,
                items=[
                    blocks.ListItem(
                        children=[blocks.Paragraph(children=[inlines.Text(text="a")])]
                    ),
                    blocks.ListItem(
                        children=[blocks.Paragraph(children=[inlines.Text(text="b")])]
                    ),
                ],
            )
        ]
    )
    assert render(doc) == "- a\n- b\n"


def test_bullet_list_loose():
    doc = blocks.Document(
        children=[
            blocks.BulletList(
                tight=False,
                items=[
                    blocks.ListItem(
                        children=[blocks.Paragraph(children=[inlines.Text(text="a")])]
                    ),
                    blocks.ListItem(
                        children=[blocks.Paragraph(children=[inlines.Text(text="b")])]
                    ),
                ],
            )
        ]
    )
    assert render(doc) == "- a\n\n- b\n"


def test_bullet_list_checked():
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


def test_ordered_list_with_start():
    doc = blocks.Document(
        children=[
            blocks.OrderedList(
                start=3,
                items=[
                    blocks.ListItem(
                        children=[blocks.Paragraph(children=[inlines.Text(text="a")])]
                    ),
                    blocks.ListItem(
                        children=[blocks.Paragraph(children=[inlines.Text(text="b")])]
                    ),
                ],
            )
        ]
    )
    assert render(doc) == "3. a\n4. b\n"


def test_thematic_break():
    doc = blocks.Document(children=[blocks.ThematicBreak()])
    assert render(doc) == "---\n"


def test_table_with_alignment():
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableCell(children=[inlines.Text(text="Left")]),
                    blocks.TableCell(children=[inlines.Text(text="Center")]),
                    blocks.TableCell(children=[inlines.Text(text="Right")]),
                ],
                body=[
                    [
                        blocks.TableCell(children=[inlines.Text(text="a")]),
                        blocks.TableCell(children=[inlines.Text(text="b")]),
                        blocks.TableCell(children=[inlines.Text(text="c")]),
                    ]
                ],
                alignments=["left", "center", "right"],
            )
        ]
    )
    expected = "| Left | Center | Right |\n| :--- | :---: | ---: |\n| a | b | c |\n"
    assert render(doc) == expected


def test_table_empty_body():
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableCell(children=[inlines.Text(text="A")]),
                    blocks.TableCell(children=[inlines.Text(text="B")]),
                ],
                body=[],
            )
        ]
    )
    expected = "| A | B |\n| --- | --- |\n"
    assert render(doc) == expected


def test_table_body_pad_cells():
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableCell(children=[inlines.Text(text="A")]),
                    blocks.TableCell(children=[inlines.Text(text="B")]),
                    blocks.TableCell(children=[inlines.Text(text="C")]),
                ],
                body=[
                    [
                        blocks.TableCell(children=[inlines.Text(text="1")]),
                    ]
                ],
            )
        ]
    )
    expected = "| A | B | C |\n| --- | --- | --- |\n| 1 |  |  |\n"
    assert render(doc) == expected


def test_table_cell_hard_break_renders_as_br():
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableCell(children=[inlines.Text(text="Col")]),
                ],
                body=[
                    [
                        blocks.TableCell(
                            children=[
                                inlines.Strong(
                                    children=[inlines.Text(text="first")]
                                ),
                                inlines.HardBreak(),
                                inlines.Strong(
                                    children=[inlines.Text(text="second")]
                                ),
                            ]
                        ),
                    ]
                ],
            )
        ]
    )
    expected = "| Col |\n| --- |\n| **first**<br>**second** |\n"
    assert render(doc) == expected


# ── Inline renderers ──────────────────────────────────────────────────


def test_text():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.Text(text="hello")])]
    )
    assert render(doc) == "hello\n"


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


def test_strong_emphasis_nested():
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


def test_link():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Link(
                        url="https://example.com",
                        children=[inlines.Text(text="click")],
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
                        title="My Title",
                    )
                ]
            )
        ]
    )
    assert render(doc) == '[click](https://example.com "My Title")\n'


def test_image():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Image(url="https://example.com/img.png", alt="photo")]
            )
        ]
    )
    assert render(doc) == "![photo](https://example.com/img.png)\n"


def test_image_with_title():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Image(
                        url="https://example.com/img.png",
                        alt="photo",
                        title="My Image",
                    )
                ]
            )
        ]
    )
    assert render(doc) == '![photo](https://example.com/img.png "My Image")\n'


def test_code_span():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.CodeSpan(code="foo")])]
    )
    assert render(doc) == "`foo`\n"


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
                    inlines.Text(text="line1"),
                    inlines.HardBreak(),
                    inlines.Text(text="line2"),
                ]
            )
        ]
    )
    assert render(doc) == "line1\\\nline2\n"


def test_soft_break():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Text(text="line1"),
                    inlines.SoftBreak(),
                    inlines.Text(text="line2"),
                ]
            )
        ]
    )
    assert render(doc) == "line1\nline2\n"
