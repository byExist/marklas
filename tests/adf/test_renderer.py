"""ADF renderer tests: AST → ADF JSON"""

from __future__ import annotations

from typing import Any, cast

from marklas.adf.parser import parse
from marklas.adf.renderer import render
from marklas.nodes import blocks, inlines


# ── helpers ──────────────────────────────────────────────────────────


def _doc(*content: dict[str, Any]) -> dict[str, Any]:
    return {"type": "doc", "version": 1, "content": list(content)}


def _p(*content: dict[str, Any]) -> dict[str, Any]:
    return {"type": "paragraph", "content": list(content)}


def _text(t: str, **kwargs: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "text", "text": t}
    if kwargs:
        result.update(kwargs)
    return result


# ── Intersection block rendering ──────────────────────────────────────


def test_paragraph():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.Text(text="hello")])]
    )
    assert render(doc) == _doc(_p(_text("hello")))


def test_heading():
    doc = blocks.Document(
        children=[blocks.Heading(level=2, children=[inlines.Text(text="title")])]
    )
    result = render(doc)
    assert result["content"][0] == {
        "type": "heading",
        "attrs": {"level": 2},
        "content": [_text("title")],
    }


def test_code_block():
    doc = blocks.Document(children=[blocks.CodeBlock(code="x = 1", language="python")])
    result = render(doc)
    assert result["content"][0] == {
        "type": "codeBlock",
        "content": [_text("x = 1")],
        "attrs": {"language": "python"},
    }


def test_code_block_no_language():
    doc = blocks.Document(children=[blocks.CodeBlock(code="x")])
    result = render(doc)
    assert "attrs" not in result["content"][0]


def test_blockquote():
    doc = blocks.Document(
        children=[
            blocks.BlockQuote(
                children=[blocks.Paragraph(children=[inlines.Text(text="quoted")])]
            )
        ]
    )
    result = render(doc)
    assert result["content"][0] == {
        "type": "blockquote",
        "content": [_p(_text("quoted"))],
    }


def test_bullet_list():
    doc = blocks.Document(
        children=[
            blocks.BulletList(
                items=[
                    blocks.ListItem(
                        children=[blocks.Paragraph(children=[inlines.Text(text="a")])]
                    ),
                ]
            )
        ]
    )
    result = render(doc)
    assert result["content"][0]["type"] == "bulletList"
    assert result["content"][0]["content"][0]["type"] == "listItem"


def test_ordered_list():
    doc = blocks.Document(
        children=[
            blocks.OrderedList(
                items=[
                    blocks.ListItem(
                        children=[
                            blocks.Paragraph(children=[inlines.Text(text="first")])
                        ]
                    ),
                ],
                start=3,
            )
        ]
    )
    result = render(doc)
    assert result["content"][0]["attrs"] == {"order": 3}


def test_ordered_list_default_start():
    doc = blocks.Document(
        children=[
            blocks.OrderedList(
                items=[
                    blocks.ListItem(
                        children=[blocks.Paragraph(children=[inlines.Text(text="x")])]
                    ),
                ]
            )
        ]
    )
    result = render(doc)
    assert "attrs" not in result["content"][0]


def test_thematic_break():
    doc = blocks.Document(children=[blocks.ThematicBreak()])
    assert render(doc) == _doc({"type": "rule"})


def test_table():
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableHeader(
                        children=[blocks.Paragraph(children=[inlines.Text(text="H")])]
                    )
                ],
                body=[
                    [
                        blocks.TableCell(
                            children=[
                                blocks.Paragraph(children=[inlines.Text(text="D")])
                            ]
                        )
                    ]
                ],
            )
        ]
    )
    result = render(doc)
    table = result["content"][0]
    assert table["type"] == "table"
    assert table["content"][0]["content"][0]["type"] == "tableHeader"
    assert table["content"][1]["content"][0]["type"] == "tableCell"


