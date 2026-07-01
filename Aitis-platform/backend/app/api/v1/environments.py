"""Environment management API routes."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.models import EnvironmentType
from app.services import EnvironmentService, PermissionService
from app.core.security import claim_uuid, get_current_user, require_project_access
from app.db.database import get_db

router = APIRouter(prefix="/environments", tags=["environments"])


# ── Schemas ──────────────────────────────────────────────────────
class EnvironmentCreate(BaseModel):
    """Create environment request."""
    name: str = Field(..., min_length=1, max_length=255)
    environment_type: EnvironmentType
    description: Optional[str] = None
    base_url: Optional[str] = None
    environment_variables: Optional[list] = None
    health_check_url: Optional[str] = None
    health_check_enabled: bool = False


class EnvironmentUpdate(BaseModel):
    """Update environment request."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    environment_type: Optional[EnvironmentType] = None
    description: Optional[str] = None
    base_url: Optional[str] = None
    environment_variables: Optional[list] = None
    health_check_url: Optional[str] = None
    health_check_enabled: Optional[bool] = None


class EnvironmentOut(BaseModel):
    """Environment response."""
    id: UUID
    application_id: UUID
    workspace_id: UUID
    name: str
    environment_type: EnvironmentType
    description: Optional[str]
    base_url: Optional[str]
    environment_variables: Optional[list]
    health_check_url: Optional[str]
    health_check_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Routes ───────────────────────────────────────────────────────

@router.post("/applications/{application_id}/environments", response_model=EnvironmentOut, status_code=201)
async def create_environment(
    application_id: UUID,
    data: EnvironmentCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new environment for an application."""
    # Check permissions (to the workspace that owns this application)
    from app.services import ApplicationService as AppService
    app = await AppService.get_application(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        application_id=application_id,
    )
    
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    await require_project_access(
        db, current_user, claim_uuid(current_user, "project_id"), ("administrator", "qa_lead")
    )

    env = await EnvironmentService.create_environment(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        workspace_id=app.workspace_id,
        application_id=application_id,
        name=data.name,
        environment_type=data.environment_type,
        description=data.description,
        base_url=data.base_url,
        environment_variables=data.environment_variables,
        health_check_url=data.health_check_url,
        health_check_enabled=data.health_check_enabled,
    )

    return env


@router.get("/applications/{application_id}/environments", response_model=dict)
async def list_application_environments(
    application_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all environments for an application."""
    # Check permissions
    from app.services import ApplicationService as AppService
    app = await AppService.get_application(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        application_id=application_id,
    )
    
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    await require_project_access(db, current_user, claim_uuid(current_user, "project_id"))

    envs, total = await EnvironmentService.list_application_environments(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        application_id=application_id,
        skip=skip,
        limit=limit,
    )

    return {
        "items": [EnvironmentOut.from_orm(env).model_dump() for env in envs],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/workspaces/{workspace_id}/environments", response_model=dict)
async def list_workspace_environments(
    workspace_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all environments across every application in a workspace.

    Convenience endpoint so callers (e.g. the Execution target picker) don't have to
    list applications first and then fan out to each one's environments.
    """
    await require_project_access(db, current_user, claim_uuid(current_user, "project_id"))

    envs, total = await EnvironmentService.list_workspace_environments(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        workspace_id=workspace_id,
        skip=skip,
        limit=limit,
    )

    return {
        "items": [EnvironmentOut.from_orm(env).model_dump() for env in envs],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{environment_id}", response_model=EnvironmentOut)
async def get_environment(
    environment_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get environment by ID."""
    env = await EnvironmentService.get_environment(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        environment_id=environment_id,
    )

    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    return env


@router.patch("/{environment_id}", response_model=EnvironmentOut)
async def update_environment(
    environment_id: UUID,
    data: EnvironmentUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an environment."""
    # Get env first
    env = await EnvironmentService.get_environment(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        environment_id=environment_id,
    )

    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    await require_project_access(
        db, current_user, claim_uuid(current_user, "project_id"), ("administrator", "qa_lead")
    )

    updated_env = await EnvironmentService.update_environment(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        environment_id=environment_id,
        name=data.name,
        environment_type=data.environment_type,
        description=data.description,
        base_url=data.base_url,
        environment_variables=data.environment_variables,
        health_check_url=data.health_check_url,
        health_check_enabled=data.health_check_enabled,
    )

    return updated_env


@router.delete("/{environment_id}", status_code=204)
async def delete_environment(
    environment_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an environment."""
    # Get env first
    env = await EnvironmentService.get_environment(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        environment_id=environment_id,
    )

    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    await require_project_access(
        db, current_user, claim_uuid(current_user, "project_id"), ("administrator", "qa_lead")
    )

    await EnvironmentService.delete_environment(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        environment_id=environment_id,
    )
