import random
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.constants import (
    EXTRACTION_PROMPT,
    POI_TYPE_OPTIONS,
    SUMMARY_PROMPT,
    SYSTEM_PROMPT,
)
from app.core.exceptions import LLMUnresponsiveError
from app.models.ai_model import Message, Trip
from app.schemas.ai import ChatResponse, GeminiResponse, TripParameters, UIOption
from app.services.ai.base import LLMProvider
from app.services.ai.search_tool import (
    SEARCH_POIS,
    run_search_tool,
    search_pois_declaration,
)
from app.services.ai.tool_loop import run_tool_loop
from app.services.ai.trip_state import (
    fallback_message,
    missing_details_error,
    missing_trip_details,
    next_selector,
)
from app.services.itinerary.itinerary_service import auto_generate_itinerary
from app.services.rag.embedder import make_gemini_embedder
from app.services.user_services import get_user_by_id

CHAT_MODEL = "gemini-3.5-flash"
ITINERARY_TOOL = "auto_generate_itinerary"

ITINERARY_DECLARATION = types.FunctionDeclaration(
    name=ITINERARY_TOOL,
    description="""
                Generate the user's itinerary when all required trip details have been collected.
                Call this only when you know:
                - itinerary name
                - trip dates
                - pace of days
                - POIs and POI types to be excluded
                - user POI type preferences
                """,
    parameters=types.Schema(type="OBJECT", properties={}, required=[]),
)

# TODO 5.1: also offer search_pois (after the itinerary tool)
SEARCH_POIS_DECLARATION = search_pois_declaration()
tools = [types.Tool(function_declarations=[ITINERARY_DECLARATION]), types.Tool(function_declarations=[SEARCH_POIS_DECLARATION])]

# Appended to the chat system prompt (练习册 Part 5).
RECOMMENDATION_RULES = """
Recommendations:
- When the user asks for recommendations, ideas, or places that match a mood or activity,
  call search_pois first. Do this even in the middle of collecting trip details, then
  continue with the next trip question.
- Recommend only attractions that search_pois returned, by their exact name. Never invent
  attractions or use places you know from elsewhere.
- Say in one short phrase why each place fits, using its summary.
- If search_pois returns no results or an error, say you could not find a match and ask
  one question that would help; do not guess.
- Reply in the language the user wrote in.
"""


def parse_reply(response) -> GeminiResponse:
    """The structured reply if Gemini returned one, otherwise its plain text (练习册 Part 5)."""
    if isinstance(response.parsed, GeminiResponse):
        return response.parsed
    return GeminiResponse(message=response.text or "")


def make_json_serializable(obj):
        if isinstance(obj, (date, datetime, time)):
            return obj.isoformat()

        if isinstance(obj, dict):
            return {
                key: make_json_serializable(value)
                for key, value in obj.items()
            }

        if isinstance(obj, list):
            return [
                make_json_serializable(item)
                for item in obj
            ]

        return obj

