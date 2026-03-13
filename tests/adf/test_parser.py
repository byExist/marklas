from typing import Any

from marklas.adf.parser import parse
from marklas.nodes import blocks, inlines


def _doc(*content: dict[str, Any]) -> dict[str, Any]:
    return {"type": "doc", "version": 1, "content": list(content)}


# ── Intersection parsing ──────────────────────────────────────────────


def test_paragraph():
    doc = _doc({"type": "paragraph", "content": [{"type": "text", "text": "hello"}]})
    result = parse(doc)
    assert len(result.children) == 1
    p = result.children[0]
    assert isinstance(p, blocks.Paragraph)
    t = p.children[0]
    assert isinstance(t, inlines.Text)
    assert t.text == "hello"


def test_paragraph_empty():
    doc = _doc({"type": "paragraph"})
    result = parse(doc)
    p = result.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.children == []


def test_heading():
    doc = _doc(
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "title"}],
        }
    )
    h = parse(doc).children[0]
    assert isinstance(h, blocks.Heading)
    assert h.level == 2
    t = h.children[0]
    assert isinstance(t, inlines.Text)
    assert t.text == "title"


def test_code_block():
    doc = _doc(
        {
            "type": "codeBlock",
            "attrs": {"language": "python"},
            "content": [{"type": "text", "text": "x = 1"}],
        }
    )
    cb = parse(doc).children[0]
    assert isinstance(cb, blocks.CodeBlock)
    assert cb.code == "x = 1"
    assert cb.language == "python"


def test_blockquote():
    doc = _doc(
        {
            "type": "blockquote",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "q"}]}
            ],
        }
    )
    bq = parse(doc).children[0]
    assert isinstance(bq, blocks.BlockQuote)
    assert len(bq.children) == 1


def test_bullet_list():
    doc = _doc(
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
    )
    bl = parse(doc).children[0]
    assert isinstance(bl, blocks.BulletList)
    assert len(bl.items) == 1


def test_ordered_list():
    doc = _doc(
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
    )
    ol = parse(doc).children[0]
    assert isinstance(ol, blocks.OrderedList)
    assert ol.start == 3


def test_thematic_break():
    doc = _doc({"type": "rule"})
    assert isinstance(parse(doc).children[0], blocks.ThematicBreak)


def test_table_header():
    doc = _doc(
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
                        }
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
                        }
                    ],
                },
            ],
        }
    )
    table = parse(doc).children[0]
    assert isinstance(table, blocks.Table)
    assert len(table.head) == 1
    assert len(table.body) == 1


def test_text_marks():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "bold", "marks": [{"type": "strong"}]}
            ],
        }
    )
    p = parse(doc).children[0]
    assert isinstance(p, blocks.Paragraph)
    s = p.children[0]
    assert isinstance(s, inlines.Strong)
    inner = s.children[0]
    assert isinstance(inner, inlines.Text)
    assert inner.text == "bold"


def test_emphasis_and_strike():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "a", "marks": [{"type": "em"}]},
                {"type": "text", "text": "b", "marks": [{"type": "strike"}]},
            ],
        }
    )
    p = parse(doc).children[0]
    assert isinstance(p, blocks.Paragraph)
    assert isinstance(p.children[0], inlines.Emphasis)
    assert isinstance(p.children[1], inlines.Strikethrough)


def test_link_mark():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "click",
                    "marks": [{"type": "link", "attrs": {"href": "http://x"}}],
                }
            ],
        }
    )
    p = parse(doc).children[0]
    assert isinstance(p, blocks.Paragraph)
    link = p.children[0]
    assert isinstance(link, inlines.Link)
    assert link.url == "http://x"


def test_code_mark():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": "code", "marks": [{"type": "code"}]}],
        }
    )
    p = parse(doc).children[0]
    assert isinstance(p, blocks.Paragraph)
    cs = p.children[0]
    assert isinstance(cs, inlines.CodeSpan)
    assert cs.code == "code"


def test_text_and_hard_break():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "hello",
                },
                {"type": "hardBreak"},
            ],
        }
    )
    p = parse(doc).children[0]
    assert isinstance(p, blocks.Paragraph)
    assert isinstance(p.children[0], inlines.Text)
    assert isinstance(p.children[1], inlines.HardBreak)


