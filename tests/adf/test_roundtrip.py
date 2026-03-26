"""ADF roundtrip tests: ADF JSON → AST → ADF JSON.

Lossy fields (localId, etc.) are stripped before comparison.
"""

from __future__ import annotations

from typing import Any, cast

from marklas.adf.parser import parse
from marklas.adf.renderer import render


# ── Helpers ──────────────────────────────────────────────────────────────────


_LOSSY_KEYS = {"localId", "uniqueId", "occurrenceKey"}
_DEFAULT_ATTRS = {"colspan": 1, "rowspan": 1, "order": 1}


def _strip_lossy(obj: Any) -> Any:
    """Strip lossy fields and normalize for structural comparison."""
    if isinstance(obj, dict):
        src = cast(dict[str, Any], obj)
        d: dict[str, Any] = {}
        for k, v in src.items():
            if k in _LOSSY_KEYS:
                continue
            # Strip FragmentMark from table marks
            if k == "marks" and isinstance(v, list):
                marks_list = cast(list[dict[str, Any]], v)
                v = [m for m in marks_list if m.get("type") != "fragment"]
                if not v:
                    continue
            # Strip default attrs (colspan=1, rowspan=1, order=1)
            if k in _DEFAULT_ATTRS and v == _DEFAULT_ATTRS[k]:
                continue
            d[k] = _strip_lossy(v)
        # Strip hardBreak injected attrs
        if d.get("type") == "hardBreak":
            d.pop("attrs", None)
        # Strip empty attrs
        if "attrs" in d and d["attrs"] == {}:
            del d["attrs"]
        return d
    if isinstance(obj, list):
        return [_strip_lossy(i) for i in cast(list[Any], obj)]
    # Normalize emoji surrogate pairs
    if isinstance(obj, str) and "\\u" in obj:
        import re

        def _decode(m: re.Match[str]) -> str:
            high = int(m.group(1), 16)
            low = int(m.group(2), 16)
            return chr(0x10000 + (high - 0xD800) * 0x400 + (low - 0xDC00))

        return re.sub(
            r"\\u([Dd][89AaBb][0-9A-Fa-f]{2})\\u([Dd][CcDdEeFf][0-9A-Fa-f]{2})",
            _decode,
            obj,
        )
    return obj


def _rt(adf: dict[str, Any]) -> None:
    """Assert ADF roundtrip: parse → render == original (lossy fields stripped)."""
    result = render(parse(adf))
    assert _strip_lossy(result) == _strip_lossy(adf)


def _doc(*content: dict[str, Any]) -> dict[str, Any]:
    return {"type": "doc", "version": 1, "content": list(content)}


def _p(*content: dict[str, Any]) -> dict[str, Any]:
    return {"type": "paragraph", "content": list(content)}


def _text(t: str, **kwargs: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "text", "text": t}
    if kwargs:
        result.update(kwargs)
    return result


# ── Block nodes ──────────────────────────────────────────────────────────────


