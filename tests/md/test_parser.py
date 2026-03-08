"""MD parser 테스트: Markdown → AST"""

from __future__ import annotations

from marklas.md.parser import parse
from marklas.md.renderer import render
from marklas.nodes import blocks, inlines


# ── 교집합 블록 파싱 ───────────────────────────────────────────────


def test_paragraph():
    doc = parse("hello world\n")
    assert len(doc.children) == 1
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert len(p.children) == 1
    assert isinstance(p.children[0], inlines.Text)
    assert p.children[0].text == "hello world"


def test_heading_levels():
    for level in (1, 2, 3, 4, 5, 6):
        doc = parse(f"{'#' * level} title\n")
        assert len(doc.children) == 1
        h = doc.children[0]
        assert isinstance(h, blocks.Heading)
        assert h.level == level
        assert isinstance(h.children[0], inlines.Text)
        assert h.children[0].text == "title"


def test_code_block_with_language():
    doc = parse("```python\nprint(1)\n```\n")
    assert len(doc.children) == 1
    cb = doc.children[0]
    assert isinstance(cb, blocks.CodeBlock)
    assert cb.code == "print(1)"
    assert cb.language == "python"


def test_code_block_without_language():
    doc = parse("```\nhello\n```\n")
    cb = doc.children[0]
    assert isinstance(cb, blocks.CodeBlock)
    assert cb.code == "hello"
    assert cb.language is None


def test_blockquote():
    doc = parse("> quoted\n")
    assert len(doc.children) == 1
    bq = doc.children[0]
    assert isinstance(bq, blocks.BlockQuote)
    assert len(bq.children) == 1
    assert isinstance(bq.children[0], blocks.Paragraph)


def test_bullet_list():
    doc = parse("- a\n- b\n")
    bl = doc.children[0]
    assert isinstance(bl, blocks.BulletList)
    assert len(bl.items) == 2
    assert isinstance(bl.items[0], blocks.ListItem)


def test_ordered_list():
    doc = parse("3. a\n4. b\n")
    ol = doc.children[0]
    assert isinstance(ol, blocks.OrderedList)
    assert ol.start == 3
    assert len(ol.items) == 2


def test_bullet_list_with_checkbox():
    doc = parse("- [x] done\n- [ ] todo\n")
    bl = doc.children[0]
    assert isinstance(bl, blocks.BulletList)
    assert bl.items[0].checked is True
    assert bl.items[1].checked is False


def test_thematic_break():
    doc = parse("---\n")
    assert isinstance(doc.children[0], blocks.ThematicBreak)


def test_multiple_blocks():
    doc = parse("a\n\nb\n")
    paragraphs = [
        c for c in doc.children if isinstance(c, blocks.Paragraph) and c.children
    ]
    assert len(paragraphs) == 2


def test_empty_document():
    doc = parse("")
    non_empty = [
        c for c in doc.children if not isinstance(c, blocks.Paragraph) or c.children
    ]
    assert len(non_empty) == 0


# ── Table ────────────────────────────────────────────────────────────


def test_table_basic():
    md = "| A | B |\n| --- | --- |\n| 1 | 2 |\n"
    doc = parse(md)
    t = doc.children[0]
    assert isinstance(t, blocks.Table)
    assert len(t.head) == 2
    assert len(t.body) == 1
    assert len(t.body[0]) == 2


def test_table_cell_has_block_children():
    md = "| A |\n| --- |\n"
    doc = parse(md)
    t = doc.children[0]
    assert isinstance(t, blocks.Table)
    cell = t.head[0]
    assert isinstance(cell.children[0], blocks.Paragraph)


def test_table_alignments():
    md = "| L | C | R |\n| :--- | :---: | ---: |\n"
    doc = parse(md)
    t = doc.children[0]
    assert isinstance(t, blocks.Table)
    assert t.alignments == ["left", "center", "right"]


# ── 교집합 인라인 파싱 ─────────────────────────────────────────────


def test_strong():
    doc = parse("**bold**\n")
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert isinstance(p.children[0], inlines.Strong)


