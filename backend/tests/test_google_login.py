"""Tests for login_with_google (federated login via Google OIDC).

These run against a real, disposable Postgres given by TEST_DATABASE_URL and
are skipped when it is unset (e.g. in CI). Each test runs inside a transaction
that is rolled back afterwards, so the database is left empty.
"""
import os

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="needs TEST_DATABASE_URL (a disposable Postgres)"
)


@pytest.fixture(scope="module")
def engine():
    # Register every mapped class so User's relationships can be resolved.
    import app.models.ai_model
    import app.models.itinerary_model
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
    # Commits inside the code under test only release a savepoint; the outer
    # transaction is rolled back so every test starts from an empty database.
    with engine.connect() as conn:
        outer = conn.begin()
        session = Session(bind=conn, join_transaction_mode="create_savepoint")
        yield session
        session.close()
        outer.rollback()


@pytest.fixture
def login():
    # Imported lazily so a missing implementation fails the tests, not collection.
    from app.services.auth_service import login_with_google

    return login_with_google


def claims(**overrides):
    """Userinfo claims as returned by Google after the ID token is verified."""
    data = {
        "sub": "google-sub-1",
        "email": "new@example.com",
        "email_verified": True,
        "name": "Sean Cai",
    }
    data.update(overrides)
    return data


def make_password_user(db, email="sean@example.com", display_name="Sean"):
    from app.models.user_model import User

    user = User(email=email, password_hash="argon2-hash", display_name=display_name)
    db.add(user)
    db.commit()
    return user


def make_google_user(db, sub="google-sub-1", email="sean@example.com"):
    from app.models.user_model import UserIdentity

    user = make_password_user(db, email=email)
    user.password_hash = None
    user.identities.append(UserIdentity(provider="google", provider_user_id=sub))
    db.commit()
    return user


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def users(db):
    from app.models.user_model import User

    return count(db, User)


def identities(db):
    from app.models.user_model import UserIdentity

    return count(db, UserIdentity)


def sessions(db):
    from app.models.user_model import UserSession

    return count(db, UserSession)


# ---------------------------------------------------------------- Part 1


class TestPart1ReturningUser:
    def test_signs_in_existing_google_user(self, db, login):
        from app.core.security.tokens import decode_token

        user = make_google_user(db)

        result = login(claims(), db)

        assert decode_token(result["access_token"])["sub"] == str(user.id)
        assert result["display_name"] == user.display_name
        assert result["accessibility"] is False
        assert result["is_new_user"] is False
        assert users(db) == 1
        assert identities(db) == 1

    def test_creates_a_refresh_session(self, db, login):
        from app.core.security.tokens import decode_token
        from app.models.user_model import UserSession

        user = make_google_user(db)

        result = login(claims(), db)

        sid = decode_token(result["refresh_token"])["sid"]
        session = db.get(UserSession, sid)
        assert session is not None
        assert session.user_id == user.id

    def test_matches_by_google_sub_not_email(self, db, login):
        from app.core.security.tokens import decode_token

        user = make_google_user(db, email="old@example.com")

        # The user changed their Google email; sub stays the same.
        result = login(claims(email="renamed@example.com"), db)

        assert decode_token(result["access_token"])["sub"] == str(user.id)
        assert users(db) == 1


# ---------------------------------------------------------------- Part 2


class TestPart2NewUser:
    def test_creates_user_and_identity(self, db, login):
        from app.models.user_model import User, UserIdentity

        result = login(claims(), db)

        user = db.scalar(select(User))
        identity = db.scalar(select(UserIdentity))
        assert result["is_new_user"] is True
        assert user.email == "new@example.com"
        assert user.display_name == "Sean Cai"
        assert user.password_hash is None
        assert user.accessibility is False
        assert identity.user_id == user.id
        assert identity.provider == "google"
        assert identity.provider_user_id == "google-sub-1"

    def test_email_is_normalised(self, db, login):
        from app.models.user_model import User

        login(claims(email="  New@Example.COM "), db)

        assert db.scalar(select(User)).email == "new@example.com"

    def test_display_name_is_trimmed(self, db, login):
        result = login(claims(name="  Sean Cai  "), db)

        assert result["display_name"] == "Sean Cai"

    def test_display_name_falls_back_to_email_local_part(self, db, login):
        result = login(claims(name=None), db)

        assert result["display_name"] == "new"

    def test_blank_display_name_falls_back_too(self, db, login):
        result = login(claims(name="   "), db)

        assert result["display_name"] == "new"

    def test_display_name_fits_the_column(self, db, login):
        result = login(claims(name="x" * 80), db)

        assert len(result["display_name"]) == 50

    def test_second_login_reuses_the_account(self, db, login):
        login(claims(), db)
        second = login(claims(), db)

        assert second["is_new_user"] is False
        assert users(db) == 1
        assert identities(db) == 1


