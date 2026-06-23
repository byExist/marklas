"""Direct unit tests for marklas.md.parser.normalize edge cases."""

from __future__ import annotations

import pytest

from marklas.md.parser.ir import HtmlPaired, HtmlVoid
from marklas.md.parser.normalize import (
    find_paired_close,
    normalize_blocks,
    normalize_inlines,
    parse_params,
    parse_tag,
    split_html_string,
    tokenize,
)


class TestTokenize:
    def test_returns_list_for_normal_markdown(self) -> None:
        tokens = tokenize("hello")
        assert isinstance(tokens, list)

    def test_raises_on_non_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import marklas.md.parser.normalize as norm_mod

        def fake(_: str) -> str:
            return "not a list"

        monkeypatch.setattr(norm_mod, "_md", fake)
        with pytest.raises(TypeError):
            tokenize("hello")


class TestParseTag:
    def test_unparseable_returns_empty(self) -> None:
        assert parse_tag("not a tag at all") == ("", {}, False)


class TestParseParams:
    def test_invalid_json_returns_empty_dict(self) -> None:
        assert parse_params("not-json{") == {}

    def test_valid_json(self) -> None:
        assert parse_params('{"x": 1}') == {"x": 1}


class TestFindPairedClose:
    def test_skips_non_dict_tokens(self) -> None:
        # HtmlPaired is a non-dict token — it must be skipped without crashing.
        tokens = [
            HtmlPaired(tag="other", attrs={}, inner=[]),
            {"type": "block_html", "raw": "</aside>"},
        ]
        assert find_paired_close(tokens, 0, "aside", token_type="block_html") == 1

    def test_increments_depth_on_nested_open(self) -> None:
        tokens = [
            {"type": "block_html", "raw": '<aside adf="panel">'},
            {"type": "block_html", "raw": "</aside>"},
            {"type": "block_html", "raw": "</aside>"},
        ]
        # Depth: starts at 1, then sees nested open → 2, then close → 1,
        # then close → 0 (match).
        assert find_paired_close(tokens, 0, "aside", token_type="block_html") == 2

    def test_returns_none_when_no_close(self) -> None:
        tokens = [{"type": "block_html", "raw": '<aside adf="panel">'}]
        assert find_paired_close(tokens, 0, "aside", token_type="block_html") is None


class TestSplitHtmlString:
    def test_text_after_last_tag(self) -> None:
        # Trailing text after the last tag exercises the final pos < len branch.
        result = split_html_string("<li>a</li>trailing")
        assert result[-1] == {"type": "text", "raw": "trailing"}


class TestAdfTagLineRule:
    """The registered `adf_tag_line` block rule separates a blank-line-free
    container into discrete open/inner/close tokens at tokenize time, so the
    standard pairing logic can recover the inner content (issue #1)."""

    def test_jammed_container_tokenized_as_separate_tags(self) -> None:
        tokens = tokenize(
            '<details adf="expand">\n<summary>t</summary>\nbody\n</details>'
        )
        # Not a single merged block_html: open, summary, body, close.
        raws = [t.get("raw", "") for t in tokens if t.get("type") == "block_html"]
        assert any(r.strip() == '<details adf="expand">' for r in raws)
        assert any(r.strip() == "</details>" for r in raws)
        assert any(t.get("type") == "paragraph" for t in tokens)

    def test_self_contained_one_line_element_stays_opaque(self) -> None:
        # A void element with content + close on one line is NOT matched by
        # the rule, so it remains a single block_html (handled as void later).
        tokens = tokenize('<div adf="extension" params=\'{"extensionKey":"k"}\'></div>')
        block_htmls = [t for t in tokens if t.get("type") == "block_html"]
        assert len(block_htmls) == 1


class TestNormalizeBlocks:
    def test_already_normalized_passes_through(self) -> None:
        already = HtmlPaired(tag="x", attrs={}, inner=[])
        out = normalize_blocks([already])
        assert out == [already]

    def test_void_passes_through(self) -> None:
        already = HtmlVoid(tag="hr", attrs={})
        out = normalize_blocks([already])
        assert out == [already]

    def test_closing_block_html_dropped(self) -> None:
        # An orphan closing block_html token is simply skipped.
        out = normalize_blocks([{"type": "block_html", "raw": "</aside>"}])
        assert out == []

    def test_adfless_raw_block_html_dropped(self) -> None:
        out = normalize_blocks([{"type": "block_html", "raw": "<aside>"}])
        assert out == []

    def test_opening_with_adf_but_no_close_dropped(self) -> None:
        out = normalize_blocks([{"type": "block_html", "raw": '<aside adf="panel">'}])
        assert out == []


class TestNormalizeInlines:
    def test_closing_inline_html_dropped(self) -> None:
        out = normalize_inlines([{"type": "inline_html", "raw": "</span>"}])
        assert out == []

    def test_unmatched_open_inline_html_dropped(self) -> None:
        out = normalize_inlines(
            [{"type": "inline_html", "raw": '<span adf="underline">'}]
        )
        assert out == []
