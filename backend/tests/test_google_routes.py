"""Tests for the Google OIDC routes and GET /api/auth/me.

Google is never contacted: the tests pre-load Authlib's server metadata and
replace authorize_access_token with a stub. Like test_google_login.py they need
a disposable Postgres in TEST_DATABASE_URL and are skipped without one.
"""
import os
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="needs TEST_DATABASE_URL (a disposable Postgres)"
)

CALLBACK_PATH = "/api/auth/google/callback"


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
def google(monkeypatch):
    """Configure Google as if the env vars were set, without any network calls."""
    from app.core.config import settings
    from app.core.security.oauth import oauth

    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(oauth.google, "client_id", "test-client-id")
    monkeypatch.setattr(oauth.google, "client_secret", "test-client-secret")
    monkeypatch.setattr(
        oauth.google,
        "server_metadata",
        {
            "_loaded_at": 0,
            "issuer": "https://accounts.google.com",
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
        },
    )
    return oauth.google


@pytest.fixture
def client(db):
    from fastapi.testclient import TestClient

    from app.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, base_url="https://testserver", follow_redirects=False) as c:
        yield c
    app.dependency_overrides.clear()


def google_returns(monkeypatch, google, userinfo=None, error=None):
    """Make the callback's token exchange return `userinfo`, or raise `error`."""

    async def fake_authorize_access_token(request, **kwargs):
        if error is not None:
            raise error
        return {"access_token": "google-access-token", "userinfo": userinfo}

    monkeypatch.setattr(google, "authorize_access_token", fake_authorize_access_token)


def claims(**overrides):
    data = {
        "sub": "google-sub-1",
        "email": "new@example.com",
        "email_verified": True,
        "name": "Sean Cai",
    }
    data.update(overrides)
    return data


def make_google_user(db, sub="google-sub-1", email="sean@example.com"):
    from app.models.user_model import User, UserIdentity

    user = User(email=email, password_hash=None, display_name="Sean")
    user.identities.append(UserIdentity(provider="google", provider_user_id=sub))
    db.add(user)
    db.commit()
    return user


def set_cookies(response):
    """Map cookie name -> the full Set-Cookie header for that cookie."""
    headers = response.headers.get_list("set-cookie")
    return {h.split("=", 1)[0]: h for h in headers}


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


# ---------------------------------------------------------------- Part 1


class TestPart1GoogleLogin:
    def test_returns_503_when_google_is_not_configured(self, client, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")

        response = client.get("/api/auth/google/login")

        assert response.status_code == 503

    def test_redirects_to_google(self, client, google):
        response = client.get("/api/auth/google/login")

        assert response.status_code == 302
        location = urlparse(response.headers["location"])
        assert location.netloc == "accounts.google.com"

        params = parse_qs(location.query)
        assert params["client_id"] == ["test-client-id"]
        assert params["response_type"] == ["code"]
        assert set(params["scope"][0].split()) == {"openid", "email", "profile"}
        assert params["redirect_uri"] == ["https://testserver" + CALLBACK_PATH]
        assert params["state"][0]
        assert params["nonce"][0]

    def test_remembers_state_in_the_session_cookie(self, client, google):
        response = client.get("/api/auth/google/login")

        assert "session" in set_cookies(response)


# ---------------------------------------------------------------- Part 2


class TestPart2CallbackSuccess:
    def test_new_user_is_sent_to_welcome(self, client, db, google, monkeypatch):
        from app.models.user_model import User

        google_returns(monkeypatch, google, claims())

        response = client.get(CALLBACK_PATH, params={"code": "c", "state": "s"})

        assert response.status_code == 302
        assert response.headers["location"] == "/welcome"
        assert count(db, User) == 1

    def test_returning_user_is_sent_home(self, client, db, google, monkeypatch):
        make_google_user(db)
        google_returns(monkeypatch, google, claims())

        response = client.get(CALLBACK_PATH, params={"code": "c", "state": "s"})

        assert response.status_code == 302
        assert response.headers["location"] == "/"

    def test_sets_both_auth_cookies_on_the_redirect(self, client, google, monkeypatch):
        from app.core.security.tokens import decode_token

        google_returns(monkeypatch, google, claims())

        response = client.get(CALLBACK_PATH, params={"code": "c", "state": "s"})

        cookies = set_cookies(response)
        for name in ("access_token", "refresh_token"):
            assert name in cookies
            header = cookies[name].lower()
            assert "httponly" in header
            assert "secure" in header
            assert "samesite=lax" in header

        access = cookies["access_token"].split("=", 1)[1].split(";", 1)[0]
        assert decode_token(access)["type"] == "access"

    def test_password_login_still_sets_cookies(self, client, db):
        """Regression guard for refactoring the cookie code into a helper."""
        from app.core.security.passwords import hash_password
        from app.models.user_model import User

        db.add(
            User(
                email="pw@example.com",
                password_hash=hash_password("secret123"),
                display_name="Pw",
            )
        )
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": "pw@example.com", "password": "secret123"}
        )

        assert response.status_code == 200
        cookies = set_cookies(response)
        assert "access_token" in cookies
        assert "refresh_token" in cookies


# ---------------------------------------------------------------- Part 3


class TestPart3CallbackErrors:
    def test_returns_503_when_google_is_not_configured(self, client, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")

        response = client.get(CALLBACK_PATH, params={"code": "c", "state": "s"})

        assert response.status_code == 503

    def test_cancelled_or_failed_google_login(self, client, google, monkeypatch):
        from authlib.integrations.starlette_client import OAuthError

        google_returns(monkeypatch, google, error=OAuthError(error="access_denied"))

        response = client.get(CALLBACK_PATH, params={"error": "access_denied"})

        assert response.status_code == 302
        assert response.headers["location"] == "/?auth_error=google_failed"
        assert "access_token" not in set_cookies(response)

    def test_unverified_email(self, client, db, google, monkeypatch):
        from app.models.user_model import User

        google_returns(monkeypatch, google, claims(email_verified=False))

        response = client.get(CALLBACK_PATH, params={"code": "c", "state": "s"})

        assert response.status_code == 302
        assert response.headers["location"] == "/?auth_error=google_unverified"
        assert "access_token" not in set_cookies(response)
        assert count(db, User) == 0


# ---------------------------------------------------------------- Part 4


class TestPart4Me:
    def test_returns_the_signed_in_user(self, client, db):
        from app.core.security.tokens import create_access_token

        user = make_google_user(db, email="sean@example.com")
        token = create_access_token(user.id)

        response = client.get("/api/auth/me", headers={"Cookie": f"access_token={token}"})

        assert response.status_code == 200
        assert response.json() == {
            "email": "sean@example.com",
            "display_name": "Sean",
            "accessibility": False,
        }

    def test_accepts_a_bearer_token_too(self, client, db):
        from app.core.security.tokens import create_access_token

        user = make_google_user(db)
        token = create_access_token(user.id)

        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200

    def test_requires_a_token(self, client):
        response = client.get("/api/auth/me")

        assert response.status_code == 401

    def test_token_for_a_deleted_user(self, client, db):
        import uuid

        from app.core.security.tokens import create_access_token

        token = create_access_token(uuid.uuid4())

        response = client.get("/api/auth/me", headers={"Cookie": f"access_token={token}"})

        assert response.status_code == 401
