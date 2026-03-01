# marklas

GFM(GitHub Flavored Markdown) ↔ ADF(Atlassian Document Format) 양방향 변환 라이브러리.

중간 표현(AST)을 경유하여 Markdown과 ADF 간 변환을 수행한다.

```
ADF ──parser──▶ AST ──renderer──▶ Markdown
Markdown ──parser──▶ AST ──renderer──▶ ADF
```

## 설치

```bash
pip install marklas
```

## 사용법

### Markdown → ADF

```python
from marklas.parser.md import parse
from marklas.renderer.adf import render

doc = parse("**Hello** world")
adf_json = render(doc)
```

### ADF → Markdown

```python
from marklas.parser.adf import parse
from marklas.renderer.md import render

doc = parse(adf_json)
markdown = render(doc)
```

### Markdown → AST → Markdown (라운드트립)

```python
from marklas.parser.md import parse
from marklas.renderer.md import render

doc = parse("# Title\n\nParagraph with **bold** and *italic*.")
md = render(doc)
```

## 지원 범위

### 블록

| 요소 | Markdown | ADF |
| --- | --- | --- |
| Paragraph | `text` | `paragraph` |
| Heading | `# ~ ######` | `heading` (level 1-6) |
| CodeBlock | `` ``` `` / `~~~` / 4칸 들여쓰기 | `codeBlock` |
| BlockQuote | `>` | `blockquote` |
| BulletList | `- item` | `bulletList` |
| OrderedList | `1. item` | `orderedList` |
| TaskList | `- [ ] / - [x]` | `taskList` |
| Table | GFM 테이블 | `table` |
| ThematicBreak | `---` / `***` / `___` | `rule` |
| Image (block) | `![alt](url)` (단독) | `mediaSingle` |

### 인라인

| 요소 | Markdown | ADF |
| --- | --- | --- |
| Text | plain text | `text` |
| Strong | `**bold**` | `strong` mark |
| Emphasis | `*italic*` | `em` mark |
| Strikethrough | `~~deleted~~` | `strike` mark |
| Link | `[text](url)` | `link` mark |
| CodeSpan | `` `code` `` | `code` mark |
| Image (inline) | `![alt](url)` (인라인) | `link` mark fallback |
| HardBreak | `\` + 개행 / 2+ spaces | `hardBreak` |

## 개발

```bash
uv sync --extra dev
uv run pytest -v
uv run black src/ tests/
```
