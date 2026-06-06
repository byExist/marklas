"""Direct unit tests for marklas.md.parser.cell edge cases."""

from __future__ import annotations

from marklas import ast
from marklas.md.parser.cell import (
    _parse_list,
    _promote_paired,
    _promote_void,
    _unescape_codespan_pipes,
    group_inline_html,
    parse_cell_content,
)


class TestParseCellContent:
    def test_empty_tokens_yields_empty_paragraph(self) -> None:
        assert parse_cell_content([]) == [ast.Paragraph(content=[])]

    def test_no_block_yield_empty_paragraph(self) -> None:
        # A token stream that yields no block-level nodes after promotion
        # still produces a fallback empty paragraph. A plain inline_html
        # closing tag is dropped and leaves no blocks behind.
        result = parse_cell_content([{"type": "inline_html", "raw": "</span>"}])
        assert result == [ast.Paragraph(content=[])]


class TestUnescapeCodespanPipes:
    def test_codespan_pipe_restored(self) -> None:
        out = _unescape_codespan_pipes([{"type": "codespan", "raw": "a\\|b"}])
        assert out == [{"type": "codespan", "raw": "a|b"}]

    def test_codespan_without_escape_unchanged(self) -> None:
        # Branch where the codespan has no \\| escape.
        out = _unescape_codespan_pipes([{"type": "codespan", "raw": "abc"}])
        assert out == [{"type": "codespan", "raw": "abc"}]

    def test_children_recursed(self) -> None:
        out = _unescape_codespan_pipes(
            [
                {
                    "type": "strong",
                    "children": [{"type": "codespan", "raw": "x\\|y"}],
                }
            ]
        )
        assert out == [
            {"type": "strong", "children": [{"type": "codespan", "raw": "x|y"}]}
        ]


class TestGroupInlineHtml:
    def test_closing_tag_goes_to_inline_buffer(self) -> None:
        # An orphan closing tag in the cell stream is buffered as inline text.
        groups = group_inline_html([{"type": "inline_html", "raw": "</span>"}])
        assert len(groups) == 1
        assert isinstance(groups[0], list)

    def test_no_matching_close_falls_through_as_inline(self) -> None:
        groups = group_inline_html(
            [{"type": "inline_html", "raw": '<span adf="underline">'}]
        )
        assert len(groups) == 1
        assert isinstance(groups[0], list)


class TestPromoteVoid:
    def test_non_table_cell_node_returns_none(self) -> None:
        # An HtmlVoid whose adf type maps to a non-TableCellContent node
        # (e.g. syncBlock isn't in TableCellContent union) is filtered out.
        assert _promote_void("div", {"adf": "syncBlock", "params": "{}"}) is None

    def test_unknown_tag_returns_none(self) -> None:
        assert _promote_void("xyz", {}) is None

    def test_extension_void_passes_table_cell_check(self) -> None:
        # Extension is in the TableCellContent union, so the void dispatch
        # returns the built node rather than dropping it.
        node = _promote_void(
            "div",
            {
                "adf": "extension",
                "params": '{"extensionKey":"k","extensionType":"t"}',
            },
        )
        assert isinstance(node, ast.Extension)


class TestPromotePaired:
    def test_paired_extension_via_void_dispatch(self) -> None:
        # extension/bodiedExtension arrive paired (open/close inline_html) but
        # route through the void dispatch.
        node = _promote_paired(
            tag="div",
            attrs={
                "adf": "extension",
                "params": ('{"extensionKey":"k","extensionType":"t"}'),
            },
            inner=[],
        )
        assert isinstance(node, ast.Extension)

    def test_paired_bodied_sync_block_returns_none_when_not_table_cell(self) -> None:
        # BodiedSyncBlock isn't in TableCellContent union, so the routed call
        # builds the node, then the is_table_cell guard filters it out.
        node = _promote_paired(
            tag="div",
            attrs={
                "adf": "bodiedSyncBlock",
                "params": '{"resourceId":"r"}',
            },
            inner=[],
        )
        assert node is None

    def test_paired_block_card(self) -> None:
        node = _promote_paired(
            tag="div",
            attrs={"adf": "blockCard", "params": '{"url":"u"}'},
            inner=[],
        )
        assert isinstance(node, ast.BlockCard)


class TestParseList:
    def test_skip_list_groups(self) -> None:
        # _parse_list iterates groups; non-paired/non-li groups are skipped.
        # An inline text-only token stream produces a list (inline run)
        # group that the loop will skip.
        result = _parse_list([{"type": "text", "raw": "stray"}], ordered=False)
        assert isinstance(result, ast.BulletList)
        assert result.content == []

    def test_empty_li_gets_empty_paragraph(self) -> None:
        # `<li adf="..."></li>` with no inner content yields a ListItem
        # holding an empty paragraph (the empty-content fallback).
        result = _parse_list(
            [
                {"type": "inline_html", "raw": "<li>"},
                {"type": "inline_html", "raw": "</li>"},
            ],
            ordered=True,
            start=1,
        )
        assert isinstance(result, ast.OrderedList)
        assert len(result.content) == 1
        assert result.content[0].content == [ast.Paragraph(content=[])]
