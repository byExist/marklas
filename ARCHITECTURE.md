# Architecture

Internal behavior of marklas: how rendered Markdown parses back to ADF, and which fields are lost or have no counterpart in conversion. The authoring/rendering reference (ADF → Markdown) lives in [docs/format.md](docs/format.md); this document is the parsing-side and fidelity counterpart, aimed at contributors.

This is the implementation contract — if the parser disagrees with this document, the parser is right.

---

## Roundtrip Parsing

The parser restores AST from rendered Markdown:

- An HTML element with `adf=<type>` becomes the corresponding AST node. Extra fields come from `params` (HTML-unescaped, then JSON-parsed).
- A `<div adf="marks">` attaches block marks to the next block.
- A `<div adf="table">` attaches table metadata to the next GFM table.
- A `<div adf="cell">` attaches cell metadata to its cell.
- Native Markdown (headings, lists, blockquotes, …) parses directly to the corresponding AST node.

## Node-specific parsing notes

How individual nodes round-trip; the renderer/parser owns these, so authors and editors don't need them.

- **Paragraph** — paired `<p></p>` or legacy `&nbsp;` / `\xa0` → empty Paragraph.
- **OrderedList** — `start=1` stored as `order=None` (symmetric with the ADF parser).
- **TaskItem** — 2+ block children in a task item produce `BlockTaskItem`.
- **Mention** — `@`-prefix display whose tail equals `id` → `text=None`.
- **Emoji** — display is `node.text or node.short_name`; display equal to `shortName` → `text=None`.
- **Date** — parser restores the value from `datetime`.
- **Status** — the backtick codespan is unwrapped transparently; it exists only for visual emphasis.
- **AnnotationMark** — `annotationType` is omitted from `params` (the schema only defines `"inlineComment"`); the parser restores the default.
- **CodeMark** — the ADF schema allows only `code`, `link`, and `annotation` marks on a code-marked node; incompatible marks (e.g. `StrongMark` from `` **bold `code`** ``) are dropped on the ADF side, while `LinkMark`/`AnnotationMark` survive. AST and Markdown rendering preserve every mark faithfully.
- **Table colwidths** — ADF stores the width per cell; marklas consolidates to one entry per column because every cell in a column shares the same width.
- **Cell merge** — filler padding cells adjacent to a merge are dropped when reconstructing the AST.
- **Inline flanking** — spaces adjacent to a Markdown delimiter (`**`, `*`, `~~`) violate CommonMark flanking, so the renderer moves them outside: `** hello **` → ` **hello** `.

## Raw Markdown Parsing

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

## Plain Mode

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
