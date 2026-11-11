"""Let the model call tools until it answers in words (练习册 Part 4)."""
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from google.genai import types

# generate(contents, allow_tools) -> a Gemini response (or a fake with the same attributes)
Generate = Callable[[list, bool], Any]
Handler = Callable[[dict], dict]

MAX_ROUNDS = 3


@dataclass
class ToolCall:
    name: str
    args: dict
    response: dict


@dataclass
class ToolLoopResult:
    response: Any
    calls: list[ToolCall] = field(default_factory=list)
    exhausted: bool = False


def run_tool_loop(
    generate: Generate, contents: list, handlers: dict[str, Handler], *, max_rounds: int = MAX_ROUNDS
) -> ToolLoopResult:
    """Call the model; run every tool it asks for; send the results back; repeat."""
    calls = []
    for _ in range(max_rounds):
        contents = list(contents)
        response = generate(contents, True)
        contents.append(response.candidates[0].content)
        if not response.function_calls:
            return ToolLoopResult(response, calls = calls)
        else:
            parts = []
            for call in response.function_calls:
                args = call.args or {}
                handler = handlers.get(call.name)
                if not handler:
                    result = {"error": f"Unknown tool {call.name}. Available tools: {sorted(handlers)}"}
                else:
                    result = handler(args)
                calls.append(ToolCall(call.name, args, result))
                parts.append(types.Part.from_function_response(name = call.name, response = result))
            contents.append(types.Content(role = "user", parts = parts))

    contents = list(contents)
    response = generate(contents, False)
    return ToolLoopResult(response, calls = calls, exhausted = True)








