from typing import Any

from marklas.nodes.inlines import (
    Inline,
    Text,
    Strong,
    Emphasis,
    Strikethrough,
    Link,
    Image,
    CodeSpan,
    HardBreak,
    SoftBreak,
    Mention,
    Emoji,
    Date,
    Status,
    InlineCard,
    MediaInline,
    Underline,
    TextColor,
    BackgroundColor,
    SubSup,
    Annotation,
    Placeholder,
    InlineExtension,
)
from marklas.nodes.blocks import (
    Block,
    Document,
    Paragraph,
    Heading,
    CodeBlock,
    BlockQuote,
    ThematicBreak,
    ListItem,
    BulletList,
    OrderedList,
    TableCell,
    TableHeader,
    Table,
    Panel,
    Expand,
    NestedExpand,
    TaskItem,
    TaskList,
    DecisionItem,
    DecisionList,
    LayoutColumn,
    LayoutSection,
    Media,
    MediaSingle,
    MediaGroup,
    BlockCard,
    EmbedCard,
    Extension,
    BodiedExtension,
    SyncBlock,
    BodiedSyncBlock,
)


# --- Intersection node instantiation ---


def test_intersection_blocks():
    t = Text(text="hello")
    p = Paragraph(children=[t])
    h = Heading(level=1, children=[t])
    cb = CodeBlock(code="x = 1", language="python")
    bq = BlockQuote(children=[p])
    tb = ThematicBreak()
    li = ListItem(children=[p])
    bl = BulletList(items=[li])
    ol = OrderedList(items=[li], start=1)
    doc = Document(children=[p, h, cb, bq, tb, bl, ol])
    assert len(doc.children) == 7


def test_intersection_table():
    cell = TableCell(children=[Paragraph(children=[Text(text="a")])])
    table = Table(head=[cell], body=[[cell]])
    assert table.alignments == []


def test_table_header_is_table_cell():
    header = TableHeader(children=[Paragraph(children=[Text(text="h")])])
    assert isinstance(header, TableCell)
    assert isinstance(header, TableHeader)


def test_intersection_inlines():
    t = Text(text="hello")
    assert Strong(children=[t]).children == [t]
    assert Emphasis(children=[t]).children == [t]
    assert Strikethrough(children=[t]).children == [t]
    assert Link(url="http://x", children=[t]).url == "http://x"
    assert Image(url="http://x").alt == ""
    assert CodeSpan(code="x").code == "x"
    assert isinstance(HardBreak(), Inline)
    assert isinstance(SoftBreak(), Inline)


# --- Difference-set block instantiation ---


def test_panel():
    p = Paragraph(children=[Text(text="hi")])
    panel = Panel(children=[p], panel_type="info")
    assert panel.panel_type == "info"
    assert panel.panel_color is None


def test_expand():
    p = Paragraph(children=[])
    assert Expand(children=[p], title="t").title == "t"
    assert NestedExpand(children=[p]).title is None


def test_task_list():
    item = TaskItem(children=[Text(text="task")], state="TODO", local_id="abc")
    tl = TaskList(items=[item])
    assert tl.items[0].state == "TODO"


def test_decision_list():
    item = DecisionItem(children=[Text(text="d")], state="DECIDED", local_id="abc")
    dl = DecisionList(items=[item])
    assert dl.items[0].state == "DECIDED"


def test_layout_column_is_block():
    assert issubclass(LayoutColumn, Block)


def test_layout_section():
    col = LayoutColumn(children=[], width=50.0)
    ls = LayoutSection(columns=[col, col])
    assert len(ls.columns) == 2
    assert ls.columns[0].width == 50.0


def test_media_single():
    m = Media(media_type="external", url="http://img.png")
    ms = MediaSingle(media=m, layout="center")
    assert ms.media.url == "http://img.png"


def test_media_group():
    m = Media(media_type="file", id="abc", collection="col")
    mg = MediaGroup(media_list=[m])
    assert len(mg.media_list) == 1


def test_block_card():
    bc = BlockCard(url="http://x")
    assert bc.data is None


def test_embed_card():
    ec = EmbedCard(url="http://x", layout="wide")
    assert ec.width is None


def test_placeholder_blocks():
    raw: dict[str, Any] = {"type": "extension", "attrs": {"extensionKey": "k"}}
    assert Extension(raw=raw).raw == raw
    assert BodiedExtension(raw=raw).raw == raw
    assert SyncBlock(raw=raw).raw == raw
    assert BodiedSyncBlock(raw=raw).raw == raw


# --- Difference-set inline instantiation ---


def test_mention():
    m = Mention(id="user-1", text="John")
    assert m.access_level is None


def test_emoji():
    e = Emoji(short_name=":smile:")
    assert e.text is None


def test_date():
    assert Date(timestamp="1234567890").timestamp == "1234567890"


def test_status():
    s = Status(text="Done", color="green")
    assert s.style is None


def test_inline_card():
    ic = InlineCard(url="http://x")
    assert ic.data is None


def test_media_inline():
    mi = MediaInline(id="abc")
    assert mi.collection is None


def test_wrapping_marks():
    t = Text(text="hello")
    assert Underline(children=[t]).children == [t]
    assert TextColor(color="#ff0000", children=[t]).color == "#ff0000"
    assert BackgroundColor(color="#00ff00", children=[t]).color == "#00ff00"
    assert SubSup(type="sub", children=[t]).type == "sub"
    ann = Annotation(id="ann-1", children=[t])
    assert ann.annotation_type == "inlineComment"


def test_placeholder_inlines():
    assert Placeholder(text="fallback").text == "fallback"
    raw: dict[str, Any] = {"type": "inlineExtension", "attrs": {"extensionKey": "k"}}
    assert InlineExtension(raw=raw).raw == raw


# --- Existing node modification verification ---


def test_table_cell_children_are_blocks():
    cell = TableCell(children=[Paragraph(children=[Text(text="a")])])
    assert isinstance(cell.children[0], Block)


def test_paragraph_block_marks():
    p = Paragraph(children=[], alignment="center", indentation=1)
    assert p.alignment == "center"
    assert p.indentation == 1


def test_heading_block_marks():
    h = Heading(level=2, children=[], alignment="end", indentation=2)
    assert h.alignment == "end"


def test_table_attrs():
    cell = TableCell(
        children=[Paragraph(children=[])],
        colspan=2,
        rowspan=1,
        col_width=[100],
        background="#eee",
    )
    table = Table(
        head=[cell],
        body=[],
        display_mode="fixed",
        is_number_column_enabled=True,
        layout="wide",
        width=760.0,
    )
    assert table.display_mode == "fixed"
    assert cell.colspan == 2
