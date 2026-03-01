# Conversion Rules

## Block Elements

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

## Inline Elements

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

## Mark Handling

### ADF -> AST (mark flattening -> nesting)

ADF는 mark를 flat array로 표현하고, AST는 중첩 노드로 표현한다.

```
ADF: { "text": "bold italic", "marks": [{"type": "strong"}, {"type": "em"}] }
AST: Strong(children=[Emphasis(children=[Text("bold italic")])])
```

- mark 적용 우선순위 (바깥 → 안쪽): `code` > `link` > `strong` > `em` > `strike`
- `code` mark이 있으면 나머지 mark 무시하고 `CodeSpan`으로 변환
- 무시되는 mark: `underline`, `textColor`, `backgroundColor`, `subsup`

### AST -> ADF (nesting -> mark flattening)

AST의 중첩 인라인 노드를 ADF의 flat text + marks로 변환한다.

```
AST: Strong(children=[Emphasis(children=[Text("hello")])])
ADF: { "text": "hello", "marks": [{"type": "strong"}, {"type": "em"}] }
```

- ADF mark 정렬 순서: `link` > `strong` > `em` > `strike` > `code`

## Special Cases

### Paragraph with single Image (AST -> ADF)

`Paragraph`에 `Image` 하나만 있으면 `mediaSingle`로 변환한다.
여러 인라인과 섞여 있는 `Image`는 `link` mark + alt 텍스트로 fallback한다.

### taskList / decisionList (ADF -> AST)

둘 다 `BulletList > ListItem(checked=bool)`로 변환된다.

- `taskItem.state == "DONE"` → `checked=True`
- `decisionItem.state == "DECIDED"` → `checked=True`

### BulletList with checked items (AST -> ADF)

`ListItem.checked`가 `None`이 아닌 항목이 있으면 `taskList`로 변환한다.

### Code fence escaping (AST -> MD)

코드 내용에 ` ``` `이 포함되면 ` ` ````로 fence를 확장한다.

### Code span escaping (AST -> MD)

코드 내용에 `` ` ``이 포함되면 ` `` code `` `로 감싼다.
