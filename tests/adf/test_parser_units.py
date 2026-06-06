"""Direct unit tests for marklas.adf.parser edge cases."""

from __future__ import annotations

from typing import Any

import pytest

from marklas import ast
from marklas.adf.parser import (
    _consolidate_colwidths,
    _equalize_row_widths,
    _parse_inline,
    _parse_inlines,
    _parse_mark,
    _parse_task_list,
    _resolve_emoji_text,
    parse,
)


class TestParseMark:
    def test_fragment_returns_none(self) -> None:
        assert _parse_mark({"type": "fragment"}) is None

    def test_unknown_mark_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown mark type"):
            _parse_mark({"type": "definitelyNotARealMark"})


class TestParseBlockUnknown:
    def test_unknown_block_returns_none(self) -> None:
        doc = parse({"type": "doc", "version": 1, "content": [{"type": "ghost"}]})
        assert list(doc.content) == []


class TestColwidths:
    def test_colwidth_distributed_under_colspan(self) -> None:
        # A single cell with colspan=2 reports widths for both columns.
        adf: dict[str, Any] = {
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
                                    "attrs": {"colspan": 2, "colwidth": [80, 120]},
                                    "content": [],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        doc = parse(adf)
        table = doc.content[0]
        assert isinstance(table, ast.Table)
        assert table.colwidths == [80.0, 120.0]

    def test_non_list_colwidth_skipped(self) -> None:
        # A non-list colwidth is silently ignored — the `continue` arm.
        table = ast.Table(content=[ast.TableRow(content=[ast.TableCell(content=[])])])
        raw_rows: list[dict[str, Any]] = [
            {
                "type": "tableRow",
                "content": [
                    {
                        "type": "tableCell",
                        "attrs": {"colwidth": "garbage"},
                        "content": [],
                    }
                ],
            }
        ]
        result = _consolidate_colwidths(table, raw_rows)
        assert result is None

    def test_zero_widths_yield_none(self) -> None:
        # All zero widths means no column gets a width recorded → None.
        table = ast.Table(content=[ast.TableRow(content=[ast.TableCell(content=[])])])
        raw_rows: list[dict[str, Any]] = [
            {
                "type": "tableRow",
                "content": [
                    {"type": "tableCell", "attrs": {"colwidth": [0]}, "content": []}
                ],
            }
        ]
        assert _consolidate_colwidths(table, raw_rows) is None


class TestEqualizeRowWidths:
    def test_empty_table_short_circuits(self) -> None:
        table = ast.Table(content=[])
        _equalize_row_widths(table)
        assert table.content == []

    def test_short_row_extends_last_cell(self) -> None:
        table = ast.Table(
            content=[
                ast.TableRow(
                    content=[
                        ast.TableCell(content=[]),
                        ast.TableCell(content=[]),
                    ]
                ),
                ast.TableRow(content=[ast.TableCell(content=[])]),
            ]
        )
        _equalize_row_widths(table)
        # Row 2's last (only) cell should now have colspan = 2 to match row 1.
        assert table.content[1].content[-1].colspan == 2


class TestParseTaskList:
    def test_nested_task_list(self) -> None:
        node = {
            "type": "taskList",
            "attrs": {"localId": "outer"},
            "content": [
                {
                    "type": "taskList",
                    "attrs": {"localId": "inner"},
                    "content": [
                        {
                            "type": "taskItem",
                            "attrs": {"state": "TODO"},
                            "content": [{"type": "text", "text": "x"}],
                        }
                    ],
                }
            ],
        }
        result = _parse_task_list(node)
        assert isinstance(result.content[0], ast.TaskList)

    def test_unknown_task_child_raises(self) -> None:
        node = {
            "type": "taskList",
            "attrs": {"localId": "x"},
            "content": [{"type": "ghostItem"}],
        }
        with pytest.raises(ValueError, match="Unknown taskList child"):
            _parse_task_list(node)


class TestResolveEmojiText:
    def test_emoji_id_decoded_when_text_empty(self) -> None:
        # Falls through to the chr(int(id, 16)) branch.
        assert _resolve_emoji_text(None, "1F600") == "\U0001f600"

    def test_text_passthrough_when_no_escape(self) -> None:
        assert _resolve_emoji_text("😀", None) == "😀"

    def test_none_when_no_text_no_id(self) -> None:
        assert _resolve_emoji_text(None, None) is None


class TestParseInlinesWithNewlines:
    def test_text_with_newline_splits_to_hardbreak(self) -> None:
        result = _parse_inlines(
            [
                {
                    "type": "text",
                    "text": "a\nb\nc",
                    "marks": [{"type": "strong"}],
                }
            ]
        )
        # Pattern: Text("a") + HardBreak + Text("b") + HardBreak + Text("c")
        assert len(result) == 5
        assert isinstance(result[0], ast.Text) and result[0].text == "a"
        assert isinstance(result[1], ast.HardBreak)
        assert isinstance(result[2], ast.Text) and result[2].text == "b"
        assert isinstance(result[3], ast.HardBreak)
        assert isinstance(result[4], ast.Text) and result[4].text == "c"
        # Marks survive the split.
        assert any(isinstance(m, ast.StrongMark) for m in result[0].marks)

    def test_text_leading_newline_drops_empty_segment(self) -> None:
        result = _parse_inlines([{"type": "text", "text": "\nb"}])
        # No leading empty text — just HardBreak then "b".
        assert len(result) == 2
        assert isinstance(result[0], ast.HardBreak)
        assert isinstance(result[1], ast.Text)
        assert result[1].text == "b"


class TestParseInlineUnknown:
    def test_unknown_inline_returns_none(self) -> None:
        assert _parse_inline({"type": "ghostInline"}) is None
