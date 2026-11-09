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
from app.services.itinerary.itinerary_service import auto_generate_itinerary
from app.services.user_services import get_user_by_id

tools = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="auto_generate_itinerary",
                description="""
                            Generate the user's itinerary when all required trip details have been collected.
                            Call this only when you know:
                            - itinerary name
                            - trip dates
                            - pace of days
                            - POIs and POI types to be excluded
                            - user POI type preferences
                            """,
                parameters=types.Schema(
                    type="OBJECT",
                    properties={},
                    required=[]
                )
            )
        ]
    )
]

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

    def generate_chat_response(self, history, summary, trip_details: Trip, conv_id, db, user):
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
        """
        response = self._generate(
            model="gemini-3.5-flash",
            contents=converted_history,
            config={
                "system_instruction": system_instruction,
                "tools": tools,
                "response_schema": GeminiResponse
            }
        )

        if response.function_calls:
            function_call = response.function_calls[0]
            if function_call.name == "auto_generate_itinerary":
                itinerary_json = auto_generate_itinerary(
                    trip=trip_details,
                    conv_id=conv_id,
                    db=db,
                    user=user
                )
                itinerary_json = make_json_serializable(itinerary_json)

                tool_response = types.Part.from_function_response(
                    name="auto_generate_itinerary",
                    response= {
                        "trip_name": itinerary_json["trip_name"],
                        "number_of_days": itinerary_json["stops"][-1]["day_number"],
                        "number_of_pois": len(itinerary_json["stops"]),
                        "pois": [stop["poi_name"] for stop in itinerary_json["stops"]]  
                    }
                )

                final_response = self._generate(
                    model="gemini-3.5-flash",
                    contents=[
                        *converted_history,
                        response.candidates[0].content,
                        # The Gemini API only accepts "user" or "model" here; a
                        # function response is sent back in a "user" turn.
                        # role="tool" is rejected with 400 INVALID_ARGUMENT.
                        types.Content(
                            role="user",
                            parts=[
                                tool_response
                            ]
                        )
                    ],
                    config={
                        "system_instruction": system_instruction
                    }
                )
                return ChatResponse(
                    message=final_response.text,
                    ui_action=None,
                    itinerary=itinerary_json
                )
        
        gemini_response = response.parsed
        if gemini_response is None:
            return ChatResponse(
                message=response.text,
                ui_action=None,
                itinerary=None
            )
        if gemini_response.ui_action and gemini_response.ui_action.component == "poi_type_selector":
            gemini_response.ui_action.options = [
                UIOption(**option)
                for option in POI_TYPE_OPTIONS
                ]
                
        return gemini_response

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