def test_emphasis():
    doc = parse("*italic*\n")
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert isinstance(p.children[0], inlines.Emphasis)


def test_strikethrough():
    doc = parse("~~deleted~~\n")
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert isinstance(p.children[0], inlines.Strikethrough)


def test_link():
    doc = parse("[click](https://example.com)\n")
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    link = p.children[0]
    assert isinstance(link, inlines.Link)
    assert link.url == "https://example.com"


def test_link_with_title():
    doc = parse('[click](https://example.com "hint")\n')
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    link = p.children[0]
    assert isinstance(link, inlines.Link)
    assert link.title == "hint"


def test_image():
    doc = parse("![photo](https://img.png)\n")
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    img = p.children[0]
    assert isinstance(img, inlines.Image)
    assert img.url == "https://img.png"
    assert img.alt == "photo"


def test_code_span():
    doc = parse("`x=1`\n")
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    cs = p.children[0]
    assert isinstance(cs, inlines.CodeSpan)
    assert cs.code == "x=1"


def test_hard_break():
    doc = parse("a\\\nb\n")
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert isinstance(p.children[1], inlines.HardBreak)


def test_nested_marks():
    doc = parse("***both***\n")
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    # mistune의 파싱 순서에 따라 Strong > Emphasis 또는 반대
    outer = p.children[0]
    assert isinstance(outer, (inlines.Strong, inlines.Emphasis))


# ── 블록 주석 복원 ──────────────────────────────────────────────────


def test_panel_annotation():
    md = '<!-- adf:panel {"panelType": "info"} -->\nnote\n<!-- /adf:panel -->\n'
    doc = parse(md)
    panel = doc.children[0]
    assert isinstance(panel, blocks.Panel)
    assert panel.panel_type == "info"
    assert len(panel.children) == 1
    assert isinstance(panel.children[0], blocks.Paragraph)


def test_panel_all_attrs():
    md = (
        '<!-- adf:panel {"panelType": "custom", "panelIcon": ":star:", '
        '"panelIconId": "icon-1", "panelIconText": "Star", "panelColor": "#ff0"} -->\n'
        "x\n"
        "<!-- /adf:panel -->\n"
    )
    doc = parse(md)
    panel = doc.children[0]
    assert isinstance(panel, blocks.Panel)
    assert panel.panel_icon == ":star:"
    assert panel.panel_icon_id == "icon-1"
    assert panel.panel_icon_text == "Star"
    assert panel.panel_color == "#ff0"


def test_expand_annotation():
    md = '<!-- adf:expand {"title": "Details"} -->\ncontent\n<!-- /adf:expand -->\n'
    doc = parse(md)
    expand = doc.children[0]
    assert isinstance(expand, blocks.Expand)
    assert expand.title == "Details"
    assert len(expand.children) == 1


def test_nested_expand_annotation():
    md = '<!-- adf:nestedExpand {"title": "Inner"} -->\ninner content\n<!-- /adf:nestedExpand -->\n'
    doc = parse(md)
    ne = doc.children[0]
    assert isinstance(ne, blocks.NestedExpand)
    assert ne.title == "Inner"


def test_expand_with_table():
    """Expand 내부 테이블이 올바르게 파싱되는지 확인."""
    md = (
        '<!-- adf:expand {"title": "Details"} -->\n'
        "| A | B |\n"
        "| --- | --- |\n"
        "| 1 | 2 |\n"
        "<!-- /adf:expand -->\n"
    )
    doc = parse(md)
    expand = doc.children[0]
    assert isinstance(expand, blocks.Expand)
    assert isinstance(expand.children[0], blocks.Table)


def test_panel_with_table():
    """Panel 내부 테이블이 올바르게 파싱되는지 확인."""
    md = (
        '<!-- adf:panel {"panelType": "info"} -->\n'
        "| H |\n"
        "| --- |\n"
        "| D |\n"
        "<!-- /adf:panel -->\n"
    )
    doc = parse(md)
    panel = doc.children[0]
    assert isinstance(panel, blocks.Panel)
    assert isinstance(panel.children[0], blocks.Table)


