"""Test Suites API — CRUD for TestSuite + TestCase + execution management."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.models.test import TestCase, TestExecution, TestSuite
from app.schemas.testcase import (
    TestCaseDBCreate, 
    TestCaseDBOut, 
    TestSuiteCreate, 
    TestSuiteOut, 
    TestSuiteUpdate,
    TestCaseUpdate,
    TestCaseOut,
    RequirementCoverageReport,
)
from app.services import manual_test_service

router = APIRouter()


@router.get("", response_model=List[TestSuiteOut])
async def list_test_suites(
    project_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List test suites scoped to the current workspace."""
    query = select(TestSuite)
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("workspace_id")
    if org_id:
        query = query.where(TestSuite.organization_id == org_id)
    if ws_id:
        query = query.where(TestSuite.workspace_id == ws_id)
    if project_id:
        query = query.where(TestSuite.project_id == project_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/coverage/{project_id}", response_model=RequirementCoverageReport)
async def get_requirement_coverage(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get requirement coverage report for a project."""
    return await manual_test_service.get_requirement_coverage(db, project_id)


@router.get("/{suite_id}", response_model=TestSuiteOut)
async def get_test_suite(
    suite_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(TestSuite).where(TestSuite.id == suite_id))
    suite = result.scalars().first()
    if not suite:
        raise HTTPException(status_code=404, detail="Test suite not found")
    return suite


@router.post("", response_model=TestSuiteOut, status_code=status.HTTP_201_CREATED)
async def create_test_suite(
    payload: TestSuiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "automation_engineer")),
):
    """Create a new test suite. Requires admin, QA lead, or automation engineer."""
    if not payload.organization_id:
        payload.organization_id = current_user.get("organization_id")
    if not payload.workspace_id:
        payload.workspace_id = current_user.get("workspace_id")

    suite = TestSuite(
        name=payload.name,
        description=payload.description,
        type=payload.type,
        project_id=payload.project_id,
        requirement_id=payload.requirement_id,
        organization_id=payload.organization_id,
        workspace_id=payload.workspace_id,
    )
    db.add(suite)
    await db.commit()
    await db.refresh(suite)
    return suite


@router.put("/{suite_id}", response_model=TestSuiteOut)
async def update_test_suite(
    suite_id: uuid.UUID,
    payload: TestSuiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead")),
):
    result = await db.execute(select(TestSuite).where(TestSuite.id == suite_id))
    suite = result.scalars().first()
    if not suite:
        raise HTTPException(status_code=404, detail="Test suite not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(suite, field, value)

    await db.commit()
    await db.refresh(suite)
    return suite


@router.delete("/{suite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_suite(
    suite_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "org_owner")),
):
    result = await db.execute(select(TestSuite).where(TestSuite.id == suite_id))
    suite = result.scalars().first()
    if not suite:
        raise HTTPException(status_code=404, detail="Test suite not found")
    await db.delete(suite)
    await db.commit()


# ── Test Cases within a Suite ──────────────────────────────────────────────

@router.get("/{suite_id}/cases", response_model=List[TestCaseDBOut])
async def list_test_cases(
    suite_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all test cases in a suite."""
    return await manual_test_service.list_test_cases(db, suite_id)


@router.post("/{suite_id}/cases", response_model=TestCaseDBOut,
             status_code=status.HTTP_201_CREATED)
async def create_test_case(
    suite_id: uuid.UUID,
    payload: TestCaseDBCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "automation_engineer")),
):
    """Create a new test case with initial versioning."""
    if not payload.organization_id:
        payload.organization_id = current_user.get("organization_id")
    if not payload.workspace_id:
        payload.workspace_id = current_user.get("workspace_id")

    return await manual_test_service.create_test_case(db, suite_id, payload)


@router.get("/{suite_id}/cases/{case_id}", response_model=TestCaseDBOut)
async def get_test_case(
    suite_id: uuid.UUID,
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    case = await manual_test_service.get_test_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Test case not found")
    return case


@router.put("/{suite_id}/cases/{case_id}", response_model=TestCaseDBOut)
async def update_test_case(
    suite_id: uuid.UUID,
    case_id: uuid.UUID,
    payload: TestCaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead")),
):
    """Update a test case and create a new version snapshot."""
    case = await manual_test_service.update_test_case(db, case_id, payload)
    if not case:
        raise HTTPException(status_code=404, detail="Test case not found")
    return case


@router.delete("/{suite_id}/cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_case(
    suite_id: uuid.UUID,
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "org_owner")),
):
    success = await manual_test_service.delete_test_case(db, case_id)
    if not success:
        raise HTTPException(status_code=404, detail="Test case not found")
    return None
