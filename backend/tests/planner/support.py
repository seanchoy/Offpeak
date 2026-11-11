"""Fake Gemini responses for exercise 06 (练习册「测试怎么检查」)."""
from types import SimpleNamespace

from google.genai import types

from app.schemas.ai import GeminiResponse


def call(name: str, **args) -> types.FunctionCall:
    """One function call, the way Gemini returns it: call("search_pois", query="art")."""
    return types.FunctionCall(name=name, args=args)


def asks_for(*calls: types.FunctionCall):
    """A model turn that asks for one or more tool calls."""
    content = types.Content(role="model", parts=[types.Part(function_call=c) for c in calls])
    return SimpleNamespace(function_calls=list(calls), candidates=[SimpleNamespace(content=content)],
                           text=None, parsed=None)


def answers(message: str, structured: bool = True):
    """A model turn that answers in words (as GeminiResponse when `structured`)."""
    parsed = GeminiResponse(message=message) if structured else None
    content = types.Content(role="model", parts=[types.Part(text=message)])
    return SimpleNamespace(function_calls=None, candidates=[SimpleNamespace(content=content)],
                           text=message, parsed=parsed)


class ScriptedGemini:
    """generate(contents, allow_tools): returns the scripted turns in order and records each call."""

    def __init__(self, *turns):
        self.turns = list(turns)
        self.requests: list[tuple[list, bool]] = []

    def __call__(self, contents, allow_tools):
        self.requests.append((list(contents), allow_tools))
        if not self.turns:
            raise AssertionError("the loop called the model more times than the test scripted")
        return self.turns.pop(0)


def function_responses(content: types.Content) -> list[tuple[str, dict]]:
    """(name, response) for every function response part in a content."""
    return [(p.function_response.name, p.function_response.response) for p in content.parts]