def test_expand_blockquote_legacy():
    """기존 형식 (blockquote 래핑)도 하위 호환으로 파싱."""
    md = '<!-- adf:expand {"title": "Old"} -->\n> legacy\n<!-- /adf:expand -->\n'
    doc = parse(md)
    expand = doc.children[0]
    assert isinstance(expand, blocks.Expand)
    assert isinstance(expand.children[0], blocks.Paragraph)


def test_inline_annotation_inside_strong():
    """Strong 내부의 인라인 주석이 정상 페어링되는지 확인."""
    md = "**bold <!-- adf:underline -->text<!-- /adf:underline --> bold**\n"
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    strong = p.children[0]
    assert isinstance(strong, inlines.Strong)
    assert isinstance(strong.children[0], inlines.Text)
    underline = strong.children[1]
    assert isinstance(underline, inlines.Underline)
    first = underline.children[0]
    assert isinstance(first, inlines.Text)
    assert first.text == "text"
    assert isinstance(strong.children[2], inlines.Text)


def test_inline_annotation_inside_emphasis():
    """Emphasis 내부의 인라인 주석이 정상 페어링되는지 확인."""
    md = "*em <!-- adf:underline -->text<!-- /adf:underline --> em*\n"
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    em = p.children[0]
    assert isinstance(em, inlines.Emphasis)
    assert isinstance(em.children[1], inlines.Underline)


def test_task_list_annotation():
    md = "<!-- adf:taskList -->\n- [x] done task\n- [ ] todo task\n<!-- /adf:taskList -->\n"
    doc = parse(md)
    tl = doc.children[0]
    assert isinstance(tl, blocks.TaskList)
    assert len(tl.items) == 2
    assert tl.items[0].state == "DONE"
    assert tl.items[1].state == "TODO"
    # children에서 Text 확인
    assert isinstance(tl.items[0].children[0], inlines.Text)
    assert tl.items[0].children[0].text == "done task"


def test_decision_list_annotation():
    md = "<!-- adf:decisionList -->\n- [x] decided\n- [ ] pending\n<!-- /adf:decisionList -->\n"
    doc = parse(md)
    dl = doc.children[0]
    assert isinstance(dl, blocks.DecisionList)
    assert len(dl.items) == 2
    assert dl.items[0].state == "DECIDED"
    assert dl.items[1].state == ""


def test_layout_section_annotation():
    md = (
        "<!-- adf:layoutSection -->\n"
        '<!-- adf:layoutColumn {"width": 50.0} -->\n'
        "col1\n\n"
        "<!-- /adf:layoutColumn -->\n"
        '<!-- adf:layoutColumn {"width": 50.0} -->\n'
        "col2\n\n"
        "<!-- /adf:layoutColumn -->\n"
        "<!-- /adf:layoutSection -->\n"
    )
    doc = parse(md)
    ls = doc.children[0]
    assert isinstance(ls, blocks.LayoutSection)
    assert len(ls.columns) == 2
    assert ls.columns[0].width == 50.0
    assert ls.columns[1].width == 50.0


def test_media_single_annotation():
    md = (
        '<!-- adf:mediaSingle {"layout": "center", '
        '"media": {"mediaType": "external", "url": "https://img.png"}} -->\n'
        "![](https://img.png)\n"
        "<!-- /adf:mediaSingle -->\n"
    )
    doc = parse(md)
    ms = doc.children[0]
    assert isinstance(ms, blocks.MediaSingle)
    assert ms.layout == "center"
    assert ms.media.media_type == "external"
    assert ms.media.url == "https://img.png"


