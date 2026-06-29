"""Requirements API — CRUD for Requirement + AcceptanceCriterion.

Replaces the legacy stories.py with async DB access, multi-tenancy, and RBAC.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.models.requirement import Requirement
from app.schemas.requirement import RequirementCreate, RequirementOut, RequirementUpdate
from app.schemas.story import StoryCreate, StoryOut, StoryUpdate
from app.services.story_service import (
    create_requirement,
    delete_requirement,
    get_requirement,
    list_requirements,
    update_requirement,
)

router = APIRouter()


def _to_out(req: Requirement) -> RequirementOut:
    """Map ORM Requirement → RequirementOut schema."""
    ac_texts = [ac.text for ac in req.acceptance_criteria] if req.acceptance_criteria else []
    return RequirementOut(
        id=req.id,
        project_id=req.project_id,
        jiraId=req.external_id,
        title=req.title,
        description=req.description,
        type=req.type,
        priority=req.priority,
        status=req.status,
        source=req.source,
        source_metadata=req.source_metadata,
        version=req.version,
        acceptanceCriteria=ac_texts,
        organization_id=req.organization_id,
        workspace_id=req.workspace_id,
        ai_input_source=req.ai_input_source,
        ai_model_id=req.ai_model_id,
        ai_prompt_version=req.ai_prompt_version,
        ai_timestamp=req.ai_timestamp,
        ai_assumptions=req.ai_assumptions,
        ai_confidence=req.ai_confidence,
        ai_review_status=req.ai_review_status,
        ai_reviewer_id=req.ai_reviewer_id,
        ai_approval_rejection_reason=req.ai_approval_rejection_reason,
        ai_final_edited_version=req.ai_final_edited_version,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


@router.get("", response_model=List[RequirementOut])
async def list_all_requirements(
    project_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List requirements scoped to the user's organization/workspace."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("workspace_id")
    reqs = await list_requirements(db, organization_id=org_id, workspace_id=ws_id, project_id=project_id)
    return [_to_out(r) for r in reqs]


@router.get("/{requirement_id}", response_model=RequirementOut)
async def get_requirement_by_id(
    requirement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    req = await get_requirement(db, requirement_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return _to_out(req)


@router.post("", response_model=RequirementOut, status_code=status.HTTP_201_CREATED)
async def create_new_requirement(
    payload: RequirementCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "automation_engineer")),
):
    """Create a new requirement. Requires admin, QA lead, or automation engineer role."""
    # Inject tenant context from JWT if not provided
    if not payload.organization_id:
        payload.organization_id = current_user.get("organization_id")
    if not payload.workspace_id:
        payload.workspace_id = current_user.get("workspace_id")
    req = await create_requirement(db, payload)
    return _to_out(req)


@router.put("/{requirement_id}", response_model=RequirementOut)
async def update_existing_requirement(
    requirement_id: uuid.UUID,
    payload: RequirementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead")),
):
    req = await update_requirement(db, requirement_id, payload)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return _to_out(req)


@router.delete("/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_requirement(
    requirement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "org_owner")),
):
    success = await delete_requirement(db, requirement_id)
    if not success:
        raise HTTPException(status_code=404, detail="Requirement not found")