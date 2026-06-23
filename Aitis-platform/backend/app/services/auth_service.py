from typing import Optional
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, User as UserSchema


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_provider_id(db: Session, provider: str, provider_id: str) -> Optional[User]:
    return db.query(User).filter(
        User.provider == provider,
        User.provider_id == provider_id
    ).first()


def create_user(db: Session, user: UserCreate) -> User:
    db_user = User(
        email=user.email,
        name=user.name,
        picture=user.picture,
        provider=user.provider,
        provider_id=user.provider_id,
        is_active=user.is_active,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_or_create_user_from_oauth(
    db: Session,
    provider: str,
    provider_id: str,
    email: str,
    name: Optional[str] = None,
    picture: Optional[str] = None
) -> User:
    """Get existing user or create new one from OAuth2 data"""
    # Try to find existing user by provider and provider_id
    user = get_user_by_provider_id(db, provider, provider_id)
    if user:
        # Update user info if changed
        if name and user.name != name:
            user.name = name
        if picture and user.picture != picture:
            user.picture = picture
        db.commit()
        db.refresh(user)
        return user

    # Try to find existing user by email (account linking)
    user = get_user_by_email(db, email)
    if user:
        # Link the OAuth account to existing user
        user.provider = provider
        user.provider_id = provider_id
        if name and not user.name:
            user.name = name
        if picture and not user.picture:
            user.picture = picture
        db.commit()
        db.refresh(user)
        return user

    # Create new user
    user_data = UserCreate(
        email=email,
        name=name,
        picture=picture,
        provider=provider,
        provider_id=provider_id,
    )
    return create_user(db, user_data)


def create_access_token_for_user(user: User) -> str:
    """Create JWT access token for user"""
    token_data = {
        "sub": user.email,
        "user_id": user.id,
        "provider": user.provider,
    }
    return create_access_token(token_data)