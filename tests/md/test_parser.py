from marklas.nodes import blocks, inlines
from marklas.md.parser import parse

# ── Block parsers ────────────────────────────────────────────────────


def test_empty_doc():
    assert parse("") == blocks.Document(children=[])


def test_paragraph():
    doc = parse("Hello")
    assert len(doc.children) == 1
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    assert para.children == [inlines.Text(text="Hello")]


def test_paragraph_multiline():
    doc = parse("line1\nline2")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    assert para.children == [
        inlines.Text(text="line1"),
        inlines.SoftBreak(),
        inlines.Text(text="line2"),
    ]


def test_heading_levels():
    for level in (1, 2, 3, 4, 5, 6):
        doc = parse(f"{'#' * level} Title")
        heading = doc.children[0]
        assert isinstance(heading, blocks.Heading)
        assert heading.level == level
        assert heading.children == [inlines.Text(text="Title")]


def test_heading_trailing_hashes():
    doc = parse("## Foo ##")
    heading = doc.children[0]
    assert isinstance(heading, blocks.Heading)
    assert heading.children == [inlines.Text(text="Foo")]


def test_fenced_code_backtick():
    doc = parse("```python\nprint('hi')\n```")
    cb = doc.children[0]
    assert isinstance(cb, blocks.CodeBlock)
    assert cb.code == "print('hi')"
    assert cb.language == "python"


def test_fenced_code_tilde():
    doc = parse("~~~\nhello\n~~~")
    cb = doc.children[0]
    assert isinstance(cb, blocks.CodeBlock)
    assert cb.code == "hello"
    assert cb.language is None


def test_fenced_code_no_close():
    doc = parse("```python\nprint(1)")
    cb = doc.children[0]
    assert isinstance(cb, blocks.CodeBlock)
    assert cb.code == "print(1)"
    assert cb.language == "python"


def test_fenced_code_no_language():
    doc = parse("```\nhello\n```")
    cb = doc.children[0]
    assert isinstance(cb, blocks.CodeBlock)
    assert cb.code == "hello"
    assert cb.language is None


def test_indented_code():
    doc = parse("    line1\n    line2")
    cb = doc.children[0]
    assert isinstance(cb, blocks.CodeBlock)
    assert cb.code == "line1\nline2"
    assert cb.language is None


def test_thematic_break():
    for marker in ("---", "***", "___"):
        doc = parse(marker)
        assert isinstance(doc.children[0], blocks.ThematicBreak)


def test_blockquote():
    doc = parse("> text")
    bq = doc.children[0]
    assert isinstance(bq, blocks.BlockQuote)
    assert len(bq.children) == 1
    para = bq.children[0]
    assert isinstance(para, blocks.Paragraph)
    assert para.children == [inlines.Text(text="text")]


def test_blockquote_lazy_continuation():
    doc = parse("> line1\nline2")
    bq = doc.children[0]
    assert isinstance(bq, blocks.BlockQuote)
    para = bq.children[0]
    assert isinstance(para, blocks.Paragraph)
    assert para.children == [
        inlines.Text(text="line1"),
        inlines.SoftBreak(),
        inlines.Text(text="line2"),
    ]


def test_blockquote_nested():
    doc = parse("> > text")
    bq = doc.children[0]
    assert isinstance(bq, blocks.BlockQuote)
    inner_bq = bq.children[0]
    assert isinstance(inner_bq, blocks.BlockQuote)
    para = inner_bq.children[0]
    assert isinstance(para, blocks.Paragraph)
    assert para.children == [inlines.Text(text="text")]


def test_bullet_list_tight():
    doc = parse("- a\n- b")
    lst = doc.children[0]
    assert isinstance(lst, blocks.BulletList)
    assert lst.tight is True
    assert len(lst.items) == 2
    assert isinstance(lst.items[0].children[0], blocks.Paragraph)


def test_bullet_list_loose():
    doc = parse("- a\n\n- b")
    lst = doc.children[0]
    assert isinstance(lst, blocks.BulletList)
    assert lst.tight is False
    assert len(lst.items) == 2


def test_bullet_list_task_checkbox():
    doc = parse("- [ ] todo\n- [x] done")
    lst = doc.children[0]
    assert isinstance(lst, blocks.BulletList)
    assert lst.items[0].checked is False
    assert lst.items[1].checked is True


def test_ordered_list_start():
    doc = parse("3. first\n4. second")
    lst = doc.children[0]
    assert isinstance(lst, blocks.OrderedList)
    assert lst.start == 3
    assert len(lst.items) == 2


def test_nested_list():
    doc = parse("- a\n  - b")
    lst = doc.children[0]
    assert isinstance(lst, blocks.BulletList)
    item = lst.items[0]
    assert len(item.children) == 2
    assert isinstance(item.children[0], blocks.Paragraph)
    inner_lst = item.children[1]
    assert isinstance(inner_lst, blocks.BulletList)
    assert len(inner_lst.items) == 1


def test_list_item_multi_block():
    md = "- para1\n\n  ```\n  code\n  ```\n\n  para2"
    doc = parse(md)
    lst = doc.children[0]
    assert isinstance(lst, blocks.BulletList)
    item = lst.items[0]
    block_types = [type(c) for c in item.children]
    assert blocks.Paragraph in block_types
    assert blocks.CodeBlock in block_types


