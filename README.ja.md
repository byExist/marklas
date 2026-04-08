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

パースとレンダリングの間でASTを変換する場合 — たとえばローカル画像をConfluenceの添付ファイルとしてアップロードするパイプラインなど — `Transformer`を使用します：

```python
from marklas import Transformer, parse_md, render_adf
from marklas.ast import Media

t = Transformer()

@t.register(Media)
def _(node: Media) -> Media | None:
    if node.type == "external":
        uploaded = upload_attachment(page_id, node.url)
        return Media(type="file", id=uploaded.media_id, collection=uploaded.collection)
    return None

doc = parse_md(markdown)
new_doc = t(doc)
adf = render_adf(new_doc)
```

| 関数 | 説明 |
| --- | --- |
| `parse_md(md)` | Markdown → AST |
| `parse_adf(adf)` | ADF JSON → AST |
| `render_md(doc)` | AST → Markdown |
| `render_adf(doc)` | AST → ADF JSON |
| `Transformer` | 型別visitorを登録してASTを変換 |

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
