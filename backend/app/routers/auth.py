from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuthError

from app.core.exceptions import AuthenticationError, UserAlreadyExists
from app.database import get_db
from app.schemas.auth import (
    LogoutRequest,
    LogoutResponse,
    MobileLoginResponse,
    MobileRefreshResponse,
    RefreshTokenRequest,
    UserLogin,
    WebLoginResponse,
    WebRefreshResponse,
    MeResponse
)
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import authenticate_user, refresh_session, login_with_google
from app.services.session_service import revoke_session
from app.services.user_services import create_user, get_user_by_id
from app.core.config import settings
from app.core.security.oauth import oauth
from app.dependencies.auth import authorise_access

GOOGLE_FAILED_REDIRECT = "/?auth_error=google_failed"
GOOGLE_UNVERIFIED_REDIRECT = "/?auth_error=google_unverified"

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    try:
        return create_user(user, db)

    except UserAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=str(e)
            )
    
    
@router.post("/login", response_model=WebLoginResponse)
def login_for_web(data: UserLogin, db: Session = Depends(get_db), response: Response = None):
    try:
        login_response = authenticate_user(data.email, data.password, db)

        _set_auth_cookies(response, login_response)

        return WebLoginResponse(
            message="Login successful",
            display_name=login_response["display_name"],
            accessibility=login_response["accessibility"]
        )
    
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    
    
@router.post("/mobile/login", response_model=MobileLoginResponse)
def login_for_mobile(data: UserLogin, db: Session = Depends(get_db)):
    try:
        login_response = authenticate_user(data.email, data.password, db)

        return MobileLoginResponse(
            access_token=login_response["access_token"],
            refresh_token=login_response["refresh_token"],
            display_name=login_response["display_name"],
            accessibility=login_response["accessibility"]
        )
    
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/refresh", response_model=WebRefreshResponse)
def refresh_session_for_web(response: Response, refresh_token: str | None = Cookie(None), db: Session = Depends(get_db)):
    try:
        if not refresh_token:
            raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorised for this resource."
        )

        tokens = refresh_session(refresh_token, db)

        _set_auth_cookies(response, tokens)

        return WebRefreshResponse(
            message="Session refreshed successfully."
        )
    
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please log in again."
        )


@router.post("/mobile/refresh", response_model=MobileRefreshResponse)
def refresh_session_for_mobile(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        tokens = refresh_session(request.refresh_token, db)
        return MobileRefreshResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"]
        )
    
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please log in again."
        )
    

@router.post("/logout", response_model=LogoutResponse)
def logout_for_web(response: Response, refresh_token: str | None = Cookie(None), db: Session = Depends(get_db)):
    try:
        if not refresh_token:
            return LogoutResponse(
                message="Session ended."
            )
        
        revoke_session(refresh_token, db)
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return LogoutResponse(
            message="Session ended."
        )
    
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    
@router.post("/mobile/logout", response_model=LogoutResponse)
def logout_for_mobile(request: LogoutRequest, db: Session = Depends(get_db)):
    try:
        revoke_session(request.refresh_token, db)
        return LogoutResponse(
            message="Session ended."
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

def _require_google():
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google login is not configured.",
        )

@router.get("/google/login")
async def google_login(request: Request):
    _require_google()
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


def _set_auth_cookies(response: Response, tokens: dict):
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="lax"
        )
        
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="lax"
        )
    
@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    _require_google()
    try:
        token = await oauth.google.authorize_access_token(request)   
    except OAuthError:
        return RedirectResponse(GOOGLE_FAILED_REDIRECT, status_code=status.HTTP_302_FOUND)
    userinfo = token["userinfo"]
    try:
        login_response = await run_in_threadpool(login_with_google, userinfo, db)
    except AuthenticationError:
        return RedirectResponse(GOOGLE_UNVERIFIED_REDIRECT, status_code=status.HTTP_302_FOUND)
    
    target = "/welcome" if login_response["is_new_user"] else "/"
    redirect_response = RedirectResponse(target, status_code=status.HTTP_302_FOUND)
    _set_auth_cookies(redirect_response, login_response)

    return redirect_response
    
@router.get("/me", response_model=MeResponse)
def get_me(user_id: str = Depends(authorise_access), db: Session = Depends(get_db)):
    user = get_user_by_id(user_id, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in again."
        )

    return MeResponse(
        email=user.email,
        display_name=user.display_name,
        accessibility=user.accessibility,
    )
