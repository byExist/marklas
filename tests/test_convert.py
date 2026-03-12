"""Integration tests: to_adf / to_md roundtrip"""

from __future__ import annotations

from typing import Any, cast

from marklas import to_adf, to_md


# ── Helpers ──────────────────────────────────────────────────────────────


def _strip_local_ids(obj: Any) -> Any:
    """Recursively strip localId fields for structural equality comparison."""
    if isinstance(obj, dict):
        return {
            k: _strip_local_ids(v)
            for k, v in cast(dict[str, Any], obj).items()
            if k != "localId"
        }
    if isinstance(obj, list):
        return [_strip_local_ids(item) for item in cast(list[Any], obj)]
    return obj


def assert_roundtrip(adf: dict[str, Any]) -> None:
    """Verify to_md → to_adf roundtrip. Ignores localId."""
    md = to_md(adf)
    restored = to_adf(md)
    assert _strip_local_ids(restored["content"]) == _strip_local_ids(adf["content"])


# ── Intersection ─────────────────────────────────────────────────────────────


def test_intersection_unchanged():
    """Intersection-only nodes produce no annotations"""
    md = "**Hello**"
    result = to_adf(md)
    assert result["content"][0]["content"][0]["marks"] == [{"type": "strong"}]


def test_intersection_adf_to_md():
    """Intersection-only nodes produce clean Markdown without annotations"""
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "hello", "marks": [{"type": "strong"}]}
                ],
            }
        ],
    }
    md = to_md(adf)
    assert "<!-- adf:" not in md
    assert md.strip() == "**hello**"


# ── Block roundtrip ───────────────────────────────────────────────────


def test_roundtrip_panel():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "panel",
                "attrs": {"panelType": "warning"},
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "경고"}],
                    }
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_expand():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "expand",
                "attrs": {"title": "Details"},
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "내용"}],
                    }
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_nested_expand():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "expand",
                "content": [
                    {
                        "type": "nestedExpand",
                        "attrs": {"title": "Inner"},
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "중첩"}],
                            }
                        ],
                    }
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_task_list():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "taskList",
                "attrs": {"localId": "tl-1"},
                "content": [
                    {
                        "type": "taskItem",
                        "attrs": {"localId": "t1", "state": "DONE"},
                        "content": [{"type": "text", "text": "완료"}],
                    },
                    {
                        "type": "taskItem",
                        "attrs": {"localId": "t2", "state": "TODO"},
                        "content": [{"type": "text", "text": "할일"}],
                    },
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_decision_list():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "decisionList",
                "attrs": {"localId": "dl-1"},
                "content": [
                    {
                        "type": "decisionItem",
                        "attrs": {"localId": "d1", "state": "DECIDED"},
                        "content": [{"type": "text", "text": "결정됨"}],
                    },
                    {
                        "type": "decisionItem",
                        "attrs": {"localId": "d2", "state": ""},
                        "content": [{"type": "text", "text": "미정"}],
                    },
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_layout_section():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "layoutSection",
                "content": [
                    {
                        "type": "layoutColumn",
                        "attrs": {"width": 50},
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "왼쪽"}],
                            }
                        ],
                    },
                    {
                        "type": "layoutColumn",
                        "attrs": {"width": 50},
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "오른쪽"}],
                            }
                        ],
                    },
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_media_single_external():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "mediaSingle",
                "attrs": {"layout": "center", "width": 80},
                "content": [
                    {
                        "type": "media",
                        "attrs": {
                            "type": "external",
                            "url": "https://example.com/img.png",
                            "alt": "예시",
                        },
                    }
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_media_group():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "mediaGroup",
                "content": [
                    {
                        "type": "media",
                        "attrs": {
                            "type": "external",
                            "url": "https://a.com/1.png",
                        },
                    },
                    {
                        "type": "media",
                        "attrs": {
                            "type": "external",
                            "url": "https://a.com/2.png",
                        },
                    },
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_block_card():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [{"type": "blockCard", "attrs": {"url": "https://example.com"}}],
    }
    assert_roundtrip(adf)


def test_roundtrip_embed_card():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "embedCard",
                "attrs": {
                    "url": "https://example.com",
                    "layout": "wide",
                    "width": 100,
                    "originalWidth": 800,
                    "originalHeight": 600,
                },
            }
        ],
    }
    assert_roundtrip(adf)


# ── Inline roundtrip ─────────────────────────────────────────────────