# ── Intersection inline/marks rendering ───────────────────────────────


def test_strong():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Strong(children=[inlines.Text(text="bold")])]
            )
        ]
    )
    result = render(doc)
    assert result["content"][0]["content"] == [
        {"type": "text", "text": "bold", "marks": [{"type": "strong"}]}
    ]


def test_emphasis():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Emphasis(children=[inlines.Text(text="em")])]
            )
        ]
    )
    result = render(doc)
    assert result["content"][0]["content"][0]["marks"] == [{"type": "em"}]


def test_strikethrough():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Strikethrough(children=[inlines.Text(text="del")])]
            )
        ]
    )
    result = render(doc)
    assert result["content"][0]["content"][0]["marks"] == [{"type": "strike"}]


def test_link():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Link(url="http://x", children=[inlines.Text(text="link")])
                ]
            )
        ]
    )
    result = render(doc)
    marks = result["content"][0]["content"][0]["marks"]
    assert marks == [{"type": "link", "attrs": {"href": "http://x"}}]


def test_link_with_title():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Link(
                        url="http://x", children=[inlines.Text(text="link")], title="t"
                    )
                ]
            )
        ]
    )
    result = render(doc)
    marks = result["content"][0]["content"][0]["marks"]
    assert marks[0]["attrs"]["title"] == "t"


def test_code_span():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.CodeSpan(code="x")])]
    )
    result = render(doc)
    assert result["content"][0]["content"] == [
        {"type": "text", "text": "x", "marks": [{"type": "code"}]}
    ]


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
    result = render(doc)
    assert result["content"][0]["content"][1] == {"type": "hardBreak"}


def test_soft_break():
    doc = blocks.Document(children=[blocks.Paragraph(children=[inlines.SoftBreak()])])
    result = render(doc)
    assert result["content"][0]["content"] == [{"type": "text", "text": " "}]


def test_image_as_media_single():
    """Single Image in Paragraph converts to mediaSingle."""
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.Image(url="http://img.png")])]
    )
    result = render(doc)
    assert result["content"][0]["type"] == "mediaSingle"
    assert result["content"][0]["content"][0]["attrs"]["url"] == "http://img.png"


def test_image_inline_fallback():
    """Image with other inlines in Paragraph falls back to link."""
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Text(text="see "),
                    inlines.Image(url="http://img.png", alt="pic"),
                ]
            )
        ]
    )
    result = render(doc)
    content = result["content"][0]["content"]
    assert content[1]["text"] == "pic"
    assert content[1]["marks"][0]["attrs"]["href"] == "http://img.png"


def test_bullet_list_checked_to_task_list():
    """BulletList(checked) → taskList conversion (intersection reverse mapping)."""
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
    assert tl["content"][0]["attrs"]["state"] == "DONE"
    assert tl["content"][1]["attrs"]["state"] == "TODO"


def test_nested_marks_ordering():
    """Strong > Em → marks order strong, em."""
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Strong(
                        children=[inlines.Emphasis(children=[inlines.Text(text="bi")])]
                    )
                ]
            )
        ]
    )
    result = render(doc)
    marks = result["content"][0]["content"][0]["marks"]
    assert [m["type"] for m in marks] == ["strong", "em"]


# ── Difference-set block rendering ────────────────────────────────────


def test_panel():
    doc = blocks.Document(
        children=[
            blocks.Panel(
                children=[blocks.Paragraph(children=[inlines.Text(text="info")])],
                panel_type="info",
                panel_color="#EAE6FF",
            )
        ]
    )
    result = render(doc)
    panel = result["content"][0]
    assert panel["type"] == "panel"
    assert panel["attrs"]["panelType"] == "info"
    assert panel["attrs"]["panelColor"] == "#EAE6FF"


