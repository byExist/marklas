# ADF ↔ Markdown Mapping Rules

Bidirectional conversion between ADF (Atlassian Document Format) and Markdown.

- **MD → ADF**: Convert standard Markdown to ADF.
- **ADF → MD → ADF**: Render ADF as Markdown and parse it back to restore the original (roundtrip).

---

## Common

### Lossy Items

Editor runtime metadata. No effect on document content, structure, or formatting. Not preserved in roundtrip.

| Item | Description |
| --- | --- |
| `local_id` (all nodes) | Collaborative editing node identifier (UUID) |
| `CodeBlock.unique_id` | Collaborative editing code block identifier |
| `FragmentMark` | Table collaborative editing fragment tracking |
| `HardBreak.text` | Fixed value `"\n"` |
| `LinkMark.id` | Atlassian internal link ID |
| `LinkMark.collection` | Media collection reference |
| `occurrence_key` (LinkMark, Media, MediaInline) | Duplicate media embed tracking |

### MD-Only Elements (No ADF Equivalent)

| Element | Reason |
| --- | --- |
| `SoftBreak` | Never generated from ADF |
| `HtmlBlock` / `HtmlInline` | Our HTML fallback uses specific patterns. Generic containers unnecessary |
| `BulletList.tight` / `OrderedList.tight` | Renderer uses fixed format. No ADF counterpart |
| `ListItem.checked` | ADF uses `TaskItem.state` |
| `Table.alignments` | ADF tables have no column alignment |

---

## General Rules

### HTML Fallback Structure

ADF nodes without native Markdown representation are rendered as HTML elements.

- `adf="type"` — AST node type identifier. Present on all HTML fallback elements.
- `params='{...}'` — AST fields preserved as JSON. Keys use ADF's original camelCase. Values are HTML-attribute-escaped (`&` → `&amp;`, `'` → `&#39;`).
- Standard HTML attributes — serve both viewer rendering and field preservation (`datetime`, `start`, `href`).
- Content — element body (for display).
- Nodes with no parameters omit `params`. Nodes fully expressed by standard attributes also omit `params`.

### Block HTML Rendering

All HTML elements in block context use CommonMark type 6 block tags. Open and close tags are separated by blank lines (`\n\n`) so the parser recognizes them as separate tokens and matches pairs.

```
<tag adf="type" params='{...}'>

content

</tag>
```

Block tags used: `<aside>`, `<details>`, `<figure>`, `<div>`, `<section>`, `<ul>`, `<figcaption>`.

Void/metadata elements render as a single-line `<div adf="type" params='{...}'></div>`.

### HTML Tag Selection

Block tags must be CommonMark type 6 tags (auto-recognized as block HTML by CommonMark parsers).

Prefer semantic tags when the meaning fits (`<aside>` → Panel, `<details>` → Expand, `<time>` → Date). Use generic containers `<div>` (block) or `<span>` (inline) otherwise.

Inline tags: `<span>`, `<time>`, `<a>`, `<mark>`, `<u>`, `<sub>`, `<sup>`.

### Rendering Contexts

| Context | Location | Behavior |
| --- | --- | --- |
| Block | Document, Blockquote, ListItem, Panel, Expand, etc. | Native MD or block HTML. Blocks separated by `\n\n` |
| Cell | GFM table cell (between `\|`) | All blocks → inline HTML |
| Inline | Inside Paragraph, Heading, TaskItem, etc. | Native MD marks or inline HTML |

### Cell Common Rules

