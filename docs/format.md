# Marklas Format Reference

How each ADF node is rendered to Markdown, and how Markdown is parsed back to ADF. This is the implementation contract — if the renderer disagrees with this document, the renderer is right.

Editing rules for LLM agents working with marklas output: [editing](editing.md).

---

## Conventions

### HTML Fallback

Markdown can't express most ADF features (panels, mentions, statuses, etc.), so marklas renders them as HTML elements with two attributes:

- `adf="<type>"` — the ADF node type. Always present on a fallback element.
- `params='{...}'` — additional fields as a JSON object. Keys use ADF's camelCase. Values are HTML-attribute-escaped (`&` → `&amp;`, `'` → `&#39;`) and JSON-decoded on parse.

Standard HTML attributes (`href`, `datetime`, `start`) are used when they fit; only the leftover fields go into `params`. Elements with no extra fields omit `params` entirely.

### Three Rendering Contexts

| Context | Where | Behavior |
| --- | --- | --- |
| Block | Document, Blockquote content, ListItem, Panel, Expand, layout columns, etc. | Native Markdown or block-level HTML, separated by blank lines |
| Cell | Inside a GFM table cell (`\| ... \|`) | All blocks collapsed to inline HTML (no blank lines allowed) |
| Inline | Inside a Paragraph, Heading, TaskItem, Caption, etc. | Inline Markdown or inline HTML |

Block-level HTML elements are emitted as CommonMark type-6 tags with blank lines around the open/close tags, so the parser recognizes them as block tokens.

```
<tag adf="..." params='{...}'>

content

</tag>
```

Inside a cell the same element collapses to one line:

```
<tag adf="..." params='{...}'>content</tag>
```

### Tag Selection

- Block: `<aside>`, `<details>`, `<figure>`, `<figcaption>`, `<section>`, `<div>`, `<ul>`, `<ol>`, `<li>`.
- Inline: `<span>`, `<a>`, `<time>`, `<u>`, `<sub>`, `<sup>`.
- Semantic tag preferred when meaning fits (`<aside>` for Panel, `<details>` for Expand, `<time>` for Date). Otherwise `<div>` (block) / `<span>` (inline).

### Plain Mode

`render_md(doc, plain=True)` strips roundtrip-only metadata so the output reads as clean Markdown. The result does not roundtrip back to the original ADF.

- `adf` and `params` attributes removed everywhere.
- Void/metadata `<div>` elements (block marks, table metadata, cell metadata, Extension, BlockCard, EmbedCard, layout columns) dropped entirely.
- Empty `<p></p>` paragraph markers dropped (the marker is a roundtrip device).
- Listed tags are unwrapped (content preserved, tag removed):

| Tag | Applies to |
| --- | --- |
| `<span>` | Mention, Emoji, Status, TextColor, BgColor, Placeholder, MediaInline, InlineExtension, AnnotationMark |
| `<time>` | Date |
| `<div>` | MediaGroup, BlockCard, EmbedCard, LayoutColumn, void/metadata |
| `<section>` | LayoutSection |
| `<p>` | Paragraph (cell context) |

### Block Marks

Marks attached to block nodes are emitted as a void `<div>` placed immediately before the block. In cell context they are folded into the block element's `params`.

```
<div adf="marks" params='{"alignment":"center"}'></div>

content
```

| Mark | Valid on | params keys |
| --- | --- | --- |
| `AlignmentMark` | Paragraph, Heading | `"align": "center"` |
| `IndentationMark` | Paragraph, Heading | `"indent": 2` |
| `BreakoutMark` | CodeBlock, Expand, LayoutSection | `"breakoutMode": "wide"` |
| `DataConsumerMark` | various | `"dataConsumerSources": [...]` |
| `BorderMark` | Media, MediaInline | merged into media `params` |

### Inline Mark Order

When multiple marks apply to the same text run, they nest innermost-to-outermost:

1. `CodeMark` — `` `code` `` (inner text is not escaped further)
2. Native Markdown — `StrongMark`, `EmMark`, `StrikeMark`
3. `LinkMark` — `[text](url)`
4. HTML marks — `UnderlineMark`, `TextColorMark`, `BackgroundColorMark`, `SubSupMark`, `AnnotationMark`

Spaces adjacent to a Markdown delimiter (`**`, `*`, `~~`) violate CommonMark flanking. The renderer moves them outside: `** hello **` → ` **hello** `.

### Roundtrip Parsing

The parser restores AST from rendered Markdown:

