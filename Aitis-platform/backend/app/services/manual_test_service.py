"""Phase 2: Manual Test Management & Execution Service.

Provides business logic for:
- Test suite folders (hierarchical CRUD)
- Test cases with version history, review workflow, bulk operations
- Manual test execution sessions with step-level result recording
- Defect draft creation from failed steps
- CSV import/export
- Requirement coverage reporting
"""

import csv
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.automation import AutomationScript
from app.services.runners import RunnerCase, RunnerRequest, RunnerScript, get_runner
from app.services.runners.simulated import SimulatedRunner
from app.models.test import (
    DefectDraft,
    ExecutionStatus,
    ExecutionType,
    ReviewStatus,
    StepExecution,
    StepType,
    TestCase,
    TestCaseExecution,
    TestCaseVersion,
    TestExecution,
    TestPriority,
    TestStatus,
    TestStep,
    TestSuite,
    TestSuiteFolder,
    TestType,
)
from app.schemas.testcase import (
    CSVImportResult,
    DefectDraftCreate,
    DefectDraftOut,
    RequirementCoverageItem,
    RequirementCoverageReport,
    StepExecutionOut,
    StepExecutionUpdate,
    TestCaseBulkUpdate,
    TestCaseClone,
    TestCaseCreate,
    TestCaseOut,
    TestCaseUpdate,
    TestCaseVersionOut,
    TestExecutionCreate,
    TestExecutionOut,
    TestExecutionUpdate,
    TestStepCreate,
    TestStepOut,
    TestStepUpdate,
    TestSuiteCreate,
    TestSuiteFolderCreate,
    TestSuiteFolderOut,
    TestSuiteFolderUpdate,
    TestSuiteOut,
    TestSuiteUpdate,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _slugify(text: str) -> str:
    import re
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", text.lower()))


async def _snapshot_test_case(db: AsyncSession, tc: TestCase, changed_by: Optional[uuid.UUID], change_summary: Optional[str]) -> None:
    """Create an immutable version snapshot before modifying a test case."""
    snapshot = TestCaseVersion(
        test_case_id=tc.id,
        version=tc.version,
        title=tc.title,
        description=tc.description,
        type=tc.type,
        priority=tc.priority,
        status=tc.status,
        preconditions=tc.preconditions,
        gherkin=tc.gherkin,
        tags=tc.tags,
        requirement_ids=tc.requirement_ids,
        steps_snapshot=[
            {"order": s.order, "type": s.type, "action": s.action,
             "expected_result": s.expected_result, "description": s.description, "test_data": s.test_data}
            for s in (tc.steps or [])
        ],
        changed_by=changed_by,
        change_summary=change_summary,
        organization_id=tc.organization_id,
        project_id=tc.project_id,
    )
    db.add(snapshot)


# ═══════════════════════════════════════════════════════════════════════
# Test Suite Folders
# ═══════════════════════════════════════════════════════════════════════

async def create_folder(db: AsyncSession, data: TestSuiteFolderCreate) -> TestSuiteFolder:
    folder = TestSuiteFolder(**data.model_dump())
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


async def get_folder(db: AsyncSession, folder_id: uuid.UUID) -> Optional[TestSuiteFolder]:
    return await db.get(TestSuiteFolder, folder_id)


async def list_folders(db: AsyncSession, workspace_id: uuid.UUID) -> List[TestSuiteFolder]:
    result = await db.execute(
        select(TestSuiteFolder)
        .where(TestSuiteFolder.workspace_id == workspace_id)
        .order_by(TestSuiteFolder.sort_order, TestSuiteFolder.name)
    )
    return list(result.scalars().all())


async def update_folder(db: AsyncSession, folder_id: uuid.UUID, data: TestSuiteFolderUpdate) -> Optional[TestSuiteFolder]:
    folder = await db.get(TestSuiteFolder, folder_id)
    if not folder:
        return None
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(folder, key, val)
    await db.commit()
    await db.refresh(folder)
    return folder


async def delete_folder(db: AsyncSession, folder_id: uuid.UUID) -> bool:
    folder = await db.get(TestSuiteFolder, folder_id)
    if not folder:
        return False
    # Move child suites to parent folder or root
    parent_id = folder.parent_id
    await db.execute(
        update(TestSuite).where(TestSuite.folder_id == folder_id).values(folder_id=parent_id)
    )
    # Move child folders up
    await db.execute(
        update(TestSuiteFolder).where(TestSuiteFolder.parent_id == folder_id).values(parent_id=parent_id)
    )
    await db.delete(folder)
    await db.commit()
    return True


def _build_folder_tree(folders: List[TestSuiteFolder], parent_id: Optional[uuid.UUID] = None) -> List[TestSuiteFolderOut]:
    """Build a nested folder tree from a flat list."""
    result = []
    for f in folders:
        if f.parent_id == parent_id:
            out = TestSuiteFolderOut.model_validate(f)
            out.children = _build_folder_tree(folders, f.id)
            result.append(out)
    return result


async def get_folder_tree(db: AsyncSession, workspace_id: uuid.UUID) -> List[TestSuiteFolderOut]:
    folders = await list_folders(db, workspace_id)
    return _build_folder_tree(folders)


# ═══════════════════════════════════════════════════════════════════════
# Test Suites
# ═══════════════════════════════════════════════════════════════════════

async def create_suite(db: AsyncSession, data: TestSuiteCreate) -> TestSuite:
    suite = TestSuite(**data.model_dump())
    db.add(suite)
    await db.commit()
    await db.refresh(suite)
    return suite


async def get_suite(db: AsyncSession, suite_id: uuid.UUID) -> Optional[TestSuite]:
    return await db.get(TestSuite, suite_id)


async def list_suites(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    folder_id: Optional[uuid.UUID] = None,
) -> List[TestSuite]:
    stmt = select(TestSuite).where(TestSuite.workspace_id == workspace_id)
    if folder_id is not None:
        stmt = stmt.where(TestSuite.folder_id == folder_id)
    stmt = stmt.order_by(TestSuite.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_suite(db: AsyncSession, suite_id: uuid.UUID, data: TestSuiteUpdate) -> Optional[TestSuite]:
    suite = await db.get(TestSuite, suite_id)
    if not suite:
        return None
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(suite, key, val)
    await db.commit()
    await db.refresh(suite)
    return suite


async def delete_suite(db: AsyncSession, suite_id: uuid.UUID) -> bool:
    suite = await db.get(TestSuite, suite_id)
    if not suite:
        return False
    await db.delete(suite)
    await db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════════
# Test Cases
# ═══════════════════════════════════════════════════════════════════════

def _precond_to_text(value):
    """The preconditions DB column is Text; the API uses a list — join on write."""
    if isinstance(value, (list, tuple)):
        return "\n".join(str(v) for v in value)
    return value


def _uuids_to_str(value):
    """requirement_ids is a JSON column — uuid.UUID objects aren't JSON-serializable."""
    if value is None:
        return None
    return [str(v) for v in value]


async def create_test_case(db: AsyncSession, data: TestCaseCreate) -> TestCase:
    # ``data`` may be a TestCaseCreate or the leaner TestCaseDBCreate, which omits
    # several fields — read optional fields defensively so both shapes work.
    steps_data = getattr(data, "steps", None) or []
    tc = TestCase(
        test_suite_id=data.test_suite_id,
        title=data.title,
        slug=_slugify(data.title),
        description=getattr(data, "description", None),
        type=data.type,
        priority=data.priority,
        status=data.status,
        preconditions=_precond_to_text(getattr(data, "preconditions", None)),
        gherkin=getattr(data, "gherkin", None),
        tags=getattr(data, "tags", None),
        requirement_ids=_uuids_to_str(getattr(data, "requirement_ids", None)),
        owner_id=getattr(data, "owner_id", None),
        review_status=getattr(data, "review_status", None) or "pending",
        risk_tag=getattr(data, "risk_tag", None),
        ac_category=getattr(data, "ac_category", None),
        version=1,
        organization_id=data.organization_id,
        project_id=data.project_id,
    )
    db.add(tc)
    await db.flush()

    for i, step_data in enumerate(steps_data):
        step = TestStep(
            test_case_id=tc.id,
            order=step_data.order if step_data.order else i + 1,
            type=step_data.type,
            action=step_data.action,
            expected_result=step_data.expected_result,
            description=step_data.description,
            test_data=step_data.test_data,
            organization_id=data.organization_id,
            project_id=data.project_id,
        )
        db.add(step)

    await db.commit()
    await db.refresh(tc)
    return tc


async def get_test_case(db: AsyncSession, case_id: uuid.UUID) -> Optional[TestCase]:
    result = await db.execute(
        select(TestCase)
        .where(TestCase.id == case_id)
        .options(selectinload(TestCase.steps))
    )
    return result.scalar_one_or_none()


async def list_test_cases(
    db: AsyncSession,
    suite_id: uuid.UUID,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    owner_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None,
    tags: Optional[List[str]] = None,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[TestCase], int]:
    stmt = select(TestCase).where(TestCase.test_suite_id == suite_id)
    count_stmt = select(func.count(TestCase.id)).where(TestCase.test_suite_id == suite_id)

    if status:
        stmt = stmt.where(TestCase.status == status)
        count_stmt = count_stmt.where(TestCase.status == status)
    if priority:
        stmt = stmt.where(TestCase.priority == priority)
        count_stmt = count_stmt.where(TestCase.priority == priority)
    if owner_id:
        stmt = stmt.where(TestCase.owner_id == owner_id)
        count_stmt = count_stmt.where(TestCase.owner_id == owner_id)
    if search:
        stmt = stmt.where(TestCase.title.ilike(f"%{search}%"))
        count_stmt = count_stmt.where(TestCase.title.ilike(f"%{search}%"))
    if tags:
        stmt = stmt.where(TestCase.tags.contains(tags))
        count_stmt = count_stmt.where(TestCase.tags.contains(tags))

    stmt = stmt.options(selectinload(TestCase.steps)).order_by(TestCase.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    cases = list(result.scalars().all())

    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    return cases, total


async def update_test_case(
    db: AsyncSession,
    case_id: uuid.UUID,
    data: TestCaseUpdate,
    changed_by: Optional[uuid.UUID] = None,
) -> Optional[TestCase]:
    tc = await get_test_case(db, case_id)
    if not tc:
        return None

    # Snapshot before modifying
    await _snapshot_test_case(db, tc, changed_by, data.change_summary)

    update_data = data.model_dump(exclude_unset=True)
    update_data.pop("change_summary", None)
    if "preconditions" in update_data:
        update_data["preconditions"] = _precond_to_text(update_data["preconditions"])
    if "requirement_ids" in update_data:
        update_data["requirement_ids"] = _uuids_to_str(update_data["requirement_ids"])

    for key, val in update_data.items():
        setattr(tc, key, val)

    tc.version += 1
    tc.updated_at = _now()

    await db.commit()
    await db.refresh(tc)
    return tc


async def delete_test_case(db: AsyncSession, case_id: uuid.UUID) -> bool:
    tc = await db.get(TestCase, case_id)
    if not tc:
        return False
    await db.delete(tc)
    await db.commit()
    return True


async def clone_test_case(db: AsyncSession, case_id: uuid.UUID, data: TestCaseClone) -> Optional[TestCase]:
    original = await get_test_case(db, case_id)
    if not original:
        return None

    new_tc = TestCase(
        test_suite_id=data.target_suite_id,
        title=data.new_title or f"{original.title} (Copy)",
        slug=_slugify(data.new_title or f"{original.title}-copy"),
        description=original.description,
        type=original.type,
        priority=original.priority,
        status="draft",
        preconditions=original.preconditions,
        gherkin=original.gherkin,
        tags=original.tags,
        requirement_ids=original.requirement_ids,
        owner_id=original.owner_id,
        review_status="pending",
        version=1,
        organization_id=original.organization_id,
        project_id=original.project_id,
    )
    db.add(new_tc)
    await db.flush()

    if data.copy_steps:
        for step in (original.steps or []):
            new_step = TestStep(
                test_case_id=new_tc.id,
                order=step.order,
                type=step.type,
                action=step.action,
                expected_result=step.expected_result,
                description=step.description,
                test_data=step.test_data,
                organization_id=original.organization_id,
                project_id=original.project_id,
            )
            db.add(new_step)

    await db.commit()
    await db.refresh(new_tc)
    return new_tc


async def bulk_update_test_cases(db: AsyncSession, data: TestCaseBulkUpdate) -> int:
    """Bulk update test cases. Returns count of updated rows."""
    values = {}
    if data.priority is not None:
        values["priority"] = data.priority
    if data.status is not None:
        values["status"] = data.status
    if data.review_status is not None:
        values["review_status"] = data.review_status
    if data.owner_id is not None:
        values["owner_id"] = data.owner_id
    if data.tags is not None:
        values["tags"] = data.tags

    if not values and not data.add_tags and not data.remove_tags:
        return 0

    if values:
        values["updated_at"] = _now()
        result = await db.execute(
            update(TestCase).where(TestCase.id.in_(data.ids)).values(**values)
        )
        return result.rowcount

    # Tag add/remove requires per-row logic
    count = 0
    for case_id in data.ids:
        tc = await db.get(TestCase, case_id)
        if tc:
            current_tags = set(tc.tags or [])
            if data.add_tags:
                current_tags.update(data.add_tags)
            if data.remove_tags:
                current_tags.difference_update(data.remove_tags)
            tc.tags = sorted(current_tags)
            tc.updated_at = _now()
            count += 1
    await db.commit()
    return count


async def bulk_delete_test_cases(db: AsyncSession, ids: List[uuid.UUID]) -> int:
    result = await db.execute(
        update(TestCase).where(TestCase.id.in_(ids)).values(status="deprecated")
    )
    await db.commit()
    return result.rowcount


async def archive_test_case(db: AsyncSession, case_id: uuid.UUID) -> Optional[TestCase]:
    tc = await db.get(TestCase, case_id)
    if not tc:
        return None
    tc.status = "deprecated"
    tc.updated_at = _now()
    await db.commit()
    await db.refresh(tc)
    return tc


# ═══════════════════════════════════════════════════════════════════════
# Test Steps
# ═══════════════════════════════════════════════════════════════════════

async def add_step(db: AsyncSession, case_id: uuid.UUID, data: TestStepCreate) -> TestStep:
    step = TestStep(test_case_id=case_id, **data.model_dump())
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


async def update_step(db: AsyncSession, step_id: uuid.UUID, data: TestStepUpdate) -> Optional[TestStep]:
    step = await db.get(TestStep, step_id)
    if not step:
        return None
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(step, key, val)
    await db.commit()
    await db.refresh(step)
    return step


async def delete_step(db: AsyncSession, step_id: uuid.UUID) -> bool:
    step = await db.get(TestStep, step_id)
    if not step:
        return False
    await db.delete(step)
    await db.commit()
    return True


async def reorder_steps(db: AsyncSession, case_id: uuid.UUID, step_ids: List[uuid.UUID]) -> List[TestStep]:
    """Reorder steps by providing the new order of step IDs."""
    for i, step_id in enumerate(step_ids):
        await db.execute(
            update(TestStep).where(TestStep.id == step_id, TestStep.test_case_id == case_id).values(order=i + 1)
        )
    await db.commit()
    result = await db.execute(
        select(TestStep).where(TestStep.test_case_id == case_id).order_by(TestStep.order)
    )
    return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════════
# Version History
# ═══════════════════════════════════════════════════════════════════════

async def list_versions(db: AsyncSession, case_id: uuid.UUID) -> List[TestCaseVersion]:
    result = await db.execute(
        select(TestCaseVersion)
        .where(TestCaseVersion.test_case_id == case_id)
        .order_by(TestCaseVersion.version.desc())
    )
    return list(result.scalars().all())


async def get_version(db: AsyncSession, version_id: uuid.UUID) -> Optional[TestCaseVersion]:
    return await db.get(TestCaseVersion, version_id)


# ═══════════════════════════════════════════════════════════════════════
# Test Executions (Manual Sessions)
# ═══════════════════════════════════════════════════════════════════════

async def create_execution(db: AsyncSession, data: TestExecutionCreate, executed_by: Optional[uuid.UUID] = None) -> TestExecution:
    execution = TestExecution(
        test_suite_id=data.test_suite_id,
        environment=data.environment,
        execution_type=data.execution_type,
        executed_by=executed_by,
        notes=data.notes,
        status="in_progress",
        started_at=_now(),
        organization_id=data.organization_id,
        project_id=data.project_id,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    return execution


async def get_execution(db: AsyncSession, execution_id: uuid.UUID) -> Optional[TestExecution]:
    return await db.get(TestExecution, execution_id)


async def list_executions(
    db: AsyncSession,
    suite_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[TestExecution], int]:
    stmt = select(TestExecution).where(TestExecution.test_suite_id == suite_id)
    count_stmt = select(func.count(TestExecution.id)).where(TestExecution.test_suite_id == suite_id)

    stmt = stmt.order_by(TestExecution.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    executions = list(result.scalars().all())

    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    return executions, total


async def list_all_executions(
    db: AsyncSession,
    organization_id: Optional[uuid.UUID],
    project_id: Optional[uuid.UUID],
    status: Optional[str] = None,
    execution_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[TestExecution]:
    """List execution sessions for a tenant across all suites (most recent first)."""
    stmt = select(TestExecution)
    if organization_id is not None:
        stmt = stmt.where(TestExecution.organization_id == organization_id)
    if project_id is not None:
        stmt = stmt.where(TestExecution.project_id == project_id)
    if status:
        stmt = stmt.where(TestExecution.status == status)
    if execution_type:
        stmt = stmt.where(TestExecution.execution_type == execution_type)

    stmt = stmt.order_by(TestExecution.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_execution(db: AsyncSession, execution_id: uuid.UUID, data: TestExecutionUpdate) -> Optional[TestExecution]:
    execution = await db.get(TestExecution, execution_id)
    if not execution:
        return None
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(execution, key, val)
    await db.commit()
    await db.refresh(execution)
    return execution


async def complete_execution(db: AsyncSession, execution_id: uuid.UUID) -> Optional[TestExecution]:
    """Mark an execution as completed and compute summary."""
    execution = await db.get(TestExecution, execution_id)
    if not execution:
        return None

    # Compute summary from case executions
    result = await db.execute(
        select(TestCaseExecution).where(TestCaseExecution.execution_id == execution_id)
    )
    case_executions = list(result.scalars().all())

    total = len(case_executions)
    passed = sum(1 for ce in case_executions if ce.status == "passed")
    failed = sum(1 for ce in case_executions if ce.status == "failed")
    blocked = sum(1 for ce in case_executions if ce.status == "blocked")
    skipped = sum(1 for ce in case_executions if ce.status == "skipped")
    errors = sum(1 for ce in case_executions if ce.status == "error")

    execution.status = "completed" if (failed == 0 and errors == 0) else "failed"
    execution.finished_at = _now()
    if execution.started_at:
        started = execution.started_at
        finished = execution.finished_at
        # SQLite returns naive datetimes; _now() is tz-aware — normalize before subtracting
        if (started.tzinfo is None) != (finished.tzinfo is None):
            started = started.replace(tzinfo=None)
            finished = finished.replace(tzinfo=None)
        execution.duration_seconds = (finished - started).total_seconds()
    execution.summary = {
        **(execution.summary or {}),
        "total": total,
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "skipped": skipped,
        "errors": errors,
    }

    await db.commit()
    await db.refresh(execution)
    return execution


# ═══════════════════════════════════════════════════════════════════════
# Automated execution — links saved automation scripts to a run
# ═══════════════════════════════════════════════════════════════════════

async def run_automated_execution(
    db: AsyncSession, execution: TestExecution, base_url: Optional[str] = None
) -> None:
    """Resolve the suite's test cases + their linked automation scripts, hand them to the
    configured runner (`settings.execution_runner`), and persist per-case results.

    The runner is pluggable (simulated by default, container runner is a stub). Runner
    failures fall back to the simulated runner so a run never errors out. ``base_url``,
    when provided, is the System Under Test's target URL (resolved from the workspace's
    configured Environment) — the simulated runner uses it to perform a real reachability
    check rather than fabricating results in a vacuum.
    """
    tc_result = await db.execute(
        select(TestCase).where(TestCase.test_suite_id == execution.test_suite_id)
    )
    test_cases = list(tc_result.scalars().all())
    case_ids = [tc.id for tc in test_cases]

    scripts_by_case: Dict[uuid.UUID, List[AutomationScript]] = {}
    if case_ids:
        s_result = await db.execute(
            select(AutomationScript).where(AutomationScript.test_case_id.in_(case_ids))
        )
        for script in s_result.scalars().all():
            scripts_by_case.setdefault(script.test_case_id, []).append(script)

    # Build a DB-agnostic request for the runner
    request = RunnerRequest(
        execution_id=str(execution.id),
        environment=execution.environment,
        base_url=base_url,
        cases=[
            RunnerCase(
                test_case_id=str(tc.id),
                title=tc.title,
                scripts=[
                    RunnerScript(
                        name=s.name,
                        framework=s.framework,
                        language=s.language,
                        code=s.code,
                        file_path=s.file_path,
                    )
                    for s in scripts_by_case.get(tc.id, [])
                ],
            )
            for tc in test_cases
        ],
    )

    runner = get_runner()
    try:
        result = await runner.run(request)
    except Exception as exc:  # noqa: BLE001 — never fail a run on a runner error
        logger.warning("Runner '%s' failed (%s); falling back to simulated runner", runner.name, exc)
        result = await SimulatedRunner().run(request)

    now = _now()
    for cr in result.case_results:
        db.add(
            TestCaseExecution(
                execution_id=execution.id,
                test_case_id=uuid.UUID(cr.test_case_id),
                status=cr.status,
                started_at=now,
                finished_at=now,
                duration_seconds=cr.duration_seconds,
                error_message=cr.error_message,
                artifacts=cr.artifacts,
                organization_id=execution.organization_id,
                project_id=execution.project_id,
            )
        )

    await db.commit()


# ═══════════════════════════════════════════════════════════════════════
# Test Case Executions
# ═══════════════════════════════════════════════════════════════════════

async def get_or_create_case_execution(
    db: AsyncSession,
    execution_id: uuid.UUID,
    case_id: uuid.UUID,
    org_id: Optional[uuid.UUID] = None,
    ws_id: Optional[uuid.UUID] = None,
) -> TestCaseExecution:
    result = await db.execute(
        select(TestCaseExecution).where(
            and_(
                TestCaseExecution.execution_id == execution_id,
                TestCaseExecution.test_case_id == case_id,
            )
        )
    )
    ce = result.scalar_one_or_none()
    if ce:
        return ce

    ce = TestCaseExecution(
        execution_id=execution_id,
        test_case_id=case_id,
        status="in_progress",
        started_at=_now(),
        organization_id=org_id,
        project_id=ws_id,
    )
    db.add(ce)
    await db.commit()
    await db.refresh(ce)
    return ce


async def get_case_execution(db: AsyncSession, case_execution_id: uuid.UUID) -> Optional[TestCaseExecution]:
    result = await db.execute(
        select(TestCaseExecution)
        .where(TestCaseExecution.id == case_execution_id)
        .options(selectinload(TestCaseExecution.step_executions))
    )
    return result.scalar_one_or_none()


async def list_case_executions(
    db: AsyncSession,
    execution_id: uuid.UUID,
) -> List[TestCaseExecution]:
    result = await db.execute(
        select(TestCaseExecution)
        .where(TestCaseExecution.execution_id == execution_id)
        .options(selectinload(TestCaseExecution.step_executions))
        .order_by(TestCaseExecution.created_at)
    )
    return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════════
# Step Executions (Manual Result Recording)
# ═══════════════════════════════════════════════════════════════════════

async def record_step_result(
    db: AsyncSession,
    step_execution_id: uuid.UUID,
    data: StepExecutionUpdate,
) -> Optional[StepExecution]:
    """Record the result of a specific step execution by its ID."""
    se = await db.get(StepExecution, step_execution_id)
    if not se:
        return None

    if data.status is not None:
        se.status = data.status
    if data.actual_result is not None:
        se.actual_result = data.actual_result
    if data.comment is not None:
        se.comment = data.comment
    if data.screenshot_url is not None:
        se.screenshot_url = data.screenshot_url

    await db.commit()
    await db.refresh(se)

    # Update parent case execution status
    await _sync_case_execution_status(db, se.case_execution_id)

    return se


async def get_case_executions(
    db: AsyncSession,
    execution_id: uuid.UUID,
) -> List[TestCaseExecution]:
    """Get all test case executions for an execution session with step executions."""
    result = await db.execute(
        select(TestCaseExecution)
        .where(TestCaseExecution.execution_id == execution_id)
        .options(selectinload(TestCaseExecution.step_executions))
        .order_by(TestCaseExecution.created_at)
    )
    return list(result.scalars().all())


async def get_step_executions(
    db: AsyncSession,
    case_execution_id: uuid.UUID,
) -> List[StepExecution]:
    """Get all step executions for a test case execution."""
    result = await db.execute(
        select(StepExecution)
        .where(StepExecution.case_execution_id == case_execution_id)
        .order_by(StepExecution.created_at)
    )
    return list(result.scalars().all())


async def create_case_executions(
    db: AsyncSession,
    execution_id: uuid.UUID,
) -> List[TestCaseExecution]:
    """Create TestCaseExecution + StepExecution records for all test cases in the suite."""
    execution = await db.get(TestExecution, execution_id)
    if not execution:
        return []

    # Get all test cases in the suite
    result = await db.execute(
        select(TestCase).where(TestCase.test_suite_id == execution.test_suite_id)
    )
    test_cases = list(result.scalars().all())

    case_executions = []
    for tc in test_cases:
        # Check if case execution already exists
        existing = await db.execute(
            select(TestCaseExecution).where(
                and_(
                    TestCaseExecution.execution_id == execution_id,
                    TestCaseExecution.test_case_id == tc.id,
                )
            )
        )
        ce = existing.scalar_one_or_none()
        if not ce:
            ce = TestCaseExecution(
                execution_id=execution_id,
                test_case_id=tc.id,
                status="in_progress",
                started_at=_now(),
                organization_id=execution.organization_id,
                project_id=execution.project_id,
            )
            db.add(ce)
            await db.flush()

            # Create step executions for each test step
            if tc.steps:
                for step in tc.steps:
                    se = StepExecution(
                        case_execution_id=ce.id,
                        step_id=step.id,
                        status="pending",
                        organization_id=execution.organization_id,
                        project_id=execution.project_id,
                    )
                    db.add(se)

        case_executions.append(ce)

    await db.commit()
    # Refresh all with step executions loaded
    result = await db.execute(
        select(TestCaseExecution)
        .where(TestCaseExecution.execution_id == execution_id)
        .options(selectinload(TestCaseExecution.step_executions))
        .order_by(TestCaseExecution.created_at)
    )
    return list(result.scalars().all())


async def _sync_case_execution_status(db: AsyncSession, case_execution_id: uuid.UUID) -> None:
    """Sync the case execution status based on its step executions."""
    result = await db.execute(
        select(StepExecution).where(StepExecution.case_execution_id == case_execution_id)
    )
    step_execs = list(result.scalars().all())

    ce = await db.get(TestCaseExecution, case_execution_id)
    if not ce:
        return

    if not step_execs:
        return

    statuses = {se.status for se in step_execs}
    if "failed" in statuses:
        ce.status = "failed"
    elif "blocked" in statuses:
        ce.status = "blocked"
    elif all(s == "passed" for s in statuses):
        ce.status = "passed"
    elif all(s == "skipped" for s in statuses):
        ce.status = "skipped"
    else:
        ce.status = "in_progress"

    if ce.status in ("passed", "failed", "blocked", "skipped"):
        ce.finished_at = _now()
        if ce.started_at:
            ce.duration_seconds = (ce.finished_at - ce.started_at).total_seconds()

    await db.commit()


# ═══════════════════════════════════════════════════════════════════════
# Defect Drafts
# ═══════════════════════════════════════════════════════════════════════

async def create_defect_draft(db: AsyncSession, data: DefectDraftCreate) -> DefectDraft:
    defect = DefectDraft(
        case_execution_id=data.case_execution_id,
        title=data.title,
        description=data.description,
        severity=data.severity,
        status="draft",
        steps_to_reproduce=data.steps_to_reproduce,
        environment=data.environment,
        labels=data.labels,
        organization_id=data.organization_id,
        project_id=data.project_id,
    )
    db.add(defect)
    await db.commit()
    await db.refresh(defect)
    return defect


async def list_defect_drafts(
    db: AsyncSession,
    case_execution_id: uuid.UUID,
) -> List[DefectDraft]:
    result = await db.execute(
        select(DefectDraft)
        .where(DefectDraft.case_execution_id == case_execution_id)
        .order_by(DefectDraft.created_at.desc())
    )
    return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════════
# CSV Import / Export
# ═══════════════════════════════════════════════════════════════════════

CSV_HEADERS = ["title", "description", "type", "priority", "status", "preconditions", "tags", "steps"]

async def export_test_cases_csv(db: AsyncSession, suite_id: uuid.UUID) -> str:
    """Export test cases from a suite as CSV string."""
    cases, _ = await list_test_cases(db, suite_id, limit=10000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADERS)

    for tc in cases:
        steps_str = " | ".join(
            f"{s.order}. [{s.type}] {s.action}" + (f" → {s.expected_result}" if s.expected_result else "")
            for s in (tc.steps or [])
        )
        writer.writerow([
            tc.title,
            tc.description or "",
            tc.type,
            tc.priority,
            tc.status,
            " ; ".join(tc.preconditions) if tc.preconditions else "",
            ", ".join(tc.tags) if tc.tags else "",
            steps_str,
        ])

    return output.getvalue()


async def import_test_cases_csv(
    db: AsyncSession,
    suite_id: uuid.UUID,
    csv_content: str,
    org_id: Optional[uuid.UUID] = None,
    ws_id: Optional[uuid.UUID] = None,
) -> CSVImportResult:
    """Import test cases from CSV into a suite."""
    reader = csv.DictReader(io.StringIO(csv_content))
    result = CSVImportResult(total_rows=0, imported=0, skipped=0, errors=[])

    for row_num, row in enumerate(reader, start=2):  # 1-indexed, header is row 1
        result.total_rows += 1
        try:
            title = row.get("title", "").strip()
            if not title:
                result.skipped += 1
                result.errors.append(f"Row {row_num}: missing title")
                continue

            preconditions = [p.strip() for p in row.get("preconditions", "").split(";") if p.strip()] if row.get("preconditions") else None
            tags = [t.strip() for t in row.get("tags", "").split(",") if t.strip()] if row.get("tags") else None

            tc = TestCase(
                test_suite_id=suite_id,
                title=title,
                slug=_slugify(title),
                description=row.get("description") or None,
                type=row.get("type", "manual"),
                priority=row.get("priority", "medium"),
                status=row.get("status", "draft"),
                preconditions=preconditions,
                tags=tags,
                version=1,
                review_status="pending",
                organization_id=org_id,
                project_id=ws_id,
            )
            db.add(tc)
            result.imported += 1

        except Exception as e:
            result.skipped += 1
            result.errors.append(f"Row {row_num}: {str(e)}")

    await db.commit()
    return result


# ═══════════════════════════════════════════════════════════════════════
# Requirement Coverage
# ═══════════════════════════════════════════════════════════════════════

async def get_requirement_coverage(db: AsyncSession, workspace_id: uuid.UUID) -> RequirementCoverageReport:
    """Calculate requirement coverage for a workspace."""
    # Get all test cases in the workspace (via suites)
    result = await db.execute(
        select(TestCase)
        .join(TestSuite, TestCase.test_suite_id == TestSuite.id)
        .where(TestSuite.workspace_id == workspace_id)
    )
    cases = list(result.scalars().all())

    # Build requirement → test case mapping
    req_map: Dict[str, List[uuid.UUID]] = {}
    tc_title_map: Dict[uuid.UUID, str] = {}
    for tc in cases:
        tc_title_map[tc.id] = tc.title
        if tc.requirement_ids:
            for rid in tc.requirement_ids:
                rid_str = str(rid)
                if rid_str not in req_map:
                    req_map[rid_str] = []
                req_map[rid_str].append(tc.id)

    # Get all requirements for the workspace (from test suites)
    result = await db.execute(
        select(TestSuite.requirement_id).where(
            and_(TestSuite.workspace_id == workspace_id, TestSuite.requirement_id.isnot(None))
        ).distinct()
    )
    all_req_ids = [row[0] for row in result.all() if row[0]]

    items = []
    for rid in all_req_ids:
        rid_str = str(rid)
        case_ids = req_map.get(rid_str, [])
        count = len(case_ids)
        items.append(RequirementCoverageItem(
            requirement_id=rid,
            requirement_title=None,
            test_case_count=count,
            covered=count > 0,
            test_cases=[{"id": str(cid), "title": tc_title_map.get(cid, "")} for cid in case_ids],
        ))

    total = len(items)
    covered = sum(1 for i in items if i.covered)
    coverage_pct = (covered / total * 100) if total > 0 else 0.0

    return RequirementCoverageReport(
        workspace_id=workspace_id,
        total_requirements=total,
        covered_requirements=covered,
        coverage_percent=round(coverage_pct, 1),
        items=items,
    )