"""Part 4: the tool loop (练习册 Part 4). No database, no Gemini: ScriptedGemini plays the model."""
from tests.planner.support import (
    ScriptedGemini,
    answers,
    asks_for,
    call,
    function_responses,
)

HISTORY = [{"role": "user", "parts": [{"text": "somewhere quiet to watch birds"}]}]


def run(gemini, handlers, **kwargs):
    from app.services.ai.tool_loop import run_tool_loop

    return run_tool_loop(gemini, HISTORY, handlers, **kwargs)


def test_part4_a_plain_answer_needs_one_call():
    gemini = ScriptedGemini(answers("Hello!"))
    result = run(gemini, {})
    assert result.response.text == "Hello!"
    assert result.calls == []
    assert result.exhausted is False
    assert [allow for _, allow in gemini.requests] == [True]


def test_part4_runs_the_tool_and_sends_the_result_back_in_a_user_turn():
    seen = []

    def search(args):
        seen.append(args)
        return {"results": [{"slug": "the-ramble-central-park"}]}

    gemini = ScriptedGemini(asks_for(call("search_pois", query="birds", k=3)), answers("Try The Ramble."))
    result = run(gemini, {"search_pois": search})

    assert seen == [{"query": "birds", "k": 3}]
    assert result.response.text == "Try The Ramble."
    assert [(c.name, c.args, c.response) for c in result.calls] == [
        ("search_pois", {"query": "birds", "k": 3}, {"results": [{"slug": "the-ramble-central-park"}]})
    ]

    second_contents, allow_tools = gemini.requests[1]
    assert allow_tools is True
    assert second_contents[: len(HISTORY)] == HISTORY
    model_turn, tool_turn = second_contents[len(HISTORY):]
    assert model_turn.role == "model"
    assert model_turn.parts[0].function_call.name == "search_pois"
    assert tool_turn.role == "user"
    assert function_responses(tool_turn) == [("search_pois", {"results": [{"slug": "the-ramble-central-park"}]})]


def test_part4_several_calls_in_one_turn_are_answered_together_in_order():
    gemini = ScriptedGemini(
        asks_for(call("search_pois", query="art"), call("search_pois", query="parks")),
        answers("Done."),
    )
    result = run(gemini, {"search_pois": lambda args: {"for": args["query"]}})
    assert [c.args["query"] for c in result.calls] == ["art", "parks"]
    tool_turn = gemini.requests[1][0][-1]
    assert function_responses(tool_turn) == [("search_pois", {"for": "art"}), ("search_pois", {"for": "parks"})]


def test_part4_an_unknown_tool_gets_an_error_and_the_loop_goes_on():
    gemini = ScriptedGemini(asks_for(call("get_poi", slug="the-met")), answers("Sorry."))
    result = run(gemini, {"search_pois": lambda args: {}})
    assert result.calls[0].name == "get_poi"
    error = result.calls[0].response["error"]
    assert "get_poi" in error and "search_pois" in error
    assert result.response.text == "Sorry."


def test_part4_after_max_rounds_the_model_must_answer_without_tools():
    gemini = ScriptedGemini(
        asks_for(call("search_pois", query="a")),
        asks_for(call("search_pois", query="b")),
        answers("Here is what I found."),
    )
    result = run(gemini, {"search_pois": lambda args: {"results": []}}, max_rounds=2)
    assert [allow for _, allow in gemini.requests] == [True, True, False]
    assert result.exhausted is True
    assert len(result.calls) == 2
    assert result.response.text == "Here is what I found."


def test_part4_the_callers_history_is_not_changed():
    before = list(HISTORY)
    gemini = ScriptedGemini(asks_for(call("search_pois", query="a")), answers("ok"))
    run(gemini, {"search_pois": lambda args: {}})
    assert HISTORY == before