def test_roundtrip_mention():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "안녕 "},
                    {"type": "mention", "attrs": {"id": "user-123", "text": "@John"}},
                    {"type": "text", "text": " 님"},
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_emoji():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "emoji",
                        "attrs": {"shortName": ":smile:", "text": "\U0001f604"},
                    },
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_date():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "date", "attrs": {"timestamp": "1700000000000"}},
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_status():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "status",
                        "attrs": {"text": "진행중", "color": "blue"},
                    },
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_inline_card():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "inlineCard", "attrs": {"url": "https://example.com"}},
                ],
            }
        ],
    }
    assert_roundtrip(adf)


# ── Inline marks (wrapping) roundtrip ────────────────────────────────────


def test_roundtrip_underline():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "밑줄",
                        "marks": [{"type": "underline"}],
                    },
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_text_color():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "빨간색",
                        "marks": [
                            {
                                "type": "textColor",
                                "attrs": {"color": "#ff0000"},
                            }
                        ],
                    },
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_background_color():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "형광펜",
                        "marks": [
                            {
                                "type": "backgroundColor",
                                "attrs": {"color": "#ffff00"},
                            }
                        ],
                    },
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_subsup():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "H"},
                    {
                        "type": "text",
                        "text": "2",
                        "marks": [{"type": "subsup", "attrs": {"type": "sub"}}],
                    },
                    {"type": "text", "text": "O"},
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_annotation():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "코멘트 대상",
                        "marks": [
                            {
                                "type": "annotation",
                                "attrs": {
                                    "id": "ann-1",
                                    "annotationType": "inlineComment",
                                },
                            }
                        ],
                    },
                ],
            }
        ],
    }
    assert_roundtrip(adf)


# ── Block marks roundtrip ────────────────────────────────────────────


def test_roundtrip_paragraph_alignment():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "marks": [{"type": "alignment", "attrs": {"align": "center"}}],
                "content": [{"type": "text", "text": "가운데"}],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_heading_indentation():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 2},
                "marks": [{"type": "indentation", "attrs": {"level": 1}}],
                "content": [{"type": "text", "text": "들여쓰기 제목"}],
            }
        ],
    }
    assert_roundtrip(adf)


# ── Table attrs roundtrip ────────────────────────────────────────────


def test_roundtrip_table_attrs():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "table",
                "attrs": {"layout": "wide", "isNumberColumnEnabled": True},
                "content": [
                    {
                        "type": "tableRow",
                        "content": [
                            {
                                "type": "tableHeader",
                                "attrs": {"background": "#f0f0f0"},
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "A"}],
                                    }
                                ],
                            },
                            {
                                "type": "tableHeader",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "B"}],
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "type": "tableRow",
                        "content": [
                            {
                                "type": "tableCell",
                                "attrs": {"colspan": 2},
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "병합"}],
                                    }
                                ],
                            },
                        ],
                    },
                ],
            }
        ],
    }
    assert_roundtrip(adf)


# ── Nested roundtrip ──────────────────────────────────────────────────


def test_roundtrip_panel_with_task_list():
    """TaskList nested inside Panel"""
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "panel",
                "attrs": {"panelType": "info"},
                "content": [
                    {
                        "type": "taskList",
                        "attrs": {"localId": "tl-1"},
                        "content": [
                            {
                                "type": "taskItem",
                                "attrs": {"localId": "t1", "state": "DONE"},
                                "content": [{"type": "text", "text": "완료"}],
                            },
                        ],
                    }
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_layout_with_panel():
    """Panel nested inside LayoutSection"""
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "layoutSection",
                "content": [
                    {
                        "type": "layoutColumn",
                        "attrs": {"width": 50},
                        "content": [
                            {
                                "type": "panel",
                                "attrs": {"panelType": "note"},
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "메모"}],
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "type": "layoutColumn",
                        "attrs": {"width": 50},
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "텍스트"}],
                            }
                        ],
                    },
                ],
            }
        ],
    }
    assert_roundtrip(adf)


# ── Placeholder (verify no roundtrip) ────────────────────────────────


def test_extension_no_roundtrip():
    """Extension cannot roundtrip. Rendered as placeholder in MD and not restored."""
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "extension",
                "attrs": {
                    "extensionType": "com.atlassian.macro",
                    "extensionKey": "jira",
                },
            }
        ],
    }
    md = to_md(adf)
    assert "jira" in md
    restored = to_adf(md)
    # Extension raw is not restored — falls back to paragraph
    assert restored["content"][0]["type"] == "paragraph"


# ── Graceful degradation ─────────────────────────────────────────────


def test_broken_annotation_no_closing():
    """Falls back to intersection scope when closing annotation is missing"""
    md = '<!-- adf:panel {"panelType":"warning"} -->\ncontent\n<!-- BROKEN -->\n'
    result = to_adf(md)
    assert result["content"][0]["type"] == "paragraph"


