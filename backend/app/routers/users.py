from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import ItineraryNotFound
from app.database import get_db
from app.dependencies.auth import authorise_access
from app.repositories.itinerary_repository import (
    get_saved_itineraries,
    get_saved_itinerary,
)
from app.schemas.itinerary import ItinerarySavedResponse, ItinerarySummaryResponse
from app.schemas.poi import POIDetailedResponse
from app.schemas.user import MeResponse, UpdateMeRequest
from app.services.poi_service import get_saved_pois, serialise_poi
from app.services.user_services import get_user_by_id

router = APIRouter(prefix="/api/users/me", tags=["users"])

@router.get("/saved-pois", response_model=list[POIDetailedResponse])
def display_saved_pois(db: Session = Depends(get_db), user=Depends(authorise_access)):
    return [serialise_poi(poi) for poi in get_saved_pois(db, user)]

@router.get("/saved-itineraries", response_model=list[ItinerarySummaryResponse])
def display_saved_itineraries(db: Session = Depends(get_db), user=Depends(authorise_access)):
    return get_saved_itineraries(db, user)

@router.get("/saved-itineraries/{itinerary_id}", response_model=ItinerarySavedResponse)
def display_saved_itinerary(itinerary_id, db: Session = Depends(get_db), user=Depends(authorise_access)):
    try:
        return get_saved_itinerary(itinerary_id, db, user)
    
    except ItineraryNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Itinerary not found."
        )


def _get_current_user(user_id: str, db: Session):
    user = get_user_by_id(user_id, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in again."
        )

    return user

@router.get("", response_model=MeResponse)
def get_me(user_id: str = Depends(authorise_access), db: Session = Depends(get_db)):
    user = _get_current_user(user_id, db)
    return MeResponse(
        email=user.email,
        display_name=user.display_name,
        accessibility=user.accessibility,
    )

@router.patch("", response_model=MeResponse)
def update_me(
    body: UpdateMeRequest,
    user_id: str = Depends(authorise_access),
    db: Session = Depends(get_db)):

    user = _get_current_user(user_id, db)
    user.display_name = body.display_name
    user.accessibility = body.accessibility
    db.commit()

    return MeResponse(
        email=user.email,
        display_name=user.display_name,
        accessibility=user.accessibility,
    )
    
