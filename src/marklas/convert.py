from __future__ import annotations

from typing import Any

from marklas.adf.parser import parse as adf_parse
from marklas.adf.renderer import render as adf_render
from marklas.md.parser import parse as md_parse
from marklas.md.renderer import render as md_render


def to_adf(md: str) -> dict[str, Any]:
    """Markdown → ADF."""
    return adf_render(md_parse(md))


def to_md(adf: dict[str, Any], *, plain: bool = False) -> str:
    """ADF → Markdown."""
    return md_render(adf_parse(adf), plain=plain)