def test_table_basic():
    md = "| A | B |\n| --- | --- |\n| 1 | 2 |"
    doc = parse(md)
    tbl = doc.children[0]
    assert isinstance(tbl, blocks.Table)
    assert len(tbl.head) == 2
    assert len(tbl.body) == 1
    assert len(tbl.body[0]) == 2


def test_table_alignment():
    md = "| L | C | R |\n| :--- | :---: | ---: |\n| a | b | c |"
    doc = parse(md)
    tbl = doc.children[0]
    assert isinstance(tbl, blocks.Table)
    assert tbl.alignments == ["left", "center", "right"]


def test_table_pipe_escape():
    md = "| A | B |\n| --- | --- |\n| a\\|b | c |"
    doc = parse(md)
    tbl = doc.children[0]
    assert isinstance(tbl, blocks.Table)
    cell = tbl.body[0][0]
    para = cell.children[0]
    assert isinstance(para, blocks.Paragraph)
    text = "".join(
        child.text for child in para.children if isinstance(child, inlines.Text)
    )
    assert "|" in text


def test_table_no_body():
    md = "| A | B |\n| --- | --- |"
    doc = parse(md)
    tbl = doc.children[0]
    assert isinstance(tbl, blocks.Table)
    assert len(tbl.head) == 2
    assert tbl.body == []


def test_multi_block_doc():
    md = "para1\n\n## heading\n\npara2"
    doc = parse(md)
    types = [type(c) for c in doc.children]
    assert types == [blocks.Paragraph, blocks.Heading, blocks.Paragraph]


# ── Inline parsers ───────────────────────────────────────────────────


def test_text():
    doc = parse("hello")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    assert para.children == [inlines.Text(text="hello")]


def test_code_span():
    doc = parse("`code`")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    assert para.children == [inlines.CodeSpan(code="code")]


def test_code_span_double_backtick():
    doc = parse("`` code ` here ``")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    assert isinstance(para.children[0], inlines.CodeSpan)
    assert "`" in para.children[0].code


def test_emphasis_asterisk():
    doc = parse("*text*")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    assert para.children == [inlines.Emphasis(children=[inlines.Text(text="text")])]


def test_emphasis_underscore():
    doc = parse("_text_")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    assert para.children == [inlines.Emphasis(children=[inlines.Text(text="text")])]


def test_strong():
    doc = parse("**text**")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    assert para.children == [inlines.Strong(children=[inlines.Text(text="text")])]


def test_strikethrough():
    doc = parse("~~text~~")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    assert para.children == [
        inlines.Strikethrough(children=[inlines.Text(text="text")])
    ]


def test_emphasis_nested():
    doc = parse("***text***")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    node = para.children[0]
    # mistune: Emphasis(Strong(Text))
    assert isinstance(node, (inlines.Strong, inlines.Emphasis))
    inner = node.children[0]
    assert isinstance(inner, (inlines.Strong, inlines.Emphasis))
    assert inner.children == [inlines.Text(text="text")]


def test_link():
    doc = parse("[click](https://example.com)")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    link = para.children[0]
    assert isinstance(link, inlines.Link)
    assert link.url == "https://example.com"
    assert link.children == [inlines.Text(text="click")]
    assert link.title is None


def test_link_with_title():
    doc = parse('[click](https://example.com "My Title")')
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    link = para.children[0]
    assert isinstance(link, inlines.Link)
    assert link.title == "My Title"


def test_link_with_inline():
    doc = parse("[**bold**](https://example.com)")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    link = para.children[0]
    assert isinstance(link, inlines.Link)
    assert len(link.children) == 1
    assert isinstance(link.children[0], inlines.Strong)


def test_image():
    doc = parse("![alt](https://example.com/img.png)")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    img = para.children[0]
    assert isinstance(img, inlines.Image)
    assert img.url == "https://example.com/img.png"
    assert img.alt == "alt"
    assert img.title is None


def test_image_with_title():
    doc = parse('![alt](https://example.com/img.png "My Image")')
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    img = para.children[0]
    assert isinstance(img, inlines.Image)
    assert img.title == "My Image"


def test_autolink():
    doc = parse("<https://example.com>")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    link = para.children[0]
    assert isinstance(link, inlines.Link)
    assert link.url == "https://example.com"


def test_hard_break_backslash():
    doc = parse("line1\\\nline2")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    assert para.children == [
        inlines.Text(text="line1"),
        inlines.HardBreak(),
        inlines.Text(text="line2"),
    ]


def test_hard_break_spaces():
    doc = parse("line1  \nline2")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    assert para.children == [
        inlines.Text(text="line1"),
        inlines.HardBreak(),
        inlines.Text(text="line2"),
    ]


def test_soft_break():
    doc = parse("line1\nline2")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    assert para.children == [
        inlines.Text(text="line1"),
        inlines.SoftBreak(),
        inlines.Text(text="line2"),
    ]


def test_backslash_escape():
    doc = parse("\\*literal\\*")
    para = doc.children[0]
    assert isinstance(para, blocks.Paragraph)
    texts = [c.text for c in para.children if isinstance(c, inlines.Text)]
    assert "*" in texts
