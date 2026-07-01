"""Workspaces API — CRUD for Workspace entities."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import claim_uuid, enforce_tenant_claims, get_current_user, require_project_access
from app.db.database import get_db
from app.models.workspace import Workspace
from app.models.requirement import Requirement
from app.models.test import TestCase, TestSuite
from app.models.tenant import Project
from app.schemas.workspace import WorkspaceCreate, WorkspaceOut, WorkspaceUpdate

router = APIRouter()


@router.get("", response_model=List[WorkspaceOut])
async def list_workspaces(
    project_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List workspaces in the current project."""
    query = select(Workspace)
    ws_id = project_id or current_user.get("project_id")
    if ws_id:
        ws_id = uuid.UUID(str(ws_id))
        await require_project_access(db, current_user, ws_id)
        query = query.where(Workspace.project_id == ws_id)
    org_id = current_user.get("organization_id")
    if org_id:
        query = query.where(Workspace.organization_id == org_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalars().first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    enforce_tenant_claims(workspace.organization_id, workspace.project_id, current_user)
    return workspace


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new workspace. Requires administrator or QA lead role."""
    await require_project_access(db, current_user, payload.project_id, ("administrator", "qa_lead"))
    org_id = claim_uuid(current_user, "organization_id", "org_id")
    if org_id is None:
        ws_result = await db.execute(select(Project).where(Project.id == payload.project_id))
        project = ws_result.scalars().first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        org_id = project.organization_id
    if payload.organization_id and org_id and payload.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Tenant access denied")
    if not payload.organization_id:
        payload.organization_id = org_id

    workspace = Workspace(
        name=payload.name,
        key=payload.key,
        description=payload.description,
        settings=payload.settings or {},
        project_id=payload.project_id,
        organization_id=payload.organization_id,
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.put("/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalars().first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await require_project_access(db, current_user, workspace.project_id, ("administrator", "qa_lead"))

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(workspace, field, value)

    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalars().first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await require_project_access(db, current_user, workspace.project_id, ("administrator", "org_owner"))
    await db.delete(workspace)
    await db.commit()


@router.get("/{workspace_id}/stats")
async def get_workspace_stats(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return aggregate counts for a workspace's dashboard."""
    # Verify workspace exists
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalars().first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    enforce_tenant_claims(workspace.organization_id, workspace.project_id, current_user)

    req_count = await db.execute(
        select(func.count()).select_from(Requirement).where(Requirement.workspace_id == workspace_id)
    )
    # TestCase has no direct workspace_id — it belongs to a workspace via its TestSuite.
    tc_count = await db.execute(
        select(func.count())
        .select_from(TestCase)
        .join(TestSuite, TestCase.test_suite_id == TestSuite.id)
        .where(TestSuite.workspace_id == workspace_id)
    )

    return {
        "total_requirements": req_count.scalar() or 0,
        "total_test_cases": tc_count.scalar() or 0,
        "team_members": 0,  # TODO: implement team membership
    }
