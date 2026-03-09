# ADF ↔ Markdown Mapping Reference

Marklas converts between ADF (Atlassian Document Format) and Markdown through a union AST. This document describes how each ADF node maps to Markdown.

Nodes are categorized as:

- **Shared** — native equivalents exist in both formats; no annotation needed.
- **Annotated** — ADF-only nodes wrapped in `<!-- adf:tag -->` HTML comments to survive roundtrip.
- **Table cell** — block nodes inside table cells use inline HTML due to GFM single-line constraint.

## Block Nodes

### Shared

| ADF Node | Markdown | Notes |
| --- | --- | --- |
| `paragraph` | Plain text line | Annotated only when `alignment` or `indentation` is set |
| `heading` | `## Text` (`#` × level) | Annotated only when `alignment` or `indentation` is set |
| `codeBlock` | ` ```lang ` fenced block | `language` attr maps to info string |
| `blockQuote` | `> quoted text` | Nested blocks rendered inside |
| `bulletList` | `- item` | Supports nested blocks in items |
| `orderedList` | `1. item` | `start` attr preserved |
| `rule` | `---` | |
| `table` | GFM table | Annotated when table-level or cell-level attrs exist (layout, colwidth, background, header cells, colspan, rowspan) |

### Annotated (ADF-only)

These nodes have no native Markdown equivalent. They are wrapped in annotation comments with a readable fallback inside.

| ADF Node | Annotation Tag | Fallback Content | Key Attrs |
| --- | --- | --- | --- |
| `panel` | `panel` | Inner blocks as Markdown | `panelType`, `panelColor`, `panelIcon` |
| `expand` | `expand` | Inner blocks as Markdown | `title` |
| `nestedExpand` | `nestedExpand` | Inner blocks as Markdown | `title` |
| `taskList` | `taskList` | `- [x]` / `- [ ]` checklist | |
| `decisionList` | `decisionList` | `- [x]` / `- [ ]` checklist | |
| `layoutSection` | `layoutSection` | Nested `layoutColumn` annotations | |
| `layoutColumn` | `layoutColumn` | Inner blocks as Markdown | `width` |
| `mediaSingle` | `mediaSingle` | `![alt](url)` or `` `📎 name` `` | `layout`, `width`, `media` |
| `mediaGroup` | `mediaGroup` | List of media fallbacks | `mediaList` |
| `blockCard` | `blockCard` | `[url](url)` | `url`, `data` |
| `embedCard` | `embedCard` | `[url](url)` | `url`, `layout`, `width` |

#### Placeholder-only (no editable content)

These preserve raw ADF JSON and render a short placeholder. Editing the placeholder has no effect on roundtrip.

| ADF Node | Fallback |
| --- | --- |
| `extension` | `` `⚙ extensionKey` `` |
| `bodiedExtension` | `` `⚙ extensionKey` `` |

#### Annotation Format

Block annotations:

```markdown
<!-- adf:panel {"panelType": "info"} -->
This is the **readable fallback** content.
<!-- /adf:panel -->
```

Inline annotations:

```markdown
<!-- adf:mention {"id": "abc123", "text": "@John"} -->`@John`<!-- /adf:mention -->
```

When `annotate=False`, annotation wrappers are stripped and only fallback content remains.

## Inline Nodes

### Shared

| ADF Node | Markdown |
| --- | --- |
| `text` | Plain text |
| `strong` (bold) | `**text**` |
| `em` (italic) | `*text*` |
| `strike` | `~~text~~` |
| `link` | `[text](url)` |
| `image` | `![alt](url)` |
| `code` (inline) | `` `code` `` |
| `hardBreak` | `\` + newline |

### Annotated (ADF-only)

| ADF Node | Annotation Tag | Fallback | Key Attrs |
| --- | --- | --- | --- |
| `mention` | `mention` | `` `@name` `` | `id`, `text` |
| `emoji` | `emoji` | Emoji char or `:shortName:` | `shortName`, `text`, `id` |
| `date` | `date` | `` `2024-01-15` `` | `timestamp` |
| `status` | `status` | `` `STATUS_TEXT` `` | `text`, `color`, `style` |
| `inlineCard` | `inlineCard` | `[url](url)` | `url`, `data` |
| `mediaInline` | `mediaInline` | `` `📎 name` `` | `id`, `collection` |
| `underline` | `underline` | Plain text (no decoration) | |
| `textColor` | `textColor` | Plain text | `color` |
| `backgroundColor` | `backgroundColor` | Plain text | `color` |
| `subsup` | `subsup` | Plain text | `type` (`sub`/`sup`) |
| `annotation` | `annotation` | Plain text | `id`, `annotationType` |

## Table Cell Substitutions

GFM tables require each cell to be a single line. Block nodes inside table cells are converted to inline HTML:

| ADF Node (in cell) | HTML Representation | Example |
| --- | --- | --- |
| `paragraph` | Plain text (no tag) | `cell text` |
| `bulletList` | `<ul><li>…</li></ul>` | `<ul><li>item 1</li><li>item 2</li></ul>` |
| `orderedList` | `<ol><li>…</li></ol>` | `<ol><li>first</li><li>second</li></ol>` |
| `blockQuote` | `<blockquote>…</blockquote>` | `<blockquote>quoted</blockquote>` |
| `heading` | `<h1>`–`<h6>` | `<h3>Title</h3>` |
| `codeBlock` | `<code>…</code>` | `<code>x = 1</code>` |
| `rule` | `<hr>` | `<hr>` |

### Cell-specific conventions

| Element | Representation | Notes |
| --- | --- | --- |
| Hard break (within paragraph) | `<br/>` | Self-closing slash distinguishes from block separator |
| Block separator (between blocks) | `<br>` | No self-closing slash; joins multiple blocks in one cell |
| Pipe character | `\|` | Escaped to avoid breaking column structure |

### Cell-level ADF-only nodes

Nodes like `panel`, `expand`, `taskList`, `mediaSingle`, etc. inside table cells use inline annotations wrapping HTML fallbacks:

```markdown
<!-- adf:panel {"panelType": "info"} --><blockquote>content</blockquote><!-- /adf:panel -->
```