def test_media_group_annotation():
    md = (
        '<!-- adf:mediaGroup {"mediaList": ['
        '{"mediaType": "external", "url": "https://a.png"}, '
        '{"mediaType": "file", "id": "f-1", "collection": "c"}'
        "]} -->\n"
        "![](https://a.png)\n"
        "`\U0001f4ce attachment`\n"
        "<!-- /adf:mediaGroup -->\n"
    )
    doc = parse(md)
    mg = doc.children[0]
    assert isinstance(mg, blocks.MediaGroup)
    assert len(mg.media_list) == 2
    assert mg.media_list[0].url == "https://a.png"
    assert mg.media_list[1].id == "f-1"


def test_block_card_annotation():
    md = (
        '<!-- adf:blockCard {"url": "https://example.com"} -->\n'
        "[https://example.com](https://example.com)\n"
        "<!-- /adf:blockCard -->\n"
    )
    doc = parse(md)
    bc = doc.children[0]
    assert isinstance(bc, blocks.BlockCard)
    assert bc.url == "https://example.com"


def test_embed_card_annotation():
    md = (
        '<!-- adf:embedCard {"url": "https://embed.com", '
        '"layout": "wide", "width": 80.0} -->\n'
        "[https://embed.com](https://embed.com)\n"
        "<!-- /adf:embedCard -->\n"
    )
    doc = parse(md)
    ec = doc.children[0]
    assert isinstance(ec, blocks.EmbedCard)
    assert ec.url == "https://embed.com"
    assert ec.layout == "wide"
    assert ec.width == 80.0


def test_paragraph_alignment_annotation():
    md = '<!-- adf:paragraph {"align": "center"} -->\ncentered\n<!-- /adf:paragraph -->\n'
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    assert p.alignment == "center"


def test_heading_indentation_annotation():
    md = '<!-- adf:heading {"indentation": 1} -->\n## indented\n<!-- /adf:heading -->\n'
    doc = parse(md)
    h = doc.children[0]
    assert isinstance(h, blocks.Heading)
    assert h.indentation == 1
    assert h.level == 2


def test_table_annotation():
    md = (
        '<!-- adf:table {"layout": "default", '
        '"cells": [[{"colspan": 2}], [null]]} -->\n'
        "| H |\n| --- |\n| X |\n"
        "<!-- /adf:table -->\n"
    )
    doc = parse(md)
    t = doc.children[0]
    assert isinstance(t, blocks.Table)
    assert t.layout == "default"
    assert t.head[0].colspan == 2


# ── 인라인 주석 복원 ────────────────────────────────────────────────


def test_mention_annotation():
    md = '<!-- adf:mention {"id": "user-1", "text": "@Alice", "userType": "DEFAULT"} -->`@Alice`<!-- /adf:mention -->\n'
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    m = p.children[0]
    assert isinstance(m, inlines.Mention)
    assert m.id == "user-1"
    assert m.text == "@Alice"
    assert m.user_type == "DEFAULT"


def test_emoji_annotation():
    md = '<!-- adf:emoji {"shortName": "smile", "text": "\U0001f604"} -->\U0001f604<!-- /adf:emoji -->\n'
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    e = p.children[0]
    assert isinstance(e, inlines.Emoji)
    assert e.short_name == "smile"
    assert e.text == "\U0001f604"


def test_date_annotation():
    md = '<!-- adf:date {"timestamp": "1609459200000"} -->`2021-01-01`<!-- /adf:date -->\n'
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    d = p.children[0]
    assert isinstance(d, inlines.Date)
    assert d.timestamp == "1609459200000"


def test_status_annotation():
    md = (
        '<!-- adf:status {"text": "In Progress", "color": "blue", '
        '"style": "bold", "localId": "s1"} -->'
        "`In Progress`"
        "<!-- /adf:status -->\n"
    )
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    s = p.children[0]
    assert isinstance(s, inlines.Status)
    assert s.text == "In Progress"
    assert s.color == "blue"


def test_inline_card_annotation():
    md = (
        '<!-- adf:inlineCard {"url": "https://example.com"} -->'
        "[https://example.com](https://example.com)"
        "<!-- /adf:inlineCard -->\n"
    )
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    ic = p.children[0]
    assert isinstance(ic, inlines.InlineCard)
    assert ic.url == "https://example.com"


