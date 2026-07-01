"""Audit Events API — Read-only audit log access for compliance and debugging."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.models.system import AuditEvent
from app.schemas.system import AuditEventOut

router = APIRouter()


@router.get("", response_model=List[AuditEventOut])
async def list_audit_events(
    organization_id: Optional[uuid.UUID] = Query(None),
    project_id: Optional[uuid.UUID] = Query(None),
    user_id: Optional[uuid.UUID] = Query(None),
    entity_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("org_owner", "administrator")),
):
    """List audit events. Requires org_owner or administrator role."""
    query = select(AuditEvent)

    # Scope to the caller's organization by default
    org_id = organization_id or current_user.get("organization_id")
    if org_id:
        query = query.where(AuditEvent.organization_id == org_id)
    if project_id:
        query = query.where(AuditEvent.project_id == project_id)
    if user_id:
        query = query.where(AuditEvent.user_id == user_id)
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)

    query = query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{event_id}", response_model=AuditEventOut)
async def get_audit_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("org_owner", "administrator")),
):
    result = await db.execute(select(AuditEvent).where(AuditEvent.id == event_id))
    event = result.scalars().first()
    if not event:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Audit event not found")
    return event