- All blocks render as inline HTML tags (no `\n\n` separation — tags themselves are boundaries).
- Inline rendering is identical to inline context, except `HardBreak` → `<br>` instead of `\`.
- Pipe characters in cell content are escaped: `|` → `\|`.

### Block Marks

Marks attached to block nodes. In block context, rendered as `<div adf="marks" params='{...}'></div>` before the block. In cell context, merged into the block element's `params`.

| Mark | Attached to | params keys |
| --- | --- | --- |
| `AlignmentMark` | Paragraph, Heading | `"align": "center"` |
| `IndentationMark` | Paragraph, Heading | `"indent": 2` |
| `BreakoutMark` | CodeBlock, Expand, LayoutSection | `"breakoutMode": "wide"` |
| `DataConsumerMark` | Various | `"dataConsumerSources": [...]` |
| `BorderMark` | Media, MediaInline | `"borderSize": 1, "borderColor": "#c0"` |

### Inline Marks Common Rules

> Spaces adjacent to delimiters (`**`, `*`, `~~`) violate CommonMark flanking rules.
> Leading/trailing spaces in mark content are moved outside the delimiter: `** hello **` → ` **hello** `.

Mark application order (innermost → outermost):
1. `CodeMark` — `code` (no MD escape) or escaped text
2. Native MD marks — `StrongMark`, `EmMark`, `StrikeMark`
3. `LinkMark` — `[text](url)`
4. HTML marks — `UnderlineMark`, `TextColorMark`, `BackgroundColorMark`, `SubSupMark`, `AnnotationMark`

### Plain Mode

`render(doc, plain=True)` — strips roundtrip metadata that is meaningless in plain Markdown.

- `adf` and `params` attributes removed.
- Void/metadata `<div>` elements (marks, table, cell) omitted.
- Tag stripping (content only, all other tags preserved):

| Tag | AST elements |
| --- | --- |
| `<span>` | Mention, Emoji, Status, TextColor, BgColor, Placeholder, MediaInline, InlineExtension |
| `<time>` | Date |
| `<div>` | MediaGroup, BlockCard, EmbedCard, LayoutColumn, void/metadata |
| `<section>` | LayoutSection |
| `<mark>` | AnnotationMark (comment metadata) |

### Roundtrip Parsing

Restore the original AST from renderer-generated Markdown.

- HTML elements with `adf` attribute → restore corresponding AST node. Extract fields from `params` JSON.
- `<div adf="marks">` → attach block marks to the next block.
- `<div adf="table">` → attach metadata to the next GFM table.
- `<div adf="cell">` → attach metadata to the cell.
- `params` values are HTML-unescaped (`&amp;` → `&`, `&#39;` → `'`) then JSON-parsed.
- Native MD elements convert directly to corresponding AST nodes.

### Raw MD Parsing

Convert user-written standard Markdown (without `adf` attributes) to ADF AST.

| MD element | AST node |
| --- | --- |
| Text | `Paragraph > Text` |
| `# ~ ######` | `Heading` |
| `` ``` `` | `CodeBlock` |
| `> ` | `Blockquote` |
| `- ` / `* ` | `BulletList > ListItem` |
| `N. ` | `OrderedList > ListItem` |
| `---` / `***` | `Rule` |
| `- [ ]` / `- [x]` | `TaskList > TaskItem` |
| GFM table | `Table` (first row = `TableHeader`, rest = `TableCell`) |
| `**text**` | `Text` + `StrongMark` |
| `*text*` | `Text` + `EmMark` |
| `~~text~~` | `Text` + `StrikeMark` |
| `` `code` `` | `Text` + `CodeMark` |
| `[text](url "title")` | `Text` + `LinkMark` |
| `![alt](url)` (solo paragraph) | `MediaSingle > Media(type="external", url, alt)` |
| `![alt](url)` (inline) | Unsupported (ADF has no inline external image) |
| `SoftBreak` | Treated as space |
| `adf`-less HTML element | Ignored (including content) |

---

## Block Nodes

### Paragraph

**Block**: Plain text. Empty Paragraph renders as `&nbsp;`.

**Cell**: `<p>text</p>`. Empty Paragraph → `<p></p>`. Single-Paragraph cell renders as bare text (no `<p>` tag).

**Parsing**: `&nbsp;` / `\xa0` → empty `Paragraph(content=[])`.

### Heading

**Block**: `# ~ ######` (level 1–6).

**Cell**: `<h1> ~ <h6>`.

### CodeBlock

