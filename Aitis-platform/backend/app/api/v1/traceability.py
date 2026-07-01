"""Traceability API — requirement-to-test-to-defect traceability matrix.

Phase 6: Full bidirectional traceability from requirements through
test cases and executions to defects, with export support.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.requirement import Requirement
from app.models.test import TestCase, TestSuite, TestExecution, TestCaseExecution
from app.models.artifact import Defect
from app.models.automation import AutomationScript

router = APIRouter()


# ── Pydantic schemas ─────────────────────────────────────────────────
from pydantic import BaseModel


class TraceabilityLink(BaseModel):
    """A single link in the traceability chain."""
    requirement_id: str
    requirement_title: str
    requirement_status: str
    test_suite_id: Optional[str] = None
    test_suite_name: Optional[str] = None
    test_case_id: Optional[str] = None
    test_case_title: Optional[str] = None
    test_case_status: Optional[str] = None
    automation_script_id: Optional[str] = None
    automation_script_name: Optional[str] = None
    last_execution_status: Optional[str] = None
    last_execution_date: Optional[str] = None
    defect_ids: List[str] = []
    defect_count: int = 0


class TraceabilityMatrix(BaseModel):
    """Full traceability matrix for a workspace."""
    workspace_id: str
    total_requirements: int
    total_links: int
    covered_requirements: int
    uncovered_requirements: int
    links: List[TraceabilityLink] = []


class RequirementCoverageItem(BaseModel):
    """Coverage info for a single requirement."""
    requirement_id: str
    requirement_title: Optional[str] = None
    test_case_count: int = 0
    covered: bool = False
    test_cases: List[dict] = []


class RequirementCoverageReport(BaseModel):
    """Coverage report for a workspace."""
    workspace_id: str
    total_requirements: int
    covered_requirements: int
    coverage_percent: float
    items: List[RequirementCoverageItem] = []


# ══════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════

@router.get("/{workspace_id}", response_model=TraceabilityMatrix)
async def get_traceability_matrix(
    workspace_id: uuid.UUID,
    requirement_id: Optional[uuid.UUID] = Query(None, description="Filter by requirement"),
    uncovered_only: bool = Query(False, description="Show only uncovered requirements"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get the full traceability matrix for a workspace.

    Maps requirements → test suites → test cases → automation scripts → defects.
    """
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("project_id")

    # Get all requirements for the workspace
    req_stmt = select(Requirement).where(
        Requirement.workspace_id == workspace_id,
        Requirement.organization_id == org_id,
        Requirement.project_id == ws_id,
    )
    if requirement_id:
        req_stmt = req_stmt.where(Requirement.id == requirement_id)

    req_result = await db.execute(req_stmt)
    requirements = req_result.scalars().all()

    links: List[TraceabilityLink] = []
    covered_count = 0

    for req in requirements:
        # Find test suites linked to this requirement
        suite_stmt = select(TestSuite).where(
            TestSuite.requirement_id == req.id,
            TestSuite.organization_id == org_id,
            TestSuite.project_id == ws_id,
        )
        suite_result = await db.execute(suite_stmt)
        suites = suite_result.scalars().all()

        if not suites:
            # Uncovered requirement
            if not uncovered_only or True:  # Always show uncovered
                links.append(TraceabilityLink(
                    requirement_id=str(req.id),
                    requirement_title=req.title,
                    requirement_status=req.status or "unknown",
                ))
            continue

        covered_count += 1
        for suite in suites:
            # Get test cases in this suite
            tc_stmt = select(TestCase).where(
                TestCase.test_suite_id == suite.id,
                TestCase.organization_id == org_id,
                TestCase.project_id == ws_id,
            )
            tc_result = await db.execute(tc_stmt)
            test_cases = tc_result.scalars().all()

            if not test_cases:
                links.append(TraceabilityLink(
                    requirement_id=str(req.id),
                    requirement_title=req.title,
                    requirement_status=req.status or "unknown",
                    test_suite_id=str(suite.id),
                    test_suite_name=suite.name,
                ))
                continue

            for tc in test_cases:
                # Find automation scripts (by name matching or explicit link)
                auto_stmt = select(AutomationScript).where(
                    AutomationScript.name.ilike(f"%{tc.title}%"),
                    AutomationScript.organization_id == org_id,
                    AutomationScript.project_id == ws_id,
                ).limit(1)
                auto_result = await db.execute(auto_stmt)
                auto_script = auto_result.scalar_one_or_none()

                # Find last execution status
                last_exec_stmt = (
                    select(TestCaseExecution)
                    .where(
                        TestCaseExecution.test_case_id == tc.id,
                        TestCaseExecution.organization_id == org_id,
                        TestCaseExecution.project_id == ws_id,
                    )
                    .order_by(TestCaseExecution.created_at.desc())
                    .limit(1)
                )
                last_exec_result = await db.execute(last_exec_stmt)
                last_exec = last_exec_result.scalar_one_or_none()

                # Find linked defects
                defect_stmt = select(Defect).where(
                    Defect.case_execution_id == (last_exec.id if last_exec else None),
                ) if last_exec else None
                defect_ids = []
                if defect_stmt is not None:
                    defect_result = await db.execute(defect_stmt)
                    defects = defect_result.scalars().all()
                    defect_ids = [str(d.id) for d in defects]

                links.append(TraceabilityLink(
                    requirement_id=str(req.id),
                    requirement_title=req.title,
                    requirement_status=req.status or "unknown",
                    test_suite_id=str(suite.id),
                    test_suite_name=suite.name,
                    test_case_id=str(tc.id),
                    test_case_title=tc.title,
                    test_case_status=tc.status or "unknown",
                    automation_script_id=str(auto_script.id) if auto_script else None,
                    automation_script_name=auto_script.name if auto_script else None,
                    last_execution_status=last_exec.status if last_exec else None,
                    last_execution_date=last_exec.created_at.isoformat() if last_exec and last_exec.created_at else None,
                    defect_ids=defect_ids,
                    defect_count=len(defect_ids),
                ))

    return TraceabilityMatrix(
        workspace_id=str(workspace_id),
        total_requirements=len(requirements),
        total_links=len(links),
        covered_requirements=covered_count,
        uncovered_requirements=len(requirements) - covered_count,
        links=links,
    )


