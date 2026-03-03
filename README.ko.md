<h1 align="center">Marklas</h1>

<p align="center">
  <a href="https://github.com/byExist/marklas/actions/workflows/ci.yml"><img src="https://github.com/byExist/marklas/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/marklas/"><img src="https://img.shields.io/pypi/v/marklas" alt="PyPI"></a>
  <a href="https://pypi.org/project/marklas/"><img src="https://img.shields.io/pypi/pyversions/marklas" alt="Python"></a>
  <a href="https://github.com/byExist/marklas/blob/master/LICENSE"><img src="https://img.shields.io/pypi/l/marklas" alt="License"></a>
</p>

<p align="center">
  <b>Markdown</b>과 <b>Atlassian Document Format (ADF)</b> 간의 무손실 양방향 변환기.
</p>

---

## 왜 Marklas인가?

Confluence와 Jira는 문서를 [ADF](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/)로 저장합니다 — 패널, 레이아웃, 멘션, 텍스트 색상 등을 포함하는 리치 JSON 구조입니다. 표준 Markdown으로는 이런 기능의 일부만 표현할 수 있습니다.

**Marklas는 두 스펙의 합집합에 해당하는 Union AST를 정의하고**, 양쪽 모두 이 AST를 경유해 변환합니다.

```
Markdown ⇄ Union AST ⇄ ADF
```

양쪽에 공통으로 존재하는 노드(paragraph, heading, list, table 등)는 직접 매핑됩니다. ADF에만 존재하는 노드(패널, 멘션, 텍스트 색상 등)는 Markdown 출력에 보이지 않는 HTML 주석 annotation으로 포함되어, 라운드트립 시 전체 구조가 보존됩니다.

```
ADF → Markdown (annotation 포함) → ADF   ✅ 무손실
```

annotation 없이도 표준 Markdown 요소는 유효한 ADF로 변환됩니다 — ADF 전용 기능만 없을 뿐입니다:

```
일반 Markdown → ADF   ✅ 동작 (표준 요소만)
```

### Annotation 작동 방식

ADF에 Markdown이 기본적으로 표현할 수 없는 기능(예: 패널, 멘션, 텍스트 색상)이 포함되어 있으면, Marklas는 읽을 수 있는 Markdown 폴백을 HTML 주석 annotation으로 감쌉니다.

```md
<!-- adf:panel {"panelType": "info"} -->
이것은 정보 패널입니다 — 일반 Markdown으로도 읽을 수 있습니다.
<!-- /adf:panel -->

사용자 <!-- adf:mention {"id": "abc123", "text": "@홍길동"} -->`@홍길동`<!-- /adf:mention -->이 승인했습니다.
```

이 annotation은 Markdown으로 렌더링할 때(GitHub, 에디터 등) 보이지 않지만, Marklas가 파싱하면 원본 ADF 구조를 정확히 복원할 수 있습니다.

## 설치

```bash
pip install marklas
```

## 사용법

```python
from marklas import to_adf, to_md
```

### Markdown → ADF

표준 Markdown은 그대로 유효한 ADF로 변환됩니다.

```python
adf = to_adf("""
## 프로젝트 업데이트

릴리즈가 **정상 진행** 중입니다. 주요 변경사항:

- 인증 모듈 리팩토링
- 크리티컬 버그 3건 수정

| 컴포넌트 | 상태 |
| -------- | ---- |
| 백엔드   | 완료 |
| 프론트   | 진행 |
""")
```

### ADF → Markdown

ADF 전용 기능(패널, 멘션, 텍스트 색상 등)은 HTML 주석 annotation으로 보존됩니다 — 렌더링 시 보이지 않지만 완전히 복원 가능합니다.

```python
md = to_md(adf_with_panel)
```

```markdown
<!-- adf:panel {"panelType": "warning"} -->
금요일에는 배포하지 **마세요**.
<!-- /adf:panel -->
```

### 라운드트립

```python
original_adf = fetch_confluence_page()     # 복잡한 ADF
markdown = to_md(original_adf)             # Markdown 에디터에서 편집
restored_adf = to_adf(markdown)            # 다시 반영 — 구조 보존
```

## 토큰 효율

Markdown은 ADF JSON보다 훨씬 컴팩트합니다 — 토큰 하나하나가 중요한 LLM 기반 워크플로우에서 큰 차이를 만듭니다.

| 형식 | 토큰 수 | 바이트 |
| --- | --- | --- |
| ADF JSON | 89,374 | 523 KB |
| Markdown | 21,798 | 49 KB |
| **절감** | **4.1x** | **10.6x** |

*실제 Confluence 페이지를 GPT-4o tokenizer(tiktoken)로 측정.*

## 유의사항

- **테이블 셀**: 테이블 셀 내의 비-paragraph 콘텐츠(리스트, 코드블록 등)는 GFM 테이블 문법에 맞추기 위해 인라인 HTML(`<ul>`, `<code>`, `<br>`)로 변환됩니다.
- **Markdown 전용 기능**: Raw HTML 블록/인라인 등 ADF에 대응하는 노드가 없는 Markdown 전용 구문은 변환 시 제거됩니다.

## 개발

```bash
uv sync --extra dev
uv run pytest -v
uv run black src/ tests/
```
