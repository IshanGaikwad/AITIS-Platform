"""Invitation service — create, accept, revoke, and list invitations."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import Invitation, InvitationStatus
from app.models.tenant import OrganizationMembership, ProjectMembership, Role
from app.schemas.invitation import InvitationCreate


def _generate_token() -> str:
    """Generate a cryptographically secure invitation token."""
    return secrets.token_urlsafe(32)


async def create_invitation(
    db: AsyncSession,
    inviter_id: uuid.UUID,
    data: InvitationCreate,
) -> Invitation:
    """Create a single invitation."""
    token = _generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)

    invitation = Invitation(
        email=data.email,
        token=token,
        status=InvitationStatus.pending.value,
        invited_by=inviter_id,
        organization_id=data.organization_id,
        project_id=data.project_id,
        role=data.role,
        expires_at=expires_at,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return invitation


async def create_bulk_invitations(
    db: AsyncSession,
    inviter_id: uuid.UUID,
    emails: list[str],
    role: str,
    organization_id: uuid.UUID,
    project_id: Optional[uuid.UUID],
    expires_in_days: int = 7,
) -> list[Invitation]:
    """Create multiple invitations at once."""
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
    invitations = []

    for email in emails:
        token = _generate_token()
        invitation = Invitation(
            email=email,
            token=token,
            status=InvitationStatus.pending.value,
            invited_by=inviter_id,
            organization_id=organization_id,
            project_id=project_id,
            role=role,
            expires_at=expires_at,
        )
        db.add(invitation)
        invitations.append(invitation)

    await db.commit()
    for inv in invitations:
        await db.refresh(inv)
    return invitations


async def accept_invitation(
    db: AsyncSession,
    token: str,
    user_id: uuid.UUID,
) -> Invitation:
    """Accept an invitation — creates org/project memberships."""
    result = await db.execute(
        select(Invitation).where(
            and_(
                Invitation.token == token,
                Invitation.status == InvitationStatus.pending.value,
            )
        )
    )
    invitation = result.scalars().first()

    if invitation is None:
        raise ValueError("Invitation not found or already used")

    now = datetime.now(timezone.utc)
    if invitation.expires_at < now:
        invitation.status = InvitationStatus.expired.value
        await db.commit()
        await db.refresh(invitation)
        raise ValueError("Invitation has expired")

    # Create org membership
    existing_org = await db.execute(
        select(OrganizationMembership).where(
            and_(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == invitation.organization_id,
            )
        )
    )
    if existing_org.scalars().first() is None:
        org_membership = OrganizationMembership(
            user_id=user_id,
            organization_id=invitation.organization_id,
            role=invitation.role,
        )
        db.add(org_membership)

    # Create project membership if project was specified
    if invitation.project_id:
        existing_ws = await db.execute(
            select(ProjectMembership).where(
                and_(
                    ProjectMembership.user_id == user_id,
                    ProjectMembership.project_id == invitation.project_id,
                )
            )
        )
        if existing_ws.scalars().first() is None:
            ws_membership = ProjectMembership(
                user_id=user_id,
                project_id=invitation.project_id,
                role=invitation.role,
            )
            db.add(ws_membership)

    # Mark invitation as accepted
    invitation.status = InvitationStatus.accepted.value
    invitation.accepted_at = now
    invitation.accepted_by = user_id

    await db.commit()
    await db.refresh(invitation)
    return invitation


async def revoke_invitation(
    db: AsyncSession,
    invitation_id: uuid.UUID,
    inviter_id: uuid.UUID,
) -> Invitation:
    """Revoke a pending invitation."""
    result = await db.execute(
        select(Invitation).where(Invitation.id == invitation_id)
    )
    invitation = result.scalars().first()

    if invitation is None:
        raise ValueError("Invitation not found")
    if invitation.invited_by != inviter_id:
        raise PermissionError("Only the inviter can revoke this invitation")
    if invitation.status != InvitationStatus.pending.value:
        raise ValueError(f"Cannot revoke invitation with status '{invitation.status}'")

    invitation.status = InvitationStatus.revoked.value
    await db.commit()
    await db.refresh(invitation)
    return invitation


async def list_organization_invitations(
    db: AsyncSession,
    organization_id: uuid.UUID,
    status: Optional[str] = None,
) -> list[Invitation]:
    """List all invitations for an organization, optionally filtered by status."""
    query = select(Invitation).where(Invitation.organization_id == organization_id)
    if status:
        query = query.where(Invitation.status == status)
    query = query.order_by(Invitation.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_pending_invitation_by_email(
    db: AsyncSession,
    email: str,
    organization_id: uuid.UUID,
) -> Optional[Invitation]:
    """Check if a pending invitation already exists for this email+org."""
    result = await db.execute(
        select(Invitation).where(
            and_(
                Invitation.email == email,
                Invitation.organization_id == organization_id,
                Invitation.status == InvitationStatus.pending.value,
            )
        )
    )
    return result.scalars().first()


async def expire_stale_invitations(db: AsyncSession) -> int:
    """Mark all expired-but-still-pending invitations as expired. Returns count."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Invitation).where(
            and_(
                Invitation.status == InvitationStatus.pending.value,
                Invitation.expires_at < now,
            )
        )
    )
    stale = result.scalars().all()
    for inv in stale:
        inv.status = InvitationStatus.expired.value
    await db.commit()
    return len(stale)
