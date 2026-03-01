from typing import Any

from marklas.ast import blocks, inlines
from marklas.renderer.adf import render as _render_adf


def render(doc: blocks.Document) -> Any:
    return _render_adf(doc)


# ── Block renderers ──────────────────────────────────────────────────


def test_empty_doc():
    result = render(blocks.Document(children=[]))
    assert result == {"type": "doc", "version": 1, "content": []}


def test_paragraph():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.Text(text="Hello")])]
    )
    result = render(doc)
    assert result["content"] == [
        {"type": "paragraph", "content": [{"type": "text", "text": "Hello"}]}
    ]


def test_empty_paragraph():
    doc = blocks.Document(children=[blocks.Paragraph(children=[])])
    result = render(doc)
    assert result["content"] == [{"type": "paragraph", "content": []}]


def test_heading_levels():
    for level in (1, 2, 3, 4, 5, 6):
        doc = blocks.Document(
            children=[
                blocks.Heading(level=level, children=[inlines.Text(text="Title")])
            ]
        )
        result = render(doc)
        heading = result["content"][0]
        assert heading["type"] == "heading"
        assert heading["attrs"]["level"] == level
        assert heading["content"] == [{"type": "text", "text": "Title"}]


def test_code_block_with_language():
    doc = blocks.Document(
        children=[blocks.CodeBlock(code="print('hi')", language="python")]
    )
    result = render(doc)
    cb = result["content"][0]
    assert cb["type"] == "codeBlock"
    assert cb.get("attrs", {}).get("language") == "python"
    assert cb["content"] == [{"type": "text", "text": "print('hi')"}]


def test_code_block_no_language():
    doc = blocks.Document(children=[blocks.CodeBlock(code="hello")])
    result = render(doc)
    cb = result["content"][0]
    assert cb["type"] == "codeBlock"
    assert "attrs" not in cb
    assert cb["content"] == [{"type": "text", "text": "hello"}]


def test_blockquote():
    doc = blocks.Document(
        children=[
            blocks.BlockQuote(
                children=[blocks.Paragraph(children=[inlines.Text(text="quoted")])]
            )
        ]
    )
    result = render(doc)
    bq = result["content"][0]
    assert bq["type"] == "blockquote"
    assert bq["content"] == [
        {"type": "paragraph", "content": [{"type": "text", "text": "quoted"}]}
    ]


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
    result = render(doc)
    outer = result["content"][0]
    assert outer["type"] == "blockquote"
    inner = outer["content"][0]
    assert inner["type"] == "blockquote"
    assert inner["content"][0]["content"] == [{"type": "text", "text": "deep"}]


def test_thematic_break():
    doc = blocks.Document(children=[blocks.ThematicBreak()])
    result = render(doc)
    assert result["content"] == [{"type": "rule"}]


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
    result = render(doc)
    lst = result["content"][0]
    assert lst["type"] == "bulletList"
    assert len(lst["content"]) == 2
    assert lst["content"][0]["type"] == "listItem"


def test_bullet_list_task():
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
    result = render(doc)
    tl = result["content"][0]
    assert tl["type"] == "taskList"
    assert "localId" in tl["attrs"]
    assert len(tl["content"]) == 2
    item0 = tl["content"][0]
    assert item0["type"] == "taskItem"
    assert item0["attrs"]["state"] == "DONE"
    assert "localId" in item0["attrs"]
    item1 = tl["content"][1]
    assert item1["attrs"]["state"] == "TODO"


def test_ordered_list():
    doc = blocks.Document(
        children=[
            blocks.OrderedList(
                items=[
                    blocks.ListItem(
                        children=[blocks.Paragraph(children=[inlines.Text(text="a")])]
                    ),
                ]
            )
        ]
    )
    result = render(doc)
    lst = result["content"][0]
    assert lst["type"] == "orderedList"
    assert lst["content"][0]["type"] == "listItem"


