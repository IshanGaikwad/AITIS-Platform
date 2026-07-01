"""Defects API — CRUD for defects, link to test executions, and Jira sync.

Phase 6: Full defects management with filtering, status transitions,
and integration with test execution results.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.models.artifact import Defect, DefectSeverity, DefectStatus
from app.models.test import TestCaseExecution, TestExecution
from app.models.workspace import Workspace

router = APIRouter()


# ── Pydantic schemas (inline to avoid circular imports) ─────────────
from pydantic import BaseModel, ConfigDict, Field


class DefectCreate(BaseModel):
    workspace_id: uuid.UUID
    case_execution_id: Optional[uuid.UUID] = None
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    severity: str = Field("major", description="blocker | critical | major | minor | trivial")
    status: str = Field("open", description="open | in_progress | resolved | closed | wont_fix")
    steps_to_reproduce: Optional[str] = None
    environment: Optional[str] = None
    labels: Optional[List[str]] = None
    external_id: Optional[str] = None


class DefectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    environment: Optional[str] = None
    labels: Optional[List[str]] = None
    external_id: Optional[str] = None


class DefectOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    case_execution_id: Optional[uuid.UUID] = None
    external_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    severity: str
    status: str
    steps_to_reproduce: Optional[str] = None
    environment: Optional[str] = None
    labels: Optional[List[str]] = None
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DefectSummary(BaseModel):
    total: int
    open: int
    in_progress: int
    resolved: int
    closed: int
    blocker: int
    critical: int
    major: int
    minor: int
    trivial: int


# ══════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════

@router.get("", response_model=List[DefectOut])
async def list_defects(
    workspace_id: Optional[uuid.UUID] = Query(None, description="Filter by workspace"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    search: Optional[str] = Query(None, description="Search in title/description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List defects with optional filters."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("project_id")

    stmt = select(Defect).where(
        Defect.organization_id == org_id,
        Defect.project_id == ws_id,
    )

    if workspace_id:
        stmt = stmt.where(Defect.workspace_id == workspace_id)
    if status_filter:
        stmt = stmt.where(Defect.status == status_filter)
    if severity:
        stmt = stmt.where(Defect.severity == severity)
    if search:
        stmt = stmt.where(
            or_(
                Defect.title.ilike(f"%{search}%"),
                Defect.description.ilike(f"%{search}%"),
            )
        )

    stmt = stmt.order_by(Defect.updated_at.desc().nulls_last()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/summary", response_model=DefectSummary)
async def defect_summary(
    workspace_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get defect counts by status and severity."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("project_id")

    base = select(Defect).where(
        Defect.organization_id == org_id,
        Defect.project_id == ws_id,
    )
    if workspace_id:
        base = base.where(Defect.workspace_id == workspace_id)

    # Total
    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_result.scalar() or 0

    async def _count(field: str, value: str) -> int:
        stmt = base.where(getattr(Defect, field) == value)
        r = await db.execute(select(func.count()).select_from(stmt.subquery()))
        return r.scalar() or 0

    return DefectSummary(
        total=total,
        open=await _count("status", "open"),
        in_progress=await _count("status", "in_progress"),
        resolved=await _count("status", "resolved"),
        closed=await _count("status", "closed"),
        blocker=await _count("severity", "blocker"),
        critical=await _count("severity", "critical"),
        major=await _count("severity", "major"),
        minor=await _count("severity", "minor"),
        trivial=await _count("severity", "trivial"),
    )


@router.post("", response_model=DefectOut, status_code=status.HTTP_201_CREATED)
async def create_defect(
    payload: DefectCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "qa_engineer")),
):
    """Create a new defect."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("project_id")

    # Verify workspace exists
    workspace = await db.get(Workspace, payload.workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    defect = Defect(
        workspace_id=payload.workspace_id,
        case_execution_id=payload.case_execution_id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        status=payload.status,
        steps_to_reproduce=payload.steps_to_reproduce,
        environment=payload.environment,
        labels=payload.labels or [],
        external_id=payload.external_id,
        organization_id=org_id,
        project_id=ws_id,
    )
    db.add(defect)
    await db.commit()
    await db.refresh(defect)
    return defect


@router.get("/{defect_id}", response_model=DefectOut)
async def get_defect(
    defect_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a single defect by ID."""
    defect = await db.get(Defect, defect_id)
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
    return defect


@router.put("/{defect_id}", response_model=DefectOut)
async def update_defect(
    defect_id: uuid.UUID,
    payload: DefectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "qa_engineer")),
):
    """Update a defect."""
    defect = await db.get(Defect, defect_id)
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(defect, key, value)

    await db.commit()
    await db.refresh(defect)
    return defect


@router.delete("/{defect_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_defect(
    defect_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead")),
):
    """Delete a defect."""
    defect = await db.get(Defect, defect_id)
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
    await db.delete(defect)
    await db.commit()


@router.post("/{defect_id}/transition")
async def transition_defect(
    defect_id: uuid.UUID,
    new_status: str = Query(..., description="New status: open | in_progress | resolved | closed | wont_fix"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "qa_engineer")),
):
    """Transition a defect to a new status."""
    valid_statuses = {s.value for s in DefectStatus}
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    defect = await db.get(Defect, defect_id)
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")

    defect.status = new_status
    await db.commit()
    await db.refresh(defect)
    return DefectOut.model_validate(defect)