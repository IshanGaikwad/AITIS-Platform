"""Workspaces API — CRUD for Workspace + membership management."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_organization_access, require_workspace_access
from app.db.database import get_db
from app.models.tenant import Organization, Role, Workspace, WorkspaceMembership
from app.schemas.tenant import (
    WorkspaceCreate,
    WorkspaceMembershipCreate,
    WorkspaceMembershipOut,
    WorkspaceOut,
    WorkspaceUpdate,
)

router = APIRouter()


@router.get("", response_model=List[WorkspaceOut])
async def list_workspaces(
    organization_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List workspaces the current user has access to."""
    user_id = current_user.get("user_id")
    query = (
        select(Workspace)
        .join(WorkspaceMembership)
        .where(WorkspaceMembership.user_id == user_id)
    )
    if organization_id:
        await require_organization_access(db, current_user, organization_id)
        query = query.where(Workspace.organization_id == organization_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = result.scalars().first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await require_workspace_access(db, current_user, workspace_id)
    return ws


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a workspace within an organization. Requires org_owner or administrator."""
    await require_organization_access(db, current_user, payload.organization_id, ("org_owner", "administrator"))
    # Verify org exists
    org_result = await db.execute(
        select(Organization).where(Organization.id == payload.organization_id)
    )
    if not org_result.scalars().first():
        raise HTTPException(status_code=404, detail="Organization not found")

    ws = Workspace(
        name=payload.name,
        slug=payload.slug,
        organization_id=payload.organization_id,
        description=payload.description,
        settings=payload.settings or {},
    )
    db.add(ws)
    await db.flush()

    # Creator becomes workspace admin
    membership = WorkspaceMembership(
        user_id=current_user.get("user_id"),
        workspace_id=ws.id,
        role=Role.administrator,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(ws)
    return ws


@router.put("/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await require_workspace_access(db, current_user, workspace_id, ("org_owner", "administrator"))
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = result.scalars().first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ws, field, value)

    await db.commit()
    await db.refresh(ws)
    return ws


@router.post("/{workspace_id}/members", response_model=WorkspaceMembershipOut,
             status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    workspace_id: uuid.UUID,
    payload: WorkspaceMembershipCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Add a member to the workspace."""
    await require_workspace_access(db, current_user, workspace_id, ("org_owner", "administrator"))
    result = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.user_id == payload.user_id,
            WorkspaceMembership.workspace_id == workspace_id,
        )
    )
    if result.scalars().first():
        raise HTTPException(status_code=409, detail="User is already a member")

    membership = WorkspaceMembership(
        user_id=payload.user_id,
        workspace_id=workspace_id,
        role=Role(payload.role),
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership


@router.get("/{workspace_id}/members", response_model=List[WorkspaceMembershipOut])
async def list_workspace_members(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await require_workspace_access(db, current_user, workspace_id)
    result = await db.execute(
        select(WorkspaceMembership)
        .where(WorkspaceMembership.workspace_id == workspace_id)
    )
    return result.scalars().all()


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await require_workspace_access(db, current_user, workspace_id, ("org_owner", "administrator"))
    result = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.workspace_id == workspace_id,
        )
    )
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    await db.delete(membership)
    await db.commit()
