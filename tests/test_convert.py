"""Tests for public API: to_adf, to_md."""

from __future__ import annotations

from marklas import to_adf, to_md


class TestToMd:
    def test_simple_paragraph(self):
        adf: dict[str, object] = {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "hello"}]}
            ],
        }
        md = to_md(adf)
        assert "hello" in md

    def test_heading(self):
        adf: dict[str, object] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "title"}],
                }
            ],
        }
        md = to_md(adf)
        assert "## title" in md


class TestToAdf:
    def test_simple_paragraph(self):
        md = "hello\n"
        adf = to_adf(md)
        assert adf["type"] == "doc"
        assert adf["content"][0]["type"] == "paragraph"
        assert adf["content"][0]["content"][0]["text"] == "hello"

    def test_heading(self):
        md = "## title\n"
        adf = to_adf(md)
        node = adf["content"][0]
        assert node["type"] == "heading"
        assert node["attrs"]["level"] == 2


class TestRoundtrip:
    def test_adf_to_md_to_adf(self):
        adf: dict[str, object] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "bold", "marks": [{"type": "strong"}]}
                    ],
                }
            ],
        }
        md = to_md(adf)
        restored = to_adf(md)
        assert restored["content"][0]["content"][0]["text"] == "bold"
        assert restored["content"][0]["content"][0]["marks"] == [{"type": "strong"}]


class TestPlain:
    def test_to_md_plain(self):
        adf: dict[str, object] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "mention", "attrs": {"id": "u1", "text": "@John"}},
                    ],
                }
            ],
        }
        md = to_md(adf, plain=True)
        assert "@John" in md
        assert "adf=" not in md
        assert "<span" not in md
