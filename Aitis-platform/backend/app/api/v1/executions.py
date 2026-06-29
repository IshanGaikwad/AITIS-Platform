"""Executions API — Manual test execution sessions and results."""

import uuid
from typing import List, Tuple, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.models.test import TestCase, TestStep
from app.schemas.testcase import (
    TestExecutionCreate,
    TestExecutionOut,
    TestExecutionUpdate,
    StepExecutionUpdate,
    StepExecutionOut,
    TestCaseExecutionOut,
)
from app.services import manual_test_service

router = APIRouter()


async def _enrich_case_executions(db: AsyncSession, case_execs) -> List[dict]:
    """Enrich TestCaseExecution objects with test_case_title and step details."""
    # Collect all test_case_ids and step_ids
    test_case_ids = set()
    step_ids = set()
    for ce in case_execs:
        test_case_ids.add(ce.test_case_id)
        for se in getattr(ce, "step_executions", []) or []:
            step_ids.add(se.step_id)

    # Batch-load test cases
    tc_map: Dict[uuid.UUID, str] = {}
    if test_case_ids:
        result = await db.execute(
            select(TestCase.id, TestCase.title).where(TestCase.id.in_(test_case_ids))
        )
        for row in result.all():
            tc_map[row[0]] = row[1]

    # Batch-load test steps
    step_map: Dict[uuid.UUID, dict] = {}
    if step_ids:
        result = await db.execute(
            select(TestStep.id, TestStep.action, TestStep.expected_result, TestStep.order)
            .where(TestStep.id.in_(step_ids))
        )
        for row in result.all():
            step_map[row[0]] = {
                "step_action": row[1],
                "step_expected_result": row[2],
                "step_order": row[3],
            }

    # Build enriched dicts
    enriched = []
    for ce in case_execs:
        ce_dict = {
            "id": ce.id,
            "execution_id": ce.execution_id,
            "test_case_id": ce.test_case_id,
            "status": ce.status,
            "started_at": ce.started_at,
            "finished_at": ce.finished_at,
            "duration_seconds": ce.duration_seconds,
            "error_message": ce.error_message,
            "stack_trace": ce.stack_trace,
            "artifacts": ce.artifacts,
            "organization_id": ce.organization_id,
            "workspace_id": ce.workspace_id,
            "created_at": ce.created_at,
            "updated_at": ce.updated_at,
            "test_case_title": tc_map.get(ce.test_case_id),
            "step_executions": [],
        }
        for se in getattr(ce, "step_executions", []) or []:
            se_dict = {
                "id": se.id,
                "case_execution_id": se.case_execution_id,
                "step_id": se.step_id,
                "status": se.status,
                "actual_result": se.actual_result,
                "comment": se.comment,
                "screenshot_url": se.screenshot_url,
                "duration_seconds": se.duration_seconds,
                "organization_id": se.organization_id,
                "workspace_id": se.workspace_id,
                "created_at": se.created_at,
                "updated_at": se.updated_at,
                **step_map.get(se.step_id, {}),
            }
            ce_dict["step_executions"].append(se_dict)
        enriched.append(ce_dict)
    return enriched

@router.post("", response_model=TestExecutionOut, status_code=status.HTTP_201_CREATED)
async def create_execution(
    payload: TestExecutionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Start a new manual execution session."""
    if not payload.organization_id:
        payload.organization_id = current_user.get("organization_id")
    if not payload.workspace_id:
        payload.workspace_id = current_user.get("workspace_id")
    
    return await manual_test_service.create_execution(
        db, payload, executed_by=current_user.get("id")
    )

@router.get("/{execution_id}", response_model=TestExecutionOut)
async def get_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    execution = await manual_test_service.get_execution(db, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution session not found")
    return execution

@router.get("/suite/{suite_id}", response_model=Tuple[List[TestExecutionOut], int])
async def list_executions(
    suite_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List execution sessions for a specific suite."""
    return await manual_test_service.list_executions(db, suite_id, skip, limit)

@router.patch("/{execution_id}", response_model=TestExecutionOut)
async def update_execution(
    execution_id: uuid.UUID,
    payload: TestExecutionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    execution = await manual_test_service.update_execution(db, execution_id, payload)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution session not found")
    return execution

@router.post("/{execution_id}/complete", response_model=TestExecutionOut)
async def complete_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Finalize an execution session and compute summary."""
    execution = await manual_test_service.complete_execution(db, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution session not found")
    return execution

@router.patch("/steps/{step_execution_id}", response_model=StepExecutionOut)
async def record_step_result(
    step_execution_id: uuid.UUID,
    payload: StepExecutionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Record the result of a specific test step during execution."""
    result = await manual_test_service.record_step_result(db, step_execution_id, payload)
    if not result:
        raise HTTPException(status_code=404, detail="Step execution not found")
    # Enrich with step details
    step_data = await db.execute(
        select(TestStep.action, TestStep.expected_result, TestStep.order)
        .where(TestStep.id == result.step_id)
    )
    row = step_data.first()
    enriched = {
        "id": result.id,
        "case_execution_id": result.case_execution_id,
        "step_id": result.step_id,
        "status": result.status,
        "actual_result": result.actual_result,
        "comment": result.comment,
        "screenshot_url": result.screenshot_url,
        "duration_seconds": result.duration_seconds,
        "organization_id": result.organization_id,
        "workspace_id": result.workspace_id,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
    }
    if row:
        enriched["step_action"] = row[0]
        enriched["step_expected_result"] = row[1]
        enriched["step_order"] = row[2]
    return enriched


@router.get("/{execution_id}/cases", response_model=List[TestCaseExecutionOut])
async def get_case_executions(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all test case executions for an execution session."""
    case_execs = await manual_test_service.get_case_executions(db, execution_id)
    return await _enrich_case_executions(db, case_execs)


@router.get("/cases/{case_execution_id}/steps", response_model=List[StepExecutionOut])
async def get_step_executions(
    case_execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all step executions for a test case execution."""
    return await manual_test_service.get_step_executions(db, case_execution_id)


@router.post("/{execution_id}/cases", response_model=List[TestCaseExecutionOut], status_code=status.HTTP_201_CREATED)
async def create_case_executions(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create TestCaseExecution + StepExecution records for all test cases in the suite."""
    case_execs = await manual_test_service.create_case_executions(db, execution_id)
    return await _enrich_case_executions(db, case_execs)
