---
description: "Rules for editing Markdown produced by marklas (ADF↔Markdown converter). Use when reading or modifying Confluence/Jira content converted to Markdown, or when the document contains <!-- adf:... --> annotation comments."
user-invocable: false
---

# Marklas Markdown Editing Guide

Marklas converts Atlassian Document Format (ADF) to Markdown. The output may contain HTML comment annotations (`<!-- adf:... -->`) that preserve ADF-specific features. These annotations are invisible when rendered but are required for lossless roundtrip back to ADF.

## Annotations

- **Do NOT delete, modify, or reorder** `<!-- adf:tag -->...<!-- /adf:tag -->` comment pairs.
- **Do NOT create new annotations.** Only marklas should generate them.
- **Edit only the fallback content** between the opening and closing comments.
- **JSON attributes** inside annotation comments (e.g., `{"panelType": "info"}`) must not be changed.

Block annotation example:

```markdown
<!-- adf:panel {"panelType": "info"} -->
Old content here. ← edit this part
<!-- /adf:panel -->
```

Inline annotation example (note the spaces around content):

```markdown
<!-- adf:mention {"id": "abc123", "text": "@John"} --> `@John` <!-- /adf:mention -->
```

## Table Cells

GFM tables require each cell to be a single line. Block-level content inside table cells uses inline HTML — NOT standard Markdown syntax.

| Block Type | Use This                        | NOT This       |
| ---------- | ------------------------------- | -------------- |
| List       | `<ul><li>item</li></ul>`        | `- item`       |
| Heading    | `<h3>Title</h3>`                | `### Title`    |
| Code       | `<code>x = 1</code>`            | ` ```code``` ` |
| Quote      | `<blockquote>text</blockquote>` | `> text`       |
| Rule       | `<hr>`                          | `---`          |

### Cell separators

- **`<br>`** (no slash) separates blocks within a cell.
- **`<br/>`** (self-closing) is a hard break within a paragraph.
- **Pipe characters** in cell content must be escaped as `\|`.

### Adding content to cells

To add a list item, insert `<li>new item</li>` inside the existing `<ul>` tag:

```markdown
| Items | <ul><li>First</li><li>Second</li><li>New item</li></ul> |
```

## Plain Text Editing

Standard Markdown elements (paragraphs, headings, bold, italic, links, images, code blocks, blockquotes, lists) follow normal Markdown rules.

**Do not introduce raw HTML outside of table cells.** It will be dropped on conversion to ADF.

## Non-editable Content

These placeholders reference Confluence macros or attachments. Editing them has no effect on roundtrip:

- `` `⚙ Confluence macro` `` or `` `⚙ {extensionKey}` `` — Confluence macro (extension, bodiedExtension, syncBlock, bodiedSyncBlock, inlineExtension)
- `` `📎 attachment` `` — file attachment (mediaSingle, mediaGroup, mediaInline)
- `` `🔗 card link` `` — smart link with data-only blockCard/inlineCard

## Summary of Restrictions

- Do not add Markdown block syntax (lists, headings, code fences) inside table cells.
- Do not remove or unbalance annotation comment pairs.
- Do not edit placeholder content.
- Do not add HTML comments that look like annotations (`<!-- adf:... -->`).
- Do not introduce raw HTML outside of table cells.