def test_media_inline_annotation():
    md = (
        '<!-- adf:mediaInline {"id": "m-1", "collection": "c", "mediaType": "file"} -->'
        "`\U0001f4ce attachment`"
        "<!-- /adf:mediaInline -->\n"
    )
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    mi = p.children[0]
    assert isinstance(mi, inlines.MediaInline)
    assert mi.id == "m-1"
    assert mi.collection == "c"


def test_underline_annotation():
    md = "<!-- adf:underline -->underlined<!-- /adf:underline -->\n"
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    u = p.children[0]
    assert isinstance(u, inlines.Underline)
    assert len(u.children) == 1
    assert isinstance(u.children[0], inlines.Text)
    assert u.children[0].text == "underlined"


def test_text_color_annotation():
    md = '<!-- adf:textColor {"color": "#ff0000"} -->red<!-- /adf:textColor -->\n'
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    tc = p.children[0]
    assert isinstance(tc, inlines.TextColor)
    assert tc.color == "#ff0000"


def test_background_color_annotation():
    md = '<!-- adf:backgroundColor {"color": "#00ff00"} -->green<!-- /adf:backgroundColor -->\n'
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    bc = p.children[0]
    assert isinstance(bc, inlines.BackgroundColor)
    assert bc.color == "#00ff00"


def test_subsup_annotation():
    md = '<!-- adf:subSup {"type": "sub"} -->2<!-- /adf:subSup -->\n'
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    ss = p.children[0]
    assert isinstance(ss, inlines.SubSup)
    assert ss.type == "sub"


def test_annotation_inline():
    md = (
        '<!-- adf:annotation {"id": "ann-1", "annotationType": "inlineComment"} -->'
        "noted"
        "<!-- /adf:annotation -->\n"
    )
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    a = p.children[0]
    assert isinstance(a, inlines.Annotation)
    assert a.id == "ann-1"


# ── 중첩 주석 ───────────────────────────────────────────────────────


def test_panel_with_task_list():
    md = (
        '<!-- adf:panel {"panelType": "info"} -->\n'
        "<!-- adf:taskList -->\n"
        "- [x] task 1\n"
        "- [ ] task 2\n"
        "<!-- /adf:taskList -->\n"
        "<!-- /adf:panel -->\n"
    )
    doc = parse(md)
    panel = doc.children[0]
    assert isinstance(panel, blocks.Panel)
    assert len(panel.children) == 1
    tl = panel.children[0]
    assert isinstance(tl, blocks.TaskList)
    assert len(tl.items) == 2


def test_nested_inline_annotations():
    md = (
        '<!-- adf:textColor {"color": "#f00"} -->'
        "<!-- adf:underline -->text<!-- /adf:underline -->"
        "<!-- /adf:textColor -->\n"
    )
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    tc = p.children[0]
    assert isinstance(tc, inlines.TextColor)
    assert tc.color == "#f00"
    u = tc.children[0]
    assert isinstance(u, inlines.Underline)


# ── Graceful degradation ────────────────────────────────────────────


def test_missing_closing_annotation():
    md = '<!-- adf:panel {"panelType": "info"} -->\n> content\n'
    doc = parse(md)
    # 닫는 주석 없으면 내부 요소가 그대로 유지
    assert len(doc.children) >= 1
    # Panel이 아닌 BlockQuote 또는 다른 블록으로 유지
    assert not isinstance(doc.children[0], blocks.Panel)


def test_orphan_closing_annotation():
    md = "hello\n<!-- /adf:panel -->\n"
    doc = parse(md)
    # 짝 없는 닫는 주석은 무시되고, 원래 콘텐츠만 유지
    assert len(doc.children) >= 1
    assert isinstance(doc.children[0], blocks.Paragraph)


def test_invalid_json_annotation():
    md = "<!-- adf:panel {invalid json} -->\n> content\n<!-- /adf:panel -->\n"
    doc = parse(md)
    # JSON 파싱 실패 → 마커 무시, 원래 blockquote 유지
    assert not isinstance(doc.children[0], blocks.Panel)


