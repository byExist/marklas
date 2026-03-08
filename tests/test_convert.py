"""통합 테스트: to_adf / to_md 라운드트립"""

from __future__ import annotations

from typing import Any, cast

from marklas import to_adf, to_md


# ── 헬퍼 ──────────────────────────────────────────────────────────────


def _strip_local_ids(obj: Any) -> Any:
    """localId 필드를 재귀적으로 제거하여 구조적 동등성만 비교."""
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
    """to_md → to_adf 라운드트립 검증. localId 무시."""
    md = to_md(adf)
    restored = to_adf(md)
    assert _strip_local_ids(restored["content"]) == _strip_local_ids(adf["content"])


# ── 교집합 ─────────────────────────────────────────────────────────────


def test_intersection_unchanged():
    """교집합 노드만 있으면 annotation 없음"""
    md = "**Hello**"
    result = to_adf(md)
    assert result["content"][0]["content"][0]["marks"] == [{"type": "strong"}]


def test_intersection_adf_to_md():
    """교집합 노드만 있으면 주석 없는 깨끗한 Markdown"""
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


# ── 블록 라운드트립 ───────────────────────────────────────────────────


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


# ── 인라인 라운드트립 ─────────────────────────────────────────────────


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


# ── 인라인 marks (래핑) 라운드트립 ────────────────────────────────────


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


# ── Block marks 라운드트립 ────────────────────────────────────────────


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


# ── Table attrs 라운드트립 ────────────────────────────────────────────


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


# ── 중첩 라운드트립 ──────────────────────────────────────────────────


def test_roundtrip_panel_with_task_list():
    """Panel 내부에 TaskList가 중첩된 케이스"""
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
    """LayoutSection 내부에 Panel이 중첩된 케이스"""
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


# ── Placeholder (라운드트립 포기 확인) ────────────────────────────────


def test_extension_no_roundtrip():
    """Extension은 라운드트립 불가. MD에서 placeholder로 렌더링되고 복원되지 않음."""
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
    # Extension raw는 복원되지 않음 — paragraph로 fallback
    assert restored["content"][0]["type"] == "paragraph"


# ── Graceful degradation ─────────────────────────────────────────────


def test_broken_annotation_no_closing():
    """닫는 주석이 없으면 교집합 범위로 fallback"""
    md = '<!-- adf:panel {"panelType":"warning"} -->\ncontent\n<!-- BROKEN -->\n'
    result = to_adf(md)
    assert result["content"][0]["type"] == "paragraph"


def test_broken_annotation_invalid_json():
    """JSON 파싱 실패 시 마커 무시 — panel 노드가 생성되지 않음"""
    md = "<!-- adf:panel {INVALID} -->\ncontent\n<!-- /adf:panel -->\n"
    result = to_adf(md)
    types = [c["type"] for c in result["content"]]
    assert "panel" not in types


def test_roundtrip_expand_with_table():
    """Expand 내부 테이블 라운드트립."""
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
    """Strong 내부 underline mark 라운드트립."""
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
    """여는/닫는 태그가 다르면 fallback"""
    md = '<!-- adf:panel {"panelType":"info"} -->\ncontent\n<!-- /adf:expand -->\n'
    result = to_adf(md)
    assert result["content"][0]["type"] == "paragraph"


def test_table_column_headers_roundtrip():
    """body 행의 tableHeader 셀이 MD 라운드트립을 통해 보존된다."""
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
    """headerless table (모든 셀이 tableCell)이 MD 라운드트립을 통해 보존된다."""
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


# ── Table cell inline block 라운드트립 ────────────────────────────────


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
    """셀 내 | 문자가 라운드트립에서 보존되어야 한다."""
    adf = _table_with_cell_content(
        [{"type": "paragraph", "content": [{"type": "text", "text": "a | b"}]}]
    )
    assert_roundtrip(adf)


def test_empty_paragraph_roundtrip():
    """빈 Paragraph가 라운드트립에서 보존되어야 한다."""
    adf = {
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
    """셀 내 HardBreak이 라운드트립에서 보존되어야 한다."""
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


def test_list_with_inline_annotation_roundtrip():
    """리스트 아이템 내 inline annotation이 라운드트립에서 보존되어야 한다."""
    adf = {
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
