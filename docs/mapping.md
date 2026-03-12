# ADF ↔ Markdown Mapping Reference

Marklas converts between ADF (Atlassian Document Format) and Markdown through a union AST. This document describes how each ADF node maps to Markdown.

Nodes are categorized as:

- **Shared** — native equivalents exist in both formats; no annotation needed.
- **Annotated** — ADF-only nodes wrapped in `<!-- adf:tag -->` HTML comments to survive roundtrip.
- **Placeholder** — raw ADF JSON preserved; editing the placeholder has no effect on roundtrip.

## Block Nodes

### Shared

| ADF Node | Markdown | Notes |
| --- | --- | --- |
| `paragraph` | Plain text line | Annotated only when `alignment` or `indentation` is set. Empty paragraph annotated as `<!-- adf:paragraph -->` (plain mode: empty line). |
| `heading` | `## Text` (`#` × level) | Annotated only when `alignment` or `indentation` is set |
| `codeBlock` | ` ```lang ` fenced block | `language` attr maps to info string |
| `blockquote` | `> quoted text` | Nested blocks rendered inside |
| `bulletList` | `- item` | `- [x]`/`- [ ]` when `ListItem.checked` is set |
| `orderedList` | `1. item` | `start` attr preserved |
| `rule` | `---` | AST: `ThematicBreak` |
| `table` | GFM table | Annotated when table-level or cell-level attrs exist (`layout`, `width`, `displayMode`, `isNumberColumnEnabled`, `colwidth`, `background`, `colspan`, `rowspan`, header cells) |

### Annotated (ADF-only)

These nodes have no native Markdown equivalent. They are wrapped in annotation comments with a readable fallback inside.

| ADF Node | Annotation Tag | Fallback Content | Attrs |
| --- | --- | --- | --- |
| `panel` | `panel` | Inner blocks as Markdown | `panelType`, `panelIcon`, `panelIconId`, `panelIconText`, `panelColor` |
| `expand` | `expand` | Inner blocks as Markdown | `title` |
| `nestedExpand` | `nestedExpand` | Inner blocks as Markdown | `title` |
| `taskList` | `taskList` | `- [x]` / `- [ ]` checklist | (none) |
| `decisionList` | `decisionList` | `- [x]` / `- [ ]` checklist | (none) |
| `layoutSection` | `layoutSection` | Nested `layoutColumn` annotations | (none) |
| `layoutColumn` | `layoutColumn` | Inner blocks as Markdown | `width` |
| `mediaSingle` | `mediaSingle` | `![alt](url)` or `` `📎 attachment` `` | `layout`, `width`, `widthType`, `media` |
| `mediaGroup` | `mediaGroup` | List of media fallbacks | `mediaList` |
| `blockCard` | `blockCard` | `[url](url)` or `` `🔗 card link` `` | `url`, `data` |
| `embedCard` | `embedCard` | `[url](url)` | `url`, `layout`, `width`, `originalWidth`, `originalHeight` |

### Placeholder-only (no editable content)

These preserve raw ADF JSON and render a short placeholder. Editing the placeholder has no effect on roundtrip.

| ADF Node | Annotation Tag | Fallback |
| --- | --- | --- |
| `extension` | `extension` | `` `⚙ {extensionKey}` `` or `` `⚙ Confluence macro` `` |
| `bodiedExtension` | `bodiedExtension` | `` `⚙ {extensionKey}` `` or `` `⚙ Confluence macro` `` |
| `syncBlock` | `syncBlock` | `` `⚙ {extensionKey}` `` or `` `⚙ Confluence macro` `` |
| `bodiedSyncBlock` | `bodiedSyncBlock` | `` `⚙ {extensionKey}` `` or `` `⚙ Confluence macro` `` |

### Annotation Format

Block annotations use newline separators:

```markdown
<!-- adf:panel {"panelType": "info"} -->
This is the **readable fallback** content.
<!-- /adf:panel -->
```

Block annotations without attrs:

```markdown
<!-- adf:taskList -->
- [x] done
- [ ] todo
<!-- /adf:taskList -->
```

Inline annotations use space separators:

```markdown
<!-- adf:mention {"id": "abc123", "text": "@John"} --> `@John` <!-- /adf:mention -->
```

When `annotate=False`, annotation wrappers are stripped and only fallback content remains.

## Inline Nodes

### Shared

| ADF Node | Markdown |
| --- | --- |
| `text` | Plain text |
| `strong` (bold mark) | `**text**` |
| `em` (italic mark) | `*text*` |
| `strike` (strikethrough mark) | `~~text~~` |
| `link` (link mark) | `[text](url)` |
| `image` | `![alt](url)` |
| `code` (code mark) | `` `code` `` |
| `hardBreak` | `\` + newline |
| `softBreak` | newline (no `\`) |

### Annotated (ADF-only)

| ADF Node | Annotation Tag | Fallback | Attrs |
| --- | --- | --- | --- |
| `mention` | `mention` | `` `@name` `` (or `` `@id` `` if no text) | `id`, `text`, `accessLevel`, `userType` |
| `emoji` | `emoji` | Emoji char or `:shortName:` | `shortName`, `text`, `id` |
| `date` | `date` | `` `YYYY-MM-DD` `` | `timestamp` |
| `status` | `status` | `` `STATUS_TEXT` `` | `text`, `color`, `style` |
| `inlineCard` | `inlineCard` | `[url](url)` or `` `🔗 card link` `` | `url`, `data` |
| `mediaInline` | `mediaInline` | `` `📎 attachment` `` | `id`, `collection`, `mediaType`, `alt`, `width`, `height` |
| `underline` (mark) | `underline` | Plain text (no decoration) | (none) |
| `textColor` (mark) | `textColor` | Plain text | `color` |
| `backgroundColor` (mark) | `backgroundColor` | Plain text | `color` |
| `subsup` (mark) | `subsup` | Plain text | `type` (`sub`/`sup`) |
| `annotation` (mark) | `annotation` | Plain text | `id`, `annotationType` |

### Placeholder-only (inline)

| ADF Node | Annotation Tag | Fallback |
| --- | --- | --- |
| `inlineExtension` | `inlineExtension` | `` `⚙ {extensionKey}` `` or `` `⚙ Confluence macro` `` |

### Dropped (inline)

| ADF Node | Behavior |
| --- | --- |
| `placeholder` | Rendered as empty string (silently dropped) |

## Table Cell Substitutions

GFM tables require each cell to be a single line. Block nodes inside table cells are converted to inline HTML:

| ADF Node (in cell) | HTML Representation | Example |
| --- | --- | --- |
| `paragraph` | Plain text (no tag) | `cell text` |
| `bulletList` | `<ul><li>…</li></ul>` | `<ul><li>item 1</li><li>item 2</li></ul>` |
| `orderedList` | `<ol><li>…</li></ol>` | `<ol><li>first</li><li>second</li></ol>` |
| `blockquote` | `<blockquote>…</blockquote>` | `<blockquote>quoted</blockquote>` |
| `heading` | `<h1>`–`<h6>` | `<h3>Title</h3>` |
| `codeBlock` | `<code>…</code>` | `<code>x = 1</code>` |
| `rule` | `<hr>` | `<hr>` |
| `taskList` | `<ul><li>[x] …</li></ul>` | `<ul><li>[x] done</li><li>[ ] todo</li></ul>` |
| `decisionList` | `<ul><li>[x] …</li></ul>` | `<ul><li>[x] decided</li></ul>` |

### Cell-specific conventions

| Element | Representation | Notes |
| --- | --- | --- |
| Hard break (within paragraph) | `<br/>` | Self-closing slash distinguishes from block separator |
| Block separator (between blocks) | `<br>` | No self-closing slash; joins multiple blocks in one cell |
| Pipe character | `\|` | Escaped to avoid breaking column structure |

### Cell-level ADF-only nodes

Nodes like `panel`, `expand`, `nestedExpand`, `mediaSingle`, etc. inside table cells use inline annotations wrapping HTML fallbacks (content wrapped in `<blockquote>`):

```markdown
<!-- adf:panel {"panelType": "info"} --><blockquote>content</blockquote><!-- /adf:panel -->
```
