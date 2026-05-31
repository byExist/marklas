"""Markdown → ADF AST parser.

Pipeline:

    md string
        │
        ▼  normalize.tokenize  (mistune → list[dict])
    raw token stream
        │
        ▼  normalize.normalize_blocks  (pair block_html → IR)
    Token stream (HtmlPaired | HtmlVoid | mistune dict)
        │
        ▼  block.dispatch_blocks  (yield ast.Node per token)
    ast.Node stream
        │
        ▼  ir.collect + ir.is_doc  (narrow to ast.DocContent)
    list[ast.DocContent]
        │
        ▼  ast.Doc(content=...)
    ast.Doc

Each stage is its own module:
- ir.py:        dataclasses, container schemas, predicates, helpers
- normalize.py: tokenization + HTML tag parsing + paired matching
- inline.py:    inline dispatch + per-node inline builders
- block.py:     block dispatch + per-node block builders + cell sub-system
"""

from __future__ import annotations

from marklas import ast

from .block import dispatch_blocks
from .ir import collect, is_doc
from .normalize import normalize_blocks, tokenize


def parse(md: str) -> ast.Doc:
    """Parse a Markdown string (with marklas HTML extensions) to an ADF AST Doc."""
    tokens = normalize_blocks(tokenize(md))
    return ast.Doc(content=collect(dispatch_blocks(tokens), is_doc))


__all__ = ["parse"]