def test_panel_all_attrs():
    doc = blocks.Document(
        children=[
            blocks.Panel(
                children=[],
                panel_type="custom",
                panel_icon=":smile:",
                panel_icon_id="icon-1",
                panel_icon_text="Smile",
                panel_color="#FF0000",
            )
        ]
    )
    attrs = render(doc)["content"][0]["attrs"]
    assert attrs == {
        "panelType": "custom",
        "panelIcon": ":smile:",
        "panelIconId": "icon-1",
        "panelIconText": "Smile",
        "panelColor": "#FF0000",
    }


def test_expand():
    doc = blocks.Document(
        children=[
            blocks.Expand(
                children=[blocks.Paragraph(children=[inlines.Text(text="body")])],
                title="Details",
            )
        ]
    )
    result = render(doc)
    expand = result["content"][0]
    assert expand["type"] == "expand"
    assert expand["attrs"] == {"title": "Details"}


def test_expand_no_title():
    doc = blocks.Document(
        children=[blocks.Expand(children=[blocks.Paragraph(children=[])])]
    )
    assert "attrs" not in render(doc)["content"][0]


def test_nested_expand():
    doc = blocks.Document(
        children=[
            blocks.NestedExpand(
                children=[blocks.Paragraph(children=[inlines.Text(text="nested")])],
                title="More",
            )
        ]
    )
    result = render(doc)
    assert result["content"][0]["type"] == "nestedExpand"
    assert result["content"][0]["attrs"] == {"title": "More"}


def test_task_list():
    doc = blocks.Document(
        children=[
            blocks.TaskList(
                items=[
                    blocks.TaskItem(
                        children=[inlines.Text(text="task")],
                        state="TODO",
                        local_id="id-1",
                    ),
                ]
            )
        ]
    )
    result = render(doc)
    tl = result["content"][0]
    assert tl["type"] == "taskList"
    assert tl["content"][0]["attrs"]["localId"] == "id-1"
    assert tl["content"][0]["attrs"]["state"] == "TODO"
    assert tl["content"][0]["content"] == [_text("task")]


def test_task_list_empty_content():
    """taskItem with empty content should not have content key."""
    doc = blocks.Document(
        children=[
            blocks.TaskList(
                items=[
                    blocks.TaskItem(children=[], state="TODO", local_id="id-1"),
                ]
            )
        ]
    )
    result = render(doc)
    assert "content" not in result["content"][0]["content"][0]


def test_decision_list():
    doc = blocks.Document(
        children=[
            blocks.DecisionList(
                items=[
                    blocks.DecisionItem(
                        children=[inlines.Text(text="decide")],
                        state="DECIDED",
                        local_id="d-1",
                    ),
                ]
            )
        ]
    )
    result = render(doc)
    dl = result["content"][0]
    assert dl["type"] == "decisionList"
    assert dl["content"][0]["type"] == "decisionItem"
    assert dl["content"][0]["attrs"]["localId"] == "d-1"


def test_layout_section():
    doc = blocks.Document(
        children=[
            blocks.LayoutSection(
                columns=[
                    blocks.LayoutColumn(
                        children=[
                            blocks.Paragraph(children=[inlines.Text(text="left")])
                        ],
                        width=50.0,
                    ),
                    blocks.LayoutColumn(
                        children=[
                            blocks.Paragraph(children=[inlines.Text(text="right")])
                        ],
                        width=50.0,
                    ),
                ]
            )
        ]
    )
    result = render(doc)
    ls = result["content"][0]
    assert ls["type"] == "layoutSection"
    assert len(ls["content"]) == 2
    assert ls["content"][0]["attrs"]["width"] == 50.0


def test_layout_section_default_width():
    """Equal distribution when width is None."""
    doc = blocks.Document(
        children=[
            blocks.LayoutSection(
                columns=[
                    blocks.LayoutColumn(children=[]),
                    blocks.LayoutColumn(children=[]),
                ]
            )
        ]
    )
    result = render(doc)
    cols = result["content"][0]["content"]
    assert cols[0]["attrs"]["width"] == 50.0
    assert cols[1]["attrs"]["width"] == 50.0