def test_nested_marks():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "x",
                    "marks": [
                        {"type": "link", "attrs": {"href": "http://x"}},
                        {"type": "strong"},
                        {"type": "em"},
                    ],
                }
            ],
        }
    )
    p = parse(doc).children[0]
    assert isinstance(p, blocks.Paragraph)
    # link(0) > strong(1) > em(2) > Text
    link = p.children[0]
    assert isinstance(link, inlines.Link)
    strong = link.children[0]
    assert isinstance(strong, inlines.Strong)
    em = strong.children[0]
    assert isinstance(em, inlines.Emphasis)
    t = em.children[0]
    assert isinstance(t, inlines.Text)
    assert t.text == "x"


# ── Difference-set block parsing ──────────────────────────────────────


def test_panel():
    doc = _doc(
        {
            "type": "panel",
            "attrs": {"panelType": "info", "panelColor": "#eee"},
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "note"}]}
            ],
        }
    )
    panel = parse(doc).children[0]
    assert isinstance(panel, blocks.Panel)
    assert panel.panel_type == "info"
    assert panel.panel_color == "#eee"
    assert len(panel.children) == 1


def test_expand():
    doc = _doc(
        {
            "type": "expand",
            "attrs": {"title": "Details"},
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "body"}]}
            ],
        }
    )
    expand = parse(doc).children[0]
    assert isinstance(expand, blocks.Expand)
    assert expand.title == "Details"


def test_nested_expand():
    doc = _doc(
        {
            "type": "expand",
            "attrs": {"title": "Outer"},
            "content": [
                {
                    "type": "nestedExpand",
                    "attrs": {"title": "Inner"},
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "x"}],
                        }
                    ],
                }
            ],
        }
    )
    expand = parse(doc).children[0]
    assert isinstance(expand, blocks.Expand)
    ne = expand.children[0]
    assert isinstance(ne, blocks.NestedExpand)
    assert ne.title == "Inner"


def test_task_list():
    doc = _doc(
        {
            "type": "taskList",
            "attrs": {"localId": "tl-1"},
            "content": [
                {
                    "type": "taskItem",
                    "attrs": {"localId": "ti-1", "state": "DONE"},
                    "content": [{"type": "text", "text": "task 1"}],
                },
                {
                    "type": "taskItem",
                    "attrs": {"localId": "ti-2", "state": "TODO"},
                    "content": [{"type": "text", "text": "task 2"}],
                },
            ],
        }
    )
    tl = parse(doc).children[0]
    assert isinstance(tl, blocks.TaskList)
    assert len(tl.items) == 2
    assert tl.items[0].state == "DONE"
    assert tl.items[0].local_id == "ti-1"
    assert tl.items[1].state == "TODO"


def test_decision_list():
    doc = _doc(
        {
            "type": "decisionList",
            "attrs": {"localId": "dl-1"},
            "content": [
                {
                    "type": "decisionItem",
                    "attrs": {"localId": "di-1", "state": "DECIDED"},
                    "content": [{"type": "text", "text": "yes"}],
                }
            ],
        }
    )
    dl = parse(doc).children[0]
    assert isinstance(dl, blocks.DecisionList)
    assert dl.items[0].state == "DECIDED"


def test_layout_section():
    doc = _doc(
        {
            "type": "layoutSection",
            "content": [
                {
                    "type": "layoutColumn",
                    "attrs": {"width": 50.0},
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "left"}],
                        }
                    ],
                },
                {
                    "type": "layoutColumn",
                    "attrs": {"width": 50.0},
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "right"}],
                        }
                    ],
                },
            ],
        }
    )
    ls = parse(doc).children[0]
    assert isinstance(ls, blocks.LayoutSection)
    assert len(ls.columns) == 2
    assert ls.columns[0].width == 50.0


