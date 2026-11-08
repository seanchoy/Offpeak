"""Part 5: search_pois, vector search with SQL filters (练习册 Part 5)."""
import pytest

from tests.rag import catalog
from tests.rag.support import FakeEmbedder, needs_db, pad

pytestmark = needs_db


@pytest.fixture
def embedder(add_poi, add_embedding):
    catalog.load(add_poi, add_embedding)
    return FakeEmbedder(queries=catalog.QUERIES)


def slugs(hits):
    return [h.slug for h in hits]


def test_part5_ranks_by_cosine_similarity(db, embedder):
    from app.services.rag.retriever import search_pois

    hits = search_pois(db, embedder, "modern art", k=5)

    assert slugs(hits) == [
        "museum-of-modern-art", "the-met-cloisters", "the-ramble-central-park",
        "tenement-museum", "central-park",
    ]
    assert hits[0].score == pytest.approx(0.9435, abs=1e-3)
    assert hits[0].name == "Museum Of Modern Art"
    assert embedder.query_calls == ["modern art"]


def test_part5_k_limits_the_results(db, embedder):
    from app.services.rag.retriever import search_pois

    assert slugs(search_pois(db, embedder, "modern art", k=2)) == [
        "museum-of-modern-art", "the-met-cloisters",
    ]


@pytest.mark.parametrize("k", [0, 51])
def test_part5_rejects_k_out_of_range(db, embedder, k):
    from app.services.rag.retriever import search_pois

    with pytest.raises(ValueError):
        search_pois(db, embedder, "modern art", k=k)


def test_part5_blank_query_returns_nothing_without_calling_the_embedder(db, embedder):
    from app.services.rag.retriever import search_pois

    assert search_pois(db, embedder, "   ") == []
    assert embedder.query_calls == []


def test_part5_filter_by_type(db, embedder):
    from app.models.poi_model import POIType
    from app.services.rag.retriever import SearchFilters, search_pois

    hits = search_pois(db, embedder, "modern art", filters=SearchFilters(types=(POIType.park,)))
    assert slugs(hits) == ["the-ramble-central-park", "central-park"]


def test_part5_indoor_only(db, embedder):
    from app.services.rag.retriever import SearchFilters, search_pois

    hits = search_pois(db, embedder, "a walk in nature", filters=SearchFilters(indoor_only=True))
    assert slugs(hits) == [
        "the-ramble-central-park", "the-met-cloisters", "museum-of-modern-art", "tenement-museum",
    ]


def test_part5_wheelchair_and_filters_combine(db, embedder):
    from app.models.poi_model import POIType
    from app.services.rag.retriever import SearchFilters, search_pois

    hits = search_pois(db, embedder, "local history", filters=SearchFilters(wheelchair=True))
    assert slugs(hits) == ["museum-of-modern-art", "central-park"]

    hits = search_pois(db, embedder, "local history",
                       filters=SearchFilters(types=(POIType.museum,), wheelchair=True))
    assert slugs(hits) == ["museum-of-modern-art"]


def test_part5_ignores_vectors_from_another_model(db, embedder, add_poi, add_embedding):
    from app.services.rag.retriever import search_pois

    stale = add_poi("stale-model-poi")
    add_embedding(stale, pad(1.0, 0.0, 0.0), model="old-model")   # would be a perfect match

    assert "stale-model-poi" not in slugs(search_pois(db, embedder, "modern art", k=10))
