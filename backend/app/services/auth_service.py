from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError
from app.core.security.passwords import verify_password, verify_token
from app.core.security.tokens import create_access_token, decode_token
from app.models.user_model import UserIdentity
from app.services.session_service import (
    create_session,
    get_session_by_sid,
    rotate_session,
)
from app.services.user_services import (
    create_user_by_google,
    get_user_by_email,
    get_user_by_google_sub,
)

INVALID_CREDENTIALS="Incorrect email or password. Please try again."
INVALID_TOKEN="Invalid or expired refresh token."
UNVERIFIED_EMAIL="Email is not verified. Please try again."


def authenticate_user(email: str, password: str, db: Session):
    """
    Authenticate a user and create access and refresh tokens.

    Verifies the supplied credentials and, when successful, creates a new
    refresh-token session and returns the authentication tokens and user
    information.

    Args:
        email: User's email address.
        password: User's plaintext password.
        db: Database session.

    Returns:
        A dictionary containing access and refresh tokens and basic user data.

    Raises:
        AuthenticationError: If the email or password is incorrect.
    """
    existing_user = get_user_by_email(email, db)

    if existing_user is None:
        raise AuthenticationError(INVALID_CREDENTIALS)

    if existing_user.password_hash is None:
        raise AuthenticationError(INVALID_CREDENTIALS)

    password_verified, hash_update = verify_password(
        password, 
        existing_user.password_hash
    )

    if not password_verified:
        raise AuthenticationError(INVALID_CREDENTIALS)

    if hash_update:
        existing_user.password_hash = hash_update
        db.commit()

    access_token = create_access_token(existing_user.id)
    refresh_token = create_session(existing_user.id, db)

    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "display_name": existing_user.display_name,
        "accessibility": existing_user.accessibility
        }

def refresh_session(refresh_token: str, db: Session):
    """
    Refresh a user's access and refresh tokens.

    Validates the supplied refresh token and associated session before
    rotating the session and issuing a new pair of tokens.

    Args:
        refresh_token: The user's current refresh token.
        db: Database session.

    Returns:
        A dictionary containing a new access token and refresh token.

    Raises:
        AuthenticationError: If the refresh token is invalid, expired,
            revoked, or is not a refresh token.
    """
    payload = decode_token(refresh_token)

    if payload.get("type") != "refresh":
        raise AuthenticationError(INVALID_TOKEN)

    existing_session = get_session_by_sid(payload.get("sid"), db)

    if (
        not existing_session
        or existing_session.revoked
        or not verify_token(refresh_token, existing_session.refresh_token_hash)
    ):
        raise AuthenticationError(INVALID_TOKEN)

    user_id = existing_session.user_id

    new_access_token = create_access_token(user_id)
    new_refresh_token = rotate_session(existing_session.id, user_id, db)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token
    }


def login_with_google(userinfo: dict, db: Session) -> dict: 

    if userinfo.get("email_verified") is not True:
        raise AuthenticationError(UNVERIFIED_EMAIL)
    is_new_user = False
    # if old user is using google Oauth
    
    google_sub = userinfo["sub"]
    google_user = get_user_by_google_sub(google_sub, db)
    
    if google_user is None:
        google_email = userinfo["email"].lower().strip()
        local_user = get_user_by_email(google_email, db)
        if local_user is None:
            name = userinfo.get("name")
            name = name.strip() if name else name 
            display_name = name if name else google_email.split("@")[0]
            display_name = display_name[:50]
            try:
                is_new_user = True
                user = create_user_by_google(google_email, display_name, google_sub, db)
            except IntegrityError:
                db.rollback()
                user = get_user_by_google_sub(google_sub, db)
                is_new_user = False
                if user is None:
                    raise 

        else:
            local_user.identities.append(UserIdentity(provider="google", provider_user_id=userinfo["sub"]))
            db.commit()
            user = local_user
    else:
        user = google_user

    new_access_token = create_access_token(user.id)
    new_refresh_token = create_session(user.id, db)


    return {
        "access_token" : new_access_token,
        "refresh_token" : new_refresh_token,
        "display_name" : user.display_name,
        "accessibility" : user.accessibility,
        "is_new_user" : is_new_user,
    }
