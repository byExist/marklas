"""ADF AST → Markdown renderer.

Top-level entry: ``render(doc, *, plain=False)`` from ``block``.

The package is split along the GFM-cell context divide:

- ``block`` — the standard Markdown emission path (dispatch, top-level
  block renderers, table, inline, marks, helpers).
- ``cell``  — cell-context block renderers (single-line HTML emission).
  ``block`` delegates to ``cell`` whenever ``_in_cell()`` is true.
"""

from .block import render

__all__ = ["render"]