**Block**: `` ```lang\ncode\n``` ``. If code contains `` ``` ``, use a longer fence.

**Cell**: `<code>code</code>`. Newlines in code → `<br>`. Language → `params='{"language":"python"}'`.

### Blockquote

**Block**: `> ` prefix per line. Blank lines within use bare `>`.

**Cell**: `<blockquote>content</blockquote>`.

### BulletList

**Block**: `- ` prefix. Nested lists indented.

**Cell**: `<ul><li>content</li></ul>`. Single-Paragraph items → bare text in `<li>`.

### OrderedList

**Block**: `N. ` prefix (sequential numbering from `order`).

**Cell**: `<ol start="N"><li>content</li></ol>`. `start` omitted when 1.

**Parsing**: `start` = 1 → stored as `order=None`.

### Rule

**Block**: `---`.

**Cell**: `<hr>`.

### Table

GFM table with metadata elements.

**Table metadata**: `<div adf="table" params='{...}'></div>` before the GFM table. Rendered only when non-default attributes exist.

| params key | Notes |
| --- | --- |
| `header` | `"none"` / `"column"` / `"both"`. Omitted = `"row"` (GFM default) |
| `layout` | |
| `displayMode` | |
| `isNumberColumnEnabled` | |
| `width` | |
| `colwidths` | Column width array extracted from first row's cells |

**Header modes**:

| Mode | Meaning | GFM first row |
| --- | --- | --- |
| `"row"` (default) | First row is header | Content present |
| `"none"` | No header | Empty filler cells |
| `"column"` | First column is header | Empty filler cells |
| `"both"` | First row + first column | Content present |

**Cell metadata**: `<div adf="cell" params='{...}'></div>` before cell content. Rendered only for cells with `colspan > 1`, `rowspan > 1`, or `background`.

**colspan / rowspan**: Merged cells produce empty filler cells to maintain the GFM grid. Parser infers filler positions from `colspan`/`rowspan` values.

**Example**:

```markdown
<!-- Simple table: no metadata -->

| Name | Role |
| --- | --- |
| Alice | Dev |

<!-- No header + table attrs -->

<div adf="table" params='{"header":"none","layout":"wide"}'></div>

|     |     |
| --- | --- |
| A   | B   |

<!-- Row+column header + colwidths -->

<div adf="table" params='{"header":"both","colwidths":[100,200,150]}'></div>

|       | Sub A | Sub B |
| ----- | ----- | ----- |
| Alice | 90    | 85    |

<!-- Cell merge -->

| <div adf="cell" params='{"colspan":2}'></div>Merged Header |  | C |
| --- | --- | --- |
| A | <div adf="cell" params='{"rowspan":2,"background":"#ff0"}'></div>Vertical | C |
| D |  | F |
```

### Panel

```
<aside adf="panel" params='{"panelType":"info","panelIcon":"...","panelIconId":"...","panelIconText":"...","panelColor":"..."}'>

content

</aside>
```

**Cell**: `<aside ...>content</aside>` (inline, no `\n\n`). Blocks joined without separator.

**Parsing**: `panelType` defaults to `"info"`.

### Expand

```
<details adf="expand">

<summary>title</summary>

content

</details>
```

- `title` → extracted from `<summary>`, not stored in params. No title → `<summary>` omitted.
- Supports `BreakoutMark`.

### NestedExpand

Same format as Expand. Distinguished by `adf="nestedExpand"`.

```
<details adf="nestedExpand">

<summary>title</summary>

content

</details>
```

### TaskList / TaskItem

**Block (native MD)**:

```markdown
- [ ] todo text
- [x] done text
```

`state`: `TODO` → `[ ]`, `DONE` → `[x]`.

**Cell**: `<ul adf="taskList"><li adf="taskItem" params='{"state":"TODO"}'>text</li></ul>`.

**BlockTaskItem**: TaskItem variant containing block content (Paragraph, Extension). Rendered as a list item with nested blocks (indented continuation).

**Nested TaskList**: Indented under parent item.

**Parsing (raw MD)**: `- [ ]` / `- [x]` → `TaskList > TaskItem`. 2+ block children in a task item → `BlockTaskItem`.

### DecisionList / DecisionItem

```
<ul adf="decisionList">

<li adf="decisionItem" params='{"state":"DECIDED"}'>text</li>

</ul>
```

### MediaSingle

```html
<figure adf="mediaSingle" params='{"layout":"...","width":...,"widthType":"...","linkHref":"...","linkTitle":"..."}'>

<span adf="media" params='{"type":"...","id":"...","collection":"...","alt":"...","width":...,"height":...}'>📎 fallback</span>
<figcaption adf="caption">caption text</figcaption>

</figure>
```

- Fallback text: `📎 {alt or "attachment"} ({id})`.
- `type="external"` → `url` included in media params.
- `Caption` → `<figcaption adf="caption">`. Omitted when absent.
- `Media.marks`: LinkMark → `<a>` wrapping the `<span>`. AnnotationMark → `<mark>` wrapping. BorderMark → merged into media params.
- `MediaSingle.marks` (LinkMark only) → merged into figure params as `linkHref`, `linkTitle`.

### MediaGroup

```html
<div adf="mediaGroup">