def test_broken_annotation_invalid_json():
    """Marker ignored on JSON parse failure — no panel node created"""
    md = "<!-- adf:panel {INVALID} -->\ncontent\n<!-- /adf:panel -->\n"
    result = to_adf(md)
    types = [c["type"] for c in result["content"]]
    assert "panel" not in types


def test_roundtrip_expand_with_table():
    """Table inside Expand roundtrip."""
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "expand",
                "attrs": {"title": "Details"},
                "content": [
                    {
                        "type": "table",
                        "content": [
                            {
                                "type": "tableRow",
                                "content": [
                                    {
                                        "type": "tableHeader",
                                        "content": [
                                            {
                                                "type": "paragraph",
                                                "content": [
                                                    {"type": "text", "text": "A"}
                                                ],
                                            }
                                        ],
                                    },
                                ],
                            },
                            {
                                "type": "tableRow",
                                "content": [
                                    {
                                        "type": "tableCell",
                                        "content": [
                                            {
                                                "type": "paragraph",
                                                "content": [
                                                    {"type": "text", "text": "1"}
                                                ],
                                            }
                                        ],
                                    },
                                ],
                            },
                        ],
                    }
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_roundtrip_underline_inside_strong():
    """Underline mark inside Strong roundtrip."""
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "bold ", "marks": [{"type": "strong"}]},
                    {
                        "type": "text",
                        "text": "underlined",
                        "marks": [{"type": "strong"}, {"type": "underline"}],
                    },
                    {"type": "text", "text": " bold", "marks": [{"type": "strong"}]},
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_broken_annotation_mismatched_tags():
    """Falls back when open/close tags mismatch"""
    md = '<!-- adf:panel {"panelType":"info"} -->\ncontent\n<!-- /adf:expand -->\n'
    result = to_adf(md)
    assert result["content"][0]["type"] == "paragraph"


def test_table_column_headers_roundtrip():
    """tableHeader cells in body rows are preserved through MD roundtrip."""
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
                                "type": "tableHeader",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "Name"}],
                                    }
                                ],
                            },
                            {
                                "type": "tableHeader",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "Value"}],
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "type": "tableRow",
                        "content": [
                            {
                                "type": "tableHeader",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "A"}],
                                    }
                                ],
                            },
                            {
                                "type": "tableCell",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "1"}],
                                    }
                                ],
                            },
                        ],
                    },
                ],
            }
        ],
    }
    assert_roundtrip(adf)


# ── annotate=False (to_md) ─────────────────────────────────────────


def test_to_md_annotate_false_no_comments():
    """annotate=False strips annotation comments from difference-set nodes."""
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "panel",
                "attrs": {"panelType": "warning"},
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "경고"}],
                    }
                ],
            }
        ],
    }
    md = to_md(adf, annotate=False)
    assert "<!-- adf:" not in md
    assert "경고" in md


def test_to_md_annotate_false_inline():
    """annotate=False strips inline difference-set annotations."""
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "hello "},
                    {"type": "mention", "attrs": {"id": "user-1", "text": "@John"}},
                ],
            }
        ],
    }
    md = to_md(adf, annotate=False)
    assert "<!-- adf:" not in md
    assert "`@John`" in md


def test_to_md_annotate_false_mixed():
    """annotate=False strips all annotations from mixed block + inline difference-set."""
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "panel",
                "attrs": {"panelType": "info"},
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "see "},
                            {
                                "type": "emoji",
                                "attrs": {"shortName": ":smile:", "text": "\U0001f604"},
                            },
                        ],
                    }
                ],
            }
        ],
    }
    md = to_md(adf, annotate=False)
    assert "<!-- adf:" not in md
    assert "see" in md
    assert "\U0001f604" in md


def test_to_md_annotate_true_default():
    """annotate defaults to True, matching existing behavior."""
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "panel",
                "attrs": {"panelType": "info"},
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "note"}],
                    }
                ],
            }
        ],
    }
    assert to_md(adf) == to_md(adf, annotate=True)
    assert "<!-- adf:panel" in to_md(adf)


def test_headerless_table_roundtrip():
    """Headerless table (all cells are tableCell) is preserved through MD roundtrip."""
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
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "A1"}],
                                    }
                                ],
                            },
                            {
                                "type": "tableCell",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "B1"}],
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "type": "tableRow",
                        "content": [
                            {
                                "type": "tableCell",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "A2"}],
                                    }
                                ],
                            },
                            {
                                "type": "tableCell",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "B2"}],
                                    }
                                ],
                            },
                        ],
                    },
                ],
            }
        ],
    }
    assert_roundtrip(adf)


