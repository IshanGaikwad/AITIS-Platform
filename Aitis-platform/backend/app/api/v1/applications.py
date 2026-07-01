"""Application management API routes."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.models import ApplicationType
from app.services import ApplicationService, PermissionService
from app.core.security import claim_uuid, get_current_user, require_project_access
from app.db.database import get_db
from app.services.stack_detection_service import (
    StackDetectionError,
    StackDetectionResult,
    detect_stack,
)

router = APIRouter(prefix="/applications", tags=["applications"])


class StackDetectRequest(BaseModel):
    """Detect a System Under Test's technology stack from its URL."""
    url: str = Field(..., min_length=1, max_length=2048)


@router.post("/detect-stack", response_model=StackDetectionResult)
async def detect_application_stack(
    payload: StackDetectRequest,
    current_user=Depends(get_current_user),
):
    """Fetch a candidate SUT URL and infer its tech stack. Does not persist anything —
    the frontend confirms the result, then calls create_application/create_environment."""
    try:
        return await detect_stack(payload.url)
    except StackDetectionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


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
    workspace_id: UUID
    name: str
    application_type: ApplicationType
    description: Optional[str]
    repository_url: Optional[str]
    metadata_: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Routes ───────────────────────────────────────────────────────

@router.post("/workspaces/{workspace_id}/applications", response_model=ApplicationOut, status_code=201)
async def create_application(
    workspace_id: UUID,
    data: ApplicationCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new application in a workspace."""
    # User must be a project member with a write role
    await require_project_access(
        db, current_user, claim_uuid(current_user, "project_id"), ("administrator", "qa_lead")
    )

    app = await ApplicationService.create_application(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        workspace_id=workspace_id,
        name=data.name,
        application_type=data.application_type,
        description=data.description,
        repository_url=data.repository_url,
        metadata_=data.metadata_,
    )

    return app


@router.get("/workspaces/{workspace_id}/applications", response_model=dict)
async def list_workspace_applications(
    workspace_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all applications in a workspace."""
    # User must be a member of the project
    await require_project_access(db, current_user, claim_uuid(current_user, "project_id"))

    apps, total = await ApplicationService.list_workspace_applications(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        workspace_id=workspace_id,
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
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
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
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        application_id=application_id,
    )

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # User must be a project member with a write role
    await require_project_access(
        db, current_user, claim_uuid(current_user, "project_id"), ("administrator", "qa_lead")
    )

    updated_app = await ApplicationService.update_application(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
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
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        application_id=application_id,
    )

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # User must be a project member with a write role
    await require_project_access(
        db, current_user, claim_uuid(current_user, "project_id"), ("administrator", "qa_lead")
    )

    await ApplicationService.delete_application(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        application_id=application_id,
    )