def test_media_single():
    doc = blocks.Document(
        children=[
            blocks.MediaSingle(
                media=blocks.Media(media_type="external", url="http://img.png"),
                layout="center",
                width=640.0,
            )
        ]
    )
    result = render(doc)
    ms = result["content"][0]
    assert ms["type"] == "mediaSingle"
    assert ms["attrs"] == {"layout": "center", "width": 640.0}
    assert ms["content"][0]["attrs"]["url"] == "http://img.png"


def test_media_single_no_attrs():
    doc = blocks.Document(
        children=[
            blocks.MediaSingle(
                media=blocks.Media(media_type="external", url="http://img.png")
            )
        ]
    )
    assert "attrs" not in render(doc)["content"][0]


def test_media_group():
    doc = blocks.Document(
        children=[
            blocks.MediaGroup(
                media_list=[
                    blocks.Media(media_type="file", id="f-1", collection="c"),
                ]
            )
        ]
    )
    result = render(doc)
    mg = result["content"][0]
    assert mg["type"] == "mediaGroup"
    assert mg["content"][0]["attrs"] == {"type": "file", "id": "f-1", "collection": "c"}


def test_block_card():
    doc = blocks.Document(children=[blocks.BlockCard(url="http://card")])
    result = render(doc)
    assert result["content"][0] == {
        "type": "blockCard",
        "attrs": {"url": "http://card"},
    }


def test_embed_card():
    doc = blocks.Document(
        children=[blocks.EmbedCard(url="http://embed", layout="wide", width=100.0)]
    )
    result = render(doc)
    ec = result["content"][0]
    assert ec["type"] == "embedCard"
    assert ec["attrs"]["width"] == 100.0


def test_extension_raw():
    raw: dict[str, Any] = {
        "type": "extension",
        "attrs": {"extensionType": "t", "extensionKey": "k"},
    }
    doc = blocks.Document(children=[blocks.Extension(raw=raw)])
    assert render(doc)["content"][0] is raw


def test_bodied_extension_raw():
    raw: dict[str, Any] = {
        "type": "bodiedExtension",
        "attrs": {"extensionType": "t", "extensionKey": "k"},
    }
    doc = blocks.Document(children=[blocks.BodiedExtension(raw=raw)])
    assert render(doc)["content"][0] is raw


def test_sync_block_raw():
    raw: dict[str, Any] = {
        "type": "syncBlock",
        "attrs": {"resourceId": "r", "localId": "l"},
    }
    doc = blocks.Document(children=[blocks.SyncBlock(raw=raw)])
    assert render(doc)["content"][0] is raw


def test_bodied_sync_block_raw():
    raw: dict[str, Any] = {
        "type": "bodiedSyncBlock",
        "attrs": {"resourceId": "r", "localId": "l"},
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "x"}]}],
    }
    doc = blocks.Document(children=[blocks.BodiedSyncBlock(raw=raw)])
    assert render(doc)["content"][0] is raw


# ── Difference-set inline rendering ───────────────────────────────────


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
    assert result["content"][0]["content"][0] == {
        "type": "mention",
        "attrs": {"id": "user-1", "text": "@Alice", "userType": "DEFAULT"},
    }


def test_emoji():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(children=[inlines.Emoji(short_name=":smile:", id="e-1")])
        ]
    )
    result = render(doc)
    assert result["content"][0]["content"][0] == {
        "type": "emoji",
        "attrs": {"shortName": ":smile:", "id": "e-1"},
    }


def test_date():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.Date(timestamp="1234567890")])]
    )
    result = render(doc)
    assert result["content"][0]["content"][0] == {
        "type": "date",
        "attrs": {"timestamp": "1234567890"},
    }


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
    assert result["content"][0]["content"][0] == {
        "type": "status",
        "attrs": {"text": "In Progress", "color": "blue", "style": "bold"},
    }


