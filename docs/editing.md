---
description: "Rules for editing marklas-generated Markdown. Apply when working with Markdown that contains HTML elements with adf= attributes (output of marklas, the ADF↔Markdown converter)."
user-invocable: false
---

# Editing Marklas Output

Marklas converts Atlassian Document Format (ADF) to Markdown and back. The output is standard Markdown plus HTML elements that carry ADF-specific structure. This document defines the rules that govern edits to that output. Full format reference: [format](format.md).

## Identification

A document is marklas output if it contains HTML elements with an `adf="<type>"` attribute. Every such element follows the shape:

```
<tag adf="<type>" params='{...}'>content</tag>
```

- `tag` — a standard HTML tag chosen for visual fit.
- `adf` — the ADF node type. Required.
- `params` — additional fields as a JSON object. Optional.
- `content` — visible body. Edit target.

## Roundtrip Contract

The following MUST be preserved verbatim across edits:

- The `adf` attribute and its value on every fallback element.
- The `params` attribute, its JSON well-formedness, and any fields not being deliberately changed. `params` values use HTML-attribute escaping (`&amp;`, `&#39;`); preserve the escaped form.
- Standard HTML attributes that carry data: `href` on `<a adf="inlineCard">`, `datetime` on `<time adf="date">`, `start` on `<ol>`.
- Filler cells adjacent to merged cells in GFM tables (empty cells that maintain grid width).
- The empty `<p></p>` marker that represents an intentionally empty paragraph.
- The backtick wrapping inside `<span adf="status">` (visual chip).
- A void-form element (`<tag ...></tag>` with no content) MUST remain void.

## Editable Surfaces

The following MAY be edited freely:

- Body text inside a fallback element with non-void content.
- Standard Markdown constructs outside fallback elements (headings, paragraphs, lists, blockquotes, code blocks, links, emphasis).
- Blocks added or removed inside `<aside adf="panel">`, `<details adf="expand">`, `<div adf="layoutColumn">`, and other block-content fallbacks, provided the blank-line separation rules below are respected.
- The text label of a `<span adf="mention">` (the `@name`). The `id` in `params` is the identity — do not change it.
- Specific `params` fields when the change is intentional (e.g., `panelType` on a panel, `state` on a task item).

## Block-HTML Layout

Block-level fallback elements separate their open and close tags from inner content with blank lines:

```
<aside adf="panel" params='{"panelType":"info"}'>

content

</aside>
```

The blank lines are required for the parser to recognize the open/close tags as block tokens. Do not collapse them.

## Cell Context

GFM table cells cannot contain blank lines, so block content inside a cell is emitted as inline HTML:

```
| <p>Para 1</p><p>Para 2</p> | <ul><li>A</li><li>B</li></ul> |
```

Cell rules:

- Pipe characters in cell content MUST be escaped as `\|`.
- Line breaks inside a cell MUST use `<br>`, not a literal newline.
- Block content inside a cell MUST use inline HTML wrappers: `<p>`, `<ul>`, `<ol>`, `<li>`, `<h1>`–`<h6>`, `<code>`, `<blockquote>`, `<hr>`, `<aside>`, `<details>`.
- A cell-leading `<div adf="cell" params='{...}'></div>` carries `colspan`, `rowspan`, and `background`. Removing this `<div>` removes those attributes; keep it unless the merge is being undone.
- A `<div adf="table" params='{...}'></div>` immediately before a GFM table carries table-level settings. When `header` is `"none"` or `"column"`, the first GFM row is filler — body data starts after the separator row.

## Nested Tables

A table inside a table cell appears as `<div adf="extension" params='{"extensionKey":"nested-table",...}'>` whose `params.parameters.adf` carries the inner table as a JSON string. The paired form includes a visual inner rendering:

```
<div adf="extension" params='{"extensionKey":"nested-table","parameters":{"adf":"{...}"}}'>

<table>...</table>

</div>
```

The visual `<table>` is for display only and is ignored by the parser. To change the inner table, edit the JSON string in `params.parameters.adf`, not the visual block.

## Prohibitions

The following actions corrupt the document and MUST NOT be performed:

- Adding HTML elements with `adf=` from scratch. Only marklas produces them.
- Adding HTML elements without `adf=` outside table cells. The parser drops them.
- Renaming or removing the `adf` attribute on an existing fallback element.
- Producing malformed JSON in `params` (unbalanced braces, unescaped quotes).
- Inserting blank lines inside a GFM table cell.
- Inserting unescaped `|` inside a GFM table cell.
- Deleting a filler cell adjacent to a merged cell without adjusting `colspan` / `rowspan`.
- Removing the backticks around inner text of `<span adf="status">`.

## Plain Mode

A separate render path, `render_md(doc, plain=True)`, produces Markdown with all `adf=` and `params=` metadata stripped. Plain output does not roundtrip and is not the target of these rules. If a document has no `adf=` attributes, treat it as plain output and edit as ordinary Markdown — do not attempt to apply the rules above.
