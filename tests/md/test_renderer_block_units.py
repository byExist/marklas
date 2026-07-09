"""Direct unit tests for marklas.md.renderer.block edge cases."""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest

from marklas import ast
from marklas.md.renderer import block as block_renderer
from marklas.md.renderer.block import (
    _apply_marks,
    _build_grid,
    _cell_meta,
    _expected_header,
    _header_mode,
    _nested_table_visual,
    _node_to_dict,
    _render_cell_content,
    _render_inline,
    _render_table_html,
    _table_meta,
    _wrap_code,
    _wrap_codespan,
    _wrap_flanking,
    _wrap_html_mark,
    block_marks_params,
    render,
    render_block,
)


@pytest.fixture
def in_cell() -> Iterator[None]:
    token = block_renderer._ctx.set(block_renderer._Ctx.CELL)
    try:
        yield
    finally:
        block_renderer._ctx.reset(token)


class _UnknownMark(ast.Mark):
    pass


class _UnknownNode(ast.Node):
    pass


class _UnknownInline(ast.Node):
    pass


class TestBlockMarksParams:
    def test_unknown_mark_falls_through(self) -> None:
        # The `case _: pass` arm.
        d = block_marks_params([_UnknownMark()])
        assert d == {}

    def test_breakout_with_width(self) -> None:
        d = block_marks_params([ast.BreakoutMark(mode="wide", width=900)])
        assert d == {"breakoutMode": "wide", "breakoutWidth": 900}

    def test_border_mark(self) -> None:
        d = block_marks_params([ast.BorderMark(size=2, color="#abc")])
        assert d == {"borderSize": 2, "borderColor": "#abc"}


class TestRenderBlockErrors:
    def test_unknown_block_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown block"):
            render_block(_UnknownNode())


class TestRenderInlineErrors:
    def test_unknown_inline_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown inline"):
            _render_inline(_UnknownInline())  # type: ignore[arg-type]


class TestParagraphEdgeCases:
    def test_leading_and_trailing_hardbreaks_stripped(self) -> None:
        node = ast.Paragraph(
            content=[ast.HardBreak(), ast.Text(text="x"), ast.HardBreak()]
        )
        result = render(ast.Doc(content=[node]))
        # Both edge HardBreaks dropped → just "x"
        assert "x" in result
        assert "<br>" not in result

    def test_empty_paragraph_in_plain_mode(self) -> None:
        node = ast.Paragraph(content=[])
        result = render(ast.Doc(content=[node]), plain=True)
        assert result == ""

    def test_empty_paragraph_with_marks_prefix(self) -> None:
        node = ast.Paragraph(
            content=[],
            marks=[ast.AlignmentMark(align="center")],
        )
        result = render_block(node)
        assert '<div adf="marks"' in result
        assert "<p></p>" in result


class TestHeadingEdgeCases:
    def test_leading_and_trailing_hardbreaks_stripped(self) -> None:
        node = ast.Heading(
            level=2,
            content=[ast.HardBreak(), ast.Text(text="t"), ast.HardBreak()],
        )
        result = render_block(node)
        assert result == "## t"


class TestListItemEmpty:
    def test_empty_list_item(self) -> None:
        node = ast.BulletList(content=[ast.ListItem(content=[])])
        result = render_block(node)
        # Marker with no body
        assert result.strip() == "-"


class TestExpandWithMarks:
    def test_expand_with_breakout_marks(self) -> None:
        node = ast.Expand(
            title="t",
            content=[],
            marks=[ast.BreakoutMark(mode="wide")],
        )
        result = render_block(node)
        assert '<div adf="marks"' in result
        assert '<details adf="expand">' in result


class TestNestedExpand:
    def test_nested_expand_in_block_context(self) -> None:
        node = ast.NestedExpand(title="ne", content=[])
        result = render_block(node)
        assert '<details adf="nestedExpand">' in result
        assert "<summary>ne</summary>" in result

    def test_nested_expand_without_title(self) -> None:
        node = ast.NestedExpand(title=None, content=[])
        result = render_block(node)
        assert "summary" not in result

    def test_nested_expand_inside_cell(self, in_cell: None) -> None:
        node = ast.NestedExpand(title="x", content=[])
        result = render_block(node)
        assert '<details adf="nestedExpand">' in result