- An HTML element with `adf=<type>` becomes the corresponding AST node. Extra fields come from `params` (HTML-unescaped, then JSON-parsed).
- A `<div adf="marks">` attaches block marks to the next block.
- A `<div adf="table">` attaches table metadata to the next GFM table.
- A `<div adf="cell">` attaches cell metadata to its cell.
- Native Markdown (headings, lists, blockquotes, …) parses directly to the corresponding AST node.

### Raw Markdown Parsing

When the input has no `adf=` attributes, the parser treats it as plain Markdown:

| Markdown | AST |
| --- | --- |
| Text | `Paragraph > Text` |
| `# ~ ######` | `Heading` |
| `` ```lang ``` `` | `CodeBlock` |
| `> ` | `Blockquote` |
| `- ` / `* ` | `BulletList > ListItem` |
| `N. ` | `OrderedList > ListItem` |
| `- [ ]` / `- [x]` | `TaskList > TaskItem` |
| `---` | `Rule` |
| `**text**` | `Text` + `StrongMark` |
| `*text*` | `Text` + `EmMark` |
| `~~text~~` | `Text` + `StrikeMark` |
| `` `code` `` | `Text` + `CodeMark` |
| `[t](u "title")` | `Text` + `LinkMark` |
| `![alt](url)` solo | `MediaSingle > Media(type="external")` |
| `![alt](url)` inline | unsupported (ADF has no inline external image) |
| `SoftBreak` | space |
| HTML without `adf=` | ignored (content too) |

---

## Block Nodes

### Paragraph

Block: plain text. Empty Paragraph → `<p></p>` (paired HTML; dropped in plain mode).
Cell: `<p>text</p>`. Empty Paragraph → `<p></p>`. A cell with a single Paragraph is unwrapped (bare text, no `<p>` tag).
Parsing: paired `<p></p>` or legacy `&nbsp;` / `\xa0` → empty Paragraph.

### Heading

Block: `# ~ ######` (level 1–6).
Cell: `<h1>` ~ `<h6>`.

### CodeBlock

Block: triple-backtick fence with optional language. Code containing `` ``` `` uses a longer fence.

```
```python
print("hi")
```
```

Cell: `<code>code</code>`. Newlines → `<br>`. Language → `params='{"language":"python"}'`.

### Blockquote

Block: `> ` prefix per line. Blank lines inside use bare `>`.
Cell: `<blockquote>content</blockquote>`.

### BulletList

Block: `- ` prefix. Nested lists indented.
Cell: `<ul><li>content</li></ul>`. Single-Paragraph items unwrap to bare text in `<li>`.

### OrderedList

Block: `N. ` prefix (sequential numbering from `order`, default 1).
Cell: `<ol start="N"><li>...</li></ol>`. `start` omitted when 1.
Parsing: `start=1` stored as `order=None` (symmetric with ADF parser).

### Rule

Block: `---`. Cell: `<hr>`.

### Table

GFM table with optional metadata blocks. See [Tables](#tables) below.

### Panel

```
<aside adf="panel" params='{"panelType":"info","panelIcon":"...","panelIconId":"...","panelIconText":"...","panelColor":"..."}'>

content

</aside>
```

Cell: `<aside ...>content</aside>` (single-line). Default `panelType="info"`.

### Expand / NestedExpand

```
<details adf="expand">

<summary>title</summary>

content

</details>
```

`NestedExpand` uses `adf="nestedExpand"`. Title extracted from `<summary>` (omitted when no title). Supports `BreakoutMark`.

### TaskList / TaskItem

Block (native MD):

```
- [ ] todo
- [x] done
```

`state`: `TODO` → `[ ]`, `DONE` → `[x]`. Nested TaskLists indent under the parent item.

Cell: `<ul adf="taskList"><li adf="taskItem" params='{"state":"TODO"}'>text</li></ul>`.

`BlockTaskItem` carries block content (Paragraph + Extension, etc.) and renders as a list item with indented continuation blocks.

Parsing: 2+ block children in a task item produce `BlockTaskItem`.

### DecisionList / DecisionItem

```
<ul adf="decisionList">

<li adf="decisionItem" params='{"state":"DECIDED"}'>text</li>

</ul>
```

### MediaSingle / MediaGroup / Media / Caption

```html
<figure adf="mediaSingle" params='{"layout":"...","width":...,"widthType":"...","linkHref":"...","linkTitle":"..."}'>

