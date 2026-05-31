# Marklas 포맷 레퍼런스

각 ADF 노드가 Markdown으로 어떻게 렌더링되는지, 그리고 그 Markdown이 다시 ADF로 어떻게 파싱되는지를 정의한다. 구현 계약이며, 이 문서와 렌더러가 충돌하면 렌더러가 기준이다.

LLM agent의 편집 규칙은 [editing](editing.md)에 있다.

---

## 컨벤션

### HTML Fallback

Markdown으로 표현되지 않는 ADF 기능(panel, mention, status 등)은 두 개의 속성을 가진 HTML 요소로 렌더링된다.

- `adf="<type>"` — ADF 노드 타입. fallback 요소에는 항상 존재한다.
- `params='{...}'` — 추가 필드를 JSON 객체로 보존한다. 키는 ADF의 camelCase를 따르며, 값은 HTML 속성 escape(`&` → `&amp;`, `'` → `&#39;`)된 뒤 JSON 디코딩된다.

표준 HTML 속성(`href`, `datetime`, `start`)이 의미적으로 적합하면 우선 사용하고, 그 외 필드만 `params`에 담는다. 추가 필드가 없는 요소는 `params`를 생략한다.

### 세 가지 렌더링 컨텍스트

| 컨텍스트 | 위치 | 동작 |
| --- | --- | --- |
| Block | Document, Blockquote 내부, ListItem, Panel, Expand, layout column 등 | 네이티브 Markdown 또는 블록 HTML, 빈 줄로 구분 |
| Cell | GFM 테이블 셀(`\| ... \|`) 내부 | 모든 블록이 인라인 HTML로 압축됨 (빈 줄 불가) |
| Inline | Paragraph, Heading, TaskItem, Caption 등 내부 | 인라인 Markdown 또는 인라인 HTML |

블록 HTML 요소는 CommonMark type-6 태그로 출력되며, 열고 닫는 태그 주변에 빈 줄을 두어 parser가 블록 토큰으로 인식하게 한다.

```
<tag adf="..." params='{...}'>

content

</tag>
```

같은 요소가 셀 안에 들어가면 한 줄로 압축된다.

```
<tag adf="..." params='{...}'>content</tag>
```

### 태그 선택

- 블록: `<aside>`, `<details>`, `<figure>`, `<figcaption>`, `<section>`, `<div>`, `<ul>`, `<ol>`, `<li>`.
- 인라인: `<span>`, `<a>`, `<time>`, `<u>`, `<sub>`, `<sup>`.
- 의미가 맞는 시맨틱 태그를 우선한다(`<aside>`는 Panel, `<details>`는 Expand, `<time>`은 Date). 그 외에는 `<div>` (블록) 또는 `<span>` (인라인)을 사용한다.

### plain 모드

`render_md(doc, plain=True)`는 roundtrip 전용 메타데이터를 제거한 깔끔한 Markdown을 출력한다. 결과물은 원래 ADF로 roundtrip되지 않는다.

- 모든 위치에서 `adf`와 `params` 속성을 제거한다.
- void/metadata `<div>` 요소(block marks, table metadata, cell metadata, Extension, BlockCard, EmbedCard, layout column)를 완전히 제거한다.
- 빈 `<p></p>` 단락 마커를 제거한다 (roundtrip 용도이므로 plain에서는 의미가 없다).
- 다음 태그는 unwrap한다 (콘텐츠는 보존, 태그만 제거).

| 태그 | 적용 대상 |
| --- | --- |
| `<span>` | Mention, Emoji, Status, TextColor, BgColor, Placeholder, MediaInline, InlineExtension, AnnotationMark |
| `<time>` | Date |
| `<div>` | MediaGroup, BlockCard, EmbedCard, LayoutColumn, void/metadata |
| `<section>` | LayoutSection |
| `<p>` | Paragraph (셀 컨텍스트) |

### 블록 마크

