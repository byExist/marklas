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

## Advanced Usage

For pipelines that need to modify the AST between parsing and rendering, use `Transformer`:

```python
from marklas import Transformer, parse_md, render_adf
from marklas.ast import CodeBlock, Expand, Extension, Media, Node

t = Transformer()

# Replace: return a Node to substitute the original
@t.register(Media)
def _(node: Media) -> Media | None:
    if node.type == "external":
        uploaded = upload_attachment(page_id, node.url)
        return Media(type="file", id=uploaded.media_id, collection=uploaded.collection)
    return None

# Splice: return a list[Node] to expand one node into many
@t.register(CodeBlock)
def _(node: CodeBlock) -> list[Node] | None:
    if node.language == "mermaid":
        return [
            Expand(title="mermaid source", content=[node]),
            Extension(
                extension_key="mermaid-macro",
                extension_type="com.example.mermaid",
                parameters={"code": "".join(c.text for c in node.content)},
            ),
        ]
    return None

doc = parse_md(markdown)
new_doc = t(doc)
adf = render_adf(new_doc)
```

A handler returns one of three values:

| Return | Effect |
| --- | --- |
| `None` | Skip — pass to the next handler, or leave unchanged |
| `Node` | Replace the original node |
| `list[Node]` | Splice multiple nodes in place of the original |

Multiple handlers can be registered for the same type; they run in registration order and the first non-`None` result wins. The tree is traversed bottom-up, and nodes returned by a handler are not revisited.

| Function | Description |
| --- | --- |
| `parse_md(md)` | Markdown → AST |
| `parse_adf(adf)` | ADF JSON → AST |
| `render_md(doc)` | AST → Markdown |
| `render_adf(doc)` | AST → ADF JSON |
| `Transformer` | Registry of typed visitors for AST rewriting |

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