def test_ordered_list_start():
    doc = blocks.Document(
        children=[
            blocks.OrderedList(
                start=3,
                items=[
                    blocks.ListItem(
                        children=[blocks.Paragraph(children=[inlines.Text(text="a")])]
                    ),
                ],
            )
        ]
    )
    result = render(doc)
    lst = result["content"][0]
    assert lst["attrs"]["order"] == 3


def test_ordered_list_start_default():
    doc = blocks.Document(
        children=[
            blocks.OrderedList(
                items=[
                    blocks.ListItem(
                        children=[blocks.Paragraph(children=[inlines.Text(text="a")])]
                    ),
                ]
            )
        ]
    )
    result = render(doc)
    lst = result["content"][0]
    assert "attrs" not in lst


def test_nested_list():
    doc = blocks.Document(
        children=[
            blocks.BulletList(
                items=[
                    blocks.ListItem(
                        children=[
                            blocks.Paragraph(children=[inlines.Text(text="a")]),
                            blocks.BulletList(
                                items=[
                                    blocks.ListItem(
                                        children=[
                                            blocks.Paragraph(
                                                children=[inlines.Text(text="b")]
                                            )
                                        ]
                                    )
                                ]
                            ),
                        ]
                    )
                ]
            )
        ]
    )
    result = render(doc)
    outer = result["content"][0]
    assert outer["type"] == "bulletList"
    item = outer["content"][0]
    assert item["type"] == "listItem"
    assert len(item["content"]) == 2
    inner = item["content"][1]
    assert inner["type"] == "bulletList"


def test_list_item_multi_block():
    doc = blocks.Document(
        children=[
            blocks.BulletList(
                items=[
                    blocks.ListItem(
                        children=[
                            blocks.Paragraph(children=[inlines.Text(text="para")]),
                            blocks.CodeBlock(code="code"),
                        ]
                    )
                ]
            )
        ]
    )
    result = render(doc)
    item = result["content"][0]["content"][0]
    types = [c["type"] for c in item["content"]]
    assert "paragraph" in types
    assert "codeBlock" in types


def test_table_header_body():
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableCell(children=[inlines.Text(text="A")]),
                    blocks.TableCell(children=[inlines.Text(text="B")]),
                ],
                body=[
                    [
                        blocks.TableCell(children=[inlines.Text(text="1")]),
                        blocks.TableCell(children=[inlines.Text(text="2")]),
                    ]
                ],
            )
        ]
    )
    result = render(doc)
    tbl = result["content"][0]
    assert tbl["type"] == "table"
    assert len(tbl["content"]) == 2
    header_row = tbl["content"][0]
    assert header_row["content"][0]["type"] == "tableHeader"
    assert header_row["content"][0]["content"] == [
        {"type": "paragraph", "content": [{"type": "text", "text": "A"}]}
    ]
    body_row = tbl["content"][1]
    assert body_row["content"][0]["type"] == "tableCell"


def test_table_empty_body():
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableCell(children=[inlines.Text(text="A")]),
                ],
                body=[],
            )
        ]
    )
    result = render(doc)
    tbl = result["content"][0]
    assert len(tbl["content"]) == 1
    assert tbl["content"][0]["content"][0]["type"] == "tableHeader"


def test_table_alignment_ignored():
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[blocks.TableCell(children=[inlines.Text(text="A")])],
                body=[],
                alignments=["left", "center", "right"],
            )
        ]
    )
    result = render(doc)
    tbl = result["content"][0]
    assert "attrs" not in tbl or "alignment" not in tbl.get("attrs", {})


def test_paragraph_single_image():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Image(url="https://example.com/img.png", alt="photo")]
            )
        ]
    )
    result = render(doc)
    ms = result["content"][0]
    assert ms["type"] == "mediaSingle"
    media = ms["content"][0]
    assert media["type"] == "media"
    assert media["attrs"]["type"] == "external"
    assert media["attrs"]["url"] == "https://example.com/img.png"


