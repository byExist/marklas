"""Direct unit tests for marklas.md.parser.block edge cases.

Targets the same code paths as the integration tests in test_parser.py /
test_roundtrip.py, but pokes the seldom-touched branches by feeding the
internal builders synthetic mistune-style token dicts directly.
"""

from __future__ import annotations

from typing import Any

from marklas import ast, parse_md
from marklas.md.parser.block import (
    _build_block,
    _build_block_task_item,
    _build_expand,
    _build_html_paired,
    _build_image,
    _build_mistune_block,
    _build_paragraph,
    _build_task_item_dispatch,
    _collect_media_items,
    _extract_cell_meta,
    _is_empty_cell,
    _media_wrapping_mark,
    _sparsify_rows,
    _split_mixed_list_token,
    _split_nested_task_lists,
    build_decision_list,
    build_html_void,
    build_task_list,
    dispatch_blocks,
)
from marklas.md.parser.ir import HtmlPaired, HtmlVoid


def _para(raw: str) -> dict[str, Any]:
    return {
        "type": "paragraph",
        "children": [{"type": "text", "raw": raw}],
    }


class TestBuildBlockDispatch:
    def test_unknown_token_returns_none(self) -> None:
        # The fallthrough case in _build_block. Any non-(HtmlPaired|HtmlVoid|dict)
        # token returns None.
        assert _build_block("not a token") is None  # type: ignore[arg-type]

    def test_unknown_mistune_type_returns_none(self) -> None:
        assert _build_mistune_block({"type": "future_node_type"}) is None


class TestHtmlPairedBuilders:
    def test_paired_task_list(self) -> None:
        token = HtmlPaired(
            tag="ul",
            attrs={"adf": "taskList"},
            inner=[
                {
                    "type": "block_html",
                    "raw": '<li adf="taskItem" params=\'{"state":"TODO"}\'>x</li>',
                }
            ],
        )
        node = _build_html_paired(token)
        assert isinstance(node, ast.TaskList)
        assert len(node.content) == 1
        assert isinstance(node.content[0], ast.TaskItem)

    def test_paired_extension_routes_to_void(self) -> None:
        token = HtmlPaired(
            tag="div",
            attrs={
                "adf": "extension",
                "params": '{"extensionKey":"k","extensionType":"t"}',
            },
            inner=[],
        )
        node = _build_html_paired(token)
        assert isinstance(node, ast.Extension)

    def test_paired_empty_adf_non_p_returns_none(self) -> None:
        # Plain HTML element with no `adf=` and not `<p>`.
        token = HtmlPaired(tag="span", attrs={}, inner=[])
        assert _build_html_paired(token) is None

    def test_paired_unknown_adf_returns_none(self) -> None:
        token = HtmlPaired(tag="div", attrs={"adf": "ghost"}, inner=[])
        assert _build_html_paired(token) is None

    def test_paired_empty_p_with_block_marks(self) -> None:
        token = HtmlPaired(
            tag="p",
            attrs={"params": '{"align":"center"}'},
            inner=[],
        )
        node = _build_html_paired(token)
        assert isinstance(node, ast.Paragraph)
        assert any(isinstance(m, ast.AlignmentMark) for m in node.marks)


class TestParagraphNbspEmpty:
    def test_nbsp_text_becomes_empty_paragraph(self) -> None:
        node = _build_paragraph(
            {
                "type": "paragraph",
                "children": [{"type": "text", "raw": "\xa0"}],
            }
        )
        assert node.content == []

    def test_amp_nbsp_text_becomes_empty_paragraph(self) -> None:
        node = _build_paragraph(
            {
                "type": "paragraph",
                "children": [{"type": "text", "raw": "&nbsp;"}],
            }
        )
        assert node.content == []


class TestSplitMixedListToken:
    def test_empty_children_returns_self(self) -> None:
        token: dict[str, Any] = {"type": "list", "children": []}
        assert _split_mixed_list_token(token) == [token]

    def test_only_one_kind_returns_self(self) -> None:
        token = {
            "type": "list",
            "children": [{"type": "list_item"}, {"type": "list_item"}],
        }
        assert _split_mixed_list_token(token) == [token]

    def test_mixed_split_with_intervening_other(self) -> None:
        # Mixed task/plain with an intervening non-item child (e.g. `list`)
        # exercises the kind-is-None branch.
        token = {
            "type": "list",
            "children": [
                {"type": "task_list_item"},
                {"type": "list"},  # not an item — sticks with current group
                {"type": "list_item"},
            ],
        }
        groups = _split_mixed_list_token(token)
        assert len(groups) == 2


