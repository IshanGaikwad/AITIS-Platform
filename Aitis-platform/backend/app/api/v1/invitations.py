"""Invitation API — create, accept, revoke, and list invitations."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import claim_uuid, get_current_user, require_role, require_organization_access
from app.db.database import get_db
from app.models.tenant import Role
from app.schemas.invitation import (
    InvitationAccept,
    InvitationBulkCreate,
    InvitationCreate,
    InvitationOut,
)
from app.services.invitation_service import (
    accept_invitation,
    create_bulk_invitations,
    create_invitation,
    get_pending_invitation_by_email,
    list_organization_invitations,
    revoke_invitation,
)

router = APIRouter()


@router.post("/", response_model=InvitationOut, status_code=status.HTTP_201_CREATED)
async def invite_user(
    data: InvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role=Depends(require_role(Role.org_owner, Role.administrator)),
):
    """Create an invitation to join an organization (and optionally a workspace)."""
    await require_organization_access(db, current_user, data.organization_id, (Role.org_owner, Role.administrator))
    inviter_id = claim_uuid(current_user, "user_id", "sub")
    if not inviter_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user claim")
    # Check for duplicate pending invite
    existing = await get_pending_invitation_by_email(db, data.email, data.organization_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A pending invitation already exists for {data.email} in this organization",
        )

    invitation = await create_invitation(db, inviter_id, data)
    return invitation


@router.post("/bulk", response_model=list[InvitationOut], status_code=status.HTTP_201_CREATED)
async def bulk_invite_users(
    data: InvitationBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role=Depends(require_role(Role.org_owner, Role.administrator)),
):
    """Bulk-create invitations for multiple emails."""
    await require_organization_access(db, current_user, data.organization_id, (Role.org_owner, Role.administrator))
    inviter_id = claim_uuid(current_user, "user_id", "sub")
    if not inviter_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user claim")
    invitations = await create_bulk_invitations(
        db,
        inviter_id=inviter_id,
        emails=data.emails,
        role=data.role,
        organization_id=data.organization_id,
        workspace_id=data.workspace_id,
        expires_in_days=data.expires_in_days,
    )
    return invitations


@router.post("/accept", response_model=InvitationOut)
async def accept_invite(
    data: InvitationAccept,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Accept an invitation using the token. Creates org/workspace memberships."""
    user_id = claim_uuid(current_user, "user_id", "sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user claim")
    try:
        invitation = await accept_invitation(db, data.token, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return invitation


@router.post("/{invitation_id}/revoke", response_model=InvitationOut)
async def revoke_invite(
    invitation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role=Depends(require_role(Role.org_owner, Role.administrator)),
):
    """Revoke a pending invitation."""
    inviter_id = claim_uuid(current_user, "user_id", "sub")
    if not inviter_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user claim")
    try:
        invitation = await revoke_invitation(db, invitation_id, inviter_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return invitation


@router.get("/", response_model=list[InvitationOut])
async def list_invitations(
    organization_id: uuid.UUID = Query(..., description="Filter by organization"),
    invitation_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _role=Depends(require_role(Role.org_owner, Role.administrator, Role.qa_lead)),
):
    """List invitations for an organization, optionally filtered by status."""
    await require_organization_access(
        db,
        current_user,
        organization_id,
        (Role.org_owner, Role.administrator, Role.qa_lead),
    )
    return await list_organization_invitations(db, organization_id, invitation_status)
