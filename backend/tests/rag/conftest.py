"""Fixtures for exercise 05 (RAG over POIs).

Database tests need a disposable Postgres with pgvector in TEST_DATABASE_URL and
are skipped without one. Gemini is never called: support.FakeEmbedder stands in for it.
"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from tests.rag.support import TEST_DATABASE_URL

DROP_TABLES = text("DROP TABLE IF EXISTS poi_embedding, poi CASCADE")


@pytest.fixture(scope="package")
def engine():
    """Creates poi + poi_embedding for tests/rag only, and drops them afterwards so the
    other test modules (which manage their own tables) start from a clean database."""
    import app.models.ai_model
    import app.models.itinerary_model
    import app.models.user_model  # noqa: F401
    from app.database import Base
    from app.models.poi_model import POI, POIEmbedding

    eng = create_engine(TEST_DATABASE_URL)
    with eng.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(DROP_TABLES)
    Base.metadata.create_all(eng, tables=[POI.__table__, POIEmbedding.__table__])
    yield eng
    with eng.begin() as conn:
        conn.execute(DROP_TABLES)
    eng.dispose()


@pytest.fixture
def db(engine):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE poi_embedding, poi RESTART IDENTITY CASCADE"))
    with Session(engine) as session:
        yield session


@pytest.fixture
def add_poi(db):
    """add_poi("the-met", type=POIType.museum, ...) inserts and commits one POI row."""
    from app.models.poi_model import POI, POIType

    def _add(slug, **overrides):
        values = {
            "slug": slug,
            "name": slug.replace("-", " ").title(),
            "type": POIType.museum,
            "borough": "Manhattan",
            "neighborhood": "Midtown",
            "summary": f"About {slug}.",
            "description": None,
            "tags": ["indoor"],
            "accessibility_labels": [],
            "is_active": True,
        }
        values.update(overrides)
        poi = POI(**values)
        db.add(poi)
        db.commit()
        return poi

    return _add


@pytest.fixture
def add_embedding(db):
    """add_embedding(poi, pad(1, 0, 0), document="...") stores a hand-made vector for a POI."""
    from app.models.poi_model import POIEmbedding

    def _add(poi, vector, document="", model="fake-embed-v1"):
        db.add(POIEmbedding(poi_id=poi.id, model=model, content_hash="0" * 64,
                            document=document, embedding=vector))
        db.commit()

    return _add
