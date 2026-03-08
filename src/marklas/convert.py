from __future__ import annotations

from typing import Any

from marklas.adf.parser import parse as _parse_adf
from marklas.adf.renderer import render as _render_adf
from marklas.md.parser import parse as _parse_md
from marklas.md.renderer import render as _render_md


def to_adf(markdown: str) -> dict[str, Any]:
    return _render_adf(_parse_md(markdown))


def to_md(adf: dict[str, Any], *, annotate: bool = True) -> str:
    return _render_md(_parse_adf(adf), annotate=annotate)