# ── 라운드트립 (render → parse) ──────────────────────────────────────


def test_roundtrip_paragraph():
    doc = blocks.Document(
        children=[blocks.Paragraph(children=[inlines.Text(text="hello")])]
    )
    md = render(doc)
    doc2 = parse(md)
    assert len(doc2.children) == 1
    p = doc2.children[0]
    assert isinstance(p, blocks.Paragraph)
    t = p.children[0]
    assert isinstance(t, inlines.Text)
    assert t.text == "hello"


def test_roundtrip_heading():
    doc = blocks.Document(
        children=[blocks.Heading(level=2, children=[inlines.Text(text="title")])]
    )
    md = render(doc)
    doc2 = parse(md)
    h = doc2.children[0]
    assert isinstance(h, blocks.Heading)
    assert h.level == 2


def test_roundtrip_panel():
    doc = blocks.Document(
        children=[
            blocks.Panel(
                panel_type="info",
                children=[blocks.Paragraph(children=[inlines.Text(text="note")])],
            )
        ]
    )
    md = render(doc)
    doc2 = parse(md)
    panel = doc2.children[0]
    assert isinstance(panel, blocks.Panel)
    assert panel.panel_type == "info"


def test_roundtrip_mention():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[
                    inlines.Mention(id="user-1", text="@Alice", user_type="DEFAULT")
                ]
            )
        ]
    )
    md = render(doc)
    doc2 = parse(md)
    p = doc2.children[0]
    assert isinstance(p, blocks.Paragraph)
    m = p.children[0]
    assert isinstance(m, inlines.Mention)
    assert m.id == "user-1"
    assert m.text == "@Alice"


def test_roundtrip_underline():
    doc = blocks.Document(
        children=[
            blocks.Paragraph(
                children=[inlines.Underline(children=[inlines.Text(text="u")])]
            )
        ]
    )
    md = render(doc)
    doc2 = parse(md)
    p = doc2.children[0]
    assert isinstance(p, blocks.Paragraph)
    u = p.children[0]
    assert isinstance(u, inlines.Underline)
    ut = u.children[0]
    assert isinstance(ut, inlines.Text)
    assert ut.text == "u"


def test_empty_header_row_parsed_as_headerless():
    """빈 헤더 행이 있는 MD 테이블은 head=[]로 파싱."""
    md = "|  |  |\n| --- | --- |\n| A1 | B1 |\n| A2 | B2 |\n"
    doc = parse(md)
    table = doc.children[0]
    assert isinstance(table, blocks.Table)
    assert table.head == []
    assert len(table.body) == 2


# ── 라운드트립 수정 관련 테스트 ───────────────────────────────────────


def test_blank_line_not_parsed_as_paragraph():
    """블록 사이 빈 줄이 빈 Paragraph로 파싱되면 안 된다."""
    md = "# A\n\n# B\n"
    doc = parse(md)
    assert len(doc.children) == 2
    assert all(isinstance(c, blocks.Heading) for c in doc.children)


def test_annotated_empty_paragraph_preserved():
    """annotated 빈 Paragraph는 보존되어야 한다."""
    md = "# A\n\n<!-- adf:paragraph -->\n\n<!-- /adf:paragraph -->\n\n# B\n"
    doc = parse(md)
    assert len(doc.children) == 3
    assert isinstance(doc.children[0], blocks.Heading)
    assert isinstance(doc.children[1], blocks.Paragraph)
    assert doc.children[1].children == []
    assert isinstance(doc.children[2], blocks.Heading)


def test_blank_line_in_list_item_ignored():
    """리스트 아이템 내 blank_line은 무시되어야 한다."""
    md = "- item one\n\n- item two\n"
    doc = parse(md)
    assert len(doc.children) == 1
    bl = doc.children[0]
    assert isinstance(bl, blocks.BulletList)
    assert len(bl.items) == 2


