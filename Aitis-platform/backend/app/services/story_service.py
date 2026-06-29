"""Async requirement service — CRUD for Requirement + AcceptanceCriterion entities.

Legacy story_service functions are preserved as thin wrappers for backward compatibility.
"""

import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.requirement import Requirement, AcceptanceCriterion
from app.schemas.requirement import RequirementCreate, RequirementUpdate


# ── Requirement CRUD ────────────────────────────────────────────────
async def list_requirements(
    db: AsyncSession,
    organization_id: Optional[uuid.UUID] = None,
    workspace_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
) -> List[Requirement]:
    stmt = select(Requirement).order_by(Requirement.created_at.desc())
    if organization_id:
        stmt = stmt.where(Requirement.organization_id == organization_id)
    if workspace_id:
        stmt = stmt.where(Requirement.workspace_id == workspace_id)
    if project_id:
        stmt = stmt.where(Requirement.project_id == project_id)
    result = await db.execute(stmt.options(selectinload(Requirement.acceptance_criteria)))
    return list(result.scalars().all())


async def get_requirement(db: AsyncSession, requirement_id: uuid.UUID) -> Optional[Requirement]:
    result = await db.execute(
        select(Requirement)
        .where(Requirement.id == requirement_id)
        .options(selectinload(Requirement.acceptance_criteria))
    )
    return result.scalars().first()


async def create_requirement(db: AsyncSession, payload: RequirementCreate) -> Requirement:
    req = Requirement(
        project_id=payload.project_id,
        external_id=payload.jiraId,
        title=payload.title,
        description=payload.description,
        type=payload.type or "functional",
        priority=payload.priority or "medium",
        status="draft",
        source=payload.source or "manual",
        organization_id=payload.organization_id,
        workspace_id=payload.workspace_id,
    )
    db.add(req)
    await db.flush()

    # Create acceptance criteria rows
    for idx, ac_text in enumerate(payload.acceptanceCriteria or []):
        ac = AcceptanceCriterion(
            requirement_id=req.id,
            text=ac_text if isinstance(ac_text, str) else ac_text.get("text", str(ac_text)),
            category="positive",
            order=idx,
            organization_id=payload.organization_id,
            workspace_id=payload.workspace_id,
        )
        db.add(ac)

    await db.commit()
    await db.refresh(req)
    return req


async def update_requirement(
    db: AsyncSession, requirement_id: uuid.UUID, payload: RequirementUpdate
) -> Optional[Requirement]:
    req = await get_requirement(db, requirement_id)
    if not req:
        return None

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "jiraId":
            setattr(req, "external_id", value)
        elif field == "acceptanceCriteria":
            # Replace all ACs
            for ac in req.acceptance_criteria:
                await db.delete(ac)
            await db.flush()
            for idx, ac_text in enumerate(value or []):
                ac = AcceptanceCriterion(
                    requirement_id=req.id,
                    text=ac_text if isinstance(ac_text, str) else ac_text.get("text", str(ac_text)),
                    category="positive",
                    order=idx,
                    organization_id=req.organization_id,
                    workspace_id=req.workspace_id,
                )
                db.add(ac)
        elif hasattr(req, field):
            setattr(req, field, value)

    await db.commit()
    await db.refresh(req)
    return req


async def delete_requirement(db: AsyncSession, requirement_id: uuid.UUID) -> bool:
    req = await get_requirement(db, requirement_id)
    if not req:
        return False
    await db.delete(req)
    await db.commit()
    return True


# ── Legacy story_service wrappers ───────────────────────────────────
async def list_stories(db: AsyncSession, **kwargs) -> List[Requirement]:
    return await list_requirements(db, **kwargs)


async def get_story(db: AsyncSession, story_id: uuid.UUID) -> Optional[Requirement]:
    return await get_requirement(db, story_id)


async def create_story(db: AsyncSession, payload) -> Requirement:
    return await create_requirement(db, payload)


async def update_story(db: AsyncSession, story_id: uuid.UUID, payload) -> Optional[Requirement]:
    return await update_requirement(db, story_id, payload)


async def delete_story(db: AsyncSession, story_id: uuid.UUID) -> bool:
    return await delete_requirement(db, story_id)