"""Tests for crediting Google Places photos (GET /api/pois/{slug}/photo/attribution).

Google is never contacted: photo_service._resolve is replaced by a stub, and the
POI lookup is replaced so the test database only needs the photo cache table.
Needs a disposable Postgres in TEST_DATABASE_URL; skipped without one.
"""
import os
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="needs TEST_DATABASE_URL (a disposable Postgres)"
)

ATTRIBUTION = "/api/pois/the-met/photo/attribution"

GOOGLE_PHOTO = {
    "photo_uri": "https://lh3.googleusercontent.com/place-photos/abc",
    "author_name": "Jane Doe",
    "author_uri": "https://maps.google.com/maps/contrib/123",
    "google_maps_uri": "https://www.google.com/maps/place//data=photo",
}


@pytest.fixture(scope="module")
def engine():
    import app.models.ai_model
    import app.models.itinerary_model
    import app.models.user_model  # noqa: F401
    from app.database import Base
    from app.models.poi_model import POIPhotoCache

    tables = [POIPhotoCache.__table__]
    eng = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(eng, tables=tables)
    Base.metadata.create_all(eng, tables=tables)
    yield eng
    Base.metadata.drop_all(eng, tables=tables)
    eng.dispose()


@pytest.fixture
def db(engine):
    with engine.connect() as conn:
        outer = conn.begin()
        session = Session(bind=conn, join_transaction_mode="create_savepoint")
        yield session
        session.close()
        outer.rollback()


@pytest.fixture
def client(db, monkeypatch):
    from fastapi.testclient import TestClient

    from app.core.config import settings
    from app.database import get_db
    from app.main import app
    from app.routers import pois

    monkeypatch.setattr(settings, "GOOGLE_PLACES_API_KEY", "test-key")
    monkeypatch.setattr(
        pois,
        "get_poi_by_slug",
        lambda slug, db: SimpleNamespace(google_place_id="place-1")
        if slug == "the-met"
        else None,
    )

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, base_url="https://testserver", follow_redirects=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def google(monkeypatch):
    """Replace the call to Google; returns the list of place_ids it was asked for."""
    from app.services import photo_service

    calls = []

    def fake_resolve(place_id):
        calls.append(place_id)
        return dict(GOOGLE_PHOTO)

    monkeypatch.setattr(photo_service, "_resolve", fake_resolve)
    return calls


class TestPhotoAttribution:
    def test_returns_the_photo_author(self, client, google):
        response = client.get(ATTRIBUTION)

        assert response.status_code == 200
        assert response.json() == {
            "author_name": "Jane Doe",
            "author_uri": "https://maps.google.com/maps/contrib/123",
            "google_maps_uri": "https://www.google.com/maps/place//data=photo",
        }
        assert google == ["place-1"]

    def test_reuses_the_cached_photo(self, client, google):
        client.get(ATTRIBUTION)
        client.get(ATTRIBUTION)

        assert google == ["place-1"]

    def test_refreshes_rows_cached_before_attribution_existed(self, client, db, google):
        from app.models.poi_model import POIPhotoCache

        db.add(POIPhotoCache(place_id="place-1", photo_uri="https://old.example/photo"))
        db.commit()

        response = client.get(ATTRIBUTION)

        assert response.json()["author_name"] == "Jane Doe"
        assert google == ["place-1"]

    def test_404_when_the_place_has_no_photo(self, client, monkeypatch):
        from app.services import photo_service

        monkeypatch.setattr(photo_service, "_resolve", lambda place_id: None)

        assert client.get(ATTRIBUTION).status_code == 404

    def test_404_for_an_unknown_attraction(self, client, google):
        assert client.get("/api/pois/nowhere/photo/attribution").status_code == 404

    def test_photo_redirect_still_works(self, client, google):
        response = client.get("/api/pois/the-met/photo")

        assert response.status_code == 307
        assert response.headers["location"] == GOOGLE_PHOTO["photo_uri"]
