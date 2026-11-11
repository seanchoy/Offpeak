"""Part 3: run the search and describe the results for the model (练习册 Part 3)."""
import pytest

from tests.rag import catalog
from tests.rag.support import FakeEmbedder, needs_db


@pytest.mark.parametrize(
    ("text", "limit", "expected"),
    [
        ("Short.", 20, "Short."),
        ("  extra   spaces\nand lines ", 40, "extra spaces and lines"),
        ("The Ramble is a wild woodland, great for birds.", 30, "The Ramble is a wild…"),
        ("Unbreakablewordthatgoesonandon", 10, "Unbreakab…"),
        (None, 20, ""),
    ],
)
def test_part3_shorten_cuts_at_a_word_and_marks_the_cut(text, limit, expected):
    from app.services.ai.search_tool import shorten

    result = shorten(text, limit)
    assert result == expected
    assert len(result) <= limit


@pytest.fixture
def embedder(add_poi, add_embedding):
    catalog.load(add_poi, add_embedding)
    return FakeEmbedder(queries=catalog.QUERIES)


@needs_db
def test_part3_results_carry_what_the_model_needs(db, embedder):
    from app.services.ai.search_tool import run_search_tool

    out = run_search_tool(db, embedder, {"query": "modern art", "k": 2})
    assert out["query"] == "modern art"
    assert out["filters"] == {"types": [], "indoor_only": False, "wheelchair": False}
    assert [r["slug"] for r in out["results"]] == ["museum-of-modern-art", "the-met-cloisters"]
    first = out["results"][0]
    assert set(first) == {"slug", "name", "type", "neighborhood", "summary", "score"}
    assert first["type"] == "museum"
    assert first["neighborhood"] == "Midtown"
    assert first["summary"] == "About museum-of-modern-art."
    assert first["score"] == 0.943   # 0.943456... rounded to 3 places


@needs_db
def test_part3_filters_from_the_model_and_the_user_profile_are_applied(db, embedder):
    from app.services.ai.search_tool import run_search_tool

    out = run_search_tool(db, embedder, {"query": "modern art", "types": ["museum"]}, wheelchair_user=True)
    assert out["filters"] == {"types": ["museum"], "indoor_only": False, "wheelchair": True}
    assert [r["slug"] for r in out["results"]] == ["museum-of-modern-art"]


@needs_db
def test_part3_no_match_says_so_instead_of_returning_nothing(db, embedder):
    from app.services.ai.search_tool import run_search_tool

    out = run_search_tool(db, embedder, {"query": "modern art", "types": ["gallery"]})
    assert out["results"] == []
    assert "note" in out


@needs_db
def test_part3_bad_arguments_come_back_as_an_error_without_searching(db, embedder):
    from app.services.ai.search_tool import run_search_tool

    out = run_search_tool(db, embedder, {"query": "   "})
    assert set(out) == {"error"}
    assert "query" in out["error"]
    assert embedder.query_calls == []