<span adf="media" params='{"type":"...","id":"...","collection":"...","alt":"...","width":...,"height":...}'>📎 fallback</span>
<figcaption adf="caption">caption text</figcaption>

</figure>
```

- Fallback text: `📎 {alt or "attachment"} ({id})`.
- `type="external"` → `url` in media params.
- `Caption` → `<figcaption adf="caption">`, omitted when absent.
- `Media.marks`: `LinkMark` → `<a>` wrapper around `<span>`. `AnnotationMark` → `<span adf="annotation">` wrapper. `BorderMark` → merged into media params.
- `MediaSingle.marks` (`LinkMark` only) → merged into figure params as `linkHref`/`linkTitle`.

`MediaGroup` uses `<div adf="mediaGroup">` containing one or more `<span adf="media">` children.

### BlockCard

```
<div adf="blockCard" params='{"url":"...","layout":"...","width":...,"data":{...},"datasource":{...}}'>

url

</div>
```

### EmbedCard

```
<div adf="embedCard" params='{"url":"...","layout":"...","width":...,"originalHeight":...,"originalWidth":...}'>

url

</div>
```

### LayoutSection / LayoutColumn

```html
<section adf="layoutSection">

<div adf="layoutColumn" params='{"width":50}'>

content

</div>

<div adf="layoutColumn" params='{"width":50}'>

content

</div>

</section>
```

`LayoutSection` supports `BreakoutMark`.

### Extension

```
<div adf="extension" params='{"extensionKey":"...","extensionType":"...","parameters":{...},"text":"...","layout":"..."}'></div>
```

Void element. Supports block marks.

`extensionKey="nested-table"` (Confluence's cell-nested-table wrapper) is rendered as a paired `<div adf="extension">…</div>` whose inner content is the inline-HTML rendering of `parameters.adf`. The inner is visual only — roundtrip rides on the `params` JSON, which carries the full inner ADF verbatim.

### BodiedExtension

```
<div adf="bodiedExtension" params='{"extensionKey":"...","extensionType":"...","content":[...],"parameters":{...},"text":"...","layout":"..."}'></div>
```

Void element. Inner content is serialized as ADF JSON inside `params.content`.

### SyncBlock / BodiedSyncBlock

```
<div adf="syncBlock" params='{"resourceId":"..."}'></div>
<div adf="bodiedSyncBlock" params='{"resourceId":"...","content":[...]}'></div>
```

Void elements. Support block marks.

---

## Inline Nodes

### Text

Plain text with Markdown escapes for `\ * _ [ ] ` ~`.

### HardBreak

Inline: trailing `\` + newline. Cell: `<br>`. Trailing HardBreak at the end of a Paragraph is dropped (visually identical to the paragraph terminator).

### Mention

`<span adf="mention" params='{"id":"...","accessLevel":"...","userType":"..."}'>@text</span>`

`text` includes the `@` prefix. Parser: `@`-prefix display whose tail equals `id` → stores `text=None`.

### Emoji

`<span adf="emoji" params='{"shortName":":name:","id":"..."}'>text</span>`

Display: `node.text or node.short_name`. Parser: display equal to `shortName` → `text=None`.

### Date

`<time adf="date" datetime="1705276800000">2024-01-15</time>`

`timestamp` (Unix millis string) goes in `datetime`. Display in `YYYY-MM-DD` for legibility; parser restores from `datetime`.

### Status

``<span adf="status" params='{"color":"...","style":"..."}'>`TEXT`</span>``

Inner text is wrapped in a backtick codespan so plain-Markdown viewers render it as a visually distinct chip. The parser unwraps the codespan transparently — the codespan exists only for visual emphasis.

### InlineCard

`<a adf="inlineCard" href="...">url</a>`

`url` in `href`; optional `data` dict in `params`.

### Placeholder

`<span adf="placeholder">text</span>`

### MediaInline

`<span adf="mediaInline" params='{"id":"...","collection":"...","type":"...","alt":"...","width":...,"height":...}'>📎 fallback</span>`

Fallback text and `marks` behavior identical to inline `Media`. `marks`: `LinkMark` → `<a>` wrapper, `AnnotationMark` → `<span adf="annotation">` wrapper, `BorderMark` → merged into params.

### InlineExtension

`<span adf="inlineExtension" params='{"extensionKey":"...","extensionType":"...","parameters":{...},"text":"..."}'></span>`

Void inline (no content).

---

## Marks

| Mark | Markdown form |
| --- | --- |
| `StrongMark` | `**text**` |
| `EmMark` | `*text*` |
| `StrikeMark` | `~~text~~` |
| `CodeMark` | `` `code` `` (longer fence if code contains backticks) |
| `LinkMark` | `[text](url "title")` (title optional) |
| `UnderlineMark` | `<u adf="underline">text</u>` |
| `TextColorMark` | `<span adf="textColor" params='{"color":"..."}'>text</span>` |
| `BackgroundColorMark` | `<span adf="bgColor" params='{"color":"..."}'>text</span>` |
| `SubSupMark` | `<sub adf="subSup">text</sub>` / `<sup adf="subSup">text</sup>` (tag from `type`) |
| `AnnotationMark` | `<span adf="annotation" params='{"id":"..."}'>text</span>` |

### CodeMark compatibility

The ADF schema allows only `code`, `link`, and `annotation` marks on a code-marked text node. When the AST has `CodeMark` combined with incompatible marks (e.g., `StrongMark` arising from `**bold `code`**`), the ADF renderer drops the incompatible marks; `LinkMark` and `AnnotationMark` are preserved. AST and Markdown rendering preserve every mark faithfully.

### AnnotationMark notes

`annotationType` is omitted from `params` since the ADF schema only defines `"inlineComment"`. The parser restores the default.

---

## Tables

### Table metadata

```
<div adf="table" params='{...}'></div>