class TestTaskListBlock:
    def test_nested_task_list_indented(self) -> None:
        node = ast.TaskList(
            content=[
                ast.TaskItem(state="TODO", content=[ast.Text(text="parent")]),
                ast.TaskList(
                    content=[ast.TaskItem(state="DONE", content=[ast.Text(text="kid")])]
                ),
            ]
        )
        result = render_block(node)
        # Nested list is indented by two spaces.
        assert "  - [x] kid" in result

    def test_task_list_with_unknown_child(self) -> None:
        # `case _: pass` arm in _render_task_list_block.
        node = ast.TaskList(content=[ast.Paragraph(content=[])])  # type: ignore[list-item]
        result = render_block(node)
        # Foreign child silently dropped.
        assert result == ""

    def test_block_task_item_empty(self) -> None:
        # Empty content → marker alone.
        node = ast.BlockTaskItem(state="TODO", content=[])
        result = render_block(ast.TaskList(content=[node]))
        assert result.strip() == "- [ ]"


class TestMediaSingle:
    def test_media_single_with_link_mark(self) -> None:
        node = ast.MediaSingle(
            content=[ast.Media(type="file", id="i", collection="c")],
            marks=[ast.LinkMark(href="http://x", title="t")],
        )
        result = render_block(node)
        assert "linkHref" in result
        assert "linkTitle" in result

    def test_media_single_with_unknown_child(self) -> None:
        # The `case _: pass` fallthrough for unknown content children.
        node = ast.MediaSingle(
            content=[ast.Rule()],  # type: ignore[list-item]
        )
        result = render_block(node)
        # Renders the empty figure shell.
        assert "<figure" in result


class TestMediaMarks:
    def test_media_with_link_mark(self) -> None:
        media = ast.Media(
            type="file",
            id="i",
            collection="c",
            marks=[ast.LinkMark(href="http://x")],
        )
        # Drive via mediaSingle.
        result = render_block(ast.MediaSingle(content=[media]))
        assert '<a adf="link" href="http://x"' in result

    def test_media_with_annotation_mark(self) -> None:
        media = ast.Media(
            type="file",
            id="i",
            collection="c",
            marks=[ast.AnnotationMark(id="a1")],
        )
        result = render_block(ast.MediaSingle(content=[media]))
        assert 'adf="annotation"' in result


class TestLayoutSectionInCell:
    def test_layout_section_inside_cell(self, in_cell: None) -> None:
        node = ast.LayoutSection(content=[], marks=[ast.BreakoutMark(mode="wide")])
        result = render_block(node)
        # Inside a cell the marks prefix is suppressed.
        assert '<div adf="marks"' not in result

    def test_layout_section_with_marks_prefix(self) -> None:
        node = ast.LayoutSection(content=[], marks=[ast.BreakoutMark(mode="wide")])
        result = render_block(node)
        assert '<div adf="marks"' in result


class TestExtensionWithMarks:
    def test_extension_in_cell(self, in_cell: None) -> None:
        node = ast.Extension(extension_key="k", extension_type="t")
        result = render_block(node)
        # Inside a cell the marks prefix is suppressed; void emitted as `<div ...></div>`.
        assert '<div adf="extension"' in result

    def test_extension_with_marks_prefix(self) -> None:
        node = ast.Extension(
            extension_key="k",
            extension_type="t",
            marks=[ast.BreakoutMark(mode="wide")],
        )
        result = render_block(node)
        assert '<div adf="marks"' in result


