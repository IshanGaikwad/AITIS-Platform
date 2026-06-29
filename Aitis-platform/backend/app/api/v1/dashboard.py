"""Dashboard API — aggregated metrics, trends, and release readiness.

Phase 6: Provides project-level dashboards with test execution trends,
defect burndown, coverage metrics, and release readiness scoring.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.test import TestCase, TestExecution, TestCaseExecution, ExecutionStatus
from app.models.artifact import Defect, DefectStatus, DefectSeverity
from app.models.requirement import Requirement, RequirementStatus
from app.models.automation import AutomationScript, ExecutionJob, ExecutionJobStatus

router = APIRouter()


# ── Pydantic schemas ─────────────────────────────────────────────────
from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    """Top-level dashboard metrics for a project."""
    total_requirements: int = 0
    total_test_cases: int = 0
    total_automation_scripts: int = 0
    total_defects: int = 0
    open_defects: int = 0
    critical_defects: int = 0
    last_execution_pass_rate: float = 0.0
    coverage_percent: float = 0.0
    automation_coverage_percent: float = 0.0


class ExecutionTrend(BaseModel):
    """Daily execution trend data point."""
    date: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0


class DefectBurndown(BaseModel):
    """Weekly defect burndown data point."""
    week: str
    opened: int = 0
    closed: int = 0
    open_total: int = 0


class ReleaseReadiness(BaseModel):
    """Release readiness assessment."""
    overall_score: float = 0.0  # 0-100
    status: str = "unknown"  # go | caution | no_go
    test_pass_rate: float = 0.0
    coverage_score: float = 0.0
    defect_score: float = 0.0
    automation_score: float = 0.0
    blocker_count: int = 0
    critical_count: int = 0
    recommendations: List[str] = []


class DashboardResponse(BaseModel):
    metrics: DashboardMetrics
    execution_trends: List[ExecutionTrend] = []
    defect_burndown: List[DefectBurndown] = []
    release_readiness: ReleaseReadiness = ReleaseReadiness()


# ══════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════

@router.get("/{project_id}", response_model=DashboardResponse)
async def get_dashboard(
    project_id: uuid.UUID,
    days: int = Query(30, ge=7, le=365, description="Trend window in days"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get full dashboard for a project."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("workspace_id")

    # ── Metrics ────────────────────────────────────────────────────
    metrics = await _compute_metrics(db, project_id, org_id, ws_id)

    # ── Execution trends ───────────────────────────────────────────
    trends = await _compute_execution_trends(db, project_id, org_id, ws_id, days)

    # ── Defect burndown ────────────────────────────────────────────
    burndown = await _compute_defect_burndown(db, project_id, org_id, ws_id, days)

    # ── Release readiness ──────────────────────────────────────────
    readiness = await _compute_release_readiness(db, project_id, org_id, ws_id, metrics)

    return DashboardResponse(
        metrics=metrics,
        execution_trends=trends,
        defect_burndown=burndown,
        release_readiness=readiness,
    )


@router.get("/{project_id}/release-readiness", response_model=ReleaseReadiness)
async def get_release_readiness(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get release readiness assessment for a project."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("workspace_id")
    metrics = await _compute_metrics(db, project_id, org_id, ws_id)
    return await _compute_release_readiness(db, project_id, org_id, ws_id, metrics)


# ── Internal helpers ─────────────────────────────────────────────────

async def _compute_metrics(db: AsyncSession, project_id: uuid.UUID, org_id, ws_id) -> DashboardMetrics:
    """Compute top-level dashboard metrics."""

    # Requirements count
    req_result = await db.execute(
        select(func.count()).select_from(Requirement).where(
            Requirement.project_id == project_id,
            Requirement.organization_id == org_id,
            Requirement.workspace_id == ws_id,
        )
    )
    total_reqs = req_result.scalar() or 0

    # Test cases count
    tc_result = await db.execute(
        select(func.count()).select_from(TestCase).where(
            TestCase.organization_id == org_id,
            TestCase.workspace_id == ws_id,
        )
    )
    total_tcs = tc_result.scalar() or 0

    # Automation scripts
    auto_result = await db.execute(
        select(func.count()).select_from(AutomationScript).where(
            AutomationScript.organization_id == org_id,
            AutomationScript.workspace_id == ws_id,
        )
    )
    total_auto = auto_result.scalar() or 0

    # Defects
    defect_base = select(Defect).where(
        Defect.project_id == project_id,
        Defect.organization_id == org_id,
        Defect.workspace_id == ws_id,
    )
    total_defects_result = await db.execute(
        select(func.count()).select_from(defect_base.subquery())
    )
    total_defects = total_defects_result.scalar() or 0

    open_defects_result = await db.execute(
        select(func.count()).select_from(
            defect_base.where(Defect.status.in_(["open", "in_progress"])).subquery()
        )
    )
    open_defects = open_defects_result.scalar() or 0

    critical_defects_result = await db.execute(
        select(func.count()).select_from(
            defect_base.where(
                Defect.severity.in_(["blocker", "critical"]),
                Defect.status.in_(["open", "in_progress"]),
            ).subquery()
        )
    )
    critical_defects = critical_defects_result.scalar() or 0

    # Last execution pass rate
    last_exec = await db.execute(
        select(TestExecution)
        .where(
            TestExecution.organization_id == org_id,
            TestExecution.workspace_id == ws_id,
        )
        .order_by(TestExecution.created_at.desc())
        .limit(1)
    )
    last_exec_obj = last_exec.scalar_one_or_none()
    pass_rate = 0.0
    if last_exec_obj and last_exec_obj.summary:
        summary = last_exec_obj.summary if isinstance(last_exec_obj.summary, dict) else {}
        total = summary.get("total_cases", 0)
        passed = summary.get("passed", 0)
        pass_rate = (passed / total * 100) if total > 0 else 0.0

    # Coverage: requirements with at least one test case
    # Count requirements that have linked test cases via test_suites
    cov_result = await db.execute(
        select(func.count(func.distinct(Requirement.id)))
        .select_from(Requirement)
        .where(
            Requirement.project_id == project_id,
            Requirement.organization_id == org_id,
            Requirement.workspace_id == ws_id,
        )
    )
    covered = 0
    if total_reqs > 0:
        # Check which requirements have test suites linked
        from app.models.test import TestSuite
        suite_result = await db.execute(
            select(func.count(func.distinct(TestSuite.requirement_id)))
            .where(
                TestSuite.requirement_id.isnot(None),
                TestSuite.organization_id == org_id,
                TestSuite.workspace_id == ws_id,
            )
        )
        covered = suite_result.scalar() or 0

    coverage_pct = (covered / total_reqs * 100) if total_reqs > 0 else 0.0
    auto_coverage = (total_auto / total_tcs * 100) if total_tcs > 0 else 0.0

    return DashboardMetrics(
        total_requirements=total_reqs,
        total_test_cases=total_tcs,
        total_automation_scripts=total_auto,
        total_defects=total_defects,
        open_defects=open_defects,
        critical_defects=critical_defects,
        last_execution_pass_rate=round(pass_rate, 1),
        coverage_percent=round(coverage_pct, 1),
        automation_coverage_percent=round(auto_coverage, 1),
    )


async def _compute_execution_trends(
    db: AsyncSession, project_id: uuid.UUID, org_id, ws_id, days: int
) -> List[ExecutionTrend]:
    """Compute daily execution trends."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Get all executions in the window
    result = await db.execute(
        select(TestExecution)
        .where(
            TestExecution.organization_id == org_id,
            TestExecution.workspace_id == ws_id,
            TestExecution.created_at >= cutoff,
        )
        .order_by(TestExecution.created_at)
    )
    executions = result.scalars().all()

    # Group by date
    from collections import defaultdict
    daily: dict = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})

    for ex in executions:
        if ex.created_at:
            date_key = ex.created_at.strftime("%Y-%m-%d")
            summary = ex.summary if isinstance(ex.summary, dict) else {}
            daily[date_key]["total"] += summary.get("total_cases", 0)
            daily[date_key]["passed"] += summary.get("passed", 0)
            daily[date_key]["failed"] += summary.get("failed", 0)

    trends = []
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        data = daily.get(d, {"total": 0, "passed": 0, "failed": 0})
        total = data["total"]
        trends.append(ExecutionTrend(
            date=d,
            total=total,
            passed=data["passed"],
            failed=data["failed"],
            pass_rate=round(data["passed"] / total * 100, 1) if total > 0 else 0.0,
        ))

    return trends


