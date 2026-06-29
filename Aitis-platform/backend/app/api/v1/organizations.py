"""Organizations API — CRUD for Organization + membership management."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_organization_access
from app.db.database import get_db
from app.models.tenant import Organization, OrganizationMembership, Role
from app.models.user import User
from app.schemas.tenant import (
    OrganizationCreate,
    OrganizationMembershipCreate,
    OrganizationMembershipOut,
    OrganizationOut,
    OrganizationUpdate,
)
from app.services.auth_service import get_user_by_id

router = APIRouter()


@router.get("", response_model=List[OrganizationOut])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List organizations the current user belongs to."""
    user_id = current_user.get("user_id")
    result = await db.execute(
        select(Organization)
        .join(OrganizationMembership)
        .where(OrganizationMembership.user_id == user_id)
    )
    return result.scalars().all()


@router.get("/{org_id}", response_model=OrganizationOut)
async def get_organization(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    await require_organization_access(db, current_user, org_id)
    return org


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new organization. Creator becomes org_owner."""
    org = Organization(
        name=payload.name,
        slug=payload.slug,
        logo_url=payload.logo_url,
        settings=payload.settings or {},
    )
    db.add(org)
    await db.flush()

    membership = OrganizationMembership(
        user_id=current_user.get("user_id"),
        organization_id=org.id,
        role=Role.org_owner,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(org)
    return org


@router.put("/{org_id}", response_model=OrganizationOut)
async def update_organization(
    org_id: uuid.UUID,
    payload: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await require_organization_access(db, current_user, org_id, ("org_owner", "administrator"))
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(org, field, value)

    await db.commit()
    await db.refresh(org)
    return org


@router.post("/{org_id}/members", response_model=OrganizationMembershipOut,
             status_code=status.HTTP_201_CREATED)
async def add_organization_member(
    org_id: uuid.UUID,
    payload: OrganizationMembershipCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Add a member to the organization. Requires org_owner or administrator role."""
    await require_organization_access(db, current_user, org_id, ("org_owner", "administrator"))
    # Check for existing membership
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == payload.user_id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    if result.scalars().first():
        raise HTTPException(status_code=409, detail="User is already a member")

    membership = OrganizationMembership(
        user_id=payload.user_id,
        organization_id=org_id,
        role=Role(payload.role),
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership


@router.get("/{org_id}/members", response_model=List[OrganizationMembershipOut])
async def list_organization_members(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await require_organization_access(db, current_user, org_id)
    result = await db.execute(
        select(OrganizationMembership)
        .where(OrganizationMembership.organization_id == org_id)
    )
    return result.scalars().all()


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_organization_member(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await require_organization_access(db, current_user, org_id, ("org_owner",))
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    await db.delete(membership)
    await db.commit()