def test_inline_card():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(children=[inlines.InlineCard(url="http://inline-card")])
        ]
    )
    result = render(doc)
    assert result["content"][0]["content"][0] == {
        "type": "inlineCard",
        "attrs": {"url": "http://inline-card"},
    }


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
    assert result["content"][0]["content"][0] == {
        "type": "mediaInline",
        "attrs": {"id": "m-1", "collection": "c", "type": "file"},
    }


def test_placeholder():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.Placeholder(text="Type here")])]
    )
    result = render(doc)
    assert result["content"][0]["content"][0] == {
        "type": "placeholder",
        "attrs": {"text": "Type here"},
    }


def test_inline_extension_raw():
    raw: dict[str, Any] = {"type": "inlineExtension", "attrs": {"extensionKey": "k"}}
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.InlineExtension(raw=raw)])]
    )
    assert render(doc)["content"][0]["content"][0] is raw


# ── Wrapping marks → ADF marks ────────────────────────────────────────


def test_underline():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Underline(children=[inlines.Text(text="u")])]
            )
        ]
    )
    result = render(doc)
    assert result["content"][0]["content"][0]["marks"] == [{"type": "underline"}]


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
    assert result["content"][0]["content"][0]["marks"] == [
        {"type": "textColor", "attrs": {"color": "#ff0000"}}
    ]


def test_background_color():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.BackgroundColor(
                        color="#00ff00", children=[inlines.Text(text="bg")]
                    )
                ]
            )
        ]
    )
    result = render(doc)
    assert result["content"][0]["content"][0]["marks"] == [
        {"type": "backgroundColor", "attrs": {"color": "#00ff00"}}
    ]


def test_subsup():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.SubSup(type="sub", children=[inlines.Text(text="2")])]
            )
        ]
    )
    result = render(doc)
    assert result["content"][0]["content"][0]["marks"] == [
        {"type": "subsup", "attrs": {"type": "sub"}}
    ]


def test_annotation():
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
    assert result["content"][0]["content"][0]["marks"] == [
        {
            "type": "annotation",
            "attrs": {"id": "ann-1", "annotationType": "inlineComment"},
        }
    ]


# ── Block marks ──────────────────────────────────────────────────────


def test_paragraph_alignment():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Text(text="centered")], alignment="center"
            )
        ]
    )
    result = render(doc)
    assert result["content"][0]["marks"] == [
        {"type": "alignment", "attrs": {"align": "center"}}
    ]


def test_heading_indentation():
    doc = blocks.Document(
        children=[
            blocks.Heading(
                level=1, children=[inlines.Text(text="indented")], indentation=2
            )
        ]
    )
    result = render(doc)
    assert result["content"][0]["marks"] == [
        {"type": "indentation", "attrs": {"level": 2}}
    ]


def test_paragraph_no_marks():
    """No marks key when alignment/indentation absent."""
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.Text(text="plain")])]
    )
    result = render(doc)
    assert "marks" not in result["content"][0]


# ── Table attrs ──────────────────────────────────────────────────────


def test_table_attrs():
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[],
                body=[],
                display_mode="fixed",
                is_number_column_enabled=True,
                layout="wide",
                width=760,
            )
        ]
    )
    result = render(doc)
    assert result["content"][0]["attrs"] == {
        "displayMode": "fixed",
        "isNumberColumnEnabled": True,
        "layout": "wide",
        "width": 760,
    }


def test_table_no_attrs():
    doc = blocks.Document(children=[blocks.Table(head=[], body=[])])
    assert "attrs" not in render(doc)["content"][0]


def test_cell_attrs():
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[],
                body=[
                    [
                        blocks.TableCell(
                            children=[
                                blocks.Paragraph(children=[inlines.Text(text="x")])
                            ],
                            colspan=2,
                            rowspan=3,
                            col_width=[100, 200],
                            background="#fff",
                        )
                    ]
                ],
            )
        ]
    )
    result = render(doc)
    cell = result["content"][0]["content"][0]["content"][0]
    assert cell["attrs"] == {
        "colspan": 2,
        "rowspan": 3,
        "colwidth": [100, 200],
        "background": "#fff",
    }


