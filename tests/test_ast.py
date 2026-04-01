from __future__ import annotations

from marklas import parse_md, render_adf, walk
from marklas.ast import Doc, Heading, Media, MediaSingle, Paragraph, Text


class TestWalk:
    def test_find_media_nodes(self) -> None:
        doc = parse_md("![diagram](./arch.png)")
        medias = list(walk(doc, Media))
        assert len(medias) == 1
        assert medias[0].type == "external"
        assert medias[0].url == "./arch.png"

    def test_mutate_media_for_upload(self) -> None:
        doc = parse_md("![diagram](./arch.png)")
        for media in walk(doc, Media):
            if media.type == "external":
                media.type = "file"
                media.id = "abc-123"
                media.collection = "contentId-456"
                media.url = None

        adf = render_adf(doc)
        media_node = adf["content"][0]["content"][0]
        assert media_node["type"] == "media"
        assert media_node["attrs"]["type"] == "file"
        assert media_node["attrs"]["id"] == "abc-123"
        assert media_node["attrs"]["collection"] == "contentId-456"

    def test_walk_all_nodes(self) -> None:
        doc = parse_md("hello **world**")
        all_nodes = list(walk(doc))
        assert any(isinstance(n, Paragraph) for n in all_nodes)
        assert any(isinstance(n, Text) for n in all_nodes)

    def test_walk_empty_doc(self) -> None:
        doc = Doc(content=[])
        assert list(walk(doc)) == []

    def test_multiple_media(self) -> None:
        md = "![a](./a.png)\n\n![b](./b.png)"
        doc = parse_md(md)
        medias = list(walk(doc, Media))
        assert len(medias) == 2
        assert {m.url for m in medias} == {"./a.png", "./b.png"}

    def test_filter_media_single(self) -> None:
        doc = parse_md("![img](./a.png)")
        singles = list(walk(doc, MediaSingle))
        assert len(singles) == 1
        assert isinstance(singles[0], MediaSingle)

    def test_no_media_in_text_only(self) -> None:
        doc = parse_md("just text")
        assert list(walk(doc, Media)) == []

    def test_nested_media_in_blockquote(self) -> None:
        doc = parse_md("> ![img](./a.png)")
        medias = list(walk(doc, Media))
        assert len(medias) == 1
        assert medias[0].url == "./a.png"

    def test_heading_filter(self) -> None:
        doc = parse_md("# Title\n\nparagraph")
        headings = list(walk(doc, Heading))
        assert len(headings) == 1
