"""Direct unit tests for marklas.md.parser.inline edge cases.

The integration tests in tests/md/test_parser.py exercise the common
paths through the inline pipeline. This module pokes the seldom-touched
branches directly so coverage reaches every dispatcher arm.
"""

from __future__ import annotations

from marklas import ast
from marklas.md.parser.inline import (
    _apply_html_mark,
    _build_paired_inline,
    _build_raw_inline,
    parse_inlines,
    parse_normalized_inlines,
    reparse_text_inlines,
)
from marklas.md.parser.ir import HtmlPaired, HtmlVoid


class TestReparseTextInlines:
    def test_text_token_is_reparsed(self) -> None:
        out = reparse_text_inlines([{"type": "text", "raw": "**bold**"}])
        # Re-parsed inline → at least one strong token in the output
        assert any(t.get("type") == "strong" for t in out)

    def test_non_text_token_passes_through(self) -> None:
        token = {"type": "softbreak"}
        out = reparse_text_inlines([token])
        assert out == [token]

    def test_empty_raw_text_is_dropped(self) -> None:
        # Empty raw text → inline parser yields nothing; the helper produces []
        out = reparse_text_inlines([{"type": "text", "raw": ""}])
        assert out == []


class TestFlattenEdgeCases:
    def test_non_br_void_is_dropped(self) -> None:
        result = parse_normalized_inlines(
            [HtmlVoid(tag="img", attrs={"src": "x"}), {"type": "text", "raw": "after"}]
        )
        assert result == [ast.Text(text="after")]

    def test_softbreak_with_parent_marks(self) -> None:
        # Softbreak nested under strong inherits the StrongMark.
        result = parse_inlines(
            [
                {
                    "type": "strong",
                    "children": [
                        {"type": "text", "raw": "a"},
                        {"type": "softbreak"},
                        {"type": "text", "raw": "b"},
                    ],
                }
            ]
        )
        # Should produce a single merged Text "a b" with StrongMark applied.
        assert len(result) == 1
        node = result[0]
        assert isinstance(node, ast.Text)
        assert node.text == "a b"
        assert any(isinstance(m, ast.StrongMark) for m in node.marks)

    def test_linebreak_token(self) -> None:
        result = parse_inlines([{"type": "linebreak"}])
        assert result == [ast.HardBreak()]

    def test_softbreak_without_parent_marks(self) -> None:
        result = parse_inlines([{"type": "softbreak"}])
        assert result == [ast.Text(text=" ")]

    def test_unknown_raw_token_no_children(self) -> None:
        result = parse_inlines([{"type": "mystery"}])
        assert result == []


class TestPairedInlineUnknownAdf:
    def test_unknown_adf_emits_inline_text(self) -> None:
        token = HtmlPaired(
            tag="span",
            attrs={"adf": "definitelyUnknownThing"},
            inner=[{"type": "text", "raw": "hello"}],
        )
        result = _build_paired_inline(token, [])
        assert len(result) == 1
        node = result[0]
        assert isinstance(node, ast.Text)
        assert node.text == "hello"
        assert list(node.marks) == []

    def test_unknown_adf_preserves_parent_marks(self) -> None:
        token = HtmlPaired(
            tag="span",
            attrs={"adf": "definitelyUnknownThing"},
            inner=[{"type": "text", "raw": "x"}],
        )
        result = _build_paired_inline(token, [ast.StrongMark()])
        assert len(result) == 1
        node = result[0]
        assert isinstance(node, ast.Text)
        assert any(isinstance(m, ast.StrongMark) for m in node.marks)


class TestApplyHtmlMarkUnknown:
    def test_unknown_adf_returns_text(self) -> None:
        # Direct call simulates a future-extended dispatch path that handed
        # _apply_html_mark an adf_type outside the matched set.
        result = _apply_html_mark(
            tag="span",
            adf_type="someFutureMark",
            attrs={},
            inner=[{"type": "text", "raw": "x"}],
            parent_marks=[],
        )
        assert len(result) == 1
        node = result[0]
        assert isinstance(node, ast.Text)
        assert node.text == "x"
        assert list(node.marks) == []

    def test_unknown_adf_preserves_parent_marks(self) -> None:
        result = _apply_html_mark(
            tag="span",
            adf_type="someFutureMark",
            attrs={},
            inner=[{"type": "text", "raw": "x"}],
            parent_marks=[ast.EmMark()],
        )
        node = result[0]
        assert isinstance(node, ast.Text)
        assert any(isinstance(m, ast.EmMark) for m in node.marks)


class TestBuildRawInlineDirectly:
    def test_text_without_marks(self) -> None:
        out = _build_raw_inline({"type": "text", "raw": "x"}, [])
        assert out == [ast.Text(text="x")]