class TestBlocks:
    def test_paragraph(self):
        _rt(_doc(_p(_text("hello"))))

    def test_paragraph_empty(self):
        _rt(_doc({"type": "paragraph"}))

    def test_heading(self):
        _rt(
            _doc(
                {"type": "heading", "attrs": {"level": 3}, "content": [_text("title")]}
            )
        )

    def test_code_block(self):
        _rt(
            _doc(
                {
                    "type": "codeBlock",
                    "attrs": {"language": "python"},
                    "content": [_text("x = 1")],
                }
            )
        )

    def test_code_block_no_language(self):
        _rt(_doc({"type": "codeBlock", "content": [_text("code")]}))

    def test_blockquote(self):
        _rt(_doc({"type": "blockquote", "content": [_p(_text("q"))]}))

    def test_bullet_list(self):
        _rt(
            _doc(
                {
                    "type": "bulletList",
                    "content": [
                        {"type": "listItem", "content": [_p(_text("a"))]},
                    ],
                }
            )
        )

    def test_ordered_list(self):
        _rt(
            _doc(
                {
                    "type": "orderedList",
                    "attrs": {"order": 5},
                    "content": [
                        {"type": "listItem", "content": [_p(_text("1"))]},
                    ],
                }
            )
        )

    def test_rule(self):
        _rt(_doc({"type": "rule"}))

    def test_panel(self):
        _rt(
            _doc(
                {
                    "type": "panel",
                    "attrs": {"panelType": "info"},
                    "content": [_p(_text("note"))],
                }
            )
        )

    def test_panel_with_attrs(self):
        _rt(
            _doc(
                {
                    "type": "panel",
                    "attrs": {
                        "panelType": "custom",
                        "panelColor": "#eef",
                        "panelIcon": "🔔",
                    },
                    "content": [_p(_text("custom"))],
                }
            )
        )

    def test_expand(self):
        _rt(
            _doc(
                {
                    "type": "expand",
                    "attrs": {"title": "Title"},
                    "content": [_p(_text("body"))],
                }
            )
        )

    def test_nested_expand(self):
        _rt(
            _doc(
                {
                    "type": "expand",
                    "content": [
                        {
                            "type": "nestedExpand",
                            "attrs": {"title": "Inner"},
                            "content": [_p(_text("n"))],
                        },
                    ],
                }
            )
        )

    def test_layout_section(self):
        _rt(
            _doc(
                {
                    "type": "layoutSection",
                    "content": [
                        {
                            "type": "layoutColumn",
                            "attrs": {"width": 50.0},
                            "content": [_p(_text("L"))],
                        },
                        {
                            "type": "layoutColumn",
                            "attrs": {"width": 50.0},
                            "content": [_p(_text("R"))],
                        },
                    ],
                }
            )
        )


# ── Table ────────────────────────────────────────────────────────────────────


class TestTable:
    def test_simple(self):
        _rt(
            _doc(
                {
                    "type": "table",
                    "content": [
                        {
                            "type": "tableRow",
                            "content": [
                                {"type": "tableHeader", "content": [_p(_text("H"))]},
                            ],
                        },
                        {
                            "type": "tableRow",
                            "content": [
                                {"type": "tableCell", "content": [_p(_text("D"))]},
                            ],
                        },
                    ],
                }
            )
        )

    def test_with_attrs(self):
        _rt(
            _doc(
                {
                    "type": "table",
                    "attrs": {"layout": "wide", "isNumberColumnEnabled": False},
                    "content": [
                        {
                            "type": "tableRow",
                            "content": [
                                {
                                    "type": "tableCell",
                                    "attrs": {"colspan": 2, "background": "#eee"},
                                    "content": [_p(_text("x"))],
                                },
                            ],
                        }
                    ],
                }
            )
        )


# ── Media ────────────────────────────────────────────────────────────────────


class TestMedia:
    def test_media_single(self):
        _rt(
            _doc(
                {
                    "type": "mediaSingle",
                    "attrs": {"layout": "center"},
                    "content": [
                        {
                            "type": "media",
                            "attrs": {"type": "external", "url": "http://img.png"},
                        }
                    ],
                }
            )
        )

    def test_media_single_with_caption(self):
        _rt(
            _doc(
                {
                    "type": "mediaSingle",
                    "content": [
                        {
                            "type": "media",
                            "attrs": {"type": "file", "id": "f1", "collection": "c"},
                        },
                        {"type": "caption", "content": [_text("caption")]},
                    ],
                }
            )
        )

    def test_media_group(self):
        _rt(
            _doc(
                {
                    "type": "mediaGroup",
                    "content": [
                        {
                            "type": "media",
                            "attrs": {"type": "file", "id": "f1", "collection": "c"},
                        }
                    ],
                }
            )
        )


# ── Cards ────────────────────────────────────────────────────────────────────


