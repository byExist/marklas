<h1 align="center">Marklas</h1>

<p align="center">
  <a href="https://github.com/byExist/marklas/actions/workflows/ci.yml"><img src="https://github.com/byExist/marklas/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/marklas/"><img src="https://img.shields.io/pypi/v/marklas" alt="PyPI"></a>
  <a href="https://pypi.org/project/marklas/"><img src="https://img.shields.io/pypi/pyversions/marklas" alt="Python"></a>
  <a href="https://github.com/byExist/marklas/blob/master/LICENSE"><img src="https://img.shields.io/pypi/l/marklas" alt="License"></a>
</p>

<p align="center">
  <b>Markdown</b> ⇄ <b>AST</b> ⇄ <b>ADF</b>
</p>

## Installation

```bash
pip install marklas
```

## Usage

### Markdown → ADF

```python
from marklas.parser.md import parse
from marklas.renderer.adf import render

doc = parse("**Hello** world")
adf = render(doc)

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
from typing import Any

from marklas.parser.adf import parse
from marklas.renderer.md import render

adf: dict[str, Any] = {
    "type": "doc",
    "version": 1,
    "content": [
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Hello", "marks": [{"type": "strong"}]},
                {"type": "text", "text": " world"},
            ],
        }
    ],
}
doc = parse(adf)
md = render(doc)

# "**Hello** world\n"
```

## Conversion Rules

### Block

| ADF                                        | AST                                              | Markdown                      |
| ------------------------------------------ | ------------------------------------------------ | ----------------------------- |
| `paragraph`                                | `Paragraph(children)`                            | inline content                |
| `heading` (level 1-6)                      | `Heading(level, children)`                       | `# ~ ######`                  |
| `codeBlock` (language?)                    | `CodeBlock(code, language?)`                     | ` ```lang\ncode\n``` `        |
| `blockquote`                               | `BlockQuote(children)`                           | `> text`                      |
| `bulletList > listItem`                    | `BulletList(items) > ListItem(children)`         | `- item`                      |
| `orderedList > listItem`                   | `OrderedList(items, start) > ListItem(children)` | `1. item`                     |
| `taskList > taskItem`                      | `BulletList > ListItem(checked=bool)`            | `- [x]` / `- [ ]`             |
| `decisionList > decisionItem`              | `BulletList > ListItem(checked=bool)`            | `- [x]` / `- [ ]`             |
| `rule`                                     | `ThematicBreak`                                  | `---`                         |
| `table > tableRow > tableHeader/tableCell` | `Table(head, body, alignments)`                  | GFM table                     |
| `mediaSingle > media` (external)           | `Paragraph > Image(url, alt)`                    | `![alt](url)`                 |
| `mediaSingle > media` (non-external)       | `Paragraph > Text("[Image: id]")`                | `[Image: id]`                 |
| `mediaGroup > media`                       | `Paragraph > Image/Text`                         | `![alt](url)` / `[Image: id]` |
| `panel`                                    | `BlockQuote(children)`                           | `> text`                      |
| `expand` / `nestedExpand` (title?)         | `BlockQuote(children)` (title prepended)         | `> title\n> text`             |
| `layoutSection > layoutColumn`             | flattened blocks                                 | columns flattened             |
| `blockCard` (url)                          | `Paragraph > Link(url)`                          | `[url](url)`                  |
| `embedCard` (url)                          | `Paragraph > Link(url)`                          | `[url](url)`                  |

### Inline

| ADF                    | AST                           | Markdown            |
| ---------------------- | ----------------------------- | ------------------- |
| `text`                 | `Text(text)`                  | plain text          |
| `text` + `strong` mark | `Strong(children)`            | `**text**`          |
| `text` + `em` mark     | `Emphasis(children)`          | `*text*`            |
| `text` + `strike` mark | `Strikethrough(children)`     | `~~text~~`          |
| `text` + `code` mark   | `CodeSpan(code)`              | `` `code` ``        |
| `text` + `link` mark   | `Link(url, children, title?)` | `[text](url)`       |
| `hardBreak`            | `HardBreak`                   | `\` + newline       |
| —                      | `SoftBreak`                   | newline             |
| `mention`              | `CodeSpan(code)`              | `` `@user` ``       |
| `emoji`                | `Text(text)`                  | `:shortName:`       |
| `date`                 | `CodeSpan(code)`              | `` `2024-01-01` ``  |
| `status`               | `CodeSpan(code)`              | `` `status text` `` |
| `inlineCard` (url)     | `Link(url)`                   | `[url](url)`        |
| —                      | `Image(url, alt, title?)`     | `![alt](url)`       |

### Not Supported

| Element                                                                | Behavior             |
| ---------------------------------------------------------------------- | -------------------- |
| ADF marks: `underline`, `textColor`, `backgroundColor`, `subsup`       | silently ignored     |
| ADF blocks: `extension`, `bodiedExtension`, `syncBlock`, `bodiedSyncBlock` | `[type]` placeholder |
| ADF inlines: `placeholder`, `inlineExtension`, `mediaInline`           | `[type]` placeholder |
| ADF table: `colspan`, `rowspan`                                        | expanded with empty cells |
| ADF table: `background`, `colwidth`                                    | attributes ignored   |
| ADF table: non-paragraph cell content                                  | `[type]` placeholder |
| Markdown: raw HTML (block, inline)                                     | silently ignored     |

## Development

```bash
uv sync --extra dev
uv run pytest -v
uv run black src/ tests/
```