class TestNestedTableExtension:
    def test_nested_table_extension_renders_visual_table(self) -> None:
        from typing import Any

        inner_doc: dict[str, Any] = {
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
                                    "attrs": {"colspan": 2, "rowspan": 2},
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [{"type": "text", "text": "V"}],
                                        }
                                    ],
                                }
                            ],
                        },
                    ],
                }
            ],
        }
        ext = ast.Extension(
            extension_key="nested-table",
            extension_type="confluence",
            parameters={"adf": json.dumps(inner_doc)},
        )
        result = render_block(ext)
        # The visual table renders inline within the extension div.
        assert "<table>" in result
        assert "colspan=" in result or "rowspan=" in result

    def test_nested_table_extension_no_adf_field(self) -> None:
        # parameters has no 'adf' string → falls through to empty visual.
        assert (
            _nested_table_visual(
                ast.Extension(extension_key="nested-table", extension_type="x")
            )
            == ""
        )

    def test_nested_table_extension_invalid_json(self) -> None:
        ext = ast.Extension(
            extension_key="nested-table",
            extension_type="x",
            parameters={"adf": "not json{"},
        )
        assert _nested_table_visual(ext) == ""

    def test_nested_table_extension_parse_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # parse_adf_doc raising is caught.
        from typing import Any

        import marklas.adf.parser as adf_parser

        def boom(_: dict[str, Any]) -> ast.Doc:
            raise RuntimeError("nope")

        monkeypatch.setattr(adf_parser, "parse", boom)
        ext = ast.Extension(
            extension_key="nested-table",
            extension_type="x",
            parameters={
                "adf": json.dumps({"type": "doc", "version": 1, "content": []})
            },
        )
        assert _nested_table_visual(ext) == ""

    def test_render_table_html_with_th_and_attrs(self) -> None:
        table = ast.Table(
            content=[
                ast.TableRow(
                    content=[
                        ast.TableHeader(content=[], colspan=2, rowspan=2),
                    ]
                ),
            ]
        )
        result = _render_table_html(table)
        assert '<th colspan="2" rowspan="2">' in result


class TestSyncBlockMarks:
    def test_sync_block_in_cell(self, in_cell: None) -> None:
        node = ast.SyncBlock(resource_id="r")
        result = render_block(node)
        assert '<div adf="syncBlock"' in result

    def test_sync_block_with_marks_prefix(self) -> None:
        node = ast.SyncBlock(
            resource_id="r",
            marks=[ast.BreakoutMark(mode="wide")],
        )
        result = render_block(node)
        assert '<div adf="marks"' in result


class TestBodiedSyncBlock:
    def test_bodied_sync_block_render(self) -> None:
        node = ast.BodiedSyncBlock(
            resource_id="r",
            content=[ast.Paragraph(content=[ast.Text(text="hello")])],
        )
        result = render_block(node)
        assert '<div adf="bodiedSyncBlock"' in result


class TestTableEdgeCases:
    def test_empty_table_renders_empty(self) -> None:
        result = render_block(ast.Table(content=[]))
        assert result == ""

    def test_table_with_only_empty_rows_renders_empty(self) -> None:
        # Empty row gives empty grid first row → fallthrough on "no grid"
        result = render_block(ast.Table(content=[ast.TableRow(content=[])]))
        assert result == ""

    def test_table_with_layout_meta(self) -> None:
        table = ast.Table(
            content=[
                ast.TableRow(
                    content=[
                        ast.TableHeader(content=[]),
                        ast.TableHeader(content=[]),
                    ]
                ),
                ast.TableRow(
                    content=[ast.TableCell(content=[]), ast.TableCell(content=[])]
                ),
            ],
            display_mode="fixed",
            is_number_column_enabled=True,
            colwidths=[100.0, 200.0],
            width=300.0,
            layout="wide",
        )
        result = render_block(table)
        assert "displayMode" in result
        assert "isNumberColumnEnabled" in result
        assert "colwidths" in result


class TestExpectedHeader:
    def test_column_mode(self) -> None:
        assert _expected_header("column", 1, 0) is True
        assert _expected_header("column", 1, 1) is False

    def test_both_mode(self) -> None:
        assert _expected_header("both", 0, 5) is True
        assert _expected_header("both", 5, 0) is True
        assert _expected_header("both", 5, 5) is False

    def test_none_mode(self) -> None:
        assert _expected_header("none", 0, 0) is False


class TestBuildGrid:
    def test_empty_rows_returns_empty(self) -> None:
        assert _build_grid([], "none") == []

    def test_rowspan_clipped_by_max_cols(self) -> None:
        # Two rows: row 1 has one cell with colspan=3; row 2 has 3 cells.
        # Row 2 hits the "while occupied" inner loop because no cells of row 1
        # are placed in row 2 (no rowspan), so this doesn't directly trigger.
        # Instead test rowspan + colspan extending beyond grid.
        rows = [
            ast.TableRow(content=[ast.TableCell(content=[], colspan=2, rowspan=2)]),
            ast.TableRow(content=[ast.TableCell(content=[])]),
        ]
        grid = _build_grid(rows, "none")
        # Row 2's lone cell is at column 0 already occupied → must reach
        # `if c >= max_cols: break`. With colspan=2, max_cols=2; second row
        # is forced past column 2.
        assert len(grid) == 2