# ── ADF roundtrip ─────────────────────────────────────────────────────


def _strip_local_ids(obj: dict[str, Any]) -> dict[str, Any]:
    """Recursively strip localId to enable roundtrip comparison."""
    result: dict[str, Any] = {}
    for k, v in obj.items():
        if k == "localId":
            continue
        if isinstance(v, dict):
            result[k] = _strip_local_ids(cast(dict[str, Any], v))
        elif isinstance(v, list):
            result[k] = [
                _strip_local_ids(cast(dict[str, Any], item))
                if isinstance(item, dict)
                else item
                for item in cast(list[Any], v)
            ]
        else:
            result[k] = v
    return result


def test_roundtrip_paragraph():
    adf: dict[str, Any] = _doc(_p(_text("hello")))
    assert render(parse(adf)) == adf


def test_roundtrip_heading():
    adf: dict[str, Any] = _doc(
        {
            "type": "heading",
            "attrs": {"level": 3},
            "content": [_text("title")],
        }
    )
    assert render(parse(adf)) == adf


def test_roundtrip_code_block():
    adf: dict[str, Any] = _doc(
        {
            "type": "codeBlock",
            "content": [_text("code")],
            "attrs": {"language": "python"},
        }
    )
    assert render(parse(adf)) == adf


def test_roundtrip_marks():
    adf: dict[str, Any] = _doc(_p(_text("bold", marks=[{"type": "strong"}])))
    assert render(parse(adf)) == adf


def test_roundtrip_link():
    adf: dict[str, Any] = _doc(
        _p(_text("link", marks=[{"type": "link", "attrs": {"href": "http://x"}}]))
    )
    assert render(parse(adf)) == adf


def test_roundtrip_bullet_list():
    adf: dict[str, Any] = _doc(
        {
            "type": "bulletList",
            "content": [{"type": "listItem", "content": [_p(_text("a"))]}],
        }
    )
    assert render(parse(adf)) == adf


def test_roundtrip_ordered_list():
    adf: dict[str, Any] = _doc(
        {
            "type": "orderedList",
            "content": [{"type": "listItem", "content": [_p(_text("1"))]}],
            "attrs": {"order": 5},
        }
    )
    assert render(parse(adf)) == adf


def test_roundtrip_blockquote():
    adf: dict[str, Any] = _doc(
        {
            "type": "blockquote",
            "content": [_p(_text("q"))],
        }
    )
    assert render(parse(adf)) == adf


def test_roundtrip_rule():
    adf: dict[str, Any] = _doc({"type": "rule"})
    assert render(parse(adf)) == adf


def test_roundtrip_table():
    adf: dict[str, Any] = _doc(
        {
            "type": "table",
            "content": [
                {
                    "type": "tableRow",
                    "content": [
                        {"type": "tableHeader", "content": [_p(_text("H"))]},
                    ],
                },
                {
                    "type": "tableRow",
                    "content": [
                        {"type": "tableCell", "content": [_p(_text("D"))]},
                    ],
                },
            ],
        }
    )
    assert render(parse(adf)) == adf


def test_roundtrip_table_with_attrs():
    adf: dict[str, Any] = _doc(
        {
            "type": "table",
            "content": [
                {
                    "type": "tableRow",
                    "content": [
                        {
                            "type": "tableCell",
                            "content": [_p(_text("x"))],
                            "attrs": {"colspan": 2, "background": "#eee"},
                        },
                    ],
                },
            ],
            "attrs": {"layout": "wide", "isNumberColumnEnabled": False},
        }
    )
    assert render(parse(adf)) == adf


