"""Async auth service — user lookup, OAuth2 user provisioning, JWT token creation."""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from app.models.tenant import Organization, OrganizationMembership, Role
from app.schemas.user import UserCreate


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def get_user_by_provider_id(db: AsyncSession, provider: str, provider_id: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.provider == provider, User.provider_id == provider_id)
    )
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID | str | None) -> Optional[User]:
    if user_id is None:
        return None
    if not isinstance(user_id, uuid.UUID):
        try:
            user_id = uuid.UUID(str(user_id))
        except ValueError:
            return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    db_user = User(
        email=user.email,
        name=user.name,
        picture=user.picture,
        provider=user.provider,
        provider_id=user.provider_id,
        is_active=user.is_active,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_or_create_user_from_oauth(
    db: AsyncSession,
    provider: str,
    provider_id: str,
    email: str,
    name: Optional[str] = None,
    picture: Optional[str] = None,
) -> User:
    """Get existing user or create new one from OAuth2 data.

    On first login, auto-creates a personal Organization with org_owner role
    so the user always has at least one org context.
    """
    # Try to find existing user by provider and provider_id
    user = await get_user_by_provider_id(db, provider, provider_id)
    if user:
        # Update user info if changed
        changed = False
        if name and user.name != name:
            user.name = name
            changed = True
        if picture and user.picture != picture:
            user.picture = picture
            changed = True
        if changed:
            await db.commit()
            await db.refresh(user)
        return user

    # Try to find existing user by email (account linking)
    user = await get_user_by_email(db, email)
    if user:
        # Link the OAuth account to existing user
        user.provider = provider
        user.provider_id = provider_id
        if name and not user.name:
            user.name = name
        if picture and not user.picture:
            user.picture = picture
        await db.commit()
        await db.refresh(user)
        return user

    # Create new user
    user_data = UserCreate(
        email=email,
        name=name,
        picture=picture,
        provider=provider,
        provider_id=provider_id,
    )
    user = await create_user(db, user_data)

    # Auto-create personal organization for new user
    org = Organization(
        name=f"{name or email.split('@')[0]}'s Organization",
        slug=f"{(name or email.split('@')[0]).lower().replace(' ', '-')}-{user.id.hex[:8]}",
        settings={},
    )
    db.add(org)
    await db.flush()

    membership = OrganizationMembership(
        user_id=user.id,
        organization_id=org.id,
        role=Role.org_owner,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(user)

    return user


async def create_tokens_for_user(db: AsyncSession, user: User, organization_id: Optional[uuid.UUID] = None, project_id: Optional[uuid.UUID] = None, role: Optional[str] = None) -> dict:
    """Create JWT access + refresh tokens for user with optional tenant context."""
    token_data = {
        "sub": str(user.id),
        "user_id": str(user.id),
        "email": user.email or "",
        "name": user.name or "",
        "picture": user.picture or "",
        "provider": user.provider,
    }
    if organization_id:
        token_data["organization_id"] = str(organization_id)
    if project_id:
        token_data["project_id"] = str(project_id)
    if role:
        token_data["role"] = role

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
