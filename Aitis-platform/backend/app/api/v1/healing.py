"""Healing API — AI-powered test script self-healing.

Phase 7: Endpoints for analyzing failures, generating healing proposals,
and applying fixes to automation scripts.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.models.automation import AutomationScript
from app.models.artifact import HealingProposal as HealingProposalModel
from app.services.failure_classifier import (
    FailureCategory,
    classify_failure,
    detect_flakiness,
    generate_flakiness_report,
)
from app.services.self_healing import (
    SelectorFix,
    heal_selector,
    generate_healing_proposal,
    apply_healing,
)

router = APIRouter()


# ── Pydantic schemas ─────────────────────────────────────────────────
class FailureClassificationOut(BaseModel):
    category: str
    confidence: float
    explanation: str
    suggested_fix: str
    is_flaky_indicator: bool
    matched_patterns: List[str] = []


class ClassifyRequest(BaseModel):
    error_message: str
    stack_trace: Optional[str] = None
    test_name: Optional[str] = None


class FlakinessRequest(BaseModel):
    execution_history: List[dict] = Field(..., min_length=1)
    threshold: float = Field(0.3, ge=0.0, le=1.0)


class FlakinessResult(BaseModel):
    is_flaky: bool
    flakiness_score: float
    failure_rate: float
    total_runs: int
    failures: int
    recommendation: str


class FlakinessReportRequest(BaseModel):
    test_results: List[dict] = Field(..., min_length=1)


class FlakinessReportOut(BaseModel):
    summary: dict
    flaky_tests: List[dict]
    recommendations: List[str]


class SelectorFixOut(BaseModel):
    original_selector: str
    proposed_selector: str
    selector_type: str
    confidence: float
    reasoning: str


class HealSelectorRequest(BaseModel):
    selector: str
    error_message: str
    page_context: Optional[str] = None


class HealingProposalRequest(BaseModel):
    script_code: str
    error_message: str
    stack_trace: Optional[str] = None
    script_id: Optional[str] = None


class HealingProposalOut(BaseModel):
    script_id: str
    original_code: str
    proposed_code: str
    changes: List[SelectorFixOut]
    explanation: str
    confidence_score: float
    failure_category: str


class ApplyHealingRequest(BaseModel):
    script_code: str
    fixes: List[SelectorFixOut]
    auto_apply: bool = False


class ApplyHealingOut(BaseModel):
    healed_code: str
    changes_applied: int


class HealingProposalRecordOut(BaseModel):
    id: str
    script_id: str
    original_code: str
    proposed_code: str
    changes: List[dict]
    explanation: str
    confidence_score: float
    failure_category: str
    status: str
    created_at: str
    applied_at: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════

@router.post("/classify", response_model=FailureClassificationOut)
async def classify_test_failure(
    payload: ClassifyRequest,
    current_user=Depends(get_current_user),
):
    """Classify a test failure from its error message and stack trace."""
    result = classify_failure(
        error_message=payload.error_message,
        stack_trace=payload.stack_trace,
        test_name=payload.test_name,
    )
    return FailureClassificationOut(
        category=result.category.value,
        confidence=result.confidence,
        explanation=result.explanation,
        suggested_fix=result.suggested_fix,
        is_flaky_indicator=result.is_flaky_indicator,
        matched_patterns=result.matched_patterns,
    )


@router.post("/flakiness/detect", response_model=FlakinessResult)
async def detect_test_flakiness(
    payload: FlakinessRequest,
    current_user=Depends(get_current_user),
):
    """Detect if a test is flaky based on execution history."""
    result = detect_flakiness(
        execution_history=payload.execution_history,
        threshold=payload.threshold,
    )
    return FlakinessResult(**result)


@router.post("/flakiness/report", response_model=FlakinessReportOut)
async def get_flakiness_report(
    payload: FlakinessReportRequest,
    current_user=Depends(get_current_user),
):
    """Generate a flakiness report for a set of test results."""
    result = generate_flakiness_report(payload.test_results)
    return FlakinessReportOut(**result)


@router.post("/heal-selector", response_model=List[SelectorFixOut])
async def heal_broken_selector(
    payload: HealSelectorRequest,
    current_user=Depends(get_current_user),
):
    """Generate healing proposals for a broken selector."""
    fixes = heal_selector(
        selector=payload.selector,
        error_message=payload.error_message,
        page_context=payload.page_context,
    )
    return [
        SelectorFixOut(
            original_selector=f.original_selector,
            proposed_selector=f.proposed_selector,
            selector_type=f.selector_type,
            confidence=f.confidence,
            reasoning=f.reasoning,
        )
        for f in fixes
    ]


@router.post("/propose", response_model=Optional[HealingProposalOut])
async def propose_healing(
    payload: HealingProposalRequest,
    current_user=Depends(get_current_user),
):
    """Generate a complete healing proposal for a failing test script."""
    result = generate_healing_proposal(
        script_code=payload.script_code,
        error_message=payload.error_message,
        stack_trace=payload.stack_trace,
        script_id=payload.script_id,
    )
    if not result:
        return None
    return HealingProposalOut(
        script_id=result.script_id,
        original_code=result.original_code,
        proposed_code=result.proposed_code,
        changes=[
            SelectorFixOut(
                original_selector=f.original_selector,
                proposed_selector=f.proposed_selector,
                selector_type=f.selector_type,
                confidence=f.confidence,
                reasoning=f.reasoning,
            )
            for f in result.changes
        ],
        explanation=result.explanation,
        confidence_score=result.confidence_score,
        failure_category=result.failure_category.value,
    )


@router.post("/apply", response_model=ApplyHealingOut)
async def apply_healing_fixes(
    payload: ApplyHealingRequest,
    current_user=Depends(get_current_user),
):
    """Apply healing fixes to a script."""
    fixes = [
        SelectorFix(
            original_selector=f.original_selector,
            proposed_selector=f.proposed_selector,
            selector_type=f.selector_type,
            confidence=f.confidence,
            reasoning=f.reasoning,
        )
        for f in payload.fixes
    ]
    healed = apply_healing(
        script_code=payload.script_code,
        fixes=fixes,
        auto_apply=payload.auto_apply,
    )
    changes = sum(1 for f in fixes if f.original_selector in payload.script_code)
    return ApplyHealingOut(healed_code=healed, changes_applied=changes)


@router.post("/proposals", status_code=status.HTTP_201_CREATED)
async def save_healing_proposal(
    script_id: uuid.UUID = Query(...),
    proposed_code: str = Query(...),
    explanation: str = Query(...),
    confidence_score: float = Query(..., ge=0.0, le=1.0),
    failure_category: str = Query("unknown"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "qa_engineer")),
):
    """Save a healing proposal to the database for review."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("project_id")

    # Verify script exists
    script = await db.get(AutomationScript, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Automation script not found")

    proposal = HealingProposalModel(
        script_id=script_id,
        original_code=script.code,
        proposed_code=proposed_code,
        explanation=explanation,
        confidence_score=confidence_score,
        failure_category=failure_category,
        status="pending",
        organization_id=org_id,
        project_id=ws_id,
    )
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)

    return {
        "id": str(proposal.id),
        "script_id": str(script_id),
        "status": "pending",
        "message": "Healing proposal saved for review.",
    }


