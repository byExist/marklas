from __future__ import annotations

from collections.abc import Sequence
from dataclasses import fields
from typing import TypeVar

from marklas import Transformer, parse_md
from marklas.ast import (
    CodeBlock,
    Doc,
    Expand,
    Heading,
    Node,
    Paragraph,
    Text,
)


_N = TypeVar("_N", bound=Node)


def _collect(doc: Node, ntype: type[_N]) -> list[_N]:
    result: list[_N] = []
    for f in fields(doc):
        value = getattr(doc, f.name)
        if not isinstance(value, Sequence) or isinstance(value, str):
            continue
        for child in value:  # type: ignore
            if not isinstance(child, Node):
                continue
            if isinstance(child, ntype):
                result.append(child)
            result.extend(_collect(child, ntype))
    return result


class TestTransformer:
    def test_replace_node(self) -> None:
        t = Transformer()

        @t.register(Heading)
        def _(node: Heading) -> Paragraph:
            return Paragraph(content=[Text(text="replaced")])

        doc = parse_md("# Title\n\nparagraph")
        new_doc = t(doc)
        assert not _collect(new_doc, Heading)
        texts = [n.text for n in _collect(new_doc, Text)]
        assert "replaced" in texts

    def test_expand_node_to_list(self) -> None:
        t = Transformer()

        @t.register(CodeBlock)
        def _(node: CodeBlock) -> list[Node] | None:
            if node.language == "mermaid":
                diagram = Paragraph(content=[Text(text="[diagram]")])
                hidden = Expand(title="mermaid source", content=[node])
                return [diagram, hidden]
            return None

        doc = parse_md("```mermaid\ngraph LR\n```")
        new_doc = t(doc)
        expands = _collect(new_doc, Expand)
        assert len(expands) == 1
        assert expands[0].title == "mermaid source"
        texts = [n.text for n in _collect(new_doc, Text)]
        assert "[diagram]" in texts

    def test_no_change_returns_same_node(self) -> None:
        t = Transformer()
        doc = parse_md("hello")
        assert t(doc) is doc

    def test_original_unchanged(self) -> None:
        t = Transformer()

        @t.register(Heading)
        def _(node: Heading) -> Paragraph:
            return Paragraph(content=[Text(text="x")])

        doc = parse_md("# Title")
        t(doc)
        assert len(_collect(doc, Heading)) == 1

    def test_empty_doc(self) -> None:
        t = Transformer()
        doc = Doc(content=[])
        assert t(doc) is doc

    def test_bottom_up_order(self) -> None:
        visited: list[type] = []
        t = Transformer()

        @t.register(Text)
        def _(node: Text) -> None:
            visited.append(type(node))

        @t.register(Paragraph)
        def _(node: Paragraph) -> None:
            visited.append(type(node))

        doc = parse_md("hello **world**")
        t(doc)
        text_indices = [i for i, tp in enumerate(visited) if tp is Text]
        para_indices = [i for i, tp in enumerate(visited) if tp is Paragraph]
        assert all(ti < pi for ti in text_indices for pi in para_indices)

    def test_multiple_handlers_different_types(self) -> None:
        t = Transformer()

        @t.register(CodeBlock)
        def _(node: CodeBlock) -> list[Node] | None:
            if node.language == "mermaid":
                return [
                    Paragraph(content=[Text(text="[diagram]")]),
                    Expand(title="source", content=[node]),
                ]
            return None

        @t.register(Heading)
        def _(node: Heading) -> Heading | None:
            if node.level == 1:
                return Heading(level=2, content=node.content)
            return None

        doc = parse_md("# Title\n\n```mermaid\ngraph LR\n```")
        new_doc = t(doc)
        headings = _collect(new_doc, Heading)
        assert headings[0].level == 2
        assert len(_collect(new_doc, Expand)) == 1

    def test_multiple_handlers_same_type(self) -> None:
        t = Transformer()

        @t.register(CodeBlock)
        def _(node: CodeBlock) -> list[Node] | None:
            if node.language == "mermaid":
                return [
                    Paragraph(content=[Text(text="[diagram]")]),
                    Expand(title="source", content=[node]),
                ]
            return None

        @t.register(CodeBlock)
        def _(node: CodeBlock) -> CodeBlock | None:
            if node.language == "python":
                return CodeBlock(language="python", content=[Text(text="highlighted")])
            return None

        doc = parse_md("```mermaid\ngraph LR\n```\n\n```python\nprint(1)\n```")
        new_doc = t(doc)
        assert len(_collect(new_doc, Expand)) == 1
        texts = [n.text for n in _collect(new_doc, Text)]
        assert "[diagram]" in texts
        assert "highlighted" in texts

    def test_handler_order_first_wins(self) -> None:
        t = Transformer()

        @t.register(Heading)
        def _(node: Heading) -> Paragraph:
            return Paragraph(content=[Text(text="first")])

        @t.register(Heading)
        def _(node: Heading) -> Paragraph:
            return Paragraph(content=[Text(text="second")])

        doc = parse_md("# Title")
        new_doc = t(doc)
        texts = [n.text for n in _collect(new_doc, Text)]
        assert "first" in texts
        assert "second" not in texts

    def test_unmatched_node_unchanged(self) -> None:
        t = Transformer()

        @t.register(Heading)
        def _(node: Heading) -> Paragraph:
            return Paragraph(content=[Text(text="replaced")])

        doc = parse_md("just text")
        assert t(doc) is doc
