"""The planner's checks on what a trip still needs (app/services/ai/trip_state.py)."""
from datetime import date
from types import SimpleNamespace

from app.services.ai.trip_state import (
    fallback_message,
    missing_details_error,
    missing_trip_details,
    next_selector,
)


def trip(**overrides):
    details = {
        "name": "Winter Escape",
        "start_date": date(2026, 12, 3),
        "end_date": date(2026, 12, 5),
        "pace": "relaxed",
        "preferences": ["museum"],
        "excluded_types": ["none"],
    }
    details.update(overrides)
    return SimpleNamespace(**details)


def test_a_complete_trip_is_missing_nothing():
    assert missing_trip_details(trip()) == []


def test_missing_details_come_in_the_order_they_are_asked_for():
    assert missing_trip_details(trip(name=None, excluded_types=[])) == ["name", "excluded_types"]


def test_the_error_asks_for_the_first_missing_detail():
    error = missing_details_error(["name", "excluded_types"])["error"]
    assert "Still missing: the trip name, the types of places they want to avoid" in error
    assert "Ask the user for the trip name now" in error


def test_the_selector_follows_the_trip():
    assert next_selector(trip(preferences=[], excluded_types=[])).field == "preferences"
    assert next_selector(trip(excluded_types=[])).field == "excluded_types"
    assert next_selector(trip()) is None


def test_no_selector_before_the_name_dates_and_pace():
    assert next_selector(trip(name=None, preferences=[], excluded_types=[])) is None
    assert next_selector(trip(pace=None, preferences=[])) is None


def test_the_selector_offers_our_fixed_options():
    selector = next_selector(trip(preferences=[]))
    assert selector.component == "poi_type_selector"
    assert {option.value for option in selector.options} >= {"museum", "none"}


def test_an_empty_reply_is_replaced_by_the_next_question():
    assert "the trip name" in fallback_message(trip(name=None))
    assert "say it again" in fallback_message(trip())