블록 노드에 부착된 마크는 블록 바로 앞에 void `<div>`로 출력된다. 셀 컨텍스트에서는 블록 요소의 `params`에 병합된다.

```
<div adf="marks" params='{"alignment":"center"}'></div>

content
```

| 마크 | 부착 가능 노드 | params 키 |
| --- | --- | --- |
| `AlignmentMark` | Paragraph, Heading | `"align": "center"` |
| `IndentationMark` | Paragraph, Heading | `"indent": 2` |
| `BreakoutMark` | CodeBlock, Expand, LayoutSection | `"breakoutMode": "wide"` |
| `DataConsumerMark` | 여러 노드 | `"dataConsumerSources": [...]` |
| `BorderMark` | Media, MediaInline | media `params`에 병합됨 |

### 인라인 마크 순서

여러 마크가 같은 텍스트 런에 적용되는 경우 안쪽 → 바깥쪽 순서로 중첩된다.

1. `CodeMark` — `` `code` `` (내부 텍스트에 추가 escape 없음)
2. 네이티브 Markdown — `StrongMark`, `EmMark`, `StrikeMark`
3. `LinkMark` — `[text](url)`
4. HTML 마크 — `UnderlineMark`, `TextColorMark`, `BackgroundColorMark`, `SubSupMark`, `AnnotationMark`

`**`, `*`, `~~` 구분자에 인접한 공백은 CommonMark flanking 규칙을 위반한다. 렌더러는 공백을 구분자 바깥으로 이동시킨다: `** hello **` → ` **hello** `.

### Roundtrip 파싱

parser는 렌더된 Markdown으로부터 AST를 복원한다.

- `adf=<type>` 속성을 가진 HTML 요소는 대응하는 AST 노드로 변환된다. 추가 필드는 `params`에서 추출된다 (HTML unescape 후 JSON parse).
- `<div adf="marks">`는 다음 블록에 블록 마크를 부착한다.
- `<div adf="table">`는 다음 GFM 테이블에 테이블 메타데이터를 부착한다.
- `<div adf="cell">`는 해당 셀에 셀 메타데이터를 부착한다.
- 네이티브 Markdown(헤딩, 리스트, 인용 등)은 대응하는 AST 노드로 직접 변환된다.

### Raw Markdown 파싱

입력에 `adf=` 속성이 전혀 없는 경우 parser는 일반 Markdown으로 처리한다.

| Markdown | AST |
| --- | --- |
| 텍스트 | `Paragraph > Text` |
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
| `![alt](url)` 단독 | `MediaSingle > Media(type="external")` |
| `![alt](url)` 인라인 | 미지원 (ADF에 인라인 외부 이미지가 없음) |
| `SoftBreak` | 공백으로 처리 |
| `adf=` 없는 HTML | 무시 (내용 포함) |

---

## 블록 노드

### Paragraph

블록: 평문. 빈 Paragraph는 `<p></p>`로 출력된다 (paired HTML, plain 모드에서는 제거됨).
셀: `<p>text</p>`. 빈 Paragraph는 `<p></p>`로 출력된다. 셀에 Paragraph가 하나만 있으면 unwrap된다 (`<p>` 태그 없는 bare 텍스트).
파싱: paired `<p></p>` 또는 legacy `&nbsp;` / `\xa0` 은 빈 Paragraph로 복원된다.

### Heading

블록: `# ~ ######` (레벨 1–6).
셀: `<h1>` ~ `<h6>`.

### CodeBlock

