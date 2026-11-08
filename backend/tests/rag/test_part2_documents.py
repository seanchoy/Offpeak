"""Part 2: build_poi_document and content_hash (练习册 Part 2). No database needed."""
from types import SimpleNamespace

from app.models.poi_model import POIType
from app.services.rag.documents import build_poi_document, content_hash


def make_poi(**overrides):
    values = {
        "name": "The Met Cloisters",
        "type": POIType.museum,
        "neighborhood": "Washington Heights (North)",
        "tags": ["art_museum", "museum", "indoor"],
        "summary": "The Met Cloisters is a museum of medieval art.",
        "description": "It is in Fort Tryon Park.",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_part2_full_document():
    assert build_poi_document(make_poi()) == (
        "The Met Cloisters\n"
        "Type: museum. Neighborhood: Washington Heights (North).\n"
        "Tags: art museum, museum, indoor.\n"
        "The Met Cloisters is a museum of medieval art.\n"
        "It is in Fort Tryon Park."
    )


def test_part2_missing_neighborhood_is_left_out():
    document = build_poi_document(make_poi(neighborhood=None))
    assert document.splitlines()[1] == "Type: museum."


def test_part2_no_tags_line_without_tags():
    for tags in (None, [], ["yes"]):
        document = build_poi_document(make_poi(tags=tags))
        assert "Tags:" not in document, tags


def test_part2_tags_are_readable_unique_and_without_noise():
    document = build_poi_document(make_poi(tags=["art_museum", "yes", "indoor", "art_museum"]))
    assert document.splitlines()[2] == "Tags: art museum, indoor."


def test_part2_blank_texts_are_skipped():
    document = build_poi_document(make_poi(summary="   ", description=None))
    assert document == (
        "The Met Cloisters\n"
        "Type: museum. Neighborhood: Washington Heights (North).\n"
        "Tags: art museum, museum, indoor."
    )
    assert "None" not in document


def test_part2_whitespace_inside_texts_is_collapsed():
    document = build_poi_document(
        make_poi(summary="  Medieval   art.\n\nGardens too.  ", description="Line one.\nLine two.")
    )
    assert document.splitlines()[3:] == ["Medieval art. Gardens too.", "Line one. Line two."]


def test_part2_content_hash_is_sha256_hex():
    assert content_hash("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert len(content_hash(build_poi_document(make_poi()))) == 64


def test_part2_content_hash_follows_the_document():
    a = build_poi_document(make_poi())
    b = build_poi_document(make_poi(summary="The Met Cloisters is a museum of medieval art!"))
    assert content_hash(a) == content_hash(build_poi_document(make_poi()))
    assert content_hash(a) != content_hash(b)
