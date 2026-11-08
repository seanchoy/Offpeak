"""Shared test setup.

app/database.py builds an engine at import time from Settings, which
requires DATABASE_URL and JWT_SECRET_KEY. We inject harmless fake values
BEFORE any app import so the pure-logic modules can be imported without
a real database or .env file. (postgresql:// is lazy — nothing connects.) 
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-not-real")
# The remaining required Settings fields. CI has no backend/.env to supply
# these, so they must be injected here or Settings() fails at import time.
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

# Make `app` importable regardless of where pytest is invoked from.
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

import pytest

from app.core.constants import TIME_SLOTS
from app.domains.scheduling import POIProfile

ALL_SLOTS = tuple(s.name for s in TIME_SLOTS)


def make_profile(
    id: int,
    slug: str,
    days: list[int],
    open_slots: tuple = ALL_SLOTS,
    opening_days: list[int] | None = None,
) -> POIProfile:
    """Build a POIProfile whose availability covers `days`.

    availability[day][slot] -> bool, matching what the scheduler expects.
    """
    availability = {
        day: {slot: (slot in open_slots) for slot in ALL_SLOTS} for day in days
    }
    return POIProfile(
        id=id,
        slug=slug,
        availability=availability,
        opening_days=opening_days if opening_days is not None else list(days),
        mode="standard",
        flags=[],
    )


class FakePOI:
    """Minimal stand-in for the SQLAlchemy POI model (duck-typed)."""

    def __init__(self, slug: str, name: str | None = None, accessibility_labels=None):
        self.slug = slug
        self.name = name or slug
        self.accessibility_labels = accessibility_labels


@pytest.fixture
def make_poi():
    return FakePOI