class TestCards:
    def test_block_card(self):
        _rt(_doc({"type": "blockCard", "attrs": {"url": "http://card"}}))

    def test_embed_card(self):
        _rt(
            _doc(
                {
                    "type": "embedCard",
                    "attrs": {"url": "http://embed", "layout": "wide"},
                }
            )
        )

    def test_inline_card(self):
        _rt(_doc(_p({"type": "inlineCard", "attrs": {"url": "http://ic"}})))


# ── TaskList / DecisionList ──────────────────────────────────────────────────


class TestTaskDecision:
    def test_task_list(self):
        _rt(
            _doc(
                {
                    "type": "taskList",
                    "attrs": {"localId": "tl-1"},
                    "content": [
                        {
                            "type": "taskItem",
                            "attrs": {"localId": "ti-1", "state": "TODO"},
                            "content": [_text("task")],
                        },
                    ],
                }
            )
        )

    def test_decision_list(self):
        _rt(
            _doc(
                {
                    "type": "decisionList",
                    "attrs": {"localId": "dl-1"},
                    "content": [
                        {
                            "type": "decisionItem",
                            "attrs": {"localId": "di-1", "state": "DECIDED"},
                            "content": [_text("decide")],
                        },
                    ],
                }
            )
        )


# ── Extension / SyncBlock ────────────────────────────────────────────────────


class TestExtension:
    def test_extension(self):
        _rt(
            _doc(
                {
                    "type": "extension",
                    "attrs": {"extensionType": "com.test", "extensionKey": "key"},
                }
            )
        )

    def test_bodied_extension(self):
        _rt(
            _doc(
                {
                    "type": "bodiedExtension",
                    "attrs": {"extensionType": "com.test", "extensionKey": "key"},
                    "content": [_p(_text("body"))],
                }
            )
        )

    def test_sync_block(self):
        _rt(_doc({"type": "syncBlock", "attrs": {"resourceId": "r1"}}))

    def test_bodied_sync_block(self):
        _rt(
            _doc(
                {
                    "type": "bodiedSyncBlock",
                    "attrs": {"resourceId": "r1"},
                    "content": [_p(_text("sync"))],
                }
            )
        )


# ── Inline nodes ─────────────────────────────────────────────────────────────


class TestInlines:
    def test_hard_break(self):
        _rt(
            _doc(
                _p(
                    _text("a"),
                    {"type": "hardBreak", "attrs": {"text": "\n"}},
                    _text("b"),
                )
            )
        )

    def test_mention(self):
        _rt(_doc(_p({"type": "mention", "attrs": {"id": "u1", "text": "@Alice"}})))

    def test_emoji(self):
        _rt(_doc(_p({"type": "emoji", "attrs": {"shortName": ":smile:"}})))

    def test_date(self):
        _rt(_doc(_p({"type": "date", "attrs": {"timestamp": "1234567890"}})))

    def test_status(self):
        _rt(_doc(_p({"type": "status", "attrs": {"text": "Done", "color": "green"}})))

    def test_placeholder(self):
        _rt(_doc(_p({"type": "placeholder", "attrs": {"text": "Type here"}})))

    def test_media_inline(self):
        _rt(
            _doc(
                _p(
                    {
                        "type": "mediaInline",
                        "attrs": {"id": "m1", "collection": "c", "type": "file"},
                    }
                )
            )
        )

    def test_inline_extension(self):
        _rt(
            _doc(
                _p(
                    {
                        "type": "inlineExtension",
                        "attrs": {"extensionType": "com.test", "extensionKey": "key"},
                    }
                )
            )
        )


# ── Marks ────────────────────────────────────────────────────────────────────


