"""Direct unit tests for marklas.md.renderer.cell edge cases."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from marklas import ast
from marklas.md.renderer import block as block_renderer
from marklas.md.renderer.cell import (
    render_expand,
    render_task_list,
)


@pytest.fixture
def in_cell() -> Iterator[None]:
    """Enter cell rendering context for the duration of one test."""
    token = block_renderer._ctx.set(block_renderer._Ctx.CELL)
    try:
        yield
    finally:
        block_renderer._ctx.reset(token)


class TestLiContentMultiChildren:
    def test_list_item_with_multiple_children_in_cell(self, in_cell: None) -> None:
        # _li_content's "concatenate all" branch is reached when a list
        # item holds more than just a single paragraph.
        bullet_list = ast.BulletList(
            content=[
                ast.ListItem(
                    content=[
                        ast.Paragraph(content=[ast.Text(text="a")]),
                        ast.Paragraph(content=[ast.Text(text="b")]),
                    ]
                )
            ]
        )
        rendered = block_renderer.render_block(bullet_list)
        # Should render as <ul><li>...</li></ul> with both paragraphs joined
        assert "<ul>" in rendered
        assert "a" in rendered
        assert "b" in rendered


class TestExpandInCell:
    def test_expand_with_title_inside_cell(self, in_cell: None) -> None:
        node = ast.Expand(
            title="t",
            content=[ast.Paragraph(content=[ast.Text(text="body")])],
        )
        result = render_expand(node)
        assert '<details adf="expand">' in result
        assert "<summary>t</summary>" in result
        assert "body" in result

    def test_expand_without_title_inside_cell(self, in_cell: None) -> None:
        node = ast.Expand(title=None, content=[])
        result = render_expand(node)
        assert "summary" not in result


class TestTaskListNested:
    def test_task_item_followed_by_nested_list_in_cell(self, in_cell: None) -> None:
        node = ast.TaskList(
            content=[
                ast.TaskItem(state="TODO", content=[ast.Text(text="parent")]),
                ast.TaskList(
                    content=[ast.TaskItem(state="DONE", content=[ast.Text(text="kid")])]
                ),
            ]
        )
        result = render_task_list(node)
        # The nested list should be embedded inside the parent li.
        assert result.count("<li") == 2  # parent + child wrapped inside
        assert result.startswith('<ul adf="taskList">')

    def test_block_task_item_with_nested_list_in_cell(self, in_cell: None) -> None:
        node = ast.TaskList(
            content=[
                ast.BlockTaskItem(
                    state="TODO",
                    content=[ast.Paragraph(content=[ast.Text(text="b1")])],
                ),
                ast.TaskList(
                    content=[
                        ast.TaskItem(state="DONE", content=[ast.Text(text="nested")])
                    ]
                ),
            ]
        )
        result = render_task_list(node)
        assert "b1" in result
        assert "nested" in result

    def test_task_item_followed_by_another_task_item(self, in_cell: None) -> None:
        # Lookahead breaks early when the next sibling isn't a nested TaskList.
        node = ast.TaskList(
            content=[
                ast.TaskItem(state="TODO", content=[ast.Text(text="first")]),
                ast.TaskItem(state="DONE", content=[ast.Text(text="second")]),
            ]
        )
        result = render_task_list(node)
        assert "first" in result
        assert "second" in result

    def test_block_task_item_followed_by_task_item(self, in_cell: None) -> None:
        # Same lookahead-break path for the BlockTaskItem arm.
        node = ast.TaskList(
            content=[
                ast.BlockTaskItem(
                    state="TODO",
                    content=[ast.Paragraph(content=[ast.Text(text="b")])],
                ),
                ast.TaskItem(state="DONE", content=[ast.Text(text="after")]),
            ]
        )
        result = render_task_list(node)
        assert "b" in result
        assert "after" in result

    def test_leading_task_list_emitted_as_is(self, in_cell: None) -> None:
        # When a TaskList appears with no preceding TaskItem, the renderer
        # falls back to nesting it as a sibling.
        node = ast.TaskList(
            content=[
                ast.TaskList(
                    content=[
                        ast.TaskItem(state="TODO", content=[ast.Text(text="orphan")])
                    ]
                )
            ]
        )
        result = render_task_list(node)
        assert "orphan" in result

    def test_unknown_child_passes_silently(self, in_cell: None) -> None:
        # The `case _: pass` arm: feed a TaskList with a non-task child
        # (which violates the type but exercises the dead-branch arm).
        node = ast.TaskList(content=[ast.Paragraph(content=[])])  # type: ignore[list-item]
        result = render_task_list(node)
        # Nothing visible from the foreign child.
        assert result == '<ul adf="taskList"></ul>'