<span adf="media" params='{...}'>📎 fallback</span>

</div>
```

Media params same as MediaSingle.

### BlockCard

```
<div adf="blockCard" params='{"url":"...","layout":"...","width":...,"data":{...},"datasource":{...}}'>

url

</div>
```

- `url` → in params.
- `data`/`datasource` included in params when present.

### EmbedCard

```
<div adf="embedCard" params='{"url":"...","layout":"...","width":...,"originalHeight":...,"originalWidth":...}'>

url

</div>
```

- `url` → in params.

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

- Supports `BreakoutMark` on LayoutSection.

### Extension

Void element (no content). All fields stored in params.

`<div adf="extension" params='{"extensionKey":"...","extensionType":"...","parameters":{...},"text":"...","layout":"..."}'></div>`

- Supports block marks (AlignmentMark, etc.).

### BodiedExtension

Void element. Content serialized as ADF JSON array in params.

`<div adf="bodiedExtension" params='{"extensionKey":"...","extensionType":"...","content":[...],"parameters":{...},"text":"...","layout":"..."}'></div>`

### SyncBlock

Void element.

`<div adf="syncBlock" params='{"resourceId":"..."}'></div>`

- Supports block marks.

### BodiedSyncBlock

Void element. Content serialized as ADF JSON array in params.

`<div adf="bodiedSyncBlock" params='{"resourceId":"...","content":[...]}'></div>`

---

## Inline Nodes

### Text

Plain text. Markdown special characters escaped: `\`, `*`, `_`, `[`, `]`, `` ` ``, `~`.

### HardBreak

**Inline**: `\` + newline.

**Cell**: `<br>`.

**Note**: Trailing HardBreak (end of paragraph) is preserved.

### Mention

`<span adf="mention" params='{"id":"...","accessLevel":"...","userType":"..."}'>@text</span>`

- Display: `node.text or f"@{node.id}"`. ADF `text` field already includes `@`.
- **Parsing**: `@` prefix stripped from display text → `text` field stores name without `@`. If display equals `@{id}`, `text` is `None`.

### Emoji

`<span adf="emoji" params='{"shortName":":name:","id":"..."}'>text</span>`

- Display: `node.text or node.short_name`.
- **Parsing**: If display equals `shortName`, `text` is `None`.

### Date

`<time adf="date" datetime="1705276800000">2024-01-15</time>`

- `timestamp` → `datetime` standard attribute (Unix millis string, as-is).
- Display: `YYYY-MM-DD` format (for display only; parser restores from `datetime`).

### Status

`<span adf="status" params='{"color":"...","style":"..."}'>TEXT</span>`

- `text` → extracted from content, not stored in params.

### InlineCard

`<a adf="inlineCard" href="...">url</a>`

- `url` → `href` standard attribute.
- `data` dict (when present) → `params`.

### Placeholder

`<span adf="placeholder">text</span>`

### MediaInline

`<span adf="mediaInline" params='{"id":"...","collection":"...","type":"...","alt":"...","width":...,"height":...}'>📎 fallback</span>`

- Fallback text: same as Media (`📎 {alt or "attachment"} ({id})`).
- `data` dict (when present) → included in params.
- `marks`: LinkMark → `<a>` wrapper. AnnotationMark → `<mark>` wrapper. BorderMark → merged into params.

### InlineExtension

`<span adf="inlineExtension" params='{"extensionKey":"...","extensionType":"...","parameters":{...},"text":"..."}'></span>`

Empty content (void inline).

---

## Marks

### StrongMark

`**text**`

### EmMark

`*text*`

### StrikeMark

`~~text~~`

### CodeMark

`` `code` ``

If code contains backticks, use a longer backtick fence: ``` `` code with ` `` ```.

### LinkMark

`[text](url "title")`

- `title` included only when present.

### UnderlineMark

`<u adf="underline">text</u>`

### TextColorMark

`<span adf="textColor" params='{"color":"..."}'>text</span>`

### BackgroundColorMark

`<span adf="bgColor" params='{"color":"..."}'>text</span>`

### SubSupMark

`<sub adf="subSup">text</sub>` / `<sup adf="subSup">text</sup>`

- HTML tag determined by `type` field (`"sub"` or `"sup"`).

### AnnotationMark

`<mark adf="annotation" params='{"id":"..."}'>text</mark>`

- `annotationType` omitted from params. The schema only defines `"inlineComment"`, so the parser restores it as default.