@router.get("/proposals/{script_id}", response_model=List[HealingProposalRecordOut])
async def list_healing_proposals(
    script_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List healing proposals for a script."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("project_id")

    result = await db.execute(
        select(HealingProposalModel)
        .where(
            HealingProposalModel.script_id == script_id,
            HealingProposalModel.organization_id == org_id,
            HealingProposalModel.project_id == ws_id,
        )
        .order_by(HealingProposalModel.created_at.desc())
    )
    proposals = result.scalars().all()

    return [
        HealingProposalRecordOut(
            id=str(p.id),
            script_id=str(p.script_id),
            original_code=p.original_code or "",
            proposed_code=p.proposed_code or "",
            changes=p.changes or [],
            explanation=p.explanation or "",
            confidence_score=p.confidence_score or 0.0,
            failure_category=p.failure_category or "unknown",
            status=p.status or "pending",
            created_at=p.created_at.isoformat() if p.created_at else "",
            applied_at=p.applied_at.isoformat() if p.applied_at else None,
        )
        for p in proposals
    ]


@router.post("/proposals/{proposal_id}/apply")
async def apply_healing_proposal(
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "qa_engineer")),
):
    """Apply a saved healing proposal to its script."""
    proposal = await db.get(HealingProposalModel, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Healing proposal not found")

    script = await db.get(AutomationScript, proposal.script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Automation script not found")

    # Apply the proposed code
    script.code = proposal.proposed_code
    script.is_healed = True
    script.healing_proposal_id = proposal.id

    # Mark proposal as applied
    from datetime import datetime, timezone
    proposal.status = "applied"
    proposal.applied_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "id": str(proposal.id),
        "script_id": str(script.id),
        "status": "applied",
        "message": "Healing proposal applied successfully.",
    }