class TestBuildListNestedTask:
    def test_task_item_with_nested_sub_list(self) -> None:
        # A task_list_item whose children include a nested `list` of more
        # task_list_items.
        result = parse_md("- [ ] parent\n  - [x] child\n")
        # First DocContent should be a TaskList; nested taskList is appended
        # as a sibling inside the parent TaskList.
        task_lists = [n for n in result.content if isinstance(n, ast.TaskList)]
        assert task_lists
        outer = task_lists[0]
        # outer.content: [parent_item, nested_task_list]
        assert isinstance(outer.content[0], ast.TaskItem)
        assert any(isinstance(c, ast.TaskList) for c in outer.content)

    def test_top_level_sub_list_branch(self) -> None:
        # Drive the `child.get("type") == "list"` fallback inside _build_list:
        # an outer task list with a non-task `list` sibling child that itself
        # contains task items.
        from marklas.md.parser.block import _build_list

        token = {
            "type": "list",
            "attrs": {"ordered": False},
            "children": [
                {
                    "type": "task_list_item",
                    "attrs": {"checked": False},
                    "children": [
                        {
                            "type": "block_text",
                            "children": [{"type": "text", "raw": "p"}],
                        }
                    ],
                },
                {
                    "type": "list",
                    "attrs": {"ordered": False},
                    "children": [
                        {
                            "type": "task_list_item",
                            "attrs": {"checked": False},
                            "children": [
                                {
                                    "type": "block_text",
                                    "children": [{"type": "text", "raw": "c"}],
                                }
                            ],
                        }
                    ],
                },
            ],
        }
        node = _build_list(token)
        assert isinstance(node, ast.TaskList)
        assert any(isinstance(c, ast.TaskList) for c in node.content)


class TestBlockTaskItem:
    def test_multiple_blocks_becomes_block_task_item(self) -> None:
        # task_list_item with two paragraph children → BlockTaskItem
        token = {
            "type": "task_list_item",
            "attrs": {"checked": True},
            "children": [
                {
                    "type": "block_text",
                    "children": [{"type": "text", "raw": "first"}],
                },
                {"type": "blank_line"},
                _para("second"),
            ],
        }
        node = _build_task_item_dispatch(token)
        assert isinstance(node, ast.BlockTaskItem)
        assert node.state == "DONE"

    def test_block_task_item_ignores_unsupported_child(self) -> None:
        node = _build_block_task_item(
            {
                "type": "task_list_item",
                "attrs": {"checked": False},
                "children": [
                    _para("ok"),
                    {"type": "block_code", "raw": "x"},
                ],
            }
        )
        # CodeBlock isn't supported in BlockTaskItem content → only paragraph.
        assert all(isinstance(c, ast.Paragraph) for c in node.content)
        assert len(node.content) == 1


class TestBuildImage:
    def test_image_with_text_children_for_alt(self) -> None:
        token = {
            "type": "image",
            "attrs": {"url": "http://x/y.png"},
            "children": [{"type": "text", "raw": "alt-from-children"}],
        }
        node = _build_image(token)
        assert isinstance(node, ast.MediaSingle)
        media = node.content[0]
        assert isinstance(media, ast.Media)
        assert media.alt == "alt-from-children"


class TestBuildExpandNested:
    def test_nested_expand_branch(self) -> None:
        node = _build_expand(
            "nestedExpand",
            {"params": '{"title":"t"}'},
            inner=[_para("body")],
        )
        assert isinstance(node, ast.NestedExpand)
        assert node.title == "t"