def test_paragraph_image_with_text():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Text(text="See "),
                    inlines.Image(url="https://example.com/img.png", alt="photo"),
                ]
            )
        ]
    )
    result = render(doc)
    para = result["content"][0]
    assert para["type"] == "paragraph"
    # Image는 link mark + alt 텍스트로 fallback
    assert len(para["content"]) == 2
    img_inline = para["content"][1]
    assert img_inline["type"] == "text"
    assert img_inline["text"] == "photo"
    link_mark = next(m for m in img_inline["marks"] if m["type"] == "link")
    assert link_mark["attrs"]["href"] == "https://example.com/img.png"


# ── Inline renderers ─────────────────────────────────────────────────


def test_text():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.Text(text="hello")])]
    )
    result = render(doc)
    para = result["content"][0]
    assert para["content"] == [{"type": "text", "text": "hello"}]


def test_text_empty():
    doc = blocks.Document(children=[blocks.Paragraph(children=[inlines.Text(text="")])])
    result = render(doc)
    para = result["content"][0]
    assert para["content"] == []


def test_strong():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Strong(children=[inlines.Text(text="bold")])]
            )
        ]
    )
    result = render(doc)
    text_node = result["content"][0]["content"][0]
    assert text_node["text"] == "bold"
    assert text_node["marks"] == [{"type": "strong"}]


def test_emphasis():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Emphasis(children=[inlines.Text(text="italic")])]
            )
        ]
    )
    result = render(doc)
    text_node = result["content"][0]["content"][0]
    assert text_node["text"] == "italic"
    assert text_node["marks"] == [{"type": "em"}]


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
    result = render(doc)
    text_node = result["content"][0]["content"][0]
    assert text_node["text"] == "deleted"
    assert text_node["marks"] == [{"type": "strike"}]


def test_code_span():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.CodeSpan(code="code")])]
    )
    result = render(doc)
    text_node = result["content"][0]["content"][0]
    assert text_node["type"] == "text"
    assert text_node["text"] == "code"
    assert text_node["marks"] == [{"type": "code"}]


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
    result = render(doc)
    text_node = result["content"][0]["content"][0]
    assert text_node["text"] == "click"
    link_mark = text_node["marks"][0]
    assert link_mark["type"] == "link"
    assert link_mark["attrs"]["href"] == "https://example.com"


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
    result = render(doc)
    text_node = result["content"][0]["content"][0]
    link_mark = text_node["marks"][0]
    assert link_mark["attrs"]["title"] == "My Title"


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
    result = render(doc)
    text_node = result["content"][0]["content"][0]
    assert text_node["text"] == "both"
    mark_types = [m["type"] for m in text_node["marks"]]
    assert "strong" in mark_types
    assert "em" in mark_types


def test_marks_order():
    # link > strong > em > strike > code 순서 검증
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Link(
                        url="https://example.com",
                        children=[
                            inlines.Strong(
                                children=[
                                    inlines.Emphasis(children=[inlines.Text(text="x")])
                                ]
                            )
                        ],
                    )
                ]
            )
        ]
    )
    result = render(doc)
    text_node = result["content"][0]["content"][0]
    mark_types = [m["type"] for m in text_node["marks"]]
    assert mark_types == ["link", "strong", "em"]


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
    result = render(doc)
    content = result["content"][0]["content"]
    assert content == [
        {"type": "text", "text": "line1"},
        {"type": "hardBreak"},
        {"type": "text", "text": "line2"},
    ]


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
    result = render(doc)
    content = result["content"][0]["content"]
    assert content == [
        {"type": "text", "text": "line1"},
        {"type": "text", "text": " "},
        {"type": "text", "text": "line2"},
    ]


def test_image_inline_fallback():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Text(text="See "),
                    inlines.Image(url="https://example.com/img.png", alt="photo"),
                ]
            )
        ]
    )
    result = render(doc)
    content = result["content"][0]["content"]
    assert content[0] == {"type": "text", "text": "See "}
    img_text = content[1]
    assert img_text["type"] == "text"
    assert img_text["text"] == "photo"
    marks = img_text["marks"]
    assert any(m["type"] == "link" for m in marks)
    link_mark = next(m for m in marks if m["type"] == "link")
    assert link_mark["attrs"]["href"] == "https://example.com/img.png"
