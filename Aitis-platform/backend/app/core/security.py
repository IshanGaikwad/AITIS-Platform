"""Security utilities — JWT with multi-tenant claims, RBAC dependencies, password hashing."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.models.tenant import OrganizationMembership, Role, WorkspaceMembership
from app.models.user import User

# ── Password hashing ────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ── JWT Token handling ──────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT access token with org/workspace/role claims."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT refresh token (longer-lived)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.refresh_token_expire_days)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_tokens_for_user(
    user_id: str,
    org_id: str | None = None,
    organization_id: str | None = None,
    workspace_id: str | None = None,
    role: str | None = None,
    email: str = "",
    name: str = "",
    picture: str = "",
    provider: str = "test",
) -> dict:
    """Create access and refresh tokens from raw JWT claims."""
    token_data = {
        "sub": user_id,
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "provider": provider,
    }
    tenant_org_id = organization_id or org_id
    if tenant_org_id:
        token_data["organization_id"] = tenant_org_id
        token_data["org_id"] = tenant_org_id
    if workspace_id:
        token_data["workspace_id"] = workspace_id
    if role:
        token_data["role"] = role

    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "token_type": "bearer",
    }


def verify_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


# ── Current-user dependency ─────────────────────────────────────────
def claim_uuid(payload: dict, *names: str) -> uuid.UUID | None:
    """Return the first valid UUID claim from payload."""
    for name in names:
        value = payload.get(name)
        if value:
            try:
                return uuid.UUID(str(value))
            except (TypeError, ValueError):
                return None
    return None


def _role_value(role) -> str:
    return role.value if hasattr(role, "value") else str(role)


async def require_organization_access(
    db: AsyncSession,
    payload: dict,
    organization_id: uuid.UUID,
    allowed_roles: tuple | list | None = None,
) -> OrganizationMembership:
    """Ensure the current user belongs to an organization, optionally by role."""
    user_id = claim_uuid(payload, "user_id", "sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user claim")

    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == organization_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied")

    if allowed_roles:
        allowed = {_role_value(role) for role in allowed_roles}
        if _role_value(membership.role) not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not permitted")
    return membership


async def require_workspace_access(
    db: AsyncSession,
    payload: dict,
    workspace_id: uuid.UUID,
    allowed_roles: tuple | list | None = None,
) -> WorkspaceMembership:
    """Ensure the current user belongs to a workspace, optionally by role."""
    user_id = claim_uuid(payload, "user_id", "sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user claim")

    result = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.workspace_id == workspace_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access denied")

    if allowed_roles:
        allowed = {_role_value(role) for role in allowed_roles}
        if _role_value(membership.role) not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not permitted")
    return membership


def enforce_tenant_claims(
    resource_org_id: uuid.UUID | None,
    resource_workspace_id: uuid.UUID | None,
    payload: dict,
) -> None:
    """Raise 403 when a resource does not match the active tenant claims."""
    request_org_id = claim_uuid(payload, "organization_id", "org_id")
    request_workspace_id = claim_uuid(payload, "workspace_id")

    if resource_org_id and request_org_id != resource_org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied")
    if resource_workspace_id and request_workspace_id != resource_workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace access denied")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> dict:
    """FastAPI dependency — validates JWT and user existence/active status, returns payload dict."""
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not an access token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == uid))
        user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return payload


# ── RBAC dependencies ──────────────────────────────────────────────
def require_role(*allowed_roles):
    """Factory that returns a FastAPI dependency enforcing one of the given roles.

    Accepts Role enum members or plain strings. Composes with get_current_user
    so is_active is always checked.

    Usage:
        @router.get("/", dependencies=[Depends(require_role("administrator", "org_owner"))])
    """
    allowed = [r.value if hasattr(r, "value") else r for r in allowed_roles]

    async def _check_role(payload: dict = Depends(get_current_user)) -> dict:
        user_role = payload.get("role")
        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' not permitted. Required: {allowed}",
            )
        return payload

    return _check_role


async def require_workspace_member(
    payload: dict = Depends(get_current_user),
) -> dict:
    """Dependency — ensures the JWT contains a workspace_id claim."""
    if not payload.get("workspace_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace context required — select a workspace first",
        )
    return payload
