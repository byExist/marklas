<h1 align="center">Marklas</h1>

<p align="center">
  <a href="https://github.com/byExist/marklas/actions/workflows/ci.yml"><img src="https://github.com/byExist/marklas/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/marklas/"><img src="https://img.shields.io/pypi/v/marklas" alt="PyPI"></a>
  <a href="https://pypi.org/project/marklas/"><img src="https://img.shields.io/pypi/pyversions/marklas" alt="Python"></a>
  <a href="https://github.com/byExist/marklas/blob/master/LICENSE"><img src="https://img.shields.io/pypi/l/marklas" alt="License"></a>
</p>

<p align="center">
  <b>Markdown</b>과 <b>Atlassian Document Format (ADF)</b> 간 양방향 변환기.
</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.ja.md">日本語</a>
</p>

---

## 왜 Marklas인가?

Confluence와 Jira는 문서를 [ADF](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/)로 저장합니다 — 장황한 JSON 구조입니다. Marklas는 이를 읽기 쉬운 Markdown으로 변환하고, 다시 ADF로 복원합니다:

```
Markdown ⇄ Union AST ⇄ ADF
```

ADF 전용 기능(패널, 멘션, 텍스트 색상 등)은 `adf` 속성이 있는 HTML 요소로 보존되어 라운드트립이 가능합니다:

```markdown
<aside adf="panel" params='{"panelType":"info"}'>

정보 패널입니다 — 일반 Markdown으로 읽을 수 있습니다.

</aside>

사용자 <span adf="mention" params='{"id":"abc123"}'>@John</span>이 승인했습니다.
```

`plain=True`를 전달하면 라운드트립 메타데이터를 제거하여 LLM에 적합한 깔끔한 Markdown을 얻을 수 있습니다.

## 설치

```bash
pip install marklas
```

## 사용법

```python
from marklas import to_adf, to_md

# Markdown → ADF
adf = to_adf("## 안녕하세요\n\n**굵은 텍스트**입니다.")

# ADF → Markdown (라운드트립 메타데이터 포함)
md = to_md(adf_document)

# ADF → Markdown (메타데이터 없이)
plain_md = to_md(adf_document, plain=True)

# 라운드트립
original_adf = fetch_confluence_page()
markdown = to_md(original_adf)          # Markdown 에디터에서 편집
restored_adf = to_adf(markdown)         # 다시 저장 — 구조 보존
```

## 토큰 효율

Markdown은 ADF JSON보다 훨씬 간결합니다 — 토큰이 중요한 LLM 워크플로우에 핵심적입니다.

| | ADF JSON | Markdown | Markdown (plain) |
| --- | --- | --- | --- |
| 토큰 수 | 243,217 | 76,332 | 47,794 |
| **절감률** | — | **3.2x** | **5.1x** |

*실제 Confluence 페이지 7개 기준 (pretty-printed JSON), GPT-4o 토크나이저(tiktoken) 사용.*

## 문서

- [매핑 레퍼런스](docs/mapping.md) — ADF 노드별 Markdown 변환 규칙
- [LLM 편집 가이드](docs/llm-guide.md) — marklas 출력을 편집하는 LLM을 위한 가이드

## 개발

```bash
uv sync --extra dev
uv run pytest -v
```
