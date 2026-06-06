from __future__ import annotations

from marklas import ast


class TestTableIterCells:
    def test_rowspan_shifts_next_row_cells(self) -> None:
        table = ast.Table(
            content=[
                ast.TableRow(
                    content=[
                        ast.TableCell(content=[], rowspan=2),
                        ast.TableCell(content=[]),
                    ]
                ),
                ast.TableRow(
                    content=[
                        ast.TableCell(content=[]),
                    ]
                ),
            ]
        )
        coords = [(r, c, ci) for r, c, ci, _ in table.iter_cells()]
        assert coords == [(0, 0, 0), (0, 1, 1), (1, 1, 0)]

    def test_rowspan_exceeding_table_height_breaks(self) -> None:
        table = ast.Table(
            content=[
                ast.TableRow(
                    content=[
                        ast.TableCell(content=[], rowspan=5),
                    ]
                ),
            ]
        )
        coords = [(r, c) for r, c, _, _ in table.iter_cells()]
        assert coords == [(0, 0)]


class TestIsBodiedSync:
    def test_paragraph_is_bodied_sync_content(self) -> None:
        from marklas.md.parser.ir import is_bodied_sync

        assert is_bodied_sync(ast.Paragraph(content=[]))

    def test_text_is_not_bodied_sync_content(self) -> None:
        from marklas.md.parser.ir import is_bodied_sync

        assert not is_bodied_sync(ast.Text(text="x"))
