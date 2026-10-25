"""Tests for PATCH /api/users/me (the welcome page and profile save).

Need a disposable Postgres in TEST_DATABASE_URL; skipped without one.
"""
import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="needs TEST_DATABASE_URL (a disposable Postgres)"
)

ME = "/api/users/me"


@pytest.fixture(scope="module")
def engine():
    import app.models.ai_model  # noqa: F401
    import app.models.itinerary_model  # noqa: F401
    import app.models.poi_model  # noqa: F401
    from app.database import Base
    from app.models.user_model import User, UserIdentity, UserSession

    tables = [User.__table__, UserSession.__table__, UserIdentity.__table__]
    eng = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(eng, tables=list(reversed(tables)))
    Base.metadata.create_all(eng, tables=tables)
    yield eng
    Base.metadata.drop_all(eng, tables=list(reversed(tables)))
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
def client(db):
    from fastapi.testclient import TestClient

    from app.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, base_url="https://testserver") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def user(db):
    from app.models.user_model import User

    u = User(email="sean@example.com", password_hash=None, display_name="Sean Cai")
    db.add(u)
    db.commit()
    return u


def auth(user_id):
    from app.core.security.tokens import create_access_token

    return {"Cookie": f"access_token={create_access_token(user_id)}"}


class TestPart1UpdateMe:
    def test_updates_name_and_accessibility(self, client, db, user):
        response = client.patch(
            ME, json={"display_name": "Sean", "accessibility": True}, headers=auth(user.id)
        )

        assert response.status_code == 200
        assert response.json() == {
            "email": "sean@example.com",
            "display_name": "Sean",
            "accessibility": True,
        }
        db.refresh(user)
        assert user.display_name == "Sean"
        assert user.accessibility is True

    def test_trims_the_display_name(self, client, user):
        response = client.patch(
            ME, json={"display_name": "  Sean  ", "accessibility": False}, headers=auth(user.id)
        )

        assert response.status_code == 200
        assert response.json()["display_name"] == "Sean"

    def test_rejects_a_blank_display_name(self, client, db, user):
        response = client.patch(
            ME, json={"display_name": "   ", "accessibility": False}, headers=auth(user.id)
        )

        assert response.status_code == 422
        db.refresh(user)
        assert user.display_name == "Sean Cai"

    def test_rejects_a_display_name_longer_than_50(self, client, user):
        response = client.patch(
            ME, json={"display_name": "x" * 51, "accessibility": False}, headers=auth(user.id)
        )

        assert response.status_code == 422

    def test_requires_a_token(self, client):
        response = client.patch(ME, json={"display_name": "Sean", "accessibility": False})

        assert response.status_code == 401

    def test_token_for_a_deleted_user(self, client):
        response = client.patch(
            ME, json={"display_name": "Sean", "accessibility": False}, headers=auth(uuid.uuid4())
        )

        assert response.status_code == 401

    def test_get_me_lives_here_too(self, client, user):
        response = client.get(ME, headers=auth(user.id))

        assert response.status_code == 200
        assert response.json()["display_name"] == "Sean Cai"
