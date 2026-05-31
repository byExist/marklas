"""Cell-context block renderers.

These functions are dispatched from `block._render_*` when `_in_cell()`
is true (inside a GFM table cell). GFM cells forbid newlines and Markdown
markers (`-`, `>`, `#`) lose their meaning, so every cell-level block has
to be encoded as inline HTML on a single line. That HTML shape is
fundamentally different from the top-level Markdown shape, which is why
this module exists as a sibling of `block` rather than a sub-branch
inside each block renderer function.

Cycle-safe imports: this module calls into `block` via the module
reference (`from . import block`), so attribute access happens at call
time, not at import time.
"""

from __future__ import annotations

from collections.abc import Sequence

from marklas import ast

from . import block


# ── Cell-only helpers ─────────────────────────────────────────────────────────


def _li_content(children: Sequence[ast.Node]) -> str:
    """List item content in cell context. Single Paragraph → bare text."""
    if len(children) == 1 and isinstance(children[0], ast.Paragraph):
        return block.render_inlines(children[0].content)
    return "".join(block.render_block(c) for c in children)


# ── Block renderers ──────────────────────────────────────────────────────────


def render_paragraph(node: ast.Paragraph) -> str:
    # Inside cells we emit <p> with <br> for hardBreaks, so the boundary
    # cleanup that the block path needs isn't required here.
    content = block.render_inlines(node.content)
    params = block.build_params(block.block_marks_params(node.marks))
    return block.el("p", content, params=params)


def render_heading(node: ast.Heading) -> str:
    content = block.render_inlines(node.content)
    params = block.build_params(block.block_marks_params(node.marks))
    return block.el(f"h{node.level}", content, params=params)


def render_code_block(node: ast.CodeBlock) -> str:
    code = "".join(t.text for t in node.content)
    marks_dict = block.block_marks_params(node.marks)
    if node.language:
        marks_dict["language"] = node.language
    params = block.build_params(marks_dict)
    # Cell row is single-line in GFM — a real `\n` would terminate it.
    # Use `<br>` (the cell-context line-break form) instead of collapsing
    # to space; preserves multi-line code visually inside the cell.
    return block.el("code", code.replace("\n", "<br>"), params=params)


def render_blockquote(node: ast.Blockquote) -> str:
    parts = block.render_blocks(node.content)
    return block.el("blockquote", "".join(parts))


def render_bullet_list(node: ast.BulletList) -> str:
    items = "".join(block.el("li", _li_content(item.content)) for item in node.content)
    return block.el("ul", items)


def render_ordered_list(node: ast.OrderedList) -> str:
    start = node.order or 1
    items = "".join(block.el("li", _li_content(item.content)) for item in node.content)
    return block.el("ol", items, start=start if start != 1 else None)


def render_panel(node: ast.Panel) -> str:
    content = "".join(block.render_blocks(node.content))
    return block.block_el(
        "aside", content, adf="panel", params=block.panel_params(node)
    )


def render_expand(node: ast.Expand) -> str:
    # Cell context: block marks are folded into the surrounding `<p>` /
    # cell metadata, so we don't emit a `<data adf="marks">` prefix here.
    summary = block.el("summary", block.inline_safe(node.title)) if node.title else ""
    content = "".join(block.render_blocks(node.content))
    return block.el("details", summary + content, adf="expand")


def render_nested_expand(node: ast.NestedExpand) -> str:
    summary = block.el("summary", block.inline_safe(node.title)) if node.title else ""
    content = "".join(block.render_blocks(node.content))
    return block.el("details", summary + content, adf="nestedExpand")


def render_task_list(node: ast.TaskList) -> str:
    # ADF's `taskList > [taskItem, …, nested-taskList]` would emit
    # `<ul>…<ul>…</ul></ul>` if naively dispatched — ill-formed HTML.
    # Embed nested taskLists inside the preceding `<li>` so the markup
    # stays well-formed; the parser lifts them back to sibling position.
    items: list[str] = []
    children = list(node.content)
    i = 0
    while i < len(children):
        child = children[i]
        match child:
            case ast.TaskItem():
                body = block.render_inlines(child.content)
                params = block.build_params({"state": child.state})
                while i + 1 < len(children):
                    nxt = children[i + 1]
                    if not isinstance(nxt, ast.TaskList):
                        break
                    body += block.render_task_list(nxt)
                    i += 1
                items.append(block.el("li", body, adf="taskItem", params=params))
            case ast.BlockTaskItem():
                body = "".join(block.render_blocks(child.content))
                params = block.build_params({"state": child.state})
                while i + 1 < len(children):
                    nxt = children[i + 1]
                    if not isinstance(nxt, ast.TaskList):
                        break
                    body += block.render_task_list(nxt)
                    i += 1
                items.append(block.el("li", body, adf="taskItem", params=params))
            case ast.TaskList():
                # Leading nested taskList with no prior item — fall back
                # to ill-formed but unambiguous output rather than
                # attaching to a non-existent item.
                items.append(block.render_task_list(child))
            case _:
                pass
        i += 1
    return block.el("ul", "".join(items), adf="taskList")
