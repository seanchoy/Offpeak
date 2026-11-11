"""Fixtures for exercise 06 (the planner's search tool).

Database tests reuse exercise 05's Postgres fixtures and catalogue; they are skipped
without TEST_DATABASE_URL. Gemini is never called: support.ScriptedGemini plays it.
"""
from tests.rag.conftest import add_embedding, add_poi, db, engine  # noqa: F401
