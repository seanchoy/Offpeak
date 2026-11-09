"""Part 6: metrics, keyword search, hybrid search, golden set (练习册 Part 6)."""
import json
from pathlib import Path

import pytest

from app.services.rag.evaluation import evaluate, recall_at_k, reciprocal_rank, rrf_fuse
from tests.rag import catalog
from tests.rag.support import FakeEmbedder, needs_db

BACKEND = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- 6.1 metrics

def test_part6_recall_at_k():
    retrieved = ["a", "b", "c", "d"]
    assert recall_at_k(retrieved, {"b", "d"}, k=2) == 0.5
    assert recall_at_k(retrieved, {"b", "d"}, k=4) == 1.0
    assert recall_at_k(retrieved, {"x"}, k=4) == 0.0
    assert recall_at_k([], {"a"}, k=5) == 0.0


def test_part6_recall_needs_relevant_items():
    with pytest.raises(ValueError):
        recall_at_k(["a"], set(), k=5)


def test_part6_reciprocal_rank():
    assert reciprocal_rank(["a", "b", "c"], {"a"}) == 1.0
    assert reciprocal_rank(["a", "b", "c"], {"c", "b"}) == 0.5
    assert reciprocal_rank(["a", "b", "c"], {"x"}) == 0.0


# ---------------------------------------------------------------- 6.2 RRF

def test_part6_rrf_adds_one_over_k_plus_rank():
    fused = rrf_fuse([["a", "b", "c"], ["c", "a"]])
    assert [slug for slug, _ in fused] == ["a", "c", "b"]
    scores = dict(fused)
    assert scores["a"] == pytest.approx(1 / 61 + 1 / 62)
    assert scores["c"] == pytest.approx(1 / 63 + 1 / 61)
    assert scores["b"] == pytest.approx(1 / 62)


def test_part6_rrf_ties_break_by_slug_and_k_is_configurable():
    assert [s for s, _ in rrf_fuse([["b"], ["a"]])] == ["a", "b"]
    assert dict(rrf_fuse([["a"]], k=0))["a"] == 1.0
    assert rrf_fuse([]) == []


def test_part6_rrf_weights_scale_each_ranking():
    fused = rrf_fuse([["a", "b"], ["b", "a"]], weights=[1.0, 0.5])
    assert [slug for slug, _ in fused] == ["a", "b"]
    assert dict(fused)["a"] == pytest.approx(1 / 61 + 0.5 / 62)
    assert dict(fused)["b"] == pytest.approx(1 / 62 + 0.5 / 61)


def test_part6_rrf_needs_one_weight_per_ranking():
    with pytest.raises(ValueError):
        rrf_fuse([["a"], ["b"]], weights=[1.0])


# ---------------------------------------------------------------- 6.3 / 6.4 keyword + hybrid

@pytest.fixture
def embedder(add_poi, add_embedding):
    catalog.load(add_poi, add_embedding)
    return FakeEmbedder(queries=catalog.QUERIES)


@needs_db
def test_part6_keyword_search_matches_words(db, embedder):
    from app.services.rag.retriever import keyword_search

    assert [h.slug for h in keyword_search(db, "medieval architecture")] == ["the-met-cloisters"]
    museums = {h.slug for h in keyword_search(db, "museum", k=10)}
    assert museums == {"museum-of-modern-art", "the-met-cloisters", "tenement-museum"}


@needs_db
def test_part6_keyword_search_survives_odd_input(db, embedder):
    from app.services.rag.retriever import keyword_search

    assert [h.slug for h in keyword_search(db, "rock & roll's (history)!")] == ["tenement-museum"]
    assert keyword_search(db, "the a of") == []    # only stop words
    assert keyword_search(db, "!!!") == []
    assert "old-gallery" not in {h.slug for h in keyword_search(db, "modern art", k=10)}


@needs_db
def test_part6_hybrid_rescues_what_the_vector_search_missed(db, embedder):
    from app.services.rag.retriever import hybrid_search, search_pois

    # The fake embedding points "immigrant history" at nature, so vector search ranks
    # the Tenement Museum last. Keyword search finds it; RRF pulls it to the top.
    assert search_pois(db, embedder, "immigrant history")[-1].slug == "tenement-museum"

    hits = hybrid_search(db, embedder, "immigrant history", k=3)
    assert [h.slug for h in hits] == ["tenement-museum", "central-park", "the-ramble-central-park"]
    assert hits[0].score == pytest.approx(1 / 65 + 1 / 61)


@needs_db
def test_part6_hybrid_with_keyword_weight_zero_is_the_vector_ranking(db, embedder):
    from app.services.rag.retriever import hybrid_search, search_pois

    vector = [h.slug for h in search_pois(db, embedder, "immigrant history", k=3)]
    hybrid = [h.slug for h in hybrid_search(db, embedder, "immigrant history", k=3, keyword_weight=0.0)]
    assert hybrid == vector


# ---------------------------------------------------------------- 6.5 evaluate

def test_part6_evaluate_averages_over_queries():
    answers = {"art": ["moma", "met", "frick"], "park": ["zoo", "central-park"]}
    calls = []

    def search(query, k):
        calls.append((query, k))
        return answers[query][:k]

    golden = [
        {"query": "art", "relevant": ["met", "guggenheim"]},
        {"query": "park", "relevant": ["central-park"]},
    ]
    report = evaluate(search, golden, k=3)

    assert calls == [("art", 3), ("park", 3)]
    assert report.recall == pytest.approx((0.5 + 1.0) / 2)
    assert report.mrr == pytest.approx((1 / 2 + 1 / 2) / 2)
    assert [r.query for r in report.per_query] == ["art", "park"]
    assert report.per_query[0].retrieved == ["moma", "met", "frick"]


def test_part6_evaluate_rejects_an_empty_golden_set():
    with pytest.raises(ValueError):
        evaluate(lambda q, k: [], [])


# ---------------------------------------------------------------- 6.6 golden set

def test_part6_golden_set_has_your_queries_and_real_slugs():
    golden = json.loads((BACKEND / "eval" / "golden_queries.json").read_text())
    seed = (BACKEND / "db" / "03_dml_seed_poi_table.sql").read_text()

    assert len(golden) >= 25, "add at least 5 queries of your own (练习册 6.6)"
    queries = [item["query"] for item in golden]
    assert len(set(queries)) == len(queries), "duplicate query"
    for item in golden:
        assert item["query"].strip()
        assert 1 <= len(item["relevant"]) <= 5, item["query"]
        for slug in item["relevant"]:
            assert f"'{slug}'" in seed, f"unknown slug {slug!r} in {item['query']!r}"