# ── Table cell inline block roundtrip ────────────────────────────────


def _table_with_cell_content(cell_content: list[dict[str, Any]]) -> dict[str, Any]:
    """Helper: 1x1 table with given cell content blocks."""
    return {
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
                                "type": "tableHeader",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "H"}],
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "type": "tableRow",
                        "content": [
                            {
                                "type": "tableCell",
                                "content": cell_content,
                            },
                        ],
                    },
                ],
            }
        ],
    }


def test_table_cell_code_block_roundtrip():
    adf = _table_with_cell_content(
        [
            {
                "type": "codeBlock",
                "attrs": {"language": "python"},
                "content": [{"type": "text", "text": "x = 1"}],
            },
        ]
    )
    assert_roundtrip(adf)


def test_table_cell_bullet_list_roundtrip():
    adf = _table_with_cell_content(
        [
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "a"}],
                            }
                        ],
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "b"}],
                            }
                        ],
                    },
                ],
            },
        ]
    )
    assert_roundtrip(adf)


def test_table_cell_ordered_list_roundtrip():
    adf = _table_with_cell_content(
        [
            {
                "type": "orderedList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "first"}],
                            }
                        ],
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "second"}],
                            }
                        ],
                    },
                ],
            },
        ]
    )
    assert_roundtrip(adf)


def test_table_cell_blockquote_roundtrip():
    adf = _table_with_cell_content(
        [
            {
                "type": "blockquote",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "quoted"}],
                    },
                ],
            },
        ]
    )
    assert_roundtrip(adf)


def test_table_cell_heading_roundtrip():
    adf = _table_with_cell_content(
        [
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "title"}],
            },
        ]
    )
    assert_roundtrip(adf)


def test_table_cell_thematic_break_roundtrip():
    adf = _table_with_cell_content(
        [
            {"type": "rule"},
        ]
    )
    assert_roundtrip(adf)


def test_table_cell_mixed_blocks_roundtrip():
    """Paragraph + CodeBlock in same cell."""
    adf = _table_with_cell_content(
        [
            {"type": "paragraph", "content": [{"type": "text", "text": "before"}]},
            {"type": "codeBlock", "content": [{"type": "text", "text": "code"}]},
            {"type": "paragraph", "content": [{"type": "text", "text": "after"}]},
        ]
    )
    assert_roundtrip(adf)


def test_table_cell_pipe_roundtrip():
    """Pipe character in cell should be preserved through roundtrip."""
    adf = _table_with_cell_content(
        [{"type": "paragraph", "content": [{"type": "text", "text": "a | b"}]}]
    )
    assert_roundtrip(adf)


def test_empty_paragraph_roundtrip():
    """Empty Paragraph should be preserved through roundtrip."""
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": "A"}],
            },
            {"type": "paragraph", "content": []},
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "B"}],
            },
        ],
    }
    assert_roundtrip(adf)


def test_table_cell_hardbreak_roundtrip():
    """HardBreak in cell should be preserved through roundtrip."""
    adf = _table_with_cell_content(
        [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "line1"},
                    {"type": "hardBreak"},
                    {"type": "text", "text": "line2"},
                ],
            }
        ]
    )
    assert_roundtrip(adf)


def test_md_table_header_becomes_tableHeader():
    """MD table header cells should become ADF tableHeader, not tableCell."""
    md = "| A | B |\n| --- | --- |\n| 1 | 2 |\n"
    adf = to_adf(md)
    table = adf["content"][0]
    header_row = table["content"][0]
    body_row = table["content"][1]
    for cell in header_row["content"]:
        assert cell["type"] == "tableHeader"
    for cell in body_row["content"]:
        assert cell["type"] == "tableCell"


def test_code_block_in_nested_list_roundtrip():
    """Code block inside nested list item should survive roundtrip."""
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "item"}],
                            },
                            {
                                "type": "bulletList",
                                "content": [
                                    {
                                        "type": "listItem",
                                        "content": [
                                            {
                                                "type": "codeBlock",
                                                "content": [
                                                    {
                                                        "type": "text",
                                                        "text": '{\n  "key": "value"\n}',
                                                    }
                                                ],
                                            }
                                        ],
                                    }
                                ],
                            },
                        ],
                    }
                ],
            }
        ],
    }
    assert_roundtrip(adf)


def test_list_with_inline_annotation_roundtrip():
    """List item inline annotation should survive roundtrip."""
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "status",
                                        "attrs": {
                                            "text": "Done",
                                            "color": "green",
                                            "style": "bold",
                                        },
                                    },
                                    {"type": "text", "text": " task"},
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }
    assert_roundtrip(adf)