async def _compute_defect_burndown(
    db: AsyncSession, project_id: uuid.UUID, org_id, ws_id, days: int
) -> List[DefectBurndown]:
    """Compute weekly defect burndown."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(Defect)
        .where(
            Defect.project_id == project_id,
            Defect.organization_id == org_id,
            Defect.workspace_id == ws_id,
        )
        .order_by(Defect.created_at)
    )
    defects = result.scalars().all()

    from collections import defaultdict
    weekly: dict = defaultdict(lambda: {"opened": 0, "closed": 0})

    for d in defects:
        if d.created_at and d.created_at >= cutoff:
            wk = d.created_at.strftime("%Y-W%U")
            weekly[wk]["opened"] += 1
        if d.updated_at and d.updated_at >= cutoff and d.status == "closed":
            wk = d.updated_at.strftime("%Y-W%U")
            weekly[wk]["closed"] += 1

    # Build running total
    burndown = []
    running_open = 0
    for i in range(0, days, 7):
        d = datetime.now(timezone.utc) - timedelta(days=days - i)
        wk = d.strftime("%Y-W%U")
        data = weekly.get(wk, {"opened": 0, "closed": 0})
        running_open += data["opened"] - data["closed"]
        burndown.append(DefectBurndown(
            week=wk,
            opened=data["opened"],
            closed=data["closed"],
            open_total=max(0, running_open),
        ))

    return burndown


async def _compute_release_readiness(
    db: AsyncSession, project_id: uuid.UUID, org_id, ws_id, metrics: DashboardMetrics
) -> ReleaseReadiness:
    """Compute release readiness score and recommendations."""
    recommendations: List[str] = []

    # Test pass rate score (0-30)
    pass_score = min(30, metrics.last_execution_pass_rate * 0.3)
    if metrics.last_execution_pass_rate < 90:
        recommendations.append(f"Test pass rate is {metrics.last_execution_pass_rate}% — target ≥ 90%")

    # Coverage score (0-25)
    cov_score = min(25, metrics.coverage_percent * 0.25)
    if metrics.coverage_percent < 80:
        recommendations.append(f"Requirement coverage is {metrics.coverage_percent}% — target ≥ 80%")

    # Defect score (0-25)
    defect_score = 25.0
    if metrics.critical_defects > 0:
        defect_score -= metrics.critical_defects * 10
        recommendations.append(f"{metrics.critical_defects} critical/blocker defects open — must be resolved")
    if metrics.open_defects > 10:
        defect_score -= 5
        recommendations.append(f"{metrics.open_defects} open defects — consider reducing before release")
    defect_score = max(0, defect_score)

    # Automation score (0-20)
    auto_score = min(20, metrics.automation_coverage_percent * 0.2)
    if metrics.automation_coverage_percent < 50:
        recommendations.append(f"Automation coverage is {metrics.automation_coverage_percent}% — target ≥ 50%")

    overall = pass_score + cov_score + defect_score + auto_score

    if overall >= 80:
        status = "go"
    elif overall >= 60:
        status = "caution"
    else:
        status = "no_go"

    return ReleaseReadiness(
        overall_score=round(overall, 1),
        status=status,
        test_pass_rate=round(pass_score, 1),
        coverage_score=round(cov_score, 1),
        defect_score=round(defect_score, 1),
        automation_score=round(auto_score, 1),
        blocker_count=metrics.critical_defects,
        critical_count=metrics.critical_defects,
        recommendations=recommendations,
    )