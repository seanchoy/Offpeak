"""What the planner still needs from the visitor, read from the trip itself.

The chat model is asked to collect these details in order and to show the
type selector at the right moments, but it does not always do so. These checks
look at what has actually been stored for the trip, so the code, not the model,
decides whether an itinerary can be built and which selector comes next.
"""
from app.core.constants import POI_TYPE_OPTIONS
from app.schemas.ai import UIAction, UIOption

# Every detail auto_generate_itinerary needs, in the order the planner asks for
# them, with the wording the model is given when one is missing.
REQUIRED_TRIP_DETAILS = {
    "name": "the trip name",
    "start_date": "the start date",
    "end_date": "the end date",
    "pace": "the pace (relaxed or packed)",
    "preferences": "the types of places they would like",
    "excluded_types": "the types of places they want to avoid",
}


def missing_trip_details(trip) -> list[str]:
    """The required details this trip does not have yet, in the order they are asked for.

    An empty list counts as missing: the visitor answers "none" to mean no
    preference, which is stored as ["none"].
    """
    return [field for field in REQUIRED_TRIP_DETAILS if not getattr(trip, field, None)]


def missing_details_error(missing: list[str]) -> dict:
    """The tool result that sends the model back to ask for the first missing detail."""
    described = ", ".join(REQUIRED_TRIP_DETAILS[field] for field in missing)
    return {
        "error": (
            f"The itinerary cannot be generated yet. Still missing: {described}. "
            f"Ask the user for {REQUIRED_TRIP_DETAILS[missing[0]]} now, one question at a time, "
            "and only generate after they have answered."
        )
    }


def fallback_message(trip) -> str:
    """Words for a turn where the model replied with an empty message.

    If a detail is still missing, ask for it; otherwise ask the visitor to repeat.
    """
    missing = missing_trip_details(trip)
    if missing:
        return f"Before we go on, could you tell me {REQUIRED_TRIP_DETAILS[missing[0]]}?"
    return "Sorry, I didn't catch that. Could you say it again?"


def type_selector(field: str) -> UIAction:
    """The POI type selector for `preferences` or `excluded_types`, with our fixed options."""
    return UIAction(
        component="poi_type_selector",
        field=field,
        selection="multiple",
        options=[UIOption(**option) for option in POI_TYPE_OPTIONS],
    )


def next_selector(trip) -> UIAction | None:
    """The selector the visitor should see now, or None.

    Types are asked for only after the name, dates and pace, and preferences
    come before exclusions, matching the order in the system prompt.
    """
    missing = missing_trip_details(trip)
    if not missing or missing[0] not in ("preferences", "excluded_types"):
        return None
    return type_selector(missing[0])