| header | header |
| ------ | ------ |
| cell   | cell   |
```

The metadata block is omitted when no non-default attributes exist.

| params key | Notes |
| --- | --- |
| `header` | `"none"` / `"column"` / `"both"`. Omitted = `"row"` (GFM default) |
| `layout` | |
| `displayMode` | |
| `isNumberColumnEnabled` | |
| `width` | |
| `colwidths` | One entry per grid column (column-major). ADF stores it per cell; marklas consolidates because every cell in a column shares the same width |

### Header modes

| Mode | First GFM row |
| --- | --- |
| `"row"` (default) | content |
| `"none"` | empty filler cells |
| `"column"` | empty filler cells |
| `"both"` | content |

### Cell metadata

```
| <div adf="cell" params='{"colspan":2,"rowspan":2,"background":"#ff0"}'></div>Cell content | ... |
```

The metadata `<div>` is emitted only when at least one of `colspan>1`, `rowspan>1`, or `background` is set.

### Cell merge

Merged cells produce empty filler cells in adjacent positions to maintain the GFM grid. The parser drops these padding cells when reconstructing the AST.

### Examples

```markdown
<!-- Simple table — no metadata -->

| Name  | Role |
| ----- | ---- |
| Alice | Dev  |

<!-- No header + table layout -->

<div adf="table" params='{"header":"none","layout":"wide"}'></div>

|     |     |
| --- | --- |
| A   | B   |

<!-- Row+column header + colwidths -->

<div adf="table" params='{"header":"both","colwidths":[100,200,150]}'></div>

|       | Sub A | Sub B |
| ----- | ----- | ----- |
| Alice | 90    | 85    |

<!-- Merged cell + background -->

| <div adf="cell" params='{"colspan":2}'></div>Merged Header |  | C |
| --- | --- | --- |
| A | <div adf="cell" params='{"rowspan":2,"background":"#ff0"}'></div>Vertical | C |
| D |  | F |
```

---

## Lossy Items

These are editor-runtime metadata. They have no effect on document content, structure, or formatting, and are not preserved in roundtrip.

| Item | Description |
| --- | --- |
| `local_id` (all nodes) | Collaborative-editing node identifier (UUID) |
| `CodeBlock.unique_id` | Collaborative-editing code block identifier |
| `FragmentMark` | Table collaborative-editing fragment tracking |
| `HardBreak.text` | Always `"\n"` — no information |
| `LinkMark.id` | Atlassian internal link ID |
| `LinkMark.collection` | Media collection reference |
| `occurrence_key` (LinkMark, Media, MediaInline) | Duplicate media embed tracking |

## Markdown-only Items

Elements that exist in Markdown but have no ADF equivalent.

| Element | Reason |
| --- | --- |
| `SoftBreak` | Never generated from ADF |
| Generic `HtmlBlock` / `HtmlInline` | Marklas uses specific patterns; generic containers unnecessary |
| `BulletList.tight` / `OrderedList.tight` | Fixed format; no ADF counterpart |
| `ListItem.checked` | ADF uses `TaskItem.state` |
| `Table.alignments` | ADF tables have no column alignment |
