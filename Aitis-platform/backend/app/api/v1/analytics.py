"""Analytics API — failure classification, flakiness detection, and self-healing.

Phase 7: Provides endpoints for analyzing test failures, detecting flaky tests,
and generating/applying self-healing proposals.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.models.automation import AutomationScript, ExecutionJob, ExecutionResult
from app.models.artifact import HealingProposal as HealingProposalModel, HealingStatus
from app.services.failure_classifier import (
    classify_failure,
    detect_flakiness,
    generate_flakiness_report,
    FailureCategory,
)
from app.services.self_healing import (
    generate_healing_proposal,
    heal_selector,
    apply_healing,
    SelectorFix,
)

router = APIRouter()


# ── Pydantic schemas ─────────────────────────────────────────────────
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class FailureClassifyRequest(BaseModel):
    error_message: str
    stack_trace: Optional[str] = None
    test_name: Optional[str] = None


class FailureClassifyResponse(BaseModel):
    category: str
    confidence: float
    explanation: str
    suggested_fix: str
    is_flaky_indicator: bool
    matched_patterns: List[str] = []


class FlakinessRequest(BaseModel):
    execution_history: List[dict]
    threshold: float = 0.3


class FlakinessResponse(BaseModel):
    is_flaky: bool
    flakiness_score: float
    failure_rate: float
    total_runs: int
    failures: int = 0
    recommendation: str


class FlakinessReportRequest(BaseModel):
    test_results: List[dict]


class FlakyTestItem(BaseModel):
    test_name: str
    flakiness_score: float
    failure_rate: float
    total_runs: int
    classification: Optional[dict] = None


class FlakinessReportResponse(BaseModel):
    summary: dict
    flaky_tests: List[FlakyTestItem] = []
    consistently_failing: List[dict] = []
    recommendation: str


class HealSelectorRequest(BaseModel):
    selector: str
    error_message: str
    page_context: Optional[str] = None


class SelectorFixOut(BaseModel):
    original_selector: str
    proposed_selector: str
    selector_type: str
    confidence: float
    reasoning: str


class HealSelectorResponse(BaseModel):
    fixes: List[SelectorFixOut]


class HealingProposalRequest(BaseModel):
    script_id: str
    script_code: str
    error_message: str
    stack_trace: Optional[str] = None


class HealingProposalOut(BaseModel):
    id: str
    script_id: str
    original_code: str
    proposed_code: str
    changes: List[SelectorFixOut]
    explanation: str
    confidence_score: float
    failure_category: str
    status: str = "proposed"
    created_at: Optional[datetime] = None


class ApplyHealingRequest(BaseModel):
    script_code: str
    fixes: List[SelectorFixOut]
    auto_apply: bool = False


class ApplyHealingResponse(BaseModel):
    healed_code: str
    changes_applied: int


# ══════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════

@router.post("/classify-failure", response_model=FailureClassifyResponse)
async def classify_test_failure(
    payload: FailureClassifyRequest,
    current_user=Depends(get_current_user),
):
    """Classify a test failure from its error message."""
    result = classify_failure(
        error_message=payload.error_message,
        stack_trace=payload.stack_trace,
        test_name=payload.test_name,
    )
    return FailureClassifyResponse(
        category=result.category.value,
        confidence=result.confidence,
        explanation=result.explanation,
        suggested_fix=result.suggested_fix,
        is_flaky_indicator=result.is_flaky_indicator,
        matched_patterns=result.matched_patterns,
    )


@router.post("/detect-flakiness", response_model=FlakinessResponse)
async def detect_test_flakiness(
    payload: FlakinessRequest,
    current_user=Depends(get_current_user),
):
    """Detect if a test is flaky based on execution history."""
    result = detect_flakiness(payload.execution_history, payload.threshold)
    return FlakinessResponse(**result)


@router.post("/flakiness-report", response_model=FlakinessReportResponse)
async def get_flakiness_report(
    payload: FlakinessReportRequest,
    current_user=Depends(get_current_user),
):
    """Generate a flakiness report for a set of test results."""
    result = generate_flakiness_report(payload.test_results)
    return FlakinessReportResponse(**result)


@router.post("/heal-selector", response_model=HealSelectorResponse)
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
    return HealSelectorResponse(
        fixes=[
            SelectorFixOut(
                original_selector=f.original_selector,
                proposed_selector=f.proposed_selector,
                selector_type=f.selector_type,
                confidence=f.confidence,
                reasoning=f.reasoning,
            )
            for f in fixes
        ]
    )


@router.post("/healing-proposal", response_model=HealingProposalOut)
async def create_healing_proposal(
    payload: HealingProposalRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "qa_engineer")),
):
    """Generate and persist a healing proposal for a failing script."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("workspace_id")

    proposal = generate_healing_proposal(
        script_code=payload.script_code,
        error_message=payload.error_message,
        stack_trace=payload.stack_trace,
        script_id=payload.script_id,
    )

    if not proposal:
        raise HTTPException(
            status_code=422,
            detail="Could not generate a healing proposal for this failure. "
                   "The failure may not be related to element selectors.",
        )

    # Persist to DB
    db_proposal = HealingProposalModel(
        script_id=uuid.UUID(payload.script_id) if payload.script_id else None,
        status=HealingStatus.proposed.value,
        original_code=proposal.original_code,
        proposed_code=proposal.proposed_code,
        explanation=proposal.explanation,
        confidence_score=proposal.confidence_score,
        organization_id=org_id,
        workspace_id=ws_id,
    )
    db.add(db_proposal)
    await db.commit()
    await db.refresh(db_proposal)

    return HealingProposalOut(
        id=str(db_proposal.id),
        script_id=payload.script_id,
        original_code=proposal.original_code,
        proposed_code=proposal.proposed_code,
        changes=[
            SelectorFixOut(
                original_selector=c.original_selector,
                proposed_selector=c.proposed_selector,
                selector_type=c.selector_type,
                confidence=c.confidence,
                reasoning=c.reasoning,
            )
            for c in proposal.changes
        ],
        explanation=proposal.explanation,
        confidence_score=proposal.confidence_score,
        failure_category=proposal.failure_category.value,
        status=db_proposal.status,
        created_at=db_proposal.created_at,
    )