class TestDecisionAndTaskListBuilders:
    def test_decision_list_skips_void_group(self) -> None:
        # A self-closing tag in the inline stream becomes a `_void` group,
        # which the builder must skip.
        inline_tokens = [
            {"type": "inline_html", "raw": "<br/>"},
            {
                "type": "inline_html",
                "raw": '<li adf="decisionItem" params=\'{"state":"open"}\'>',
            },
            {"type": "text", "raw": "kept"},
            {"type": "inline_html", "raw": "</li>"},
        ]
        result = build_decision_list({}, inline_tokens)
        assert len(result.content) == 1

    def test_task_list_skips_void_group(self) -> None:
        inline_tokens = [
            {"type": "inline_html", "raw": "<br/>"},
            {
                "type": "inline_html",
                "raw": '<li adf="taskItem" params=\'{"state":"TODO"}\'>',
            },
            {"type": "text", "raw": "kept"},
            {"type": "inline_html", "raw": "</li>"},
        ]
        result = build_task_list({}, inline_tokens)
        assert len(result.content) == 1

    def test_decision_list_skips_non_li(self) -> None:
        # Inline tokens with a stray non-li paired group (e.g. `<span>`) plus
        # a real `<li>`.
        inline_tokens = [
            {"type": "inline_html", "raw": '<span adf="other">'},
            {"type": "text", "raw": "junk"},
            {"type": "inline_html", "raw": "</span>"},
            {
                "type": "inline_html",
                "raw": '<li adf="decisionItem" params=\'{"state":"open"}\'>',
            },
            {"type": "text", "raw": "kept"},
            {"type": "inline_html", "raw": "</li>"},
        ]
        result = build_decision_list({}, inline_tokens)
        assert len(result.content) == 1
        assert result.content[0].state == "open"

    def test_task_list_skips_non_li(self) -> None:
        inline_tokens = [
            {"type": "inline_html", "raw": '<span adf="other">'},
            {"type": "text", "raw": "junk"},
            {"type": "inline_html", "raw": "</span>"},
            {
                "type": "inline_html",
                "raw": '<li adf="taskItem" params=\'{"state":"DONE"}\'>',
            },
            {"type": "text", "raw": "kept"},
            {"type": "inline_html", "raw": "</li>"},
        ]
        result = build_task_list({}, inline_tokens)
        assert len(result.content) == 1
        item = result.content[0]
        assert isinstance(item, ast.TaskItem)
        assert item.state == "DONE"

    def test_task_list_with_nested_sub_list(self) -> None:
        # `<li adf="taskItem">parent <ul adf="taskList"><li ...>child</li></ul></li>`
        # The inner ul is lifted out and appended as a sibling TaskList.
        inline_tokens = [
            {
                "type": "inline_html",
                "raw": '<li adf="taskItem" params=\'{"state":"TODO"}\'>',
            },
            {"type": "text", "raw": "parent"},
            {"type": "inline_html", "raw": '<ul adf="taskList">'},
            {
                "type": "inline_html",
                "raw": '<li adf="taskItem" params=\'{"state":"DONE"}\'>',
            },
            {"type": "text", "raw": "child"},
            {"type": "inline_html", "raw": "</li>"},
            {"type": "inline_html", "raw": "</ul>"},
            {"type": "inline_html", "raw": "</li>"},
        ]
        result = build_task_list({}, inline_tokens)
        # parent + nested TaskList
        assert len(result.content) == 2
        assert isinstance(result.content[0], ast.TaskItem)
        assert isinstance(result.content[1], ast.TaskList)


class TestSplitNestedTaskLists:
    def test_unmatched_open_falls_through(self) -> None:
        # No matching </ul> means it gets appended to `cleaned`, not split.
        tokens = [
            {"type": "inline_html", "raw": '<ul adf="taskList">'},
            {"type": "text", "raw": "no close"},
        ]
        sub_lists, cleaned = _split_nested_task_lists(tokens)
        assert sub_lists == []
        assert len(cleaned) == 2


class TestCollectMediaItems:
    def test_media_with_outer_link_mark(self) -> None:
        # <a adf="link" href="..."> wrapping <span adf="media"> — the wrapping
        # LinkMark accumulates onto the leaf Media.
        wrapped = HtmlPaired(
            tag="a",
            attrs={"adf": "link", "href": "http://x"},
            inner=[
                HtmlPaired(
                    tag="span",
                    attrs={
                        "adf": "media",
                        "params": '{"id":"i","collection":"c","type":"file"}',
                    },
                    inner=[],
                )
            ],
        )
        out: list[ast.Media | ast.Caption] = []
        _collect_media_items(wrapped, out)
        assert isinstance(out[0], ast.Media)
        assert any(isinstance(m, ast.LinkMark) for m in out[0].marks)

    def test_caption_collected(self) -> None:
        # A caption HtmlPaired sibling to media in mediaSingle's inner.
        cap = HtmlPaired(
            tag="span",
            attrs={"adf": "caption"},
            inner=[{"type": "text", "raw": "hello"}],
        )
        out: list[ast.Media | ast.Caption] = []
        _collect_media_items(cap, out)
        assert isinstance(out[0], ast.Caption)

    def test_no_wrapping_mark_drops_silently(self) -> None:
        # A wrapper with no extractable mark (e.g. <span> without adf and no
        # `a` tag) drops without emitting anything.
        wrapped = HtmlPaired(tag="span", attrs={}, inner=[])
        out: list[ast.Media | ast.Caption] = []
        _collect_media_items(wrapped, out)
        assert out == []

    def test_annotation_wrapping_mark(self) -> None:
        wrapped = HtmlPaired(
            tag="span",
            attrs={"adf": "annotation", "params": '{"id":"a1"}'},
            inner=[
                HtmlPaired(
                    tag="span",
                    attrs={
                        "adf": "media",
                        "params": '{"id":"i","collection":"c","type":"file"}',
                    },
                    inner=[],
                )
            ],
        )
        out: list[ast.Media | ast.Caption] = []
        _collect_media_items(wrapped, out)
        assert isinstance(out[0], ast.Media)
        assert any(isinstance(m, ast.AnnotationMark) for m in out[0].marks)