def test_roundtrip_panel():
    adf: dict[str, Any] = _doc(
        {
            "type": "panel",
            "attrs": {"panelType": "info"},
            "content": [_p(_text("panel text"))],
        }
    )
    assert render(parse(adf)) == adf


def test_roundtrip_expand():
    adf: dict[str, Any] = _doc(
        {
            "type": "expand",
            "content": [_p(_text("body"))],
            "attrs": {"title": "Title"},
        }
    )
    assert render(parse(adf)) == adf


def test_roundtrip_task_list():
    adf: dict[str, Any] = _doc(
        {
            "type": "taskList",
            "attrs": {"localId": "tl-1"},
            "content": [
                {
                    "type": "taskItem",
                    "attrs": {"localId": "ti-1", "state": "TODO"},
                    "content": [_text("task")],
                }
            ],
        }
    )
    result = render(parse(adf))
    assert _strip_local_ids(result) == _strip_local_ids(adf)


def test_roundtrip_decision_list():
    adf: dict[str, Any] = _doc(
        {
            "type": "decisionList",
            "attrs": {"localId": "dl-1"},
            "content": [
                {
                    "type": "decisionItem",
                    "attrs": {"localId": "di-1", "state": "DECIDED"},
                    "content": [_text("decide")],
                }
            ],
        }
    )
    result = render(parse(adf))
    assert _strip_local_ids(result) == _strip_local_ids(adf)


def test_roundtrip_layout_section():
    adf: dict[str, Any] = _doc(
        {
            "type": "layoutSection",
            "content": [
                {
                    "type": "layoutColumn",
                    "attrs": {"width": 50.0},
                    "content": [_p(_text("left"))],
                },
                {
                    "type": "layoutColumn",
                    "attrs": {"width": 50.0},
                    "content": [_p(_text("right"))],
                },
            ],
        }
    )
    assert render(parse(adf)) == adf


def test_roundtrip_media_single():
    adf: dict[str, Any] = _doc(
        {
            "type": "mediaSingle",
            "content": [
                {
                    "type": "media",
                    "attrs": {"type": "external", "url": "http://img.png"},
                }
            ],
            "attrs": {"layout": "center"},
        }
    )
    assert render(parse(adf)) == adf


def test_roundtrip_media_group():
    adf: dict[str, Any] = _doc(
        {
            "type": "mediaGroup",
            "content": [
                {
                    "type": "media",
                    "attrs": {"type": "file", "id": "f-1", "collection": "c"},
                },
            ],
        }
    )
    assert render(parse(adf)) == adf


def test_roundtrip_block_card():
    adf: dict[str, Any] = _doc(
        {
            "type": "blockCard",
            "attrs": {"url": "http://card"},
        }
    )
    assert render(parse(adf)) == adf


def test_roundtrip_embed_card():
    adf: dict[str, Any] = _doc(
        {
            "type": "embedCard",
            "attrs": {"url": "http://embed", "layout": "wide"},
        }
    )
    assert render(parse(adf)) == adf


def test_roundtrip_extension():
    adf: dict[str, Any] = _doc(
        {
            "type": "extension",
            "attrs": {"extensionType": "com.test", "extensionKey": "key"},
        }
    )
    assert render(parse(adf)) == adf


def test_roundtrip_mention():
    adf: dict[str, Any] = _doc(
        _p(
            {
                "type": "mention",
                "attrs": {"id": "user-1", "text": "@Alice"},
            }
        )
    )
    assert render(parse(adf)) == adf


def test_roundtrip_emoji():
    adf: dict[str, Any] = _doc(
        _p(
            {
                "type": "emoji",
                "attrs": {"shortName": ":smile:"},
            }
        )
    )
    assert render(parse(adf)) == adf


def test_roundtrip_date():
    adf: dict[str, Any] = _doc(
        _p(
            {
                "type": "date",
                "attrs": {"timestamp": "1234567890"},
            }
        )
    )
    assert render(parse(adf)) == adf