def test_media_single():
    doc = _doc(
        {
            "type": "mediaSingle",
            "attrs": {"layout": "center", "width": 80.0},
            "content": [
                {
                    "type": "media",
                    "attrs": {
                        "type": "external",
                        "url": "http://img.png",
                        "alt": "pic",
                    },
                }
            ],
        }
    )
    ms = parse(doc).children[0]
    assert isinstance(ms, blocks.MediaSingle)
    assert ms.layout == "center"
    assert ms.width == 80.0
    assert ms.media.media_type == "external"
    assert ms.media.url == "http://img.png"
    assert ms.media.alt == "pic"


def test_media_group():
    doc = _doc(
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
    )
    mg = parse(doc).children[0]
    assert isinstance(mg, blocks.MediaGroup)
    assert len(mg.media_list) == 2
    assert mg.media_list[0].id == "a"


def test_block_card():
    doc = _doc({"type": "blockCard", "attrs": {"url": "http://x"}})
    bc = parse(doc).children[0]
    assert isinstance(bc, blocks.BlockCard)
    assert bc.url == "http://x"


def test_embed_card():
    doc = _doc(
        {
            "type": "embedCard",
            "attrs": {"url": "http://x", "layout": "wide", "width": 100.0},
        }
    )
    ec = parse(doc).children[0]
    assert isinstance(ec, blocks.EmbedCard)
    assert ec.url == "http://x"
    assert ec.layout == "wide"
    assert ec.width == 100.0


def test_extension_raw():
    ext: dict[str, Any] = {
        "type": "extension",
        "attrs": {"extensionType": "t", "extensionKey": "k"},
    }
    doc = _doc(ext)
    e = parse(doc).children[0]
    assert isinstance(e, blocks.Extension)
    assert e.raw["type"] == "extension"
    assert e.raw["attrs"]["extensionKey"] == "k"


def test_bodied_extension_raw():
    ext: dict[str, Any] = {
        "type": "bodiedExtension",
        "attrs": {"extensionType": "t", "extensionKey": "k"},
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "x"}]}],
    }
    doc = _doc(ext)
    e = parse(doc).children[0]
    assert isinstance(e, blocks.BodiedExtension)
    assert e.raw["type"] == "bodiedExtension"


def test_sync_block_raw():
    ext: dict[str, Any] = {
        "type": "syncBlock",
        "attrs": {"resourceId": "r-1", "localId": "l-1"},
    }
    doc = _doc(ext)
    e = parse(doc).children[0]
    assert isinstance(e, blocks.SyncBlock)
    assert e.raw["type"] == "syncBlock"
    assert e.raw["attrs"]["resourceId"] == "r-1"


def test_bodied_sync_block_raw():
    ext: dict[str, Any] = {
        "type": "bodiedSyncBlock",
        "attrs": {"resourceId": "r-1", "localId": "l-1"},
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "x"}]}],
    }
    doc = _doc(ext)
    e = parse(doc).children[0]
    assert isinstance(e, blocks.BodiedSyncBlock)
    assert e.raw["type"] == "bodiedSyncBlock"


# ── Difference-set inline parsing ─────────────────────────────────────


def _first_inline(doc: dict[str, Any]) -> inlines.Inline:
    """Return the first inline of the first paragraph from parse(doc)."""
    p = parse(doc).children[0]
    assert isinstance(p, blocks.Paragraph)
    return p.children[0]


def test_mention():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "mention",
                    "attrs": {"id": "u1", "text": "John", "accessLevel": "CONTAINER"},
                }
            ],
        }
    )
    m = _first_inline(doc)
    assert isinstance(m, inlines.Mention)
    assert m.id == "u1"
    assert m.text == "John"
    assert m.access_level == "CONTAINER"


def test_emoji():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {"type": "emoji", "attrs": {"shortName": ":smile:", "text": "😄"}}
            ],
        }
    )
    e = _first_inline(doc)
    assert isinstance(e, inlines.Emoji)
    assert e.short_name == ":smile:"
    assert e.text == "😄"


def test_date():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [{"type": "date", "attrs": {"timestamp": "1234567890"}}],
        }
    )
    d = _first_inline(doc)
    assert isinstance(d, inlines.Date)
    assert d.timestamp == "1234567890"