def test_block_html_annotation_in_list_item():
    """리스트 아이템 내 inline annotation이 파싱되어야 한다."""
    md = '- <!-- adf:status {"text": "Done", "color": "green", "style": "bold"} -->`Done`<!-- /adf:status -->\n'
    doc = parse(md)
    bl = doc.children[0]
    assert isinstance(bl, blocks.BulletList)
    p = bl.items[0].children[0]
    assert isinstance(p, blocks.Paragraph)
    assert isinstance(p.children[0], inlines.Status)


def test_br_to_linebreak_in_table_cell():
    """테이블 셀 내 <br>이 HardBreak으로 파싱되어야 한다."""
    md = (
        "<!-- adf:table {} -->\n"
        "| <!-- adf:paragraph -->a<br>b<!-- /adf:paragraph --> |\n"
        "| --- |\n"
        "<!-- /adf:table -->\n"
    )
    doc = parse(md)
    table = doc.children[0]
    assert isinstance(table, blocks.Table)
    cell = table.head[0]
    para = cell.children[0]
    assert isinstance(para, blocks.Paragraph)
    texts = [c for c in para.children if isinstance(c, inlines.Text)]
    breaks = [c for c in para.children if isinstance(c, inlines.HardBreak)]
    assert len(texts) == 2
    assert len(breaks) == 1


def test_split_block_html_preserves_whitespace():
    """_split_block_html이 annotation 사이 공백을 보존해야 한다."""
    md = "<!-- adf:strong -->bold<!-- /adf:strong --> text\n"
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    # " text" 부분의 공백이 보존되어야 한다
    texts = [c for c in p.children if isinstance(c, inlines.Text)]
    combined = "".join(t.text for t in texts)
    assert " text" in combined


def test_adjacent_text_nodes_merged():
    """mistune이 분리한 인접 Text 노드가 병합되어야 한다."""
    # "[" 문자가 포함되면 mistune이 텍스트를 분리함
    md = '<!-- adf:backgroundColor {"color": "#fff"} -->text[1]end<!-- /adf:backgroundColor -->\n'
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    # backgroundColor 안의 텍스트가 하나의 Text로 병합
    bg = p.children[0]
    assert isinstance(bg, inlines.BackgroundColor)
    text_children = [c for c in bg.children if isinstance(c, inlines.Text)]
    assert len(text_children) == 1
    assert text_children[0].text == "text[1]end"


def test_block_annotation_in_nested_list_item():
    """Multi-line block annotation in list item should be parsed."""
    md = (
        "- item\n\n"
        "    - <!-- adf:mediaSingle {} -->\n"
        "        content\n"
        "        <!-- /adf:mediaSingle -->\n"
    )
    doc = parse(md)
    bl = doc.children[0]
    assert isinstance(bl, blocks.BulletList)
    sub_list = bl.items[0].children[1]
    assert isinstance(sub_list, blocks.BulletList)
    sub_item = sub_list.items[0]
    assert any(isinstance(c, blocks.MediaSingle) for c in sub_item.children)


def test_split_block_html_blockquote_char_not_misinterpreted():
    """> char should not be misinterpreted as blockquote."""
    md = "<!-- adf:inlineCard -->[link](url)<!-- /adf:inlineCard -->  > tail\n"
    doc = parse(md)
    p = doc.children[0]
    assert isinstance(p, blocks.Paragraph)
    texts = [c for c in p.children if isinstance(c, inlines.Text)]
    combined = "".join(t.text for t in texts)
    assert "> tail" in combined


def test_code_block_in_list_item_dedented():
    """Residual indentation in code block inside list should be stripped."""
    md = (
        "- item\n\n"
        "    - ```\n"
        "        {\n"
        '          "key": "value"\n'
        "        }\n"
        "        ```\n"
    )
    doc = parse(md)
    bl = doc.children[0]
    sub_list = bl.items[0].children[1]
    assert isinstance(sub_list, blocks.BulletList)
    code_block = sub_list.items[0].children[0]
    assert isinstance(code_block, blocks.CodeBlock)
    assert code_block.code == '{\n  "key": "value"\n}'
