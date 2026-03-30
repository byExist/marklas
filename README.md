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

<p align="center">
  <a href="README.ko.md">한국어</a> · <a href="README.ja.md">日本語</a>
</p>

---

## Why Marklas?

Confluence and Jira store documents in [ADF](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/) — a verbose JSON structure. Marklas converts it to readable Markdown and back:

```
Markdown ⇄ ADF
```

ADF-only features (panels, mentions, colored text, etc.) are preserved as HTML elements with `adf` attributes, so the full structure survives a roundtrip:

```markdown
<aside adf="panel" params='{"panelType":"info"}'>

This is an info panel — readable as plain Markdown.

</aside>

User <span adf="mention" params='{"id":"abc123"}'>@John</span> approved this.
```

Pass `plain=True` to strip roundtrip metadata and get clean Markdown for LLM consumption.

## Installation

```bash
pip install marklas
```

## Usage

```python
from marklas import to_adf, to_md

# Markdown → ADF
adf = to_adf("## Hello\n\nThis is **bold**.")

# ADF → Markdown (with roundtrip metadata)
md = to_md(adf_document)

# ADF → Markdown (clean, no metadata)
plain_md = to_md(adf_document, plain=True)

# Roundtrip
original_adf = fetch_confluence_page()
markdown = to_md(original_adf)          # edit in any Markdown editor
restored_adf = to_adf(markdown)         # push back — structure preserved
```

## Token Efficiency

Markdown is significantly more compact than ADF JSON — critical for LLM-based workflows where every token counts.

| | ADF JSON | Markdown | Markdown (plain) |
| --- | --- | --- | --- |
| Tokens | 243,217 | 76,332 | 47,794 |
| **Reduction** | — | **3.2x** | **5.1x** |

*Measured on 7 real Confluence pages (pretty-printed JSON) using GPT-4o tokenizer (tiktoken).*

## Documentation

- [Mapping Reference](docs/mapping.md) — how each ADF node maps to Markdown
- [LLM Editing Guide](docs/llm-guide.md) — guide for LLMs editing marklas output

## Development

```bash
uv sync --extra dev
uv run pytest -v
```