def test_status():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "status",
                    "attrs": {"text": "Done", "color": "green", "style": "bold"},
                }
            ],
        }
    )
    s = _first_inline(doc)
    assert isinstance(s, inlines.Status)
    assert s.text == "Done"
    assert s.color == "green"
    assert s.style == "bold"


def test_inline_card():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [{"type": "inlineCard", "attrs": {"url": "http://x"}}],
        }
    )
    ic = _first_inline(doc)
    assert isinstance(ic, inlines.InlineCard)
    assert ic.url == "http://x"


def test_placeholder():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [{"type": "placeholder", "attrs": {"text": "Type here"}}],
        }
    )
    ph = _first_inline(doc)
    assert isinstance(ph, inlines.Placeholder)
    assert ph.text == "Type here"


def test_media_inline():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "mediaInline",
                    "attrs": {"id": "m1", "collection": "c1", "type": "file"},
                }
            ],
        }
    )
    mi = _first_inline(doc)
    assert isinstance(mi, inlines.MediaInline)
    assert mi.id == "m1"
    assert mi.media_type == "file"


def test_inline_extension_raw():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "inlineExtension",
                    "attrs": {"extensionType": "t", "extensionKey": "k"},
                }
            ],
        }
    )
    ie = _first_inline(doc)
    assert isinstance(ie, inlines.InlineExtension)
    assert ie.raw["type"] == "inlineExtension"


# ── Marks ─────────────────────────────────────────────────────────────


def test_underline_mark():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "u", "marks": [{"type": "underline"}]}
            ],
        }
    )
    u = _first_inline(doc)
    assert isinstance(u, inlines.Underline)
    t = u.children[0]
    assert isinstance(t, inlines.Text)
    assert t.text == "u"


def test_text_color_mark():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "red",
                    "marks": [{"type": "textColor", "attrs": {"color": "#ff0000"}}],
                }
            ],
        }
    )
    tc = _first_inline(doc)
    assert isinstance(tc, inlines.TextColor)
    assert tc.color == "#ff0000"


def test_background_color_mark():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "bg",
                    "marks": [
                        {"type": "backgroundColor", "attrs": {"color": "#00ff00"}}
                    ],
                }
            ],
        }
    )
    bg = _first_inline(doc)
    assert isinstance(bg, inlines.BackgroundColor)
    assert bg.color == "#00ff00"


def test_subsup_mark():
    doc = _doc(
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
    )
    ss = _first_inline(doc)
    assert isinstance(ss, inlines.SubSup)
    assert ss.type == "sup"


def test_annotation_mark():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "commented",
                    "marks": [{"type": "annotation", "attrs": {"id": "ann-1"}}],
                }
            ],
        }
    )
    ann = _first_inline(doc)
    assert isinstance(ann, inlines.Annotation)
    assert ann.id == "ann-1"


def test_mark_order():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "x",
                    "marks": [
                        {"type": "underline"},
                        {"type": "strong"},
                        {"type": "link", "attrs": {"href": "http://x"}},
                    ],
                }
            ],
        }
    )
    # sorted: link(0) > strong(1) > underline(4)
    link = _first_inline(doc)
    assert isinstance(link, inlines.Link)
    strong = link.children[0]
    assert isinstance(strong, inlines.Strong)
    underline = strong.children[0]
    assert isinstance(underline, inlines.Underline)


def test_code_mark_is_terminal():
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "x",
                    "marks": [
                        {"type": "textColor", "attrs": {"color": "#f00"}},
                        {"type": "code"},
                    ],
                }
            ],
        }
    )
    # sorted: textColor(5) > code(9) — textColor wraps CodeSpan
    tc = _first_inline(doc)
    assert isinstance(tc, inlines.TextColor)
    assert isinstance(tc.children[0], inlines.CodeSpan)


# ── Block marks ───────────────────────────────────────────────────────


def test_paragraph_alignment():
    doc = _doc(
        {
            "type": "paragraph",
            "marks": [{"type": "alignment", "attrs": {"align": "center"}}],
            "content": [{"type": "text", "text": "centered"}],
        }
    )
    p = parse(doc).children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.alignment == "center"