def test_roundtrip_status():
    adf: dict[str, Any] = _doc(
        _p(
            {
                "type": "status",
                "attrs": {"text": "Done", "color": "green"},
            }
        )
    )
    result = render(parse(adf))
    assert _strip_local_ids(result) == _strip_local_ids(adf)


def test_roundtrip_inline_card():
    adf: dict[str, Any] = _doc(
        _p(
            {
                "type": "inlineCard",
                "attrs": {"url": "http://ic"},
            }
        )
    )
    assert render(parse(adf)) == adf


def test_roundtrip_placeholder():
    adf: dict[str, Any] = _doc(
        _p(
            {
                "type": "placeholder",
                "attrs": {"text": "Type here"},
            }
        )
    )
    assert render(parse(adf)) == adf


def test_roundtrip_underline():
    adf: dict[str, Any] = _doc(_p(_text("u", marks=[{"type": "underline"}])))
    assert render(parse(adf)) == adf


def test_roundtrip_text_color():
    adf: dict[str, Any] = _doc(
        _p(_text("red", marks=[{"type": "textColor", "attrs": {"color": "#ff0000"}}]))
    )
    assert render(parse(adf)) == adf


def test_roundtrip_subsup():
    adf: dict[str, Any] = _doc(
        _p(_text("2", marks=[{"type": "subsup", "attrs": {"type": "sub"}}]))
    )
    assert render(parse(adf)) == adf


def test_roundtrip_annotation():
    adf: dict[str, Any] = _doc(
        _p(
            _text(
                "noted",
                marks=[
                    {
                        "type": "annotation",
                        "attrs": {"id": "ann-1", "annotationType": "inlineComment"},
                    }
                ],
            )
        )
    )
    assert render(parse(adf)) == adf


def test_roundtrip_background_color():
    adf: dict[str, Any] = _doc(
        _p(
            _text(
                "bg", marks=[{"type": "backgroundColor", "attrs": {"color": "#00ff00"}}]
            )
        )
    )
    assert render(parse(adf)) == adf


def test_roundtrip_media_inline():
    adf: dict[str, Any] = _doc(
        _p(
            {
                "type": "mediaInline",
                "attrs": {"id": "m-1", "collection": "c", "type": "file"},
            }
        )
    )
    assert render(parse(adf)) == adf


def test_roundtrip_inline_extension():
    adf: dict[str, Any] = _doc(
        _p(
            {
                "type": "inlineExtension",
                "attrs": {"extensionType": "com.test", "extensionKey": "key"},
            }
        )
    )
    assert render(parse(adf)) == adf


def test_roundtrip_block_marks():
    adf: dict[str, Any] = _doc(
        {
            "type": "paragraph",
            "content": [_text("centered")],
            "marks": [{"type": "alignment", "attrs": {"align": "center"}}],
        }
    )
    assert render(parse(adf)) == adf


def test_table_column_headers():
    """TableHeader cells in body rows render as tableHeader type."""
    doc = blocks.Document(
        children=[
            blocks.Table(
                head=[
                    blocks.TableHeader(
                        children=[blocks.Paragraph(children=[inlines.Text(text="H")])]
                    )
                ],
                body=[
                    [
                        blocks.TableHeader(
                            children=[
                                blocks.Paragraph(children=[inlines.Text(text="Col")])
                            ]
                        )
                    ],
                    [
                        blocks.TableCell(
                            children=[
                                blocks.Paragraph(children=[inlines.Text(text="D")])
                            ]
                        )
                    ],
                ],
            )
        ]
    )
    result = render(doc)
    table = result["content"][0]
    # row 0: head → tableHeader
    assert table["content"][0]["content"][0]["type"] == "tableHeader"
    # row 1: body TableHeader → tableHeader
    assert table["content"][1]["content"][0]["type"] == "tableHeader"
    # row 2: body TableCell → tableCell
    assert table["content"][2]["content"][0]["type"] == "tableCell"
