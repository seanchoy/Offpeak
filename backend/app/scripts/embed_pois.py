"""Embed every active POI that is new or changed.

    docker compose run --rm api python -m app.scripts.embed_pois

Prints one line: embedded=<n> skipped=<n> deleted=<n> (练习册 Part 4.3).
"""

from app.database import SessionLocal
from app.services.rag.embedder import make_gemini_embedder
from app.services.rag.indexer import sync_poi_embeddings
import app.models.ai_model
import app.models.itinerary_model
import app.models.user_model  # noqa: F401


def main() -> None:

    db = SessionLocal()

    try:
        result = sync_poi_embeddings(db, make_gemini_embedder())
        print(f"embedded={result.embedded} skipped={result.skipped} deleted={result.deleted}")
    finally:
        db.close()



if __name__ == "__main__":
    main()
