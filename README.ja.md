<h1 align="center">Marklas</h1>

<p align="center">
  <a href="https://github.com/byExist/marklas/actions/workflows/ci.yml"><img src="https://github.com/byExist/marklas/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/marklas/"><img src="https://img.shields.io/pypi/v/marklas" alt="PyPI"></a>
  <a href="https://pypi.org/project/marklas/"><img src="https://img.shields.io/pypi/pyversions/marklas" alt="Python"></a>
  <a href="https://github.com/byExist/marklas/blob/master/LICENSE"><img src="https://img.shields.io/pypi/l/marklas" alt="License"></a>
</p>

<p align="center">
  <b>Markdown</b>と<b>Atlassian Document Format (ADF)</b>間の双方向コンバーター。
</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.ko.md">한국어</a>
</p>

---

## なぜMarklasなのか？

ConfluenceとJiraはドキュメントを[ADF](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/)で保存しています — 冗長なJSON構造です。Marklasはこれを読みやすいMarkdownに変換し、再びADFに復元します：

```
Markdown ⇄ ADF
```

ADF固有の機能（パネル、メンション、テキスト色など）は`adf`属性付きのHTML要素として保持され、ラウンドトリップが可能です：

```markdown
<aside adf="panel" params='{"panelType":"info"}'>

情報パネルです — 通常のMarkdownとして読めます。

</aside>

ユーザー <span adf="mention" params='{"id":"abc123"}'>@John</span> が承認しました。
```

`plain=True`を指定すると、ラウンドトリップ用メタデータを除去し、LLMに最適なクリーンなMarkdownを取得できます。

## インストール

```bash
pip install marklas
```

## 使い方

```python
from marklas import to_adf, to_md

# Markdown → ADF
adf = to_adf("## こんにちは\n\n**太字テキスト**です。")

# ADF → Markdown（ラウンドトリップ用メタデータ付き）
md = to_md(adf_document)

# ADF → Markdown（メタデータなし）
plain_md = to_md(adf_document, plain=True)

# ラウンドトリップ
original_adf = fetch_confluence_page()
markdown = to_md(original_adf)          # Markdownエディタで編集
restored_adf = to_adf(markdown)         # 書き戻し — 構造は保持
```

## 高度な使い方

パースとレンダリングの間でASTを直接操作する必要がある場合 — たとえばローカル画像をConfluenceの添付ファイルとしてアップロードするパイプラインなど — 低レベルAPIを使用できます：

```python
from marklas import parse_md, render_adf, walk
from marklas.ast import Media

doc = parse_md(markdown)

for media in walk(doc, Media):
    if media.type == "external":
        uploaded = upload_attachment(page_id, media.url)
        media.type = "file"
        media.id = uploaded.media_id
        media.collection = uploaded.collection
        media.url = None

adf = render_adf(doc)
```

| 関数 | 説明 |
| --- | --- |
| `parse_md(md)` | Markdown → AST |
| `parse_adf(adf)` | ADF JSON → AST |
| `render_md(doc)` | AST → Markdown |
| `render_adf(doc)` | AST → ADF JSON |
| `walk(node)` | すべての子孫ノードを走査 |
| `walk(node, NodeType)` | 型でフィルタリングして走査 |

## トークン効率

MarkdownはADF JSONよりはるかにコンパクトです — トークンが重要なLLMワークフローにおいて不可欠です。

| | ADF JSON | Markdown | Markdown (plain) |
| --- | --- | --- | --- |
| トークン数 | 243,217 | 76,332 | 47,794 |
| **削減率** | — | **3.2x** | **5.1x** |

*実際のConfluenceページ7件で計測（pretty-printed JSON）、GPT-4oトークナイザー（tiktoken）使用。*

## ドキュメント

- [マッピングリファレンス](docs/mapping.md) — ADFノードごとのMarkdown変換ルール
- [LLM編集ガイド](docs/llm-guide.md) — marklas出力を編集するLLM向けガイド

## 開発

```bash
uv sync --extra dev
uv run pytest -v
```