class TestMediaWrappingMark:
    def test_link_mark_extraction(self) -> None:
        wrapped = HtmlPaired(
            tag="a", attrs={"adf": "link", "href": "h", "title": "t"}, inner=[]
        )
        mark = _media_wrapping_mark(wrapped)
        assert isinstance(mark, ast.LinkMark)
        assert mark.href == "h"
        assert mark.title == "t"


class TestSparsifyRowsEmpty:
    def test_empty_table_short_circuits(self) -> None:
        table = ast.Table(content=[])
        _sparsify_rows(table)
        assert table.content == []


class TestSparsifyRowsRowspanOverflow:
    def test_rowspan_exceeding_table_height_breaks(self) -> None:
        # A rowspan greater than the remaining rows triggers the inner
        # `if rr >= num_rows: break` short-circuit.
        table = ast.Table(
            content=[
                ast.TableRow(
                    content=[
                        ast.TableCell(content=[], rowspan=5),
                    ]
                ),
            ]
        )
        _sparsify_rows(table)
        assert len(table.content[0].content) == 1


class TestSparsifyRowsKeepsEmptyAtOccupied:
    def test_empty_cell_at_occupied_slot_skipped(self) -> None:
        # First row claims col 0 with rowspan 2. Second row's first cell
        # (empty) sits at the occupied slot and gets dropped.
        table = ast.Table(
            content=[
                ast.TableRow(
                    content=[
                        ast.TableCell(content=[], rowspan=2),
                        ast.TableCell(content=[]),
                    ]
                ),
                ast.TableRow(
                    content=[
                        ast.TableCell(content=[]),  # padding at occupied slot
                        ast.TableCell(content=[]),
                    ]
                ),
            ]
        )
        _sparsify_rows(table)
        # Second row should have only one cell left (padding dropped).
        assert len(table.content[1].content) == 1


class TestIsEmptyCell:
    def test_empty_content_is_empty(self) -> None:
        assert _is_empty_cell(ast.TableCell(content=[]))

    def test_multiple_blocks_not_empty(self) -> None:
        assert not _is_empty_cell(
            ast.TableCell(
                content=[ast.Paragraph(content=[]), ast.Paragraph(content=[])]
            )
        )

    def test_non_paragraph_not_empty(self) -> None:
        assert not _is_empty_cell(ast.TableCell(content=[ast.Rule()]))

    def test_paragraph_with_one_empty_text_is_empty(self) -> None:
        assert _is_empty_cell(
            ast.TableCell(content=[ast.Paragraph(content=[ast.Text(text="   ")])])
        )

    def test_empty_paragraph_is_empty(self) -> None:
        # Paragraph(content=[]) → inlines list is empty
        assert _is_empty_cell(ast.TableCell(content=[ast.Paragraph(content=[])]))

    def test_paragraph_with_text_is_not_empty(self) -> None:
        assert not _is_empty_cell(
            ast.TableCell(content=[ast.Paragraph(content=[ast.Text(text="x")])])
        )

    def test_paragraph_with_non_text_is_not_empty(self) -> None:
        assert not _is_empty_cell(
            ast.TableCell(content=[ast.Paragraph(content=[ast.HardBreak()])])
        )


class TestCellMetaExplicitHeader:
    def test_explicit_header_overrides_table_mode(self) -> None:
        # A cell with header=False in cell meta even when the row is the
        # head row.
        md = '| <div adf="cell" params=\'{"header":false}\'></div>X |\n| --- |\n| Y |\n'
        doc = parse_md(md)
        # The head cell carries cell meta with header=false → becomes TableCell
        table = next(n for n in doc.content if isinstance(n, ast.Table))
        head_cell = table.content[0].content[0]
        assert isinstance(head_cell, ast.TableCell) and not isinstance(
            head_cell, ast.TableHeader
        )


class TestExtractCellMeta:
    def test_empty_children_returns_empty(self) -> None:
        meta, children = _extract_cell_meta([])
        assert meta == {}
        assert children == []


class TestBuildHtmlVoidUnknown:
    def test_unknown_void_returns_none(self) -> None:
        assert build_html_void(HtmlVoid(tag="div", attrs={"adf": "ghost"})) is None


class TestListItemEmptyParagraph:
    def test_block_text_with_nbsp_only_paragraph(self) -> None:
        # Drive the `block_text → empty paragraph` branch in dispatch_blocks
        # by handing it a synthetic block_text whose sole text child is nbsp.
        from marklas.md.parser.ir import Token

        tokens: list[Token] = [
            {
                "type": "block_text",
                "children": [{"type": "text", "raw": "\xa0"}],
            }
        ]
        result = list(dispatch_blocks(tokens, list_item=True))
        assert result == [ast.Paragraph(content=[])]