@router.post("/apply-healing", response_model=ApplyHealingResponse)
async def apply_healing_fixes(
    payload: ApplyHealingRequest,
    current_user=Depends(require_role("administrator", "qa_lead", "qa_engineer")),
):
    """Apply healing fixes to a script and return the healed code."""
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

    healed = apply_healing(payload.script_code, fixes, payload.auto_apply)
    changes = sum(1 for f in fixes if f.original_selector in payload.script_code)

    return ApplyHealingResponse(
        healed_code=healed,
        changes_applied=changes,
    )


@router.get("/healing-proposals", response_model=List[HealingProposalOut])
async def list_healing_proposals(
    script_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List healing proposals, optionally filtered by script or status."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("workspace_id")

    stmt = select(HealingProposalModel).where(
        HealingProposalModel.organization_id == org_id,
        HealingProposalModel.workspace_id == ws_id,
    )
    if script_id:
        stmt = stmt.where(HealingProposalModel.script_id == script_id)
    if status_filter:
        stmt = stmt.where(HealingProposalModel.status == status_filter)

    stmt = stmt.order_by(HealingProposalModel.created_at.desc())
    result = await db.execute(stmt)
    proposals = result.scalars().all()

    return [
        HealingProposalOut(
            id=str(p.id),
            script_id=str(p.script_id) if p.script_id else "",
            original_code=p.original_code,
            proposed_code=p.proposed_code,
            changes=[],
            explanation=p.explanation or "",
            confidence_score=p.confidence_score or 0.0,
            failure_category="unknown",
            status=p.status,
            created_at=p.created_at,
        )
        for p in proposals
    ]


@router.post("/healing-proposals/{proposal_id}/apply")
async def apply_healing_proposal(
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "qa_engineer")),
):
    """Apply a healing proposal to its associated script."""
    proposal = await db.get(HealingProposalModel, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Healing proposal not found")

    if proposal.script_id:
        script = await db.get(AutomationScript, proposal.script_id)
        if script:
            script.code = proposal.proposed_code
            script.is_healed = True
            script.healing_proposal_id = proposal.id

    proposal.status = HealingStatus.applied.value
    proposal.applied_at = datetime.now()
    await db.commit()

    return {"status": "applied", "proposal_id": str(proposal_id)}


@router.post("/healing-proposals/{proposal_id}/revert")
async def revert_healing_proposal(
    proposal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead")),
):
    """Revert a previously applied healing proposal."""
    proposal = await db.get(HealingProposalModel, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Healing proposal not found")

    if proposal.script_id:
        script = await db.get(AutomationScript, proposal.script_id)
        if script:
            script.code = proposal.original_code
            script.is_healed = False
            script.healing_proposal_id = None

    proposal.status = HealingStatus.reverted.value
    proposal.reverted_at = datetime.now()
    await db.commit()

    return {"status": "reverted", "proposal_id": str(proposal_id)}