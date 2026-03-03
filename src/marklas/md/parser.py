from __future__ import annotations

from typing import Any, Literal, cast

import mistune

from marklas.nodes import blocks, inlines

type _Alignment = Literal["left", "center", "right"] | None


class _ASTRenderer(mistune.BaseRenderer):
    """mistune 커스텀 렌더러: 토큰을 AST 노드로 직접 변환한다."""

    def _render_children(self, token: dict[str, Any], state: Any) -> list[Any]:
        result: list[Any] = []
        for child in token.get("children", []):
            node: Any = self.render_token(child, state)
            if node is not None:
                result.append(node)
        return result

    def _flatten_text(self, token: dict[str, Any]) -> str:
        if "raw" in token:
            return token["raw"]
        parts: list[str] = []
        for child in token.get("children", []):
            parts.append(self._flatten_text(child))
        return "".join(parts)

    def __call__(self, tokens: Any, state: Any) -> blocks.Document:  # type: ignore[override]
        children: list[blocks.Block] = []
        for tok in tokens:
            node: Any = self.render_token(tok, state)
            if node is not None:
                children.append(node)
        return blocks.Document(children=children)

    # ── Block methods ────────────────────────────────────────────────

    def paragraph(self, token: dict[str, Any], state: Any) -> blocks.Paragraph:
        return blocks.Paragraph(children=self._render_children(token, state))

    def block_text(self, token: dict[str, Any], state: Any) -> blocks.Paragraph:
        return blocks.Paragraph(children=self._render_children(token, state))

    def heading(self, token: dict[str, Any], state: Any) -> blocks.Heading:
        return blocks.Heading(
            level=token["attrs"]["level"],
            children=self._render_children(token, state),
        )

    def block_code(self, token: dict[str, Any], state: Any) -> blocks.CodeBlock:
        code = token["raw"]
        if code.endswith("\n"):
            code = code[:-1]
        attrs: dict[str, Any] = token.get("attrs") or {}
        return blocks.CodeBlock(code=code, language=attrs.get("info"))

    def block_quote(self, token: dict[str, Any], state: Any) -> blocks.BlockQuote:
        return blocks.BlockQuote(children=self._render_children(token, state))

    def thematic_break(self, token: dict[str, Any], state: Any) -> blocks.ThematicBreak:
        return blocks.ThematicBreak()

    def list(
        self, token: dict[str, Any], state: Any
    ) -> blocks.BulletList | blocks.OrderedList:
        items = self._render_children(token, state)
        tight = token.get("tight", True)
        attrs = token["attrs"]
        if attrs["ordered"]:
            return blocks.OrderedList(
                items=items, start=attrs.get("start", 1), tight=tight
            )
        return blocks.BulletList(items=items, tight=tight)

    def list_item(self, token: dict[str, Any], state: Any) -> blocks.ListItem:
        return blocks.ListItem(children=self._render_children(token, state))

    def task_list_item(self, token: dict[str, Any], state: Any) -> blocks.ListItem:
        return blocks.ListItem(
            children=self._render_children(token, state),
            checked=token["attrs"]["checked"],
        )

    def table(self, token: dict[str, Any], state: Any) -> blocks.Table:
        head: list[blocks.TableCell] = []
        body: list[list[blocks.TableCell]] = []
        alignments: list[_Alignment] = []

        for child in token.get("children", []):
            if child["type"] == "table_head":
                for cell_tok in child.get("children", []):
                    head.append(
                        blocks.TableCell(
                            children=[
                                blocks.Paragraph(
                                    children=self._render_children(cell_tok, state)
                                )
                            ]
                        )
                    )
                    alignments.append(cell_tok.get("attrs", {}).get("align"))
            elif child["type"] == "table_body":
                for row_tok in child.get("children", []):
                    row: list[blocks.TableCell] = []
                    for cell_tok in row_tok.get("children", []):
                        row.append(
                            blocks.TableCell(
                                children=[
                                    blocks.Paragraph(
                                        children=self._render_children(
                                            cell_tok, state
                                        )
                                    )
                                ]
                            )
                        )
                    body.append(row)

        return blocks.Table(head=head, body=body, alignments=alignments)

    def blank_line(self, token: dict[str, Any], state: Any) -> None:
        return None

    def block_html(self, token: dict[str, Any], state: Any) -> None:
        return None

    # ── Inline methods ───────────────────────────────────────────────

    def text(self, token: dict[str, Any], state: Any) -> inlines.Text:
        return inlines.Text(text=token["raw"])

    def strong(self, token: dict[str, Any], state: Any) -> inlines.Strong:
        return inlines.Strong(children=self._render_children(token, state))

    def emphasis(self, token: dict[str, Any], state: Any) -> inlines.Emphasis:
        return inlines.Emphasis(children=self._render_children(token, state))

    def strikethrough(self, token: dict[str, Any], state: Any) -> inlines.Strikethrough:
        return inlines.Strikethrough(children=self._render_children(token, state))

    def link(self, token: dict[str, Any], state: Any) -> inlines.Link:
        return inlines.Link(
            url=token["attrs"]["url"],
            children=self._render_children(token, state),
            title=token["attrs"].get("title"),
        )

    def image(self, token: dict[str, Any], state: Any) -> inlines.Image:
        return inlines.Image(
            url=token["attrs"]["url"],
            alt=self._flatten_text(token),
            title=token["attrs"].get("title"),
        )

    def codespan(self, token: dict[str, Any], state: Any) -> inlines.CodeSpan:
        return inlines.CodeSpan(code=token["raw"])

    def linebreak(self, token: dict[str, Any], state: Any) -> inlines.HardBreak:
        return inlines.HardBreak()

    def softbreak(self, token: dict[str, Any], state: Any) -> inlines.SoftBreak:
        return inlines.SoftBreak()

    def inline_html(self, token: dict[str, Any], state: Any) -> None:
        return None


_md = mistune.create_markdown(
    renderer=_ASTRenderer(),
    plugins=["table", "strikethrough", "task_lists"],
)


def parse(markdown: str) -> blocks.Document:
    return cast(blocks.Document, _md(markdown))
