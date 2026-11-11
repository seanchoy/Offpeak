"""Saving the same generated itinerary twice keeps one copy (itinerary_repository)."""
from datetime import date, time
from types import SimpleNamespace

from app.repositories.itinerary_repository import is_same_itinerary


def stop(poi_id, position, slot_start=time(9), day=1):
    return SimpleNamespace(poi_id=poi_id, day_number=day, visit_date=date(2026, 11, 12),
                           slot_start=slot_start, position=position)


def generated(stops, name="Winter Escape"):
    return SimpleNamespace(trip_name=name, start_date=date(2026, 11, 12),
                           end_date=date(2026, 11, 13), stops=stops)


def saved(stops, name="Winter Escape"):
    return SimpleNamespace(name=name, start_date=date(2026, 11, 12),
                           end_date=date(2026, 11, 13), stops=stops)


def test_the_same_itinerary_is_recognised_whatever_the_stop_order():
    stops = [stop(1, 0), stop(2, 1, time(13))]
    assert is_same_itinerary(saved(list(reversed(stops))), generated(stops))


def test_a_different_stop_or_time_is_a_different_itinerary():
    assert not is_same_itinerary(saved([stop(1, 0)]), generated([stop(3, 0)]))
    assert not is_same_itinerary(saved([stop(1, 0)]), generated([stop(1, 0, time(13))]))
    assert not is_same_itinerary(saved([stop(1, 0)]), generated([stop(1, 0), stop(2, 1)]))


def test_a_renamed_trip_is_a_different_itinerary():
    assert not is_same_itinerary(saved([stop(1, 0)], name="Old"), generated([stop(1, 0)]))
