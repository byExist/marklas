"""Measure ADF / MD / MD-plain token totals over a sample corpus.

Reads ``*-adf.json`` files from a sample directory, renders each via
marklas, and reports the sum-based token counts and reduction ratios
that the README's "Token Efficiency" table is sourced from.

Usage:
    python scripts/measure_tokens.py [--samples sample/]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import tiktoken

from marklas import parse_adf, render_md


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Measure ADF / MD / MD-plain token totals over a sample corpus."
    )
    ap.add_argument(
        "--samples",
        type=Path,
        default=Path("sample"),
        help="Directory containing *-adf.json files (default: sample/)",
    )
    ap.add_argument(
        "--model",
        default="gpt-4o",
        help="Tokenizer model name passed to tiktoken (default: gpt-4o)",
    )
    args = ap.parse_args()

    enc = tiktoken.encoding_for_model(args.model)
    paths = sorted(args.samples.glob("*-adf.json"))
    if not paths:
        raise SystemExit(f"No *-adf.json files found in {args.samples}")

    adf_total = md_total = plain_total = 0
    for path in paths:
        src = json.loads(path.read_text())
        compact = json.dumps(src, ensure_ascii=False, separators=(",", ":"))
        adf_total += len(enc.encode(compact))
        doc = parse_adf(src)
        md_total += len(enc.encode(render_md(doc)))
        plain_total += len(enc.encode(render_md(doc, plain=True)))

    md_ratio = adf_total / md_total
    plain_ratio = adf_total / plain_total
    print(f"Measured on {len(paths)} pages (compact JSON, {args.model} tokenizer)")
    print()
    print(f"  ADF JSON:         {adf_total:>12,}")
    print(f"  Markdown:         {md_total:>12,}   ({md_ratio:.2f}x reduction)")
    print(f"  Markdown (plain): {plain_total:>12,}   ({plain_ratio:.2f}x reduction)")


if __name__ == "__main__":
    main()
