"""The planner keeps the conversation going when the model skips a step
(app/services/ai/trip_state.py, used by GeminiProvider.chat_turn)."""
# ruff: noqa: F811  (pytest injects the imported `planner` fixture by parameter name)
from types import SimpleNamespace

from tests.planner.support import answers, asks_for, call, function_responses
from tests.planner.test_part5_chat import COMPLETE_TRIP, history, planner  # noqa: F401


def trip(**overrides):
    return SimpleNamespace(**{**vars(COMPLETE_TRIP), **overrides})


def test_generating_without_a_trip_name_sends_the_model_back_to_ask(planner, monkeypatch):
    from app.services.ai.providers import gemini

    monkeypatch.setattr(gemini, "auto_generate_itinerary",
                        lambda **kwargs: (_ for _ in ()).throw(AssertionError("must not generate")))
    scripted = planner.script(asks_for(call("auto_generate_itinerary")),
                              answers("What would you like to name your trip?"))

    reply, _ = planner.chat_turn(history("yes"), "", trip(name=None), "conv", None, "user")

    [(_, response)] = function_responses(scripted.requests[1][0][-1])
    assert "the trip name" in response["error"]
    assert reply.message == "What would you like to name your trip?"
    assert reply.itinerary is None


def test_a_failed_itinerary_becomes_something_the_model_can_explain(planner, monkeypatch):
    from app.services.ai.providers import gemini

    def broken(**kwargs):
        raise ValueError("no POIs left after the exclusions")

    monkeypatch.setattr(gemini, "auto_generate_itinerary", broken)
    scripted = planner.script(asks_for(call("auto_generate_itinerary")),
                              answers("I couldn't build that plan. Could we change the dates?"))

    reply, _ = planner.chat_turn(history("yes"), "", trip(), "conv", None, "user")

    [(_, response)] = function_responses(scripted.requests[1][0][-1])
    assert "could not be built" in response["error"]
    assert reply.itinerary is None


def test_the_selector_is_added_when_the_model_forgets_it(planner):
    planner.script(answers("Any types of places you'd like to avoid?"))

    reply, _ = planner.chat_turn(history("museums"), "", trip(excluded_types=[]), "conv", None, "user")

    assert reply.ui_action.field == "excluded_types"
    assert len(reply.ui_action.options) > 0


def test_no_selector_is_added_once_the_types_are_known(planner):
    planner.script(answers("Shall I generate your itinerary?"))

    reply, _ = planner.chat_turn(history("none"), "", trip(), "conv", None, "user")

    assert reply.ui_action is None


def test_an_empty_model_reply_becomes_the_next_question(planner):
    planner.script(answers(""))

    reply, _ = planner.chat_turn(history("yes"), "", trip(name=None), "conv", None, "user")

    assert "the trip name" in reply.message
