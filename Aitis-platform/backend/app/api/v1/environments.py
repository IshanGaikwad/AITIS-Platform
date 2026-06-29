"""Environment management API routes."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.models import EnvironmentType
from app.services import EnvironmentService, PermissionService
from app.core.security import get_current_user
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
    project_id: UUID
    name: str
    environment_type: EnvironmentType
    description: Optional[str]
    base_url: Optional[str]
    environment_variables: Optional[list]
    health_check_url: Optional[str]
    health_check_enabled: bool
    created_at: str
    updated_at: str

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
    # Check permissions (to the project that owns this application)
    from app.services import ApplicationService as AppService
    app = await AppService.get_application(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        application_id=application_id,
    )
    
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    has_perm = await PermissionService.check_permission(
        db,
        current_user.id,
        "projects",
        "create",
        current_user.organization_id,
        current_user.workspace_id,
        resource_id=app.project_id,
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="No permission to create environments in this project")

    env = await EnvironmentService.create_environment(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        project_id=app.project_id,
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
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        application_id=application_id,
    )
    
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    has_perm = await PermissionService.check_permission(
        db,
        current_user.id,
        "projects",
        "read",
        current_user.organization_id,
        current_user.workspace_id,
        resource_id=app.project_id,
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="No permission to view this application")

    envs, total = await EnvironmentService.list_application_environments(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
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


@router.get("/{environment_id}", response_model=EnvironmentOut)
async def get_environment(
    environment_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get environment by ID."""
    env = await EnvironmentService.get_environment(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
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
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        environment_id=environment_id,
    )

    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    # Check permissions
    has_perm = await PermissionService.check_permission(
        db,
        current_user.id,
        "projects",
        "update",
        current_user.organization_id,
        current_user.workspace_id,
        resource_id=env.project_id,
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="No permission to update this environment")

    updated_env = await EnvironmentService.update_environment(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
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
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        environment_id=environment_id,
    )

    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    # Check permissions
    has_perm = await PermissionService.check_permission(
        db,
        current_user.id,
        "projects",
        "delete",
        current_user.organization_id,
        current_user.workspace_id,
        resource_id=env.project_id,
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="No permission to delete this environment")

    await EnvironmentService.delete_environment(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        environment_id=environment_id,
    )
