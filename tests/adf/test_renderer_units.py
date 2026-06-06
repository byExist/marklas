"""Direct unit tests for marklas.adf.renderer edge cases."""

from __future__ import annotations

import pytest

from marklas import ast
from marklas.adf.renderer import (
    _distribute_colwidths,
    _render_mark,
    render,
    render_block,
)
from marklas.adf.renderer import _render_inline as render_inline_helper


class _UnknownMark(ast.Mark):
    pass


class _UnknownNode(ast.Node):
    pass


class _UnknownInline(ast.Node):
    pass


class TestErrorCases:
    def test_unknown_mark_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown mark type"):
            _render_mark(_UnknownMark())

    def test_unknown_block_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown block node"):
            render_block(_UnknownNode())

    def test_unknown_inline_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown inline node"):
            render_inline_helper(_UnknownInline())  # type: ignore[arg-type]


class TestColwidthsDistribution:
    def test_colwidths_attached_to_each_cell(self) -> None:
        table = ast.Table(
            content=[
                ast.TableRow(
                    content=[
                        ast.TableCell(content=[]),
                        ast.TableCell(content=[]),
                    ]
                ),
            ],
            colwidths=[100.0, 200.0],
        )
        doc = ast.Doc(content=[table])
        result = render(doc)
        cells = result["content"][0]["content"][0]["content"]
        assert cells[0]["attrs"]["colwidth"] == [100.0]
        assert cells[1]["attrs"]["colwidth"] == [200.0]

    def test_colwidths_with_zero_slice_skipped(self) -> None:
        # When a column's width entry is 0, the slice contains only zeros
        # and the loop should `continue` rather than attach a colwidth.
        rows = [{"type": "tableRow", "content": [{"type": "tableCell"}]}]
        table = ast.Table(
            content=[ast.TableRow(content=[ast.TableCell(content=[])])],
            colwidths=[0.0],
        )
        _distribute_colwidths(table, rows)
        assert "attrs" not in rows[0]["content"][0]

    def test_empty_colwidths_returns_early(self) -> None:
        # Direct call with [] hits the early `not widths` return.
        rows = [{"type": "tableRow", "content": [{"type": "tableCell"}]}]
        table = ast.Table(
            content=[ast.TableRow(content=[ast.TableCell(content=[])])],
            colwidths=[],
        )
        _distribute_colwidths(table, rows)
        assert "attrs" not in rows[0]["content"][0]


class TestTaskListNested:
    def test_nested_task_list_in_task_list(self) -> None:
        outer = ast.TaskList(
            content=[
                ast.TaskItem(state="TODO", content=[ast.Text(text="a")]),
                ast.TaskList(
                    content=[ast.TaskItem(state="DONE", content=[ast.Text(text="b")])]
                ),
            ]
        )
        result = render(ast.Doc(content=[]))
        # Render the outer directly to drive the nested branch.
        rendered = render_block(outer)
        assert rendered is not None
        assert rendered["type"] == "taskList"
        items = rendered["content"]
        assert items[0]["type"] == "taskItem"
        assert items[1]["type"] == "taskList"
        assert result["type"] == "doc"
