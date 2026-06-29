"""Auth API — OAuth2 login, callback, token refresh, workspace selection."""

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
)
from app.db.database import get_db
from app.models.tenant import Organization, OrganizationMembership, Workspace, WorkspaceMembership
from app.models.user import User
from app.schemas.user import LoginResponse, Token, TokenData, UserOut, WorkspaceSelect
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
    """Login as demo user — creates a real session with full API access."""
    user = await get_or_create_user_from_oauth(
        db=db,
        provider="demo",
        provider_id="demo-user-001",
        email="demo@aitis.io",
        name="Demo User",
        picture="",
    )

    # Find the user's organization (auto-created on first login)
    membership_result = await db.execute(
        select(OrganizationMembership).where(OrganizationMembership.user_id == user.id)
    )
    membership = membership_result.scalars().first()
    if not membership:
        raise HTTPException(status_code=500, detail="Demo user organization not found")

    org_id = membership.organization_id

    # Get or create demo workspace
    ws_result = await db.execute(
        select(Workspace).where(Workspace.organization_id == org_id)
    )
    ws = ws_result.scalars().first()
    if not ws:
        ws = Workspace(
            name="Demo Workspace",
            slug="demo",
            organization_id=org_id,
            description="Default workspace for demo access",
        )
        db.add(ws)
        await db.flush()

        ws_member = WorkspaceMembership(
            user_id=user.id,
            workspace_id=ws.id,
            role="administrator",
        )
        db.add(ws_member)
        await db.commit()
        await db.refresh(ws)

    tokens = await create_tokens_for_user(
        db, user,
        organization_id=org_id,
        workspace_id=ws.id,
        role="administrator",
    )
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer",
    }


@router.get("/login")
async def login(provider: str = "auth0"):
    """Initiate OAuth2 login flow for the given provider."""
    state = secrets.token_urlsafe(32)
    auth_url = oauth2_provider.get_authorization_url(state)
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
    try:
        token_data = await oauth2_provider.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")

        user_info = await oauth2_provider.get_user_info(access_token)

        user = await get_or_create_user_from_oauth(
            db=db,
            provider=oauth2_provider.provider,
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

        if oauth2_provider.provider == "atlassian":
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
    ws_id = payload.get("workspace_id")
    role = payload.get("role")

    tokens = await create_tokens_for_user(
        db, user,
        organization_id=uuid.UUID(org_id) if org_id else None,
        workspace_id=uuid.UUID(ws_id) if ws_id else None,
        role=role,
    )
    return Token(access_token=tokens["access_token"], refresh_token=credentials.credentials)


@router.post("/select-workspace", response_model=LoginResponse)
async def select_workspace(
    payload: WorkspaceSelect,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Select active workspace — reissues JWT with new workspace/role claims."""
    user_id = current_user.get("user_id")

    # Verify membership
    result = await db.execute(
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.workspace_id == payload.workspace_id,
        )
    )
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    # Get workspace's org
    ws_result = await db.execute(select(Workspace).where(Workspace.id == payload.workspace_id))
    workspace = ws_result.scalars().first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    user = await get_user_by_id(db, user_id)
    tokens = await create_tokens_for_user(
        db, user,
        organization_id=workspace.organization_id,
        workspace_id=payload.workspace_id,
        role=membership.role.value,
    )
    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        user=UserOut.model_validate(user),
    )