class GeminiProvider(LLMProvider):
    def __init__(self):
        # One URL (ideally a Webshare rotating endpoint) or a comma-separated list.
        # Routing Gemini through a non-Frankfurt egress avoids the 400
        # FAILED_PRECONDITION "User location is not supported" block; see config.
        self._proxies = [
            p.strip() for p in settings.GEMINI_PROXY_URL.split(",") if p.strip()
        ]
        self._attempts = settings.GEMINI_PROXY_RETRIES if self._proxies else 1
        # Reuse one client for the direct path; when proxied we build per-attempt so
        # each retry rotates to a fresh egress IP.
        self._direct_client = (
            None if self._proxies else genai.Client(api_key=settings.GEMINI_API_KEY)
        )
        self._search_embedder = None

    def _client(self, proxy):
        if proxy is None:
            return self._direct_client
        http_options = types.HttpOptions(
            client_args={"proxy": proxy, "timeout": 20.0},
            async_client_args={"proxy": proxy, "timeout": 20.0},
            # attempts=1 disables genai's internal retry. On a failed proxy request
            # that retry closes the httpx client and masks the real cause as
            # "Cannot send a request, as the client has been closed." With it off,
            # the true error (ProxyError / ConnectTimeout / etc.) surfaces in the
            # logs, while our own _generate loop still retries + rotates proxies.
            retry_options=types.HttpRetryOptions(attempts=1),
        )
        return genai.Client(api_key=settings.GEMINI_API_KEY, http_options=http_options)

    def _generate(self, **kwargs):
        # Retry across rotating egress IPs so a dead/blocked proxy self-heals; on
        # exhaustion raise so FallbackProvider can switch to Llama.
        last_err = None
        start = random.randrange(len(self._proxies)) if self._proxies else 0
        for i in range(self._attempts):
            proxy = (
                self._proxies[(start + i) % len(self._proxies)]
                if self._proxies
                else None
            )
            try:
                # Hold a strong reference to the client for the whole call. A
                # chained `self._client(proxy).models.generate_content(...)` lets
                # the temporary genai.Client get garbage-collected mid-request,
                # which closes its httpx client -> "Cannot send a request, as the
                # client has been closed." Binding it here prevents that.
                client = self._client(proxy)
                return client.models.generate_content(**kwargs)
            except Exception as e: # noqa: BLE001
                # Broad by design: this wraps only the network call, and any
                # failure (API error, transport/proxy error) should rotate/retry
                # and ultimately fall back to Llama rather than 500 the request.
                last_err = e
                if self._proxies:
                    print(f"Gemini attempt {i + 1}/{self._attempts} via proxy failed: {e}")
        raise LLMUnresponsiveError(last_err) from last_err

    def convert_for_gemini(self, history: list[Message]):
        final_history = []
        for message in history:
            final_history.append({
                "role": message.role.value,
                "parts": [{
                    "text": message.content
                    }],
                })
        return final_history

    def _embedder(self):
        # Built on first use, so importing this module never needs the embedding client.
        if self._search_embedder is None:
            self._search_embedder = make_gemini_embedder()
        return self._search_embedder

    def chat_turn(self, history, summary, trip_details: Trip, conv_id, db, user):
        """One assistant turn: the reply, plus every tool call made on the way (练习册 Part 5)."""
        converted_history = self.convert_for_gemini(history)

        user_profile = get_user_by_id(user, db)

        system_instruction = f"""
        {SYSTEM_PROMPT}

        Today's date:
        {datetime.now(ZoneInfo("America/New_York"))}
        Users cannot select a date in the past.
        If the user selects a date in the past without specifying the year,
        ask them to specify the year.
        If the user selects a day in the past, tell them that they cannot
        and must select today or a day in the future.
        Dates must be consecutive.

        User's name:
        {user_profile.display_name}

        User's accessibility:
        {user_profile.accessibility}

        Conversation summary:
        {summary}

        Current trip details:
        {trip_details}

        - Use the summary and trip details as context.
        - Ask for missing trip details naturally.
        - Only generate an itinerary when all required details are available:
            - dates, pace and name of trip cannot be null.
            - preferences and excluded_types lists cannot be empty.

        NEVER return ui_action in message field of response schema.

        The tool returs the itinerary details:
        - Write ONE friendly paragraph.
        - Do not output JSON.
        - Do not output keys.
        - Do not output ui_action.
        - Describe some of the POIs but Do not list every POI generated
        - Return only plain text.
        - Only if a user has accessibility needs, tell them that their needs have been taken
        into account.

        {RECOMMENDATION_RULES}
        """

        itinerary = {}

        # tool 1
        def generate_itinerary(args: dict) -> dict:
            # The model may ask for an itinerary before every detail is stored (for
            # example when the trip name was not picked up). Send it back to ask
            # instead of failing the whole request.
            missing = missing_trip_details(trip_details)
            if missing:
                return missing_details_error(missing)
            try:
                itinerary_json = make_json_serializable(
                    auto_generate_itinerary(trip=trip_details, conv_id=conv_id, db=db, user=user)
                )
            except LLMUnresponsiveError:
                raise
            except Exception as e:  # noqa: BLE001
                # Broad by design: any failure to build the plan becomes something
                # the model can explain, rather than a 500 for the visitor.
                print(f"Itinerary generation failed: {e!r}")
                if db is not None:
                    db.rollback()
                return {
                    "error": (
                        "The itinerary could not be built from these trip details. Tell the "
                        "user, and suggest changing the dates, the pace or the excluded types."
                    )
                }
            itinerary["json"] = itinerary_json
            return {
                "trip_name": itinerary_json["trip_name"],
                "number_of_days": itinerary_json["stops"][-1]["day_number"],
                "number_of_pois": len(itinerary_json["stops"]),
                "pois": [stop["poi_name"] for stop in itinerary_json["stops"]],
            }

        # TODO 5.4: handlers = {tool name: function(args) -> dict} for ITINERARY_TOOL and SEARCH_POIS
        #           (the search uses this user's wheelchair need from user_profile.accessibility)
        # TODO 5.4: generate(contents, allow_tools) -> self._generate(...), tools only when allowed
        # TODO 5.4: run the loop, turn the last response into a reply, and
        #           return (ChatResponse, ToolLoopResult); the itinerary goes into the ChatResponse

        handlers = {ITINERARY_TOOL: generate_itinerary,
                    SEARCH_POIS: lambda args: run_search_tool(db, self._embedder(), args, wheelchair_user= bool(user_profile.accessibility))}

        def generate(contents, allow_tools):
            config = {
                "system_instruction": system_instruction,
                "response_schema": GeminiResponse,
            }

            if allow_tools:
                config["tools"] = tools

            return self._generate(model = CHAT_MODEL, contents = contents, config = config)

        result = run_tool_loop(generate, converted_history, handlers)
        reply = parse_reply(result.response)
        # Now and then the model returns an empty message; never show a blank bubble.
        if not reply.message.strip():
            reply.message = fallback_message(trip_details)

        # check if there is itinerary
        if "json" in itinerary:
            return ChatResponse(message=reply.message, ui_action=None, itinerary=itinerary["json"]), result

        # The model sometimes asks about place types without sending the selector.
        # The stored trip says which one is due, so the visitor always gets it.
        if reply.ui_action is None:
            reply.ui_action = next_selector(trip_details)

        if reply.ui_action and reply.ui_action.component == "poi_type_selector":
            reply.ui_action.options = [UIOption(**option) for option in POI_TYPE_OPTIONS]
        return ChatResponse(message=reply.message, ui_action=reply.ui_action, save_to_history=reply.save_to_history), result










    def generate_chat_response(self, history, summary, trip_details: Trip, conv_id, db, user):
        reply, _ = self.chat_turn(history, summary, trip_details, conv_id, db, user)
        return reply

    def extract_trip_parameters(self, prompt, last_message, trip_details) -> TripParameters:
        system_instruction = f"""
        {EXTRACTION_PROMPT}

        Today's date:
        {datetime.now(ZoneInfo("America/New_York"))}
        Users cannot select a date in the past.

        Current trip details are:
        {trip_details}

        Last assistant message:
        {last_message}

        Use trip details and last messsage for context only.
        """
        response = self._generate(
            model="gemini-3.5-flash",
            contents=prompt,
            config={
                "system_instruction": system_instruction,
                "response_schema": TripParameters
            }
        )

        return response.parsed

    def create_summary(self, history):
        converted_history = self.convert_for_gemini(history)

        formatted_history = "\n".join(
        f"{msg['role'].capitalize()}: {msg['parts'][0]["text"]}"
        for msg in converted_history
        )
        
        response = self._generate(
            model="gemini-3.5-flash",
            contents=formatted_history,
            config={
                "system_instruction": SUMMARY_PROMPT
            }
        )

        return response.text


