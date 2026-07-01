"""Projects API — CRUD for Project + membership management."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_organization_access, require_project_access
from app.db.database import get_db
from app.models.tenant import Organization, Role, Project, ProjectMembership
from app.schemas.tenant import (
    ProjectCreate,
    ProjectMembershipCreate,
    ProjectMembershipOut,
    ProjectOut,
    ProjectUpdate,
)

router = APIRouter()


@router.get("", response_model=List[ProjectOut])
async def list_projects(
    organization_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List projects the current user has access to."""
    user_id = current_user.get("user_id")
    query = (
        select(Project)
        .join(ProjectMembership)
        .where(ProjectMembership.user_id == user_id)
    )
    if organization_id:
        await require_organization_access(db, current_user, organization_id)
        query = query.where(Project.organization_id == organization_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    ws = result.scalars().first()
    if not ws:
        raise HTTPException(status_code=404, detail="Project not found")
    await require_project_access(db, current_user, project_id)
    return ws


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a project within an organization. Requires org_owner or administrator."""
    await require_organization_access(db, current_user, payload.organization_id, ("org_owner", "administrator"))
    # Verify org exists
    org_result = await db.execute(
        select(Organization).where(Organization.id == payload.organization_id)
    )
    if not org_result.scalars().first():
        raise HTTPException(status_code=404, detail="Organization not found")

    ws = Project(
        name=payload.name,
        slug=payload.slug,
        organization_id=payload.organization_id,
        description=payload.description,
        settings=payload.settings or {},
    )
    db.add(ws)
    await db.flush()

    # Creator becomes project admin
    membership = ProjectMembership(
        user_id=current_user.get("user_id"),
        project_id=ws.id,
        role=Role.administrator,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(ws)
    return ws


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await require_project_access(db, current_user, project_id, ("org_owner", "administrator"))
    result = await db.execute(select(Project).where(Project.id == project_id))
    ws = result.scalars().first()
    if not ws:
        raise HTTPException(status_code=404, detail="Project not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ws, field, value)

    await db.commit()
    await db.refresh(ws)
    return ws


@router.post("/{project_id}/members", response_model=ProjectMembershipOut,
             status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: uuid.UUID,
    payload: ProjectMembershipCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Add a member to the project."""
    await require_project_access(db, current_user, project_id, ("org_owner", "administrator"))
    result = await db.execute(
        select(ProjectMembership).where(
            ProjectMembership.user_id == payload.user_id,
            ProjectMembership.project_id == project_id,
        )
    )
    if result.scalars().first():
        raise HTTPException(status_code=409, detail="User is already a member")

    membership = ProjectMembership(
        user_id=payload.user_id,
        project_id=project_id,
        role=Role(payload.role),
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership


@router.get("/{project_id}/members", response_model=List[ProjectMembershipOut])
async def list_project_members(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await require_project_access(db, current_user, project_id)
    result = await db.execute(
        select(ProjectMembership)
        .where(ProjectMembership.project_id == project_id)
    )
    return result.scalars().all()


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await require_project_access(db, current_user, project_id, ("org_owner", "administrator"))
    result = await db.execute(
        select(ProjectMembership).where(
            ProjectMembership.user_id == user_id,
            ProjectMembership.project_id == project_id,
        )
    )
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    await db.delete(membership)
    await db.commit()
