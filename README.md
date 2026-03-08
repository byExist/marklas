<h1 align="center">Marklas</h1>

<p align="center">
  <a href="https://github.com/byExist/marklas/actions/workflows/ci.yml"><img src="https://github.com/byExist/marklas/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/marklas/"><img src="https://img.shields.io/pypi/v/marklas" alt="PyPI"></a>
  <a href="https://pypi.org/project/marklas/"><img src="https://img.shields.io/pypi/pyversions/marklas" alt="Python"></a>
  <a href="https://github.com/byExist/marklas/blob/master/LICENSE"><img src="https://img.shields.io/pypi/l/marklas" alt="License"></a>
</p>

<p align="center">
  Bidirectional converter between <b>Markdown</b> and <b>Atlassian Document Format (ADF)</b>.
</p>

---

## Why Marklas?

Confluence and Jira store documents in [ADF](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/) — a rich JSON structure with panels, layouts, mentions, colored text, and more. Standard Markdown can only represent a subset of these features.

**Marklas defines a union AST that covers both specs**, then converts in both directions through it:

```
Markdown ⇄ Union AST ⇄ ADF
```

Nodes shared by both formats (paragraphs, headings, lists, tables, etc.) map directly. ADF-only nodes (panels, mentions, colored text, etc.) are embedded as invisible HTML comment annotations in the Markdown output, so the full structure survives a roundtrip:

```
ADF → Markdown (with annotations) → ADF   ✅ lossless
```

Without annotations, standard Markdown elements still convert to valid ADF — just without the ADF-specific extras:

```
Plain Markdown → ADF   ✅ works (standard elements only)
```

### How Annotations Work

When ADF contains features that Markdown can't express natively (e.g., panels, mentions, colored text), Marklas wraps a readable Markdown fallback in HTML comment annotations:

```markdown
<!-- adf:panel {"panelType": "info"} -->
This is an info panel — readable as plain Markdown.
<!-- /adf:panel -->

User <!-- adf:mention {"id": "abc123", "text": "@John"} -->`@John`<!-- /adf:mention --> approved this.
```

These annotations are invisible when rendered as Markdown (GitHub, editors, etc.), but Marklas can parse them back to reconstruct the original ADF structure exactly.

## Installation

```bash
pip install marklas
```

## Usage

```python
from marklas import to_adf, to_md
```

### Markdown → ADF

Any standard Markdown converts to valid ADF:

```python
adf = to_adf("""
## Project Update

The release is **on track**. Key changes:

- Refactored auth module
- Fixed 3 critical bugs

| Component | Status |
| --------- | ------ |
| Backend   | Done   |
| Frontend  | WIP    |
""")
```

### ADF → Markdown

ADF-only features (panels, mentions, colored text, etc.) are preserved as HTML comment annotations — invisible in rendered Markdown, but fully restorable:

```python
md = to_md(adf_with_panel)
```

```markdown
<!-- adf:panel {"panelType": "warning"} -->
Do **not** deploy on Fridays.
<!-- /adf:panel -->
```

To get clean Markdown without annotations, pass `annotate=False`. ADF-only attributes are stripped and only standard Markdown elements remain:

```python
clean_md = to_md(adf_with_panel, annotate=False)
```

```markdown
Do **not** deploy on Fridays.
```

### Roundtrip

```python
original_adf = fetch_confluence_page()     # complex ADF
markdown = to_md(original_adf)             # edit in any Markdown editor
restored_adf = to_adf(markdown)            # push back — structure preserved
```

## Token Efficiency

Markdown is significantly more compact than ADF JSON — critical for LLM-based workflows where every token counts.

| | ADF JSON | Markdown (annotated) | Markdown (plain) |
| --- | --- | --- | --- |
| Tokens | 243,217 | 104,006 | 41,906 |
| **Reduction** | — | **2.3x** | **5.8x** |

*Measured on 7 real Confluence pages (pretty-printed JSON) using GPT-4o tokenizer (tiktoken).*

## Notes

- **Table cells**: Non-paragraph content inside table cells (lists, code blocks, etc.) is converted to inline HTML (`<ul>`, `<code>`, `<br>`) to fit within GFM table syntax.
- **Markdown-only features**: Raw HTML blocks/inlines and other Markdown-specific constructs that have no ADF equivalent are silently dropped during conversion.

## Development

```bash
uv sync --extra dev
uv run pytest -v
```