블록: 트리플 백틱 fence와 선택적 언어. 코드 내부에 `` ``` ``이 포함되면 더 긴 fence를 사용한다.

```
```python
print("hi")
```
```

셀: `<code>code</code>`. 줄바꿈은 `<br>`로 변환된다. 언어는 `params='{"language":"python"}'`로 보존된다.

### Blockquote

블록: 각 줄에 `> ` prefix. 내부의 빈 줄은 bare `>`로 표현된다.
셀: `<blockquote>content</blockquote>`.

### BulletList

블록: `- ` prefix. 중첩 리스트는 들여쓰기된다.
셀: `<ul><li>content</li></ul>`. Paragraph가 하나뿐인 아이템은 unwrap된다 (`<li>` 내부에 bare 텍스트).

### OrderedList

블록: `N. ` prefix (`order` 값부터 순차 번호, 기본값 1).
셀: `<ol start="N"><li>...</li></ol>`. `start`가 1이면 생략된다.
파싱: `start=1`은 `order=None`으로 저장된다 (ADF parser와 대칭).

### Rule

블록: `---`. 셀: `<hr>`.

### Table

선택적 메타데이터 블록을 동반한 GFM 테이블. 아래 [Tables](#tables) 섹션을 참조한다.

### Panel

```
<aside adf="panel" params='{"panelType":"info","panelIcon":"...","panelIconId":"...","panelIconText":"...","panelColor":"..."}'>

content

</aside>
```

셀: `<aside ...>content</aside>` (한 줄). 기본 `panelType="info"`.

### Expand / NestedExpand

```
<details adf="expand">

<summary>title</summary>

content

</details>
```

`NestedExpand`는 `adf="nestedExpand"`를 사용한다. 제목은 `<summary>`에서 추출된다 (제목이 없으면 `<summary>`는 생략된다). `BreakoutMark`를 지원한다.

### TaskList / TaskItem

블록 (네이티브 MD):

```
- [ ] todo
- [x] done
```

`state`: `TODO` → `[ ]`, `DONE` → `[x]`. 중첩 TaskList는 부모 아이템 아래로 들여쓰기된다.

셀: `<ul adf="taskList"><li adf="taskItem" params='{"state":"TODO"}'>text</li></ul>`.

`BlockTaskItem`은 블록 콘텐츠(Paragraph + Extension 등)를 담는 변형이며, 아이템 아래에 들여쓰기된 continuation 블록으로 렌더링된다.

파싱: 블록 자식이 2개 이상이면 `BlockTaskItem`으로 분류된다.

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

- fallback 텍스트: `📎 {alt or "attachment"} ({id})`.
- `type="external"`인 경우 media params에 `url`이 포함된다.
- `Caption`은 `<figcaption adf="caption">`으로 출력되며, 없으면 생략된다.
- `Media.marks`: `LinkMark`는 `<span>`을 감싸는 `<a>`로, `AnnotationMark`는 `<span adf="annotation">` wrapper로, `BorderMark`는 media params로 병합된다.
- `MediaSingle.marks` (`LinkMark`만)는 figure params의 `linkHref`/`linkTitle`로 병합된다.

`MediaGroup`은 `<div adf="mediaGroup">`이 하나 이상의 `<span adf="media">` 자식을 담는다.

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

`LayoutSection`은 `BreakoutMark`를 지원한다.

### Extension

```
<div adf="extension" params='{"extensionKey":"...","extensionType":"...","parameters":{...},"text":"...","layout":"..."}'></div>
```

void 요소. 블록 마크를 지원한다.

`extensionKey="nested-table"` (Confluence의 셀 내 중첩 테이블 래퍼)는 paired `<div adf="extension">…</div>`로 렌더링되며, 내부 콘텐츠는 `parameters.adf`를 인라인 HTML로 렌더링한 결과다. 내부는 시각 표현 전용이며, roundtrip은 `params` JSON이 담당한다 (내부 ADF가 그대로 보존됨).

### BodiedExtension

```
<div adf="bodiedExtension" params='{"extensionKey":"...","extensionType":"...","content":[...],"parameters":{...},"text":"...","layout":"..."}'></div>
```

void 요소. 내부 콘텐츠는 `params.content`에 ADF JSON으로 직렬화된다.

### SyncBlock / BodiedSyncBlock

```
<div adf="syncBlock" params='{"resourceId":"..."}'></div>
<div adf="bodiedSyncBlock" params='{"resourceId":"...","content":[...]}'></div>
```

void 요소. 블록 마크를 지원한다.

---

## 인라인 노드

### Text

Markdown escape가 적용된 평문: `\ * _ [ ] ` ~`.

