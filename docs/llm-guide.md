---
description: "Editing rules for marklas Markdown output (ADF↔Markdown). Activate when working with marklas, Confluence/Jira Markdown, or documents containing HTML elements with adf= attributes."
user-invocable: false
---

# Marklas Markdown Editing Guide

Marklas converts Atlassian Document Format (ADF) to Markdown. The output uses standard Markdown wherever possible and falls back to HTML elements for ADF-specific features. This guide explains the format so you can confidently read and edit it.

For the complete rendering format of every ADF node, see the [mapping rules](https://github.com/byExist/marklas/blob/master/docs/mapping.md).

## How the Format Works

Standard Markdown elements (paragraphs, headings, bold, lists, code blocks, etc.) work exactly as you'd expect. Edit them normally.

ADF-only features are represented as HTML elements with an `adf` attribute that identifies the node type, and an optional `params` attribute that stores metadata as JSON:

```markdown
<aside adf="panel" params='{"panelType":"info"}'>

This is a panel. Edit this content freely.

</aside>
```

```markdown
Text with <span adf="mention" params='{"id":"abc123"}'>@John</span> inline.
```

The `adf` and `params` attributes are roundtrip metadata — they ensure the document converts back to ADF without loss. The content inside the element is what readers see.

### Block Elements

Block-level HTML elements use blank lines to separate the open/close tags from inner content:

```markdown
<details adf="expand">

<summary>Click to expand</summary>

Content inside the expand. Standard Markdown works here.

</details>
```

Common block elements:

| Element | Tag | Editable parts |
| --- | --- | --- |
| Panel | `<aside>` | Inner content |
| Expand | `<details>` | `<summary>` title + inner content |
| Layout | `<section>` > `<div>` columns | Content within each column |
| Decision list | `<ul>` > `<li>` items | Item text |

### Void/Metadata Elements

Some `<div>` elements are single-line and carry metadata only. They have no editable content:

```markdown
<div adf="table" params='{"header":"none","layout":"wide"}'></div>

<div adf="extension" params='{"extensionKey":"...","extensionType":"..."}'></div>
```

### Non-editable Content

Elements with `📎` (media attachments) or URL-only display text (smart links) are references to external resources. Their display content is a fallback — the actual data lives in `params`.

## Table Editing

### Cell content rules

GFM table cells cannot contain multi-line content, so block-level content uses inline HTML:

```markdown
| Plain text cell | <ul><li>List item A</li><li>List item B</li></ul> |
```

- Simple text cells need no wrapping tags.
- Multi-block cells wrap each block in HTML: `<p>`, `<ul>`, `<h3>`, `<code>`, `<blockquote>`, `<hr>`.
- Pipe characters in content must be escaped: `\|`.
- Hard breaks use `<br>`.

### Cell metadata

Cells with merge or background have a `<div adf="cell">` prefix. Preserve it when editing:

```markdown
| <div adf="cell" params='{"colspan":2}'></div>Merged heading |  | C |
```

The empty cell next to a merged cell is a filler — it maintains the grid structure.

### Table metadata

A `<div adf="table">` before a GFM table carries table-level settings. When `header` is `"none"` or `"column"`, the first GFM row is a filler (empty cells) — real data starts from the second row after the separator.

## Restrictions

- Preserve `adf` and `params` attributes as-is — they are roundtrip metadata.
- Use inline HTML (not Markdown block syntax) for block content inside table cells.
- Do not introduce raw HTML without `adf` attributes outside of table cells — it will be ignored during ADF conversion.
- Do not create new elements with `adf` attributes — only marklas should generate them.