class TestHeaderMode:
    def test_empty_table_defaults_to_row(self) -> None:
        assert _header_mode(ast.Table(content=[])) == "row"

    def test_column_mode(self) -> None:
        table = ast.Table(
            content=[
                ast.TableRow(
                    content=[
                        ast.TableHeader(content=[]),
                        ast.TableCell(content=[]),
                    ]
                ),
                ast.TableRow(
                    content=[
                        ast.TableHeader(content=[]),
                        ast.TableCell(content=[]),
                    ]
                ),
            ]
        )
        assert _header_mode(table) == "column"

    def test_both_mode(self) -> None:
        table = ast.Table(
            content=[
                ast.TableRow(
                    content=[
                        ast.TableHeader(content=[]),
                        ast.TableHeader(content=[]),
                    ]
                ),
                ast.TableRow(
                    content=[
                        ast.TableHeader(content=[]),
                        ast.TableCell(content=[]),
                    ]
                ),
            ]
        )
        assert _header_mode(table) == "both"


class TestCellMeta:
    def test_rowspan_and_background_and_header_override(self) -> None:
        cell = ast.TableCell(content=[], rowspan=2, background="#fff")
        result = _cell_meta(cell, header_override=True)
        assert "rowspan" in result
        assert "background" in result
        assert '"header":true' in result


class TestTableMeta:
    def test_no_attrs_returns_none(self) -> None:
        table = ast.Table(content=[])
        assert _table_meta(table, "row") is None


class TestRenderCellContent:
    def test_empty_children_returns_empty(self) -> None:
        assert _render_cell_content([]) == ""

    def test_paragraph_with_marks_uses_block_render(self, in_cell: None) -> None:
        # When the only paragraph has block marks, fall through to "render each".
        result = _render_cell_content(
            [
                ast.Paragraph(
                    content=[ast.Text(text="x")],
                    marks=[ast.AlignmentMark(align="center")],
                )
            ]
        )
        # The paragraph render goes through cell.render_paragraph which emits <p>
        assert "<p" in result


class TestWrapCodespanEmpty:
    def test_empty_text(self) -> None:
        assert _wrap_codespan("") == ""


class TestWrapCode:
    def test_text_starting_with_backtick(self) -> None:
        # Triggers the `pad` branch.
        result = _wrap_code("`x")
        assert result.startswith("`` ")
        assert result.endswith(" ``")


class TestWrapFlanking:
    def test_empty_inner_returns_unchanged(self) -> None:
        assert _wrap_flanking("   ", "**") == "   "


class TestWrapHtmlMarkUnknown:
    def test_unknown_mark_returns_text(self) -> None:
        # `case _: return text` fallthrough.
        assert _wrap_html_mark("hello", _UnknownMark()) == "hello"


class TestApplyMarksUnknownNative:
    def test_unknown_native_falls_through(self) -> None:
        # An ast.Mark that's not strong/em/strike hits the `case _: pass`
        # within the native marks loop.
        result = _apply_marks("x", [_UnknownMark()])
        # Wraps via _wrap_html_mark fallback → bare text.
        assert "x" in result


class TestMediaInlineMarks:
    def test_media_inline_with_data(self) -> None:
        node = ast.MediaInline(id="i", collection="c", data={"k": "v"})
        result = _render_inline(node)
        assert '"data":{"k":"v"}' in result

    def test_media_inline_with_link_mark(self) -> None:
        node = ast.MediaInline(
            id="i",
            collection="c",
            marks=[ast.LinkMark(href="http://x")],
        )
        result = _render_inline(node)
        assert '<a adf="link" href="http://x"' in result

    def test_media_inline_with_annotation_mark(self) -> None:
        node = ast.MediaInline(
            id="i",
            collection="c",
            marks=[ast.AnnotationMark(id="a")],
        )
        result = _render_inline(node)
        assert 'adf="annotation"' in result


class TestNodeToDictError:
    def test_unrenderable_node_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import marklas.adf.renderer as adf_renderer

        def returns_none(_: ast.Node) -> None:
            return None

        monkeypatch.setattr(adf_renderer, "render_block", returns_none)
        with pytest.raises(ValueError, match="cannot render"):
            _node_to_dict(ast.Rule())
