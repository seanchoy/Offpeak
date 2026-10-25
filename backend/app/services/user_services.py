"""Operations for user account management."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import UserAlreadyExists
from app.core.security.passwords import hash_password
from app.models.user_model import User, UserIdentity
from app.schemas.user import UserCreate


def get_user_by_email(email: str, db: Session):
    """
    Retrieve a user by email address.

    Email input is normalised by trimming whitespace and converting
    it to lowercase before querying.
    """
    normalised_email = email.lower().strip()
    result = db.execute(select(User).where(User.email == normalised_email))
    return result.scalar_one_or_none()

def get_user_by_google_sub(google_sub: str, db: Session):
    result = db.execute(select(UserIdentity).where(UserIdentity.provider == "google", UserIdentity.provider_user_id == google_sub))
    identity = result.scalar_one_or_none()
    return identity.user if identity is not None else None


def get_user_by_id(user_id, db: Session):
    """Retrieve a user by their unique identifier."""

    statement = select(User).where(
        User.id == user_id
    )
    return db.execute(statement).scalar_one_or_none()

def create_user(user: UserCreate, db: Session):
    """
    Create a new user account.

    Checks whether the email is already registered, hashes the user's
    password, and stores the new user in the database.
    """
    
    existing_user = get_user_by_email(user.email, db)
    if existing_user:
        raise UserAlreadyExists(
            "This email is already registered. Please log in or use a different email."
            )

    new_user = User(
        email=user.email.lower().strip(),
        password_hash=hash_password(user.password),
        display_name=user.display_name.strip(),
        accessibility=user.accessibility
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

def create_user_by_google(email, name, sub, db):
    user = User(email=email, 
                display_name=name, 
                password_hash=None, 
                accessibility=False)
    user.identities.append(UserIdentity(provider="google", provider_user_id=sub))
    db.add(user)
    db.commit()
    return user