class TestMarks:
    def test_strong(self):
        _rt(_doc(_p(_text("b", marks=[{"type": "strong"}]))))

    def test_em(self):
        _rt(_doc(_p(_text("i", marks=[{"type": "em"}]))))

    def test_strike(self):
        _rt(_doc(_p(_text("s", marks=[{"type": "strike"}]))))

    def test_code(self):
        _rt(_doc(_p(_text("c", marks=[{"type": "code"}]))))

    def test_underline(self):
        _rt(_doc(_p(_text("u", marks=[{"type": "underline"}]))))

    def test_link(self):
        _rt(
            _doc(
                _p(
                    _text(
                        "link", marks=[{"type": "link", "attrs": {"href": "http://x"}}]
                    )
                )
            )
        )

    def test_link_with_title(self):
        _rt(
            _doc(
                _p(
                    _text(
                        "link",
                        marks=[
                            {
                                "type": "link",
                                "attrs": {"href": "http://x", "title": "t"},
                            }
                        ],
                    )
                )
            )
        )

    def test_text_color(self):
        _rt(
            _doc(
                _p(
                    _text(
                        "red",
                        marks=[{"type": "textColor", "attrs": {"color": "#ff0000"}}],
                    )
                )
            )
        )

    def test_background_color(self):
        _rt(
            _doc(
                _p(
                    _text(
                        "bg",
                        marks=[
                            {"type": "backgroundColor", "attrs": {"color": "#00ff00"}}
                        ],
                    )
                )
            )
        )

    def test_subsup(self):
        _rt(_doc(_p(_text("2", marks=[{"type": "subsup", "attrs": {"type": "sub"}}]))))

    def test_annotation(self):
        _rt(
            _doc(
                _p(
                    _text(
                        "noted",
                        marks=[
                            {
                                "type": "annotation",
                                "attrs": {
                                    "id": "a1",
                                    "annotationType": "inlineComment",
                                },
                            },
                        ],
                    )
                )
            )
        )

    def test_multiple_marks(self):
        _rt(
            _doc(
                _p(
                    _text(
                        "bold link",
                        marks=[
                            {"type": "strong"},
                            {"type": "link", "attrs": {"href": "http://x"}},
                        ],
                    )
                )
            )
        )

    def test_alignment(self):
        _rt(
            _doc(
                {
                    "type": "paragraph",
                    "content": [_text("centered")],
                    "marks": [{"type": "alignment", "attrs": {"align": "center"}}],
                }
            )
        )

    def test_indentation(self):
        _rt(
            _doc(
                {
                    "type": "paragraph",
                    "content": [_text("indented")],
                    "marks": [{"type": "indentation", "attrs": {"level": 2}}],
                }
            )
        )

    def test_breakout(self):
        _rt(
            _doc(
                {
                    "type": "codeBlock",
                    "content": [_text("wide")],
                    "marks": [{"type": "breakout", "attrs": {"mode": "wide"}}],
                }
            )
        )


# ── Sample ADF files ─────────────────────────────────────────────────────────


class TestSampleFiles:
    """Roundtrip real ADF JSON from sample/ directory."""

    def _roundtrip_file(self, path: str) -> None:
        import json

        with open(path) as f:
            adf = json.load(f)
        result = render(parse(adf))
        assert _strip_lossy(result)["content"] == _strip_lossy(adf)["content"]

    def test_2pager_pc(self):
        self._roundtrip_file("sample/2pager-pc-adf.json")

    def test_page_4008641165(self):
        self._roundtrip_file("sample/page-4008641165-adf.json")

    def test_prd_4312924326(self):
        self._roundtrip_file("sample/prd-4312924326-adf.json")

    def test_prd_4790648886(self):
        self._roundtrip_file("sample/prd-4790648886-adf.json")

    def test_prd_mcms_ad(self):
        self._roundtrip_file("sample/prd-mcms-ad-adf.json")

    def test_prd_pc(self):
        self._roundtrip_file("sample/prd-pc-adf.json")

    def test_weekly_tech(self):
        self._roundtrip_file("sample/weekly-tech-20240607-adf.json")
