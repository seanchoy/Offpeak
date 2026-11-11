"""Part 5: plug the loop and the search tool into the planner's chat turn (练习册 Part 5)."""
from types import SimpleNamespace

import pytest

from tests.planner.support import (
    ScriptedGemini,
    answers,
    asks_for,
    call,
    function_responses,
)
from tests.rag import catalog
from tests.rag.support import FakeEmbedder, needs_db

# Every detail an itinerary needs (see app/services/ai/trip_state.py).
COMPLETE_TRIP = SimpleNamespace(name="Art weekend", start_date="2026-12-03", end_date="2026-12-04",
                                pace="relaxed", preferences=["museum"], excluded_types=["none"])


def history(text):
    return [SimpleNamespace(role=SimpleNamespace(value="user"), content=text)]


@pytest.fixture
def planner(monkeypatch):
    """A GeminiProvider whose model is scripted per test: planner.script(turn, ...)."""
    from app.services.ai.providers import gemini

    profile = SimpleNamespace(display_name="Alex", accessibility=False)
    monkeypatch.setattr(gemini, "get_user_by_id", lambda user, db: profile)
    provider = gemini.GeminiProvider()
    provider.profile = profile
    provider.embedder = FakeEmbedder(queries=catalog.QUERIES)
    monkeypatch.setattr(gemini, "make_gemini_embedder", lambda: provider.embedder)

    def script(*turns):
        scripted = ScriptedGemini(*turns)
        provider.configs = []

        def fake_generate(*, model, contents, config):
            provider.configs.append(config)
            return scripted(contents, "tools" in config)

        monkeypatch.setattr(provider, "_generate", fake_generate)
        return scripted

    provider.script = script
    return provider


def test_part5_the_chat_offers_both_tools():
    from app.services.ai.providers.gemini import tools

    names = [d.name for tool in tools for d in tool.function_declarations]
    assert names == ["auto_generate_itinerary", "search_pois"]


def test_part5_parse_reply_prefers_the_structured_answer():
    from app.schemas.ai import GeminiResponse
    from app.services.ai.providers.gemini import parse_reply

    assert parse_reply(answers("structured")).message == "structured"
    plain = parse_reply(answers("plain text", structured=False))
    assert isinstance(plain, GeminiResponse)
    assert plain.message == "plain text"


def test_part5_the_system_prompt_tells_the_model_to_ground_its_recommendations():
    from app.services.ai.providers.gemini import RECOMMENDATION_RULES

    rules = RECOMMENDATION_RULES.lower()
    assert "search_pois" in rules
    assert "only" in rules


@needs_db
def test_part5_a_recommendation_question_searches_the_real_catalogue(db, add_poi, add_embedding, planner):
    catalog.load(add_poi, add_embedding)
    gemini = planner.script(asks_for(call("search_pois", query="modern art", k=2)), answers("Try MoMA."))

    reply, loop = planner.chat_turn(history("modern art please"), "", "", "conv", db, "user")

    assert reply.message == "Try MoMA."
    assert reply.itinerary is None
    assert [c.name for c in loop.calls] == ["search_pois"]
    [(name, response)] = function_responses(gemini.requests[1][0][-1])
    assert name == "search_pois"
    assert [r["slug"] for r in response["results"]] == ["museum-of-modern-art", "the-met-cloisters"]
    assert "search_pois" in planner.configs[0]["system_instruction"]


@needs_db
def test_part5_the_wheelchair_need_comes_from_the_profile_not_the_model(db, add_poi, add_embedding, planner):
    catalog.load(add_poi, add_embedding)
    planner.profile.accessibility = True
    planner.script(asks_for(call("search_pois", query="local history")), answers("ok"))

    _, loop = planner.chat_turn(history("history?"), "", "", "conv", db, "user")

    assert loop.calls[0].response["filters"]["wheelchair"] is True
    assert {r["slug"] for r in loop.calls[0].response["results"]} <= {"museum-of-modern-art", "central-park"}


def test_part5_the_itinerary_tool_still_returns_the_itinerary(planner, monkeypatch):
    from app.services.ai.providers import gemini

    stops = [{"day_number": 1, "poi_name": "MoMA"}, {"day_number": 2, "poi_name": "Central Park"}]
    monkeypatch.setattr(gemini, "auto_generate_itinerary",
                        lambda trip, conv_id, db, user: {"trip_name": "Art weekend", "stops": stops})
    scripted = planner.script(asks_for(call("auto_generate_itinerary")), answers("Your trip is ready."))

    reply = planner.generate_chat_response(history("yes, generate it"), "", COMPLETE_TRIP, "conv", None, "user")

    assert reply.message == "Your trip is ready."
    assert reply.itinerary["trip_name"] == "Art weekend"
    [(_, response)] = function_responses(scripted.requests[1][0][-1])
    assert response == {"trip_name": "Art weekend", "number_of_days": 2, "number_of_pois": 2,
                        "pois": ["MoMA", "Central Park"]}


def test_part5_a_plain_question_makes_one_call_with_tools_and_returns_the_reply(planner):
    scripted = planner.script(answers("What should we call the trip?"))
    reply = planner.generate_chat_response(history("hi"), "", "", "conv", None, "user")
    assert reply.message == "What should we call the trip?"
    assert [allow for _, allow in scripted.requests] == [True]