def test_heading_indentation():
    doc = _doc(
        {
            "type": "heading",
            "attrs": {"level": 1},
            "marks": [{"type": "indentation", "attrs": {"level": 2}}],
            "content": [{"type": "text", "text": "indented"}],
        }
    )
    h = parse(doc).children[0]
    assert isinstance(h, blocks.Heading)
    assert h.indentation == 2


# ── TableCell ─────────────────────────────────────────────────────────


def test_table_cell_block_children():
    doc = _doc(
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
                                    "content": [{"type": "text", "text": "a"}],
                                },
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "b"}],
                                },
                            ],
                        }
                    ],
                }
            ],
        }
    )
    table = parse(doc).children[0]
    assert isinstance(table, blocks.Table)
    cell = table.body[0][0]
    assert len(cell.children) == 2
    assert all(isinstance(c, blocks.Paragraph) for c in cell.children)


def test_table_cell_attrs():
    doc = _doc(
        {
            "type": "table",
            "content": [
                {
                    "type": "tableRow",
                    "content": [
                        {
                            "type": "tableCell",
                            "attrs": {
                                "colspan": 2,
                                "rowspan": 1,
                                "colwidth": [100, 200],
                                "background": "#eee",
                            },
                            "content": [{"type": "paragraph"}],
                        },
                        {
                            "type": "tableCell",
                            "content": [{"type": "paragraph"}],
                        },
                    ],
                }
            ],
        }
    )
    table = parse(doc).children[0]
    assert isinstance(table, blocks.Table)
    cell = table.body[0][0]
    assert cell.colspan == 2
    assert cell.rowspan == 1
    assert cell.col_width == [100, 200]
    assert cell.background == "#eee"


def test_table_attrs():
    doc = _doc(
        {
            "type": "table",
            "attrs": {
                "displayMode": "fixed",
                "isNumberColumnEnabled": True,
                "layout": "wide",
                "width": 760,
            },
            "content": [
                {
                    "type": "tableRow",
                    "content": [
                        {
                            "type": "tableCell",
                            "content": [{"type": "paragraph"}],
                        }
                    ],
                }
            ],
        }
    )
    table = parse(doc).children[0]
    assert isinstance(table, blocks.Table)
    assert table.display_mode == "fixed"
    assert table.is_number_column_enabled is True
    assert table.layout == "wide"
    assert table.width == 760


def test_table_header_cell_type():
    """tableHeader cells are parsed as TableHeader, tableCell as TableCell."""
    doc = _doc(
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
                            "type": "tableHeader",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Col"}],
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
    )
    table = parse(doc).children[0]
    assert isinstance(table, blocks.Table)
    # head: tableHeader from first row
    assert isinstance(table.head[0], blocks.TableHeader)
    # body row 0: tableHeader (column header)
    assert isinstance(table.body[0][0], blocks.TableHeader)
    # body row 1: tableCell
    assert isinstance(table.body[1][0], blocks.TableCell)
    assert not isinstance(table.body[1][0], blocks.TableHeader)


# ── Emoji surrogate pair decoding ─────────────────────────────────


def test_emoji_surrogate_pair_decoded():
    """Escaped surrogate pairs in emoji text are decoded to actual characters."""
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "emoji",
                    "attrs": {
                        "shortName": ":calendar_spiral:",
                        "text": "\\uD83D\\uDDD3",
                        "id": "1f5d3",
                    },
                }
            ],
        }
    )
    e = _first_inline(doc)
    assert isinstance(e, inlines.Emoji)
    assert e.text == "\U0001f5d3"


def test_emoji_fallback_to_id():
    """When text is absent, emoji text is derived from id code point."""
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "emoji",
                    "attrs": {
                        "shortName": ":calendar_spiral:",
                        "id": "1f5d3",
                    },
                }
            ],
        }
    )
    e = _first_inline(doc)
    assert isinstance(e, inlines.Emoji)
    assert e.text == "\U0001f5d3"


def test_emoji_normal_text_unchanged():
    """Normal Unicode emoji text is not modified."""
    doc = _doc(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "emoji",
                    "attrs": {"shortName": ":smile:", "text": "😄"},
                }
            ],
        }
    )
    e = _first_inline(doc)
    assert isinstance(e, inlines.Emoji)
    assert e.text == "😄"
