<h1 align="center">Marklas</h1>

<p align="center">
  <a href="https://github.com/byExist/marklas/actions/workflows/ci.yml"><img src="https://github.com/byExist/marklas/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/marklas/"><img src="https://img.shields.io/pypi/v/marklas" alt="PyPI"></a>
  <a href="https://pypi.org/project/marklas/"><img src="https://img.shields.io/pypi/pyversions/marklas" alt="Python"></a>
  <a href="https://github.com/byExist/marklas/blob/master/LICENSE"><img src="https://img.shields.io/pypi/l/marklas" alt="License"></a>
</p>

<p align="center">
  <b>Markdown</b> ⇄ <b>ADF</b>
</p>

## Installation

```bash
pip install marklas
```

## Usage

### Markdown → ADF

```python
from marklas import to_adf

adf = to_adf("**Hello** world")

# {
#   "type": "doc",
#   "version": 1,
#   "content": [
#     {
#       "type": "paragraph",
#       "content": [
#         {"type": "text", "text": "Hello", "marks": [{"type": "strong"}]},
#         {"type": "text", "text": " world"}
#       ]
#     }
#   ]
# }
```

### ADF → Markdown

```python
from marklas import to_md

md = to_md(adf)

# "**Hello** world\n"
```

## Conversion Rules

### Block

| ADF                                        | Markdown                                                   |
| ------------------------------------------ | ---------------------------------------------------------- |
| `paragraph`                                | inline content                                             |
| `heading` (level 1-6)                      | `# ~ ######`                                               |
| `codeBlock` (language?)                    | ` ```lang\ncode\n``` `                                     |
| `blockquote`                               | `> text`                                                   |
| `bulletList > listItem`                    | `- item`                                                   |
| `orderedList > listItem`                   | `1. item`                                                  |
| `taskList > taskItem`                      | `- [x]` / `- [ ]`                                          |
| `decisionList > decisionItem`              | `- [x]` / `- [ ]`                                          |
| `rule`                                     | `---`                                                      |
| `table > tableRow > tableHeader/tableCell` | GFM table (merged cells are split, block content flattened with `<br>`) |
| `mediaSingle > media` (external)           | `![alt](url)`                                              |
| `mediaSingle > media` (non-external)       | `[Image: id]`                                              |
| `mediaGroup > media`                       | `![alt](url)` / `[Image: id]`                              |
| `panel`                                    | `> text`                                                   |
| `expand` / `nestedExpand` (title?)         | `> title\n> text`                                          |
| `layoutSection > layoutColumn`             | columns flattened                                          |
| `blockCard` (url)                          | `[url](url)`                                               |
| `embedCard` (url)                          | `[url](url)`                                               |

### Inline

| ADF                    | Markdown            |
| ---------------------- | ------------------- |
| `text`                 | plain text          |
| `text` + `strong` mark | `**text**`          |
| `text` + `em` mark     | `*text*`            |
| `text` + `strike` mark | `~~text~~`          |
| `text` + `code` mark   | `` `code` ``        |
| `text` + `link` mark   | `[text](url)`       |
| `hardBreak`            | `\` + newline       |
| `mention`              | `` `@user` ``       |
| `emoji`                | `:shortName:`       |
| `date`                 | `` `2024-01-01` ``  |
| `status`               | `` `status text` `` |
| `inlineCard` (url)     | `[url](url)`        |

### Not Supported

| Element                                                                    | Behavior             |
| -------------------------------------------------------------------------- | -------------------- |
| ADF marks: `underline`, `textColor`, `backgroundColor`, `subsup`           | silently ignored     |
| ADF blocks: `extension`, `bodiedExtension`, `syncBlock`, `bodiedSyncBlock` | `[type]` placeholder |
| ADF inlines: `placeholder`, `inlineExtension`, `mediaInline`               | `[type]` placeholder |
| Markdown: raw HTML (block, inline)                                         | silently ignored     |

## Development

```bash
uv sync --extra dev
uv run pytest -v
uv run black src/ tests/
```
