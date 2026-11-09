"""Compare keyword, vector and hybrid retrieval on the golden queries.

    docker compose run --rm api python -m app.scripts.eval_retrieval
    docker compose run --rm api python -m app.scripts.eval_retrieval --k 10 --details

Provided for exercise 05; the functions it calls are yours (练习册 Part 6).
"""
import argparse
import json
from pathlib import Path

# Register every model so POI's relationships (Trip, SavedPOI, ...) can resolve.
import app.models.ai_model
import app.models.itinerary_model
import app.models.user_model  # noqa: F401
from app.database import SessionLocal
from app.services.rag.embedder import make_gemini_embedder
from app.services.rag.evaluation import evaluate
from app.services.rag.retriever import hybrid_search, keyword_search, search_pois

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "eval" / "golden_queries.json"


class CachedEmbedder:
    """Embed each query once, even though vector and hybrid both ask for it."""

    def __init__(self, inner):
        self._inner = inner
        self.model = inner.model
        self._cache: dict[str, list[float]] = {}

    def embed_query(self, text):
        if text not in self._cache:
            self._cache[text] = self._inner.embed_query(text)
        return self._cache[text]

    def embed_documents(self, texts):
        return self._inner.embed_documents(texts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--keyword-weight", type=float, default=1.0,
                        help="weight of the keyword ranking inside hybrid (Part 6.4)")
    parser.add_argument("--details", action="store_true", help="print every query")
    args = parser.parse_args()

    golden = json.loads(GOLDEN_PATH.read_text())
    embedder = CachedEmbedder(make_gemini_embedder())
    db = SessionLocal()
    try:
        methods = {
            "keyword": lambda q, k: [h.slug for h in keyword_search(db, q, k=k)],
            "vector": lambda q, k: [h.slug for h in search_pois(db, embedder, q, k=k)],
            "hybrid": lambda q, k: [
                h.slug
                for h in hybrid_search(db, embedder, q, k=k, keyword_weight=args.keyword_weight)
            ],
        }
        reports = {name: evaluate(fn, golden, k=args.k) for name, fn in methods.items()}
    finally:
        db.close()

    print(f"{len(golden)} queries, k={args.k}, hybrid keyword_weight={args.keyword_weight}\n")
    print(f"{'method':<10}{'recall@' + str(args.k):>10}{'MRR':>8}")
    for name, report in reports.items():
        print(f"{name:<10}{report.recall:>10.3f}{report.mrr:>8.3f}")

    if args.details:
        for i, item in enumerate(golden):
            print(f"\n{item['query']}\n  relevant: {', '.join(item['relevant'])}")
            for name, report in reports.items():
                result = report.per_query[i]
                print(f"  {name:<8} R={result.recall:.2f} RR={result.reciprocal_rank:.2f}  "
                      + ", ".join(result.retrieved))


if __name__ == "__main__":
    main()