### HardBreak

인라인: 줄 끝의 `\` + 줄바꿈. 셀: `<br>`. Paragraph 끝의 HardBreak는 제거된다 (단락 종결과 시각적으로 동일하기 때문).

### Mention

`<span adf="mention" params='{"id":"...","accessLevel":"...","userType":"..."}'>@text</span>`

`text`는 `@` prefix를 포함한다. 파싱: 표시 텍스트의 tail이 `id`와 일치하면 `text=None`으로 저장된다.

### Emoji

`<span adf="emoji" params='{"shortName":":name:","id":"..."}'>text</span>`

표시: `node.text or node.short_name`. 파싱: 표시가 `shortName`과 일치하면 `text=None`이다.

### Date

`<time adf="date" datetime="1705276800000">2024-01-15</time>`

`timestamp` (Unix 밀리초 문자열)은 `datetime`에 보존된다. 표시는 가독성을 위한 `YYYY-MM-DD` 형식이며, parser는 `datetime`에서 값을 복원한다.

### Status

``<span adf="status" params='{"color":"...","style":"..."}'>`TEXT`</span>``

내부 텍스트는 백틱 codespan으로 감싸지며, plain Markdown 뷰어가 시각적으로 구분되는 칩으로 렌더링하도록 한다. parser는 codespan을 투명하게 unwrap한다. codespan은 시각 강조 전용이다.

### InlineCard

`<a adf="inlineCard" href="...">url</a>`

`url`은 `href`에 저장되며, 선택적 `data` dict는 `params`에 포함된다.

### Placeholder

`<span adf="placeholder">text</span>`

### MediaInline

`<span adf="mediaInline" params='{"id":"...","collection":"...","type":"...","alt":"...","width":...,"height":...}'>📎 fallback</span>`

fallback 텍스트와 `marks` 동작은 인라인 `Media`와 동일하다. `marks`: `LinkMark`는 `<a>` wrapper로, `AnnotationMark`는 `<span adf="annotation">` wrapper로, `BorderMark`는 params로 병합된다.

### InlineExtension

`<span adf="inlineExtension" params='{"extensionKey":"...","extensionType":"...","parameters":{...},"text":"..."}'></span>`

void 인라인 (내용 없음).

---

## 마크

| 마크 | Markdown 형식 |
| --- | --- |
| `StrongMark` | `**text**` |
| `EmMark` | `*text*` |
| `StrikeMark` | `~~text~~` |
| `CodeMark` | `` `code` `` (백틱 포함 시 더 긴 fence) |
| `LinkMark` | `[text](url "title")` (title 선택) |
| `UnderlineMark` | `<u adf="underline">text</u>` |
| `TextColorMark` | `<span adf="textColor" params='{"color":"..."}'>text</span>` |
| `BackgroundColorMark` | `<span adf="bgColor" params='{"color":"..."}'>text</span>` |
| `SubSupMark` | `<sub adf="subSup">text</sub>` / `<sup adf="subSup">text</sup>` (태그는 `type`에 따름) |
| `AnnotationMark` | `<span adf="annotation" params='{"id":"..."}'>text</span>` |

### CodeMark 호환성

ADF 스키마는 code-marked text node에 대해 `code`, `link`, `annotation` 마크만 허용한다. AST가 `CodeMark`와 함께 호환되지 않는 마크(예: `**bold `code`**`에서 발생하는 `StrongMark`)를 보유한 경우, ADF 렌더러는 호환되지 않는 마크를 drop하며, `LinkMark`와 `AnnotationMark`는 보존된다. AST와 Markdown 렌더링은 모든 마크를 충실히 보존한다.

### AnnotationMark 비고

`annotationType`은 `params`에서 생략된다. ADF 스키마가 `"inlineComment"`만 정의하므로 parser가 기본값으로 복원한다.

---

## 테이블 (Tables)

### 테이블 메타데이터

```
<div adf="table" params='{...}'></div>

