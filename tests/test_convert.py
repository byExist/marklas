from typing import Any

from marklas import to_adf, to_md


def test_to_adf():
    adf = to_adf("**Hello** world")
    assert adf == {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "Hello",
                        "marks": [{"type": "strong"}],
                    },
                    {"type": "text", "text": " world"},
                ],
            }
        ],
    }


def test_to_md():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "Hello",
                        "marks": [{"type": "strong"}],
                    },
                    {"type": "text", "text": " world"},
                ],
            }
        ],
    }
    assert to_md(adf) == "**Hello** world\n"


def test_roundtrip_md():
    md = "**Hello** world\n"
    assert to_md(to_adf(md)) == md


def test_roundtrip_adf():
    adf: dict[str, Any] = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "plain text"}],
            }
        ],
    }
    assert to_adf(to_md(adf)) == adf
