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

Confluence and Jira store documents in [ADF](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/) — a verbose JSON structure. Marklas converts it to readable Markdown and back through a union AST:

```
Markdown ⇄ Union AST ⇄ ADF
```

ADF-only features (panels, mentions, colored text, etc.) are preserved as invisible HTML comment annotations, so the full structure survives a roundtrip:

```markdown
<!-- adf:panel {"panelType": "info"} -->
This is an info panel — readable as plain Markdown.
<!-- /adf:panel -->

User <!-- adf:mention {"id": "abc123", "text": "@John"} -->`@John`<!-- /adf:mention --> approved this.
```

Pass `annotate=False` to strip annotations and get clean Markdown.

## Installation

```bash
pip install marklas
```

## Usage

```python
from marklas import to_adf, to_md

# Markdown → ADF
adf = to_adf("## Hello\n\nThis is **bold**.")

# ADF → Markdown (with annotations for lossless roundtrip)
md = to_md(adf_document)

# ADF → Markdown (clean, no annotations)
clean_md = to_md(adf_document, annotate=False)

# Roundtrip
original_adf = fetch_confluence_page()
markdown = to_md(original_adf)          # edit in any Markdown editor
restored_adf = to_adf(markdown)         # push back — structure preserved
```

## Token Efficiency

Markdown is significantly more compact than ADF JSON — critical for LLM-based workflows where every token counts.

| | ADF JSON | Markdown (annotated) | Markdown (plain) |
| --- | --- | --- | --- |
| Tokens | 243,217 | 76,541 | 41,744 |
| **Reduction** | — | **3.2x** | **5.8x** |

*Measured on 7 real Confluence pages (pretty-printed JSON) using GPT-4o tokenizer (tiktoken).*

## Documentation

- [ADF ↔ Markdown Mapping Reference](docs/mapping.md) — how each ADF node maps to Markdown
- [LLM Editing Guide](docs/llm-guide.md) — rules for LLMs/MCP servers editing marklas output

> **Note**: Table cells use inline HTML (`<ul>`, `<code>`, `<br>`) for block-level content. Raw HTML and other Markdown-only constructs are dropped during ADF conversion. See the mapping reference for details.

## Development

```bash
uv sync --extra dev
uv run pytest -v
```
