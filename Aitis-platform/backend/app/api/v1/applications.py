"""Application management API routes."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.models import ApplicationType
from app.services import ApplicationService, PermissionService
from app.core.security import get_current_user
from app.db.database import get_db

router = APIRouter(prefix="/applications", tags=["applications"])


# ── Schemas ──────────────────────────────────────────────────────
class ApplicationCreate(BaseModel):
    """Create application request."""
    name: str = Field(..., min_length=1, max_length=255)
    application_type: ApplicationType
    description: Optional[str] = None
    repository_url: Optional[str] = None
    metadata_: Optional[dict] = None


class ApplicationUpdate(BaseModel):
    """Update application request."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    application_type: Optional[ApplicationType] = None
    description: Optional[str] = None
    repository_url: Optional[str] = None
    metadata_: Optional[dict] = None


class ApplicationOut(BaseModel):
    """Application response."""
    id: UUID
    project_id: UUID
    name: str
    application_type: ApplicationType
    description: Optional[str]
    repository_url: Optional[str]
    metadata_: Optional[dict]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ── Routes ───────────────────────────────────────────────────────

@router.post("/projects/{project_id}/applications", response_model=ApplicationOut, status_code=201)
async def create_application(
    project_id: UUID,
    data: ApplicationCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new application in a project."""
    # Check permissions
    has_perm = await PermissionService.check_permission(
        db,
        current_user.id,
        "projects",
        "create",
        current_user.organization_id,
        current_user.workspace_id,
        resource_id=project_id,
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="No permission to create applications in this project")

    app = await ApplicationService.create_application(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        project_id=project_id,
        name=data.name,
        application_type=data.application_type,
        description=data.description,
        repository_url=data.repository_url,
        metadata_=data.metadata_,
    )

    return app


@router.get("/projects/{project_id}/applications", response_model=dict)
async def list_project_applications(
    project_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all applications in a project."""
    # Check permissions
    has_perm = await PermissionService.check_permission(
        db,
        current_user.id,
        "projects",
        "read",
        current_user.organization_id,
        current_user.workspace_id,
        resource_id=project_id,
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="No permission to view this project")

    apps, total = await ApplicationService.list_project_applications(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        project_id=project_id,
        skip=skip,
        limit=limit,
    )

    return {
        "items": [ApplicationOut.from_orm(app).model_dump() for app in apps],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{application_id}", response_model=ApplicationOut)
async def get_application(
    application_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get application by ID."""
    app = await ApplicationService.get_application(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        application_id=application_id,
    )

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    return app


@router.patch("/{application_id}", response_model=ApplicationOut)
async def update_application(
    application_id: UUID,
    data: ApplicationUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an application."""
    # Get app first to check permissions
    app = await ApplicationService.get_application(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        application_id=application_id,
    )

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Check permissions
    has_perm = await PermissionService.check_permission(
        db,
        current_user.id,
        "projects",
        "update",
        current_user.organization_id,
        current_user.workspace_id,
        resource_id=app.project_id,
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="No permission to update this application")

    updated_app = await ApplicationService.update_application(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        application_id=application_id,
        name=data.name,
        application_type=data.application_type,
        description=data.description,
        repository_url=data.repository_url,
        metadata_=data.metadata_,
    )

    return updated_app


@router.delete("/{application_id}", status_code=204)
async def delete_application(
    application_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an application."""
    # Get app first
    app = await ApplicationService.get_application(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        application_id=application_id,
    )

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Check permissions
    has_perm = await PermissionService.check_permission(
        db,
        current_user.id,
        "projects",
        "delete",
        current_user.organization_id,
        current_user.workspace_id,
        resource_id=app.project_id,
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="No permission to delete this application")

    await ApplicationService.delete_application(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        application_id=application_id,
    )
