"""Resolve fresh Google Places photo URLs on demand, cached in Postgres.

Google Places (New) photo media URLs (lh3.googleusercontent.com/place-photos/...)
are short-lived by spec, so storing them in the DB permanently means they rot. We
keep only the stable google_place_id per POI and resolve a fresh URL, caching the
result in poi_photo_cache.

The cache lives in Postgres rather than process memory on purpose: Render's free
tier sleeps and restarts constantly, which would wipe an in-memory cache and send
us back to Google far too often. A shared DB row means the first viewer of a POI
within the TTL pays the two Google calls and every other viewer is served free.

Resolving a miss costs two calls:
  1. Place Details (photos field mask) -> the first photo's resource name.
  2. Place Photo media (skipHttpRedirect) -> a fresh photoUri as JSON, so the API
     key is never exposed in a browser-visible redirect.
"""
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.poi_model import POIPhotoCache

_PLACES_BASE = "https://places.googleapis.com/v1"
_MAX_WIDTH_PX = 800
_TIMEOUT_S = 8.0

# How long a cached URL is trusted before we re-resolve. Kept well under the
# lifetime of a Google media URL so we rarely serve one that has expired, while
# still collapsing repeat views to a single resolve per POI per window.
_CACHE_TTL = timedelta(hours=6)


def poi_photo_url(slug: str | None, google_place_id: str | None) -> str | None:
    """Absolute URL of our photo proxy for a POI, or None if it can't serve one.

    Points a hero image at GET /api/pois/{slug}/photo so the link is durable and
    self-healing rather than a stored Google URL that expires. Absolute (built
    from PUBLIC_API_URL) because the iOS client does URL(string:) with no base.
    None when the POI has no place_id to resolve from or no key is configured, so
    callers fall back to whatever they had stored. Pure string building — no DB or
    network — so it is cheap to call while serialising lists of POIs or stops.
    """
    if not slug or not google_place_id or not settings.GOOGLE_PLACES_API_KEY:
        return None
    return f"{settings.PUBLIC_API_URL.rstrip('/')}/api/pois/{slug}/photo"


def get_photo_url(place_id: str | None, db: Session) -> str | None:
    """Return a currently-valid image URL for a place, or None if unavailable.

    None (rather than an exception) on every failure path: no key configured, no
    place_id, the place has no photos, or Google is unreachable with nothing
    cached. Callers treat None as "no photo" and fall back to a placeholder.
    """
    if not place_id or not settings.GOOGLE_PLACES_API_KEY:
        return None

    cached = db.get(POIPhotoCache, place_id)
    if cached and cached.fetched_at > datetime.now(UTC) - _CACHE_TTL:
        return cached.photo_uri

    fresh = _resolve(place_id)
    if fresh:
        _store(db, place_id, fresh)
        return fresh["photo_uri"]

    # Stale-if-error: Google failed but we have an old row. A possibly-expired URL
    # is still a better bet than a guaranteed placeholder, and the client falls
    # back on its own if the image 404s.
    return cached.photo_uri if cached else None

def get_photo_attribution(place_id: str | None, db: Session) -> dict | None:

    if not place_id or not settings.GOOGLE_PLACES_API_KEY:
        return None

    cached = db.get(POIPhotoCache, place_id)
    if cached and cached.fetched_at > datetime.now(UTC) - _CACHE_TTL and cached.author_name is not None:
        return {
            "author_name": cached.author_name,
            "author_uri": cached.author_uri,
            "google_maps_uri": cached.google_maps_uri
        }

    fresh = _resolve(place_id)
    if fresh:
        _store(db, place_id, fresh)
        return {
            "author_name": fresh["author_name"],
            "author_uri": fresh["author_uri"],
            "google_maps_uri": fresh["google_maps_uri"]
        }

    return {
            "author_name": cached.author_name,
            "author_uri": cached.author_uri,
            "google_maps_uri": cached.google_maps_uri
        } if cached else None
    

def _store(db: Session, place_id: str, photo_details: dict) -> None:
    now = datetime.now(UTC)
    # Upsert: concurrent misses for the same place_id must not collide on the PK.
    statement = insert(POIPhotoCache).values(
        place_id=place_id, 
        photo_uri=photo_details["photo_uri"], 
        author_name = photo_details["author_name"],
        author_uri = photo_details["author_uri"],
        google_maps_uri = photo_details["google_maps_uri"],
        fetched_at=now
    )
    statement = statement.on_conflict_do_update(
        index_elements=[POIPhotoCache.place_id],
        set_={"photo_uri":photo_details["photo_uri"], 
              "author_name":photo_details["author_name"], 
              "author_uri":photo_details["author_uri"],
              "google_maps_uri":photo_details["google_maps_uri"],
              "fetched_at":now}
    )
    db.execute(statement)
    db.commit()


def _resolve(place_id: str) -> dict | None:
    headers = {"X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY}
    try:
        with httpx.Client(timeout=_TIMEOUT_S) as client:
            details = client.get(
                f"{_PLACES_BASE}/places/{place_id}",
                headers={**headers, "X-Goog-FieldMask": "photos"},
            )
            details.raise_for_status()
            photos = details.json().get("photos") or []
            if not photos:
                return None

            author = (photos[0].get("authorAttributions") or [{}])[0]
            author_name = author.get("displayName")
            author_uri = author.get("uri")
            google_maps_uri = photos[0].get("googleMapsUri") or None
            media = client.get(
                f"{_PLACES_BASE}/{photos[0]['name']}/media",
                headers=headers,
                params={"maxWidthPx": _MAX_WIDTH_PX, "skipHttpRedirect": "true"},
            )
            media.raise_for_status()
            return {
                "photo_uri": media.json().get("photoUri"),
                "author_name": author_name,
                "author_uri": author_uri,
                "google_maps_uri": google_maps_uri
            }
                
                
                
    except (httpx.HTTPError, KeyError, ValueError):
        return None

