---
description: "marklas가 생성한 Markdown 편집 규칙. adf= 속성을 가진 HTML 요소를 포함한 Markdown(ADF↔Markdown 변환기 marklas의 출력)을 다룰 때 적용."
user-invocable: false
---

# Marklas 출력 편집 규칙

Marklas는 Atlassian Document Format(ADF)을 Markdown으로, 그리고 그 역으로 변환한다. 출력물은 표준 Markdown과, ADF 전용 구조를 담은 HTML 요소들로 구성된다. 이 문서는 그 출력물에 대한 편집을 규율한다. 전체 포맷 레퍼런스: [format](format.md).

## 식별

`adf="<type>"` 속성을 가진 HTML 요소가 포함되어 있으면 marklas 출력이다. fallback 요소는 모두 다음 형태를 따른다:

```
<tag adf="<type>" params='{...}'>content</tag>
```

- `tag` — 시각적으로 어울리는 표준 HTML 태그.
- `adf` — ADF 노드 타입. 필수.
- `params` — 추가 필드를 JSON 객체로. 선택.
- `content` — 화면에 표시되는 본문. 편집 대상.

## Roundtrip 계약

다음 항목들은 편집 시 그대로 보존되어야 한다:

- 모든 fallback 요소의 `adf` 속성과 그 값.
- `params` 속성, JSON 형식, 그리고 의도적으로 변경하지 않는 모든 필드. `params` 값은 HTML 속성 escape(`&amp;`, `&#39;`)된 형태로 저장되어 있으니 escape된 상태 그대로 유지한다.
- 데이터를 담는 표준 HTML 속성들: `<a adf="inlineCard">`의 `href`, `<time adf="date">`의 `datetime`, `<ol>`의 `start`.
- GFM 테이블에서 병합된 셀에 인접한 filler 셀 (그리드 너비 유지용 빈 셀).
- 의도적으로 빈 단락을 표현하는 `<p></p>` 마커.
- `<span adf="status">` 내부 텍스트를 감싸는 백틱 (시각 칩).
- void 형태 요소(`<tag ...></tag>`, 내용 없음)는 void 상태 유지.

## 편집 가능 범위

다음 항목들은 자유롭게 편집할 수 있다:

- 내용이 있는 fallback 요소의 본문 텍스트.
- fallback 요소 외부의 표준 Markdown 구조(헤딩, 단락, 리스트, 인용, 코드 블록, 링크, 강조).
- `<aside adf="panel">`, `<details adf="expand">`, `<div adf="layoutColumn">` 등 블록 콘텐츠 fallback 내부 블록 추가/제거 (아래 빈 줄 규칙 준수).
- `<span adf="mention">`의 표시 라벨(`@name`). 식별자는 `params`의 `id`이므로 `id`는 변경하지 않는다.
- 의도적인 변경이 필요한 특정 `params` 필드 (예: panel의 `panelType`, task item의 `state`).

## 블록 HTML 레이아웃

블록 레벨 fallback 요소는 열고 닫는 태그와 내부 콘텐츠를 빈 줄로 구분한다:

```
<aside adf="panel" params='{"panelType":"info"}'>

content

</aside>
```

parser가 열고/닫는 태그를 블록 토큰으로 인식하려면 빈 줄이 필수다. 압축하지 않는다.

## 셀 컨텍스트

GFM 테이블 셀에는 빈 줄을 둘 수 없으므로, 셀 안의 블록 콘텐츠는 인라인 HTML로 표현된다:

```
| <p>Para 1</p><p>Para 2</p> | <ul><li>A</li><li>B</li></ul> |
```

셀 규칙:

- 셀 내 파이프 문자는 `\|`로 escape한다.
- 셀 내 줄바꿈은 literal newline이 아닌 `<br>`로 표현한다.
- 셀 내 블록 콘텐츠는 인라인 HTML wrapper를 사용한다: `<p>`, `<ul>`, `<ol>`, `<li>`, `<h1>`–`<h6>`, `<code>`, `<blockquote>`, `<hr>`, `<aside>`, `<details>`.
- 셀 시작 부분의 `<div adf="cell" params='{...}'></div>`는 `colspan`, `rowspan`, `background`를 담는다. 이 `<div>`를 제거하면 해당 속성도 사라지므로, 병합을 해제하는 게 아니라면 유지한다.
- GFM 테이블 바로 앞의 `<div adf="table" params='{...}'></div>`는 테이블 단위 설정을 담는다. `header`가 `"none"` 또는 `"column"`이면 첫 번째 GFM 행은 filler이고, 실제 데이터는 구분 행(`---`) 뒤부터 시작한다.

## 중첩 테이블

테이블 셀 안에 들어있는 테이블은 `<div adf="extension" params='{"extensionKey":"nested-table",...}'>`로 나타나고, `params.parameters.adf`가 내부 테이블을 JSON 문자열로 담는다. paired 형태에는 시각용 내부 렌더링이 포함된다:

```
<div adf="extension" params='{"extensionKey":"nested-table","parameters":{"adf":"{...}"}}'>

<table>...</table>

</div>
```

시각용 `<table>`은 표시 전용이며 parser가 무시한다. 내부 테이블을 변경하려면 시각 블록이 아닌 `params.parameters.adf`의 JSON 문자열을 편집한다.

## 금지 사항

다음 행위는 문서를 손상시키므로 금지된다:

- `adf=` 속성을 가진 HTML 요소를 직접 새로 만드는 것. marklas만 생성할 수 있다.
- 테이블 셀 외부에 `adf=` 없는 HTML 요소를 추가하는 것. parser가 drop한다.
- 기존 fallback 요소의 `adf` 속성을 이름 변경하거나 제거하는 것.
- `params`에 형식이 깨진 JSON을 생성하는 것 (불균형 braces, escape되지 않은 quote 등).
- GFM 테이블 셀 안에 빈 줄을 삽입하는 것.
- GFM 테이블 셀 안에 escape되지 않은 `|`를 삽입하는 것.
- 병합된 셀에 인접한 filler 셀을 `colspan`/`rowspan` 조정 없이 삭제하는 것.
- `<span adf="status">` 내부 텍스트의 백틱을 제거하는 것.

## plain 모드

별도 렌더 경로 `render_md(doc, plain=True)`는 `adf=`와 `params=` 메타데이터가 모두 제거된 Markdown을 생성한다. plain 출력은 roundtrip되지 않으며 이 규칙들의 적용 대상이 아니다. 문서에 `adf=` 속성이 전혀 없으면 plain 출력으로 간주하고 일반 Markdown처럼 편집한다 — 위 규칙을 적용하려 하지 않는다.