| header | header |
| ------ | ------ |
| cell   | cell   |
```

기본값 외의 속성이 없으면 메타데이터 블록은 생략된다.

| params 키 | 비고 |
| --- | --- |
| `header` | `"none"` / `"column"` / `"both"`. 생략 시 `"row"` (GFM 기본) |
| `layout` | |
| `displayMode` | |
| `isNumberColumnEnabled` | |
| `width` | |
| `colwidths` | grid column당 한 값 (column-major). ADF는 셀별로 저장하지만, marklas는 동일 컬럼이 동일 너비라는 의미를 반영해 통합한다 |

### 헤더 모드

| 모드 | GFM 첫 행 |
| --- | --- |
| `"row"` (기본) | 내용 있음 |
| `"none"` | 빈 filler 셀 |
| `"column"` | 빈 filler 셀 |
| `"both"` | 내용 있음 |

### 셀 메타데이터

```
| <div adf="cell" params='{"colspan":2,"rowspan":2,"background":"#ff0"}'></div>Cell content | ... |
```

`colspan>1`, `rowspan>1`, `background` 중 하나라도 설정된 경우에만 메타 `<div>`가 출력된다.

### 셀 병합

병합된 셀은 인접 위치에 빈 filler 셀을 생성해 GFM 그리드를 유지한다. parser는 AST 재구성 시 이 padding 셀들을 drop한다.

### 예시

```markdown
<!-- 단순 테이블 — 메타데이터 없음 -->

| Name  | Role |
| ----- | ---- |
| Alice | Dev  |

<!-- 헤더 없음 + 테이블 layout -->

<div adf="table" params='{"header":"none","layout":"wide"}'></div>

|     |     |
| --- | --- |
| A   | B   |

<!-- 행+열 헤더 + colwidths -->

<div adf="table" params='{"header":"both","colwidths":[100,200,150]}'></div>

|       | Sub A | Sub B |
| ----- | ----- | ----- |
| Alice | 90    | 85    |

<!-- 셀 병합 + 배경 -->

| <div adf="cell" params='{"colspan":2}'></div>Merged Header |  | C |
| --- | --- | --- |
| A | <div adf="cell" params='{"rowspan":2,"background":"#ff0"}'></div>Vertical | C |
| D |  | F |
```

---

## 손실 항목 (Lossy Items)

에디터 런타임 메타데이터. 문서 내용·구조·서식에 영향이 없으며 roundtrip에서 보존되지 않는다.

| 항목 | 설명 |
| --- | --- |
| `local_id` (모든 노드) | 협업 편집 노드 식별자 (UUID) |
| `CodeBlock.unique_id` | 협업 편집 코드 블록 식별자 |
| `FragmentMark` | 테이블 협업 편집 fragment 추적 |
| `HardBreak.text` | 항상 `"\n"` — 정보 없음 |
| `LinkMark.id` | Atlassian 내부 link ID |
| `LinkMark.collection` | Media collection 참조 |
| `occurrence_key` (LinkMark, Media, MediaInline) | 중복 media embed 추적 |

## Markdown 전용 요소 (No ADF Equivalent)

Markdown에는 존재하지만 ADF에 대응이 없는 요소.

| 요소 | 이유 |
| --- | --- |
| `SoftBreak` | ADF에서 생성되지 않음 |
| 일반 `HtmlBlock` / `HtmlInline` | marklas는 특정 패턴만 사용하며, 일반 컨테이너는 불필요 |
| `BulletList.tight` / `OrderedList.tight` | 고정 형식, ADF 대응 없음 |
| `ListItem.checked` | ADF는 `TaskItem.state`를 사용 |
| `Table.alignments` | ADF 테이블은 컬럼 정렬을 지원하지 않음 |