@router.get("/{workspace_id}/coverage", response_model=RequirementCoverageReport)
async def get_requirement_coverage(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get requirement coverage report for a workspace."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("project_id")

    # Get all requirements
    req_result = await db.execute(
        select(Requirement).where(
            Requirement.workspace_id == workspace_id,
            Requirement.organization_id == org_id,
            Requirement.project_id == ws_id,
        )
    )
    requirements = req_result.scalars().all()

    items: List[RequirementCoverageItem] = []
    covered_count = 0

    for req in requirements:
        # Find test suites linked to this requirement
        suite_result = await db.execute(
            select(TestSuite).where(
                TestSuite.requirement_id == req.id,
                TestSuite.organization_id == org_id,
                TestSuite.project_id == ws_id,
            )
        )
        suites = suite_result.scalars().all()

        test_cases_list = []
        for suite in suites:
            tc_result = await db.execute(
                select(TestCase.id, TestCase.title).where(
                    TestCase.test_suite_id == suite.id,
                    TestCase.organization_id == org_id,
                    TestCase.project_id == ws_id,
                )
            )
            for row in tc_result.all():
                test_cases_list.append({"id": str(row[0]), "title": row[1]})

        covered = len(test_cases_list) > 0
        if covered:
            covered_count += 1

        items.append(RequirementCoverageItem(
            requirement_id=str(req.id),
            requirement_title=req.title,
            test_case_count=len(test_cases_list),
            covered=covered,
            test_cases=test_cases_list,
        ))

    total = len(requirements)
    return RequirementCoverageReport(
        workspace_id=str(workspace_id),
        total_requirements=total,
        covered_requirements=covered_count,
        coverage_percent=round(covered_count / total * 100, 1) if total > 0 else 0.0,
        items=items,
    )