"""Auth API — OAuth2 login, callback, token refresh, project selection."""

import secrets
import uuid
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.oauth2 import oauth2_provider
from app.core.security import (
    get_current_user,
    verify_token,
    _role_value,
)
from app.db.database import get_db
from app.models.tenant import Organization, OrganizationMembership, Project, ProjectMembership
from app.models.user import User
from app.schemas.user import LoginResponse, Token, TokenData, UserOut, ProjectSelect
from app.services import sso_service
from app.services.auth_service import (
    create_tokens_for_user,
    get_or_create_user_from_oauth,
    get_user_by_email,
    get_user_by_id,
)

router = APIRouter()
security = HTTPBearer()


async def _get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """Extract and verify JWT token."""
    try:
        payload = verify_token(credentials.credentials)
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/demo")
async def demo_login(db: AsyncSession = Depends(get_db)):
    """Login as a fresh, isolated demo user — a real session with full access.

    Each demo entry provisions a brand-new user, organization, and project so the
    experience always starts completely empty, with no data carried over from prior
    demo sessions. Demo sessions are fully isolated from one another.
    """
    # Unique suffix makes every demo entry a distinct, empty account
    unique = uuid.uuid4().hex[:12]

    user = await get_or_create_user_from_oauth(
        db=db,
        provider="demo",
        provider_id=f"demo-{unique}",
        email=f"demo+{unique}@aitis.io",
        name="Demo User",
        picture="",
    )

    # Personal organization is auto-created on first login
    membership_result = await db.execute(
        select(OrganizationMembership).where(OrganizationMembership.user_id == user.id)
    )
    membership = membership_result.scalars().first()
    if not membership:
        raise HTTPException(status_code=500, detail="Demo user organization not found")

    org_id = membership.organization_id

    # No project is auto-created — the demo user starts with an empty organization
    # and creates their own project from the switcher. The token therefore carries
    # the org context (org_owner) but no project claim yet.
    tokens = await create_tokens_for_user(
        db, user,
        organization_id=org_id,
        role=_role_value(membership.role),
    )
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer",
    }


@router.get("/login")
async def login(provider: Optional[str] = None):
    """Initiate OAuth2 login flow for the given provider.

    The provider is encoded into `state` (format ``provider:<name>:<nonce>``) so the
    callback can recover which provider issued the code — and so the frontend can
    parse it back after the redirect.
    """
    resolved = (provider or oauth2_provider.provider or "").lower()
    if resolved == "sso":
        # Organization SSO (SAML/OIDC/LDAP) is configured per-organization under the
        # SSO admin subsystem, not via the global OAuth2 flow.
        raise HTTPException(
            status_code=400,
            detail="Organization SSO must be configured by your administrator before use.",
        )
    state = f"provider:{resolved}:{secrets.token_urlsafe(24)}"
    auth_url = oauth2_provider.get_authorization_url(state, resolved)
    return {"authorization_url": auth_url, "state": state}


@router.post("/callback")
async def oauth2_callback(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """Handle OAuth2 callback — exchange authorization code for JWT tokens.

    Called by the frontend after the OAuth2 provider redirects to /auth/callback
    with a code. The frontend extracts the code and POSTs it here.
    """
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Resolve which provider issued this code: prefer the explicit field, then the
    # provider encoded in state (provider:<name>:<nonce>), then the server default.
    provider = payload.get("provider")
    state = payload.get("state") or ""
    if not provider and state.startswith("provider:"):
        parts = state.split(":")
        if len(parts) >= 2 and parts[1]:
            provider = parts[1]
    provider = (provider or oauth2_provider.provider or "").lower()

    # Organization SSO (OIDC) follows a separate, DB-backed provider flow.
    if provider == "sso":
        user = await sso_service.complete_sso_callback(db, code, state)
        tokens = await create_tokens_for_user(db, user)
        return {**tokens, "user": UserOut.model_validate(user)}

    try:
        token_data = await oauth2_provider.exchange_code_for_token(code, provider)
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")

        user_info = await oauth2_provider.get_user_info(access_token, provider)

        user = await get_or_create_user_from_oauth(
            db=db,
            provider=provider,
            provider_id=user_info.get("sub") or user_info.get("id"),
            email=user_info.get("email"),
            name=user_info.get("name"),
            picture=user_info.get("picture"),
        )

        tokens = await create_tokens_for_user(db, user)

        response_payload: Dict[str, Any] = {
            **tokens,
            "user": UserOut.model_validate(user),
        }

        if provider == "atlassian":
            response_payload["atlassian_access_token"] = access_token

        return response_payload

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth2 authentication failed: {str(e)}",
        )


@router.get("/me", response_model=UserOut)
async def get_current_user_profile(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user profile."""
    user_id = current_user.get("user_id")
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user)


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Exchange a valid refresh token for a new access token."""
    payload = verify_token(credentials.credentials)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id_str = payload.get("user_id")
    user = await get_user_by_id(db, uuid.UUID(user_id_str) if user_id_str else None)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    org_id = payload.get("organization_id")
    ws_id = payload.get("project_id")
    role = payload.get("role")

    tokens = await create_tokens_for_user(
        db, user,
        organization_id=uuid.UUID(org_id) if org_id else None,
        project_id=uuid.UUID(ws_id) if ws_id else None,
        role=role,
    )
    return Token(access_token=tokens["access_token"], refresh_token=credentials.credentials)


@router.post("/select-project", response_model=LoginResponse)
async def select_project(
    payload: ProjectSelect,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Select active project — reissues JWT with new project/role claims."""
    user_id = current_user.get("user_id")

    # Verify membership
    result = await db.execute(
        select(ProjectMembership)
        .where(
            ProjectMembership.user_id == user_id,
            ProjectMembership.project_id == payload.project_id,
        )
    )
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this project")

    # Get project's org
    ws_result = await db.execute(select(Project).where(Project.id == payload.project_id))
    project = ws_result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    user = await get_user_by_id(db, user_id)
    tokens = await create_tokens_for_user(
        db, user,
        organization_id=project.organization_id,
        project_id=payload.project_id,
        role=_role_value(membership.role),
    )
    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        user=UserOut.model_validate(user),
    )