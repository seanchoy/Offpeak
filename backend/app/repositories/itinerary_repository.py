"""Services for busyness data and saved itinerary management."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ItineraryNotFound, POINotFoundError, StopNotFound
from app.models.itinerary_model import ItineraryStop, SavedItinerary
from app.models.poi_model import POIBusynessForecast
from app.schemas.itinerary import ItineraryRequest, ItineraryResponse
from app.services.photo_service import poi_photo_url
from app.services.poi_service import get_poi_by_slug


def get_crowd_level(id, day, slot, db: Session):
    """Return the crowd-level label for a POI at a specified day and time slot."""

    statement = select(
        func.avg(POIBusynessForecast.busyness_pct).label("avg_busyness_pct"),
        POIBusynessForecast.poi_id,
        POIBusynessForecast.day_of_week,
        POIBusynessForecast.time_slot
        ).where(
            POIBusynessForecast.time_slot == slot,
            POIBusynessForecast.poi_id == id,
            POIBusynessForecast.day_of_week == day
        ).group_by(
            POIBusynessForecast.time_slot,
            POIBusynessForecast.poi_id,
            POIBusynessForecast.day_of_week
        )

    result = db.execute(statement).one_or_none()

    if result is None:
        return "Unavailable"
    
    elif result.avg_busyness_pct < 30:
        return "Quiet"
    
    elif 30 <= result.avg_busyness_pct < 50:
        return "Moderate"
        
    elif 50 <= result.avg_busyness_pct < 70:
        return "Busy"
    
    return "Very Busy"

def get_busyness_for_day(id, day: int, db: Session):
    """Return hourly predicted busyness percentages for a POI on a given day."""

    statement = select(
        POIBusynessForecast.hour_of_day,
        POIBusynessForecast.busyness_pct
        ).where(
            POIBusynessForecast.poi_id == id,
            POIBusynessForecast.day_of_week == day
        ).order_by(
            POIBusynessForecast.hour_of_day
        )
    result = db.execute(statement).all()

    return [
        {
            "hour_of_day": row[0],
            "busyness": row[1]
            }
         for row in result
         ]

def get_busyness_for_trip(poi_ids, trip_days: list[int], db: Session):
    """Return average predicted busyness for each POI across the selected trip days."""

    statement = select(
        POIBusynessForecast.poi_id,
        func.avg(POIBusynessForecast.busyness_pct).label("avg_busyness_pct"),
    ).where(
        POIBusynessForecast.poi_id.in_(poi_ids),
        POIBusynessForecast.day_of_week.in_(trip_days)
    ).group_by(
        POIBusynessForecast.poi_id
    ).order_by(
        func.avg(POIBusynessForecast.busyness_pct)
        )
    results = db.execute(statement).all()
    return [
    {
        "poi_id": row.poi_id,
        "avg_busyness_pct": row.avg_busyness_pct
    }
    for row in results
]

def _stop_key(stop) -> tuple:
    """What makes a stop the same stop: the place, the day and the time slot."""
    return (stop.poi_id, stop.day_number, stop.visit_date, stop.slot_start, stop.position)


def is_same_itinerary(saved: SavedItinerary, itinerary: ItineraryResponse) -> bool:
    """True when `saved` already holds this generated itinerary (name, dates and stops)."""
    return (
        saved.name == itinerary.trip_name
        and saved.start_date == itinerary.start_date
        and saved.end_date == itinerary.end_date
        and sorted(map(_stop_key, saved.stops)) == sorted(map(_stop_key, itinerary.stops))
    )


def save_itinerary_for_user(itinerary: ItineraryResponse, db: Session, user: uuid.UUID):
    """Save a generated itinerary and its stops for an authenticated user.

    Saving is idempotent: posting the same itinerary again (a second click, a
    retry after a timeout, saving from another page) returns the copy the user
    already has instead of creating a duplicate.
    """
    candidates = db.scalars(
        select(SavedItinerary).where(
            SavedItinerary.user_id == user,
            SavedItinerary.name == itinerary.trip_name,
            SavedItinerary.start_date == itinerary.start_date,
            SavedItinerary.end_date == itinerary.end_date,
        )
    )
    for saved in candidates:
        if is_same_itinerary(saved, itinerary):
            return saved

    itinerary_entry = SavedItinerary(
        user_id=user,
        name=itinerary.trip_name,
        start_date=itinerary.start_date,
        end_date=itinerary.end_date,
        accessibility_requirements=itinerary.accessibility,
        warning=itinerary.warning
    )

    db.add(itinerary_entry)
    db.flush()

    for stop in itinerary.stops:
        db.add(
            ItineraryStop(
                itinerary_id=itinerary_entry.id,
                poi_id= stop.poi_id,
                day_number=stop.day_number,
                visit_date=stop.visit_date,
                slot=stop.slot,
                slot_start=stop.slot_start,
                slot_end=stop.slot_end,
                position=stop.position,
                crowd_level=stop.crowd_level,
                flags=stop.flags,
                busyness_for_day=[item.model_dump() for item in stop.busyness_for_day],
                hero_image_url=stop.hero_image_url,
        ))

    db.commit()
    db.refresh(itinerary_entry)

    return itinerary_entry

def serialize_itinerary(itinerary: SavedItinerary):
    """Convert a saved itinerary database object into a frontend-ready dictionary."""

    return {
        "itinerary_id": str(itinerary.id),
        "trip_name" : itinerary.name,
        "start_date" : itinerary.start_date,
        "end_date": itinerary.end_date,
        "warning": itinerary.warning,
        "stops": [
            {
                "stop_id": str(stop.id),
                "poi_id": stop.poi_id,
                "poi_name": stop.poi.name,
                "slug": stop.poi.slug,
                "day_number": stop.day_number,
                "visit_date": stop.visit_date,
                "slot": stop.slot,
                "slot_start": stop.slot_start,
                "slot_end": stop.slot_end,
                "position": stop.position,
                "poi_type": stop.poi.type,
                "crowd_level": stop.crowd_level,
                "hero_image_url": poi_photo_url(stop.poi.slug, stop.poi.google_place_id) or stop.hero_image_url or "",
                "borough": stop.poi.borough,
                "neighborhood": stop.poi.neighborhood,
                "suggested_duration": stop.poi.recommended_duration_min,
                "accessibility": stop.poi.accessibility_labels,
                "flags": stop.flags,
                "busyness_for_day": stop.busyness_for_day
            } for stop in itinerary.stops
        ]
    }

def get_saved_itineraries(db: Session, user: uuid.UUID):
    """Return all saved itineraries belonging to a specified user."""

    statement = select(SavedItinerary).where(SavedItinerary.user_id == user)
    all_itineraries = db.execute(statement).scalars().all()

    return [{
        "itinerary_id": str(itinerary.id),
        "trip_name": itinerary.name,
        "start_date": itinerary.start_date,
        "end_date": itinerary.end_date,
        "number_of_places": len(itinerary.stops),
        "hero_image_url": (
            poi_photo_url(itinerary.stops[0].poi.slug, itinerary.stops[0].poi.google_place_id)
            or itinerary.stops[0].hero_image_url
        ) if len(itinerary.stops) > 0 else None
    }
    for itinerary in all_itineraries]

def get_saved_itinerary(itinerary_id, db: Session, user: uuid.UUID):
    """Retrieve and serialize a saved itinerary belonging to the user."""

    statement = select(SavedItinerary).where(
        SavedItinerary.id == itinerary_id,
        SavedItinerary.user_id == user
        )
    itinerary = db.execute(statement).scalar_one_or_none()

    if not itinerary:
        raise ItineraryNotFound
    
    return serialize_itinerary(itinerary)

def unsave_itinerary_for_user(itinerary_id, db: Session, user: uuid.UUID):
    """Delete a saved itinerary belonging to the authenticated user."""

    statement = select(SavedItinerary).where(
        SavedItinerary.id == itinerary_id,
        SavedItinerary.user_id == user
        )
    itinerary = db.execute(statement).scalar_one_or_none()

    if not itinerary:
        raise ItineraryNotFound
    
    db.delete(itinerary)
    db.commit()

def create_new_request(itinerary_id, slug: str | None, stop_id: str | None, db: Session, user):
    """Create an itinerary request by adding or removing a POI from a saved itinerary."""

    statement = select(SavedItinerary).where(
        SavedItinerary.id == itinerary_id,
        SavedItinerary.user_id == user
        )
    itinerary = db.execute(statement).scalar_one_or_none()

    if itinerary is None:
        raise ItineraryNotFound

    trip_name = itinerary.name
    start_date = itinerary.start_date
    end_date = itinerary.end_date
    accessibility_labels = itinerary.accessibility_requirements 

    # adding a stop
    if slug:
        slug_found = get_poi_by_slug(slug, db)
        if not slug_found:
            raise POINotFoundError
        
        pois = [stop.poi.slug for stop in itinerary.stops]
        pois.append(slug)

    # removing a stop
    elif stop_id:
        stop_found = False
        for stop in itinerary.stops:
            if str(stop.id) == stop_id:
                stop_found = True
        if not stop_found:
            raise StopNotFound

        pois = [stop.poi.slug for stop in itinerary.stops if str(stop.id) != stop_id]

    request = ItineraryRequest(
        trip_name=trip_name,
        trip_dates=[start_date, end_date],
        pois=pois,
        accessibility=accessibility_labels
    )

    return request

def update_saved_itinerary(new_itinerary, itinerary_id, db: Session, user: uuid.UUID):
    """Replace the stops and warning of an existing saved itinerary."""

    statement = select(SavedItinerary).where(
        SavedItinerary.id == itinerary_id,
        SavedItinerary.user_id == user
        )
    itinerary = db.execute(statement).scalar_one_or_none()

    for stop in itinerary.stops:
        db.delete(stop)

    db.flush()

    for new_stop in new_itinerary["stops"]:
        itinerary.stops.append(
            ItineraryStop(
                itinerary_id=itinerary.id,
                poi_id=new_stop["poi_id"],
                day_number=new_stop["day_number"],
                visit_date=new_stop["visit_date"],
                slot=new_stop["slot"],
                slot_start=new_stop["slot_start"],
                slot_end=new_stop["slot_end"],
                position=new_stop["position"],
                crowd_level=new_stop["crowd_level"],
                flags=new_stop["flags"],
                busyness_for_day=new_stop["busyness_for_day"],
                hero_image_url=new_stop["hero_image_url"],
            ))
        
    itinerary.warning = new_itinerary["warning"]
    db.commit()

    return serialize_itinerary(itinerary)
    






    
    