# ---------------------------------------------------------------- Part 3


class TestPart3LinkExistingAccount:
    def test_verified_email_links_to_password_account(self, db, login):
        from app.models.user_model import UserIdentity

        user = make_password_user(db, email="sean@example.com", display_name="Sean")

        result = login(claims(email="sean@example.com", name="Google Name"), db)

        identity = db.scalar(select(UserIdentity))
        assert users(db) == 1
        assert identity.user_id == user.id
        assert user.password_hash == "argon2-hash"
        assert result["display_name"] == "Sean"
        assert result["is_new_user"] is False

    def test_linking_ignores_email_case(self, db, login):
        user = make_password_user(db, email="sean@example.com")

        login(claims(email="Sean@Example.com"), db)

        assert users(db) == 1
        assert user.identities[0].provider_user_id == "google-sub-1"

    def test_next_login_uses_the_linked_identity(self, db, login):
        make_password_user(db, email="sean@example.com")

        login(claims(email="sean@example.com"), db)
        second = login(claims(email="sean@example.com"), db)

        assert second["is_new_user"] is False
        assert users(db) == 1
        assert identities(db) == 1


# ---------------------------------------------------------------- Part 4


class TestPart4Security:
    def test_unverified_email_never_links(self, db, login):
        from app.core.exceptions import AuthenticationError

        make_password_user(db, email="sean@example.com")

        with pytest.raises(AuthenticationError):
            login(claims(email="sean@example.com", email_verified=False), db)

        assert identities(db) == 0
        assert sessions(db) == 0

    def test_unverified_email_is_rejected_for_new_users(self, db, login):
        from app.core.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError):
            login(claims(email_verified=False), db)

        assert users(db) == 0

    def test_missing_email_verified_counts_as_unverified(self, db, login):
        from app.core.exceptions import AuthenticationError

        info = claims()
        del info["email_verified"]

        with pytest.raises(AuthenticationError):
            login(info, db)

        assert users(db) == 0


class TestPart4bConcurrentFirstLogin:
    def test_recovers_when_another_request_created_the_user_first(
        self, db, login, monkeypatch
    ):
        """Two tabs race on a first login: both lookups miss, then the INSERT
        hits the unique constraints because the other request committed first.
        Simulated by making each lookup miss once while the row already exists.
        """
        from app.core.security.tokens import decode_token
        from app.services import auth_service

        winner = make_google_user(db, email="new@example.com")

        for name in ("get_user_by_google_sub", "get_user_by_email"):
            real = getattr(auth_service, name)
            calls = []

            def miss_once(*args, _real=real, _calls=calls):
                _calls.append(args)
                return None if len(_calls) == 1 else _real(*args)

            monkeypatch.setattr(auth_service, name, miss_once)

        result = login(claims(), db)

        assert decode_token(result["access_token"])["sub"] == str(winner.id)
        assert users(db) == 1
        assert identities(db) == 1


# ---------------------------------------------------------------- Part 5


class TestPart5PasswordLoginForGoogleOnlyUser:
    def test_rejects_password_login_without_a_password(self, db):
        from app.core.exceptions import AuthenticationError
        from app.services.auth_service import INVALID_CREDENTIALS, authenticate_user

        make_google_user(db, email="sean@example.com")

        with pytest.raises(AuthenticationError) as excinfo:
            authenticate_user("sean@example.com", "any-password", db)

        # Same message as a wrong password, so the response doesn't reveal
        # that the email is registered.
        assert str(excinfo.value) == INVALID_CREDENTIALS
        assert sessions(db) == 0
