
"""Automation Studio API — Script CRUD, version management, execution, and recorder.

Phase 4 extends the original single-endpoint generation router with full
Automation Studio capabilities: script CRUD, version history, diff, review,
approve, restore, execution job management, result retrieval, and recorded
action batch submission.
"""

import difflib
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select, func, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user, require_role, verify_token
from app.db.database import AsyncSessionLocal, get_db
from app.models.automation import (
    AutomationScript,
    ExecutionJob,
    ExecutionJobStatus,
    ExecutionResult,
    ExecutionStepResult,
    FrameworkConfiguration,
    Locator,
    PageObject,
    RecordedAction,
    ScriptVersion,
    ScriptStatus,
)
from app.schemas.automation import (
    AutomationOut,
    AutomationRequest,
    AutomationScriptCreate,
    AutomationScriptDetail,
    AutomationScriptOut,
    AutomationScriptUpdate,
    ExecutionJobCreate,
    ExecutionJobOut,
    ExecutionJobSummary,
    ExecutionResultDetail,
    ExecutionResultOut,
    ExecutionStepResultOut,
    FrameworkConfigurationCreate,
    FrameworkConfigurationOut,
    LocatorCreate,
    LocatorOut,
    LocatorUpdate,
    PageObjectCreate,
    PageObjectOut,
    RecordedActionBatch,
    RecordedActionOut,
    RecordingSessionOut,
    ScriptVersionCreate,
    ScriptVersionDiff,
    ScriptVersionOut,
    ScriptVersionSummary,
    SuiteSummary,
)
from app.services.automation_service import generate_automation
from app.services.execution_queue import ExecutionQueue
from app.services.execution_security import (
    AuditEvent,
    AuditEventType,
    create_execution_token,
    get_audit_log,
    record_audit_event,
    validate_script,
    verify_tenant_access,
)
from app.services.playwright_converter import (
    generate_playwright_from_recorded,
    compute_code_hash,
)
from app.services.selenium_converter import generate_selenium_from_recorded
from app.services.robot_converter import generate_robot_from_recorded
from app.services.appium_converter import convert_to_appium, generate_appium_config

router = APIRouter()


# ══════════════════════════════════════════════════════════════════════
# Legacy — AI-powered generation endpoint
# ══════════════════════════════════════════════════════════════════════

@router.post("/generate", response_model=AutomationOut)
async def generate(
    payload: AutomationRequest,
    current_user=Depends(get_current_user),
):
    """Generate an automation script for the given requirement + test case.

    Dispatches to the correct framework generator (Playwright, Selenium, Cypress)
    based on the framework field in the request.
    """
    return generate_automation(payload.story, payload.test_case, payload.story.framework)


# ══════════════════════════════════════════════════════════════════════
# Automation Scripts — CRUD
# ══════════════════════════════════════════════════════════════════════

@router.get("/scripts", response_model=List[AutomationScriptOut])
async def list_scripts(
    framework: Optional[str] = Query(None, description="Filter by framework"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List automation scripts for the current tenant."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("workspace_id")

    stmt = select(AutomationScript).where(
        AutomationScript.organization_id == org_id,
        AutomationScript.workspace_id == ws_id,
    )
    if framework:
        stmt = stmt.where(AutomationScript.framework == framework)
    if status_filter:
        stmt = stmt.where(AutomationScript.status == status_filter)

    stmt = stmt.order_by(AutomationScript.updated_at.desc())
    result = await db.execute(stmt)
    scripts = result.scalars().all()
    return scripts


@router.post("/scripts", response_model=AutomationScriptOut, status_code=status.HTTP_201_CREATED)
async def create_script(
    payload: AutomationScriptCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "automation_engineer")),
):
    """Create a new automation script."""
    org_id = payload.organization_id or current_user.get("organization_id")
    ws_id = payload.workspace_id or current_user.get("workspace_id")

    script = AutomationScript(
        name=payload.name,
        language=payload.language,
        framework=payload.framework,
        status=payload.status,
        code=payload.code,
        file_path=payload.file_path,
        version=payload.version,
        organization_id=org_id,
        workspace_id=ws_id,
    )
    db.add(script)
    await db.commit()
    await db.refresh(script)
    return script


@router.get("/scripts/{script_id}", response_model=AutomationScriptDetail)
async def get_script(
    script_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get automation script detail with version history and execution jobs."""
    stmt = (
        select(AutomationScript)
        .options(
            selectinload(AutomationScript.versions),
            selectinload(AutomationScript.execution_jobs),
        )
        .where(AutomationScript.id == script_id)
    )
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Automation script not found")
    if not verify_tenant_access(
        script.organization_id,
        script.workspace_id,
        current_user.get("organization_id") or current_user.get("org_id"),
        current_user.get("workspace_id"),
    ):
        raise HTTPException(status_code=403, detail="Automation script access denied")

    # ── Security: verify tenant access ──
    verify_tenant_access(
        script.organization_id, script.workspace_id,
        current_user.get("organization_id"), current_user.get("workspace_id"),
    )
    return script


@router.put("/scripts/{script_id}", response_model=AutomationScriptOut)
async def update_script(
    script_id: uuid.UUID,
    payload: AutomationScriptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "automation_engineer")),
):
    """Update an automation script's metadata."""
    stmt = select(AutomationScript).where(AutomationScript.id == script_id)
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Automation script not found")

    # ── Security: verify tenant access ──
    verify_tenant_access(
        script.organization_id, script.workspace_id,
        current_user.get("organization_id"), current_user.get("workspace_id"),
    )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(script, field, value)

    await db.commit()
    await db.refresh(script)
    return script


@router.delete("/scripts/{script_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_script(
    script_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "org_owner")),
):
    """Delete an automation script and all associated versions/jobs."""
    stmt = select(AutomationScript).where(AutomationScript.id == script_id)
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Automation script not found")

    # ── Security: verify tenant access ──
    verify_tenant_access(
        script.organization_id, script.workspace_id,
        current_user.get("organization_id"), current_user.get("workspace_id"),
    )

    await db.delete(script)
    await db.commit()


# ══════════════════════════════════════════════════════════════════════
# Script Versions — history, diff, approve, restore
# ══════════════════════════════════════════════════════════════════════

@router.get("/scripts/{script_id}/versions", response_model=List[ScriptVersionSummary])
async def list_script_versions(
    script_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List version summaries for a script (no code body for performance)."""
    stmt = (
        select(ScriptVersion)
        .where(ScriptVersion.script_id == script_id)
        .order_by(ScriptVersion.version.desc())
    )
    result = await db.execute(stmt)
    versions = result.scalars().all()
    return versions


@router.post("/scripts/{script_id}/versions", response_model=ScriptVersionOut, status_code=status.HTTP_201_CREATED)
async def create_script_version(
    script_id: uuid.UUID,
    payload: ScriptVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "automation_engineer")),
):
    """Save a new version snapshot of the script.

    Creates an immutable version with the current code. The version number
    auto-increments based on the highest existing version for this script.
    """
    # Verify script exists
    stmt = select(AutomationScript).where(AutomationScript.id == script_id)
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Automation script not found")

    # Auto-increment version number
    max_ver_stmt = select(func.max(ScriptVersion.version)).where(ScriptVersion.script_id == script_id)
    max_ver_result = await db.execute(max_ver_stmt)
    max_ver = max_ver_result.scalar() or 0

    code = payload.code or script.code
    code_hash = compute_code_hash(code)

    version = ScriptVersion(
        script_id=script_id,
        version=max_ver + 1,
        code=code,
        file_path=payload.file_path or script.file_path,
        status=ScriptStatus.draft.value,
        changed_by=current_user.get("id") if isinstance(current_user, dict) else None,
        change_summary=payload.change_summary,
        code_hash=code_hash,
        organization_id=script.organization_id,
        workspace_id=script.workspace_id,
    )
    db.add(version)

    # Update the script's current code and version counter
    script.code = code
    script.version = max_ver + 1
    script.status = ScriptStatus.draft.value

    await db.commit()
    await db.refresh(version)

    # ── Security: record audit event ──
    record_audit_event(AuditEvent(
        event_type=AuditEventType.version_created,
        script_id=script_id,
        script_version_id=version.id,
        organization_id=script.organization_id,
        workspace_id=script.workspace_id,
        actor_id=current_user.get("id") if isinstance(current_user, dict) else None,
        actor_type="user",
        details={"version_number": max_ver + 1, "change_summary": payload.change_summary},
    ))

    return version


@router.get("/scripts/{script_id}/versions/{v1}/diff/{v2}", response_model=ScriptVersionDiff)
async def diff_script_versions(
    script_id: uuid.UUID,
    v1: int,
    v2: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Compute a unified diff between two script versions."""
    stmt = select(ScriptVersion).where(
        ScriptVersion.script_id == script_id,
        ScriptVersion.version.in_([v1, v2]),
    )
    result = await db.execute(stmt)
    versions = {sv.version: sv for sv in result.scalars().all()}

    if v1 not in versions:
        raise HTTPException(status_code=404, detail=f"Version {v1} not found")
    if v2 not in versions:
        raise HTTPException(status_code=404, detail=f"Version {v2} not found")

    from_code = versions[v1].code
    to_code = versions[v2].code
    unified = difflib.unified_diff(
        from_code.splitlines(keepends=True),
        to_code.splitlines(keepends=True),
        fromfile=f"v{v1}",
        tofile=f"v{v2}",
    )

    return ScriptVersionDiff(
        from_version=v1,
        to_version=v2,
        from_code=from_code,
        to_code=to_code,
        unified_diff="".join(unified),
    )


@router.post("/scripts/{script_id}/versions/{version_id}/approve", response_model=ScriptVersionOut)
async def approve_script_version(
    script_id: uuid.UUID,
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead")),
):
    """Approve a script version for execution.

    Only approved versions can be submitted for execution. This sets the
    script's approved_version_id to the approved version.
    """
    # Get the version
    stmt = select(ScriptVersion).where(
        ScriptVersion.id == version_id,
        ScriptVersion.script_id == script_id,
    )
    result = await db.execute(stmt)
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Script version not found")

    # Mark version as approved
    version.status = ScriptStatus.ready.value

    # Update the script's approved version pointer
    script_stmt = select(AutomationScript).where(AutomationScript.id == script_id)
    script_result = await db.execute(script_stmt)
    script = script_result.scalar_one_or_none()
    if script:
        script.approved_version_id = version_id
        script.status = ScriptStatus.ready.value

    await db.commit()
    await db.refresh(version)

    # ── Security: record audit event ──
    record_audit_event(AuditEvent(
        event_type=AuditEventType.version_approved,
        script_id=script_id,
        script_version_id=version_id,
        organization_id=script.organization_id if script else None,
        workspace_id=script.workspace_id if script else None,
        actor_id=current_user.get("id") if isinstance(current_user, dict) else None,
        actor_type="user",
        details={"version_number": version.version},
    ))

    return version


@router.post("/scripts/{script_id}/versions/{version_id}/restore", response_model=AutomationScriptOut)
async def restore_script_version(
    script_id: uuid.UUID,
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "automation_engineer")),
):
    """Restore a previous version as the current script code.

    Creates a new version with the restored code (does NOT delete history).
    """
    # Get the version to restore
    stmt = select(ScriptVersion).where(
        ScriptVersion.id == version_id,
        ScriptVersion.script_id == script_id,
    )
    result = await db.execute(stmt)
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Script version not found")

    # Get the script
    script_stmt = select(AutomationScript).where(AutomationScript.id == script_id)
    script_result = await db.execute(script_stmt)
    script = script_result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Automation script not found")

    # Create a new version with the restored code
    max_ver_stmt = select(func.max(ScriptVersion.version)).where(ScriptVersion.script_id == script_id)
    max_ver_result = await db.execute(max_ver_stmt)
    max_ver = max_ver_result.scalar() or 0

    new_version = ScriptVersion(
        script_id=script_id,
        version=max_ver + 1,
        code=version.code,
        file_path=version.file_path,
        status=ScriptStatus.draft.value,
        changed_by=current_user.get("id") if isinstance(current_user, dict) else None,
        change_summary=f"Restored from version {version.version}",
        code_hash=compute_code_hash(version.code),
        organization_id=script.organization_id,
        workspace_id=script.workspace_id,
    )
    db.add(new_version)

    # Update script's current code
    script.code = version.code
    script.version = max_ver + 1
    script.status = ScriptStatus.draft.value

    await db.commit()
    await db.refresh(script)

    # ── Security: record audit event ──
    record_audit_event(AuditEvent(
        event_type=AuditEventType.version_restored,
        script_id=script_id,
        script_version_id=version_id,
        organization_id=script.organization_id,
        workspace_id=script.workspace_id,
        actor_id=current_user.get("id") if isinstance(current_user, dict) else None,
        actor_type="user",
        details={"restored_from_version": version.version, "new_version": max_ver + 1},
    ))

    return script


# ══════════════════════════════════════════════════════════════════════
# Execution Jobs — submit, list, get, cancel
# ══════════════════════════════════════════════════════════════════════

@router.post("/execution-jobs", response_model=ExecutionJobOut, status_code=status.HTTP_201_CREATED)
async def submit_execution_job(
    payload: ExecutionJobCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "automation_engineer")),
):
    """Submit an automation script for execution.

    The job is queued and will be picked up by the execution worker.
    If no specific version is provided, the approved version is used.
    """
    # Verify script exists
    stmt = select(AutomationScript).where(AutomationScript.id == payload.script_id)
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Automation script not found")

    # Determine which version to execute
    version_id = payload.script_version_id or script.approved_version_id
    if not version_id:
        raise HTTPException(
            status_code=400,
            detail="No approved version found. Approve a script version before executing.",
        )

    # Verify the version exists
    ver_stmt = select(ScriptVersion).where(ScriptVersion.id == version_id)
    ver_result = await db.execute(ver_stmt)
    ver = ver_result.scalar_one_or_none()
    if not ver:
        raise HTTPException(status_code=404, detail="Script version not found")
    if ver.script_id != script.id:
        raise HTTPException(status_code=400, detail="Script version does not belong to script")

    # ── Security: validate script code before execution ──
    validation = validate_script(ver.code, ver.language or "typescript")
    if not validation.is_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Script validation failed — contains blocked patterns",
                "errors": validation.errors,
                "warnings": validation.warnings,
            },
        )

    # Resolve base_url: explicit > environment > script metadata
    base_url = payload.base_url
    if not base_url and payload.environment_id:
        from app.models.environment import Environment
        env_stmt = select(Environment).where(Environment.id == payload.environment_id)
        env_result = await db.execute(env_stmt)
        env = env_result.scalar_one_or_none()
        if env:
            base_url = getattr(env, "base_url", None)

    job = ExecutionJob(
        script_id=payload.script_id,
        script_version_id=version_id,
        status=ExecutionJobStatus.queued.value,
        environment_id=payload.environment_id,
        base_url=base_url,
        browser=payload.browser,
        headless=payload.headless,
        timeout_seconds=payload.timeout_seconds,
        max_retries=payload.max_retries,
        retry_count=0,
        queued_at=datetime.now(timezone.utc),
        triggered_by=current_user.get("id") if isinstance(current_user, dict) else None,
        organization_id=script.organization_id,
        workspace_id=script.workspace_id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Push job to Redis queue for worker pickup
    try:
        redis = request.app.state.redis
        queue = ExecutionQueue(redis)
        await queue.submit_job(
            job_id=job.id,
            script_id=script.id,
            script_version_id=version_id,
            organization_id=script.organization_id,
            workspace_id=script.workspace_id,
            metadata={
                "browser": payload.browser,
                "headless": payload.headless,
                "timeout_seconds": payload.timeout_seconds,
                "base_url": base_url,
                "environment_id": str(payload.environment_id) if payload.environment_id else None,
            },
        )
    except Exception:
        # Queue push failure is non-fatal — worker can still poll DB
        import logging
        logging.getLogger("aitis.automation").warning(
            "Failed to push job %s to Redis queue", job.id, exc_info=True
        )

    # ── Security: create scoped execution token ──
    try:
        exec_token = create_execution_token(
            job_id=job.id,
            token_type="job_submit",
            organization_id=script.organization_id,
            workspace_id=script.workspace_id,
        )
    except Exception:
        exec_token = None  # Non-fatal — token is optional convenience

    # ── Security: record audit event ──
    record_audit_event(AuditEvent(
        event_type=AuditEventType.job_submitted,
        job_id=job.id,
        script_id=script.id,
        script_version_id=version_id,
        organization_id=script.organization_id,
        workspace_id=script.workspace_id,
        actor_id=current_user.get("id") if isinstance(current_user, dict) else None,
        actor_type="user",
        details={"browser": payload.browser, "base_url": base_url},
    ))

    # Attach execution token to response via extra field
    response_data = ExecutionJobOut.model_validate(job)
    if exec_token:
        response_data.execution_token = exec_token
    return response_data


@router.get("/execution-jobs", response_model=List[ExecutionJobSummary])
async def list_execution_jobs(
    script_id: Optional[uuid.UUID] = Query(None, description="Filter by script"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List execution jobs for the current tenant."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("workspace_id")

    stmt = select(ExecutionJob).where(
        ExecutionJob.organization_id == org_id,
        ExecutionJob.workspace_id == ws_id,
    )
    if script_id:
        stmt = stmt.where(ExecutionJob.script_id == script_id)
    if status_filter:
        stmt = stmt.where(ExecutionJob.status == status_filter)

    stmt = stmt.order_by(ExecutionJob.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    return jobs


@router.get("/execution-jobs/{job_id}", response_model=ExecutionJobOut)
async def get_execution_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get execution job detail."""
    stmt = select(ExecutionJob).where(ExecutionJob.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Execution job not found")

    # ── Security: verify tenant access ──
    if not verify_tenant_access(
        job.organization_id, job.workspace_id,
        current_user.get("organization_id"), current_user.get("workspace_id"),
    ):
        raise HTTPException(status_code=403, detail="Execution job access denied")
    return job


@router.post("/execution-jobs/{job_id}/cancel", response_model=ExecutionJobOut)
async def cancel_execution_job(
    job_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "automation_engineer")),
):
    """Cancel a queued or running execution job."""
    stmt = select(ExecutionJob).where(ExecutionJob.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Execution job not found")
    if not verify_tenant_access(
        job.organization_id, job.workspace_id,
        current_user.get("organization_id"), current_user.get("workspace_id"),
    ):
        raise HTTPException(status_code=403, detail="Execution job access denied")

    if job.status not in (
        ExecutionJobStatus.queued.value,
        ExecutionJobStatus.provisioning.value,
        ExecutionJobStatus.running.value,
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job in status '{job.status}'. Only queued, provisioning, or running jobs can be cancelled.",
        )

    job.status = ExecutionJobStatus.cancelled.value
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)

    # Signal worker to kill container via Redis pub/sub
    try:
        redis = request.app.state.redis
        queue = ExecutionQueue(redis)
        await queue.cancel_job(job.id)
    except Exception:
        import logging
        logging.getLogger("aitis.automation").warning(
            "Failed to publish cancel signal for job %s", job.id, exc_info=True
        )

    # ── Security: record audit event ──
    record_audit_event(AuditEvent(
        event_type=AuditEventType.job_cancelled,
        job_id=job.id,
        script_id=job.script_id,
        organization_id=job.organization_id,
        workspace_id=job.workspace_id,
        actor_id=current_user.get("id") if isinstance(current_user, dict) else None,
        actor_type="user",
        details={"previous_status": job.status},
    ))

    return job


# ══════════════════════════════════════════════════════════════════════
# Execution Results — retrieve results and step details
# ══════════════════════════════════════════════════════════════════════

@router.get("/execution-jobs/{job_id}/result", response_model=ExecutionResultDetail)
async def get_execution_result(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get the execution result for a job, including step-level details."""
    stmt = (
        select(ExecutionResult)
        .options(
            selectinload(ExecutionResult.step_results),
            selectinload(ExecutionResult.artifacts),
        )
        .where(ExecutionResult.job_id == job_id)
    )
    result = await db.execute(stmt)
    exec_result = result.scalar_one_or_none()
    if not exec_result:
        raise HTTPException(status_code=404, detail="Execution result not found")

    # ── Security: verify tenant access ──
    verify_tenant_access(
        exec_result.organization_id, exec_result.workspace_id,
        current_user.get("organization_id"), current_user.get("workspace_id"),
    )

    # Attach artifact links
    artifact_links = []
    if exec_result.artifacts:
        artifact_links = [
            {
                "id": str(a.id),
                "artifact_type": a.artifact_type,
                "name": a.name,
                "size_bytes": a.size_bytes,
                "content_type": a.content_type,
            }
            for a in exec_result.artifacts
        ]

    response = ExecutionResultDetail.model_validate(exec_result)
    response.artifact_links = artifact_links
    return response


@router.get("/execution-jobs/{job_id}/result/steps", response_model=List[ExecutionStepResultOut])
async def get_execution_step_results(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get step-level results for an execution job."""
    # First verify the job exists
    job_stmt = select(ExecutionJob).where(ExecutionJob.id == job_id)
    job_result = await db.execute(job_stmt)
    if not job_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Execution job not found")

    # Get all step results for all results of this job
    stmt = (
        select(ExecutionStepResult)
        .join(ExecutionResult)
        .where(ExecutionResult.job_id == job_id)
        .order_by(ExecutionStepResult.step_order)
    )
    result = await db.execute(stmt)
    steps = result.scalars().all()
    return steps


@router.get("/execution-jobs/{job_id}/suite-summary", response_model=SuiteSummary)
async def get_suite_summary(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get an aggregate suite summary for all test results in an execution job.

    Returns counts of passed/failed/skipped/timed_out tests, pass rate,
    duration statistics, and a summary of errors from failed tests.
    """
    # Verify job exists and tenant access
    job_stmt = select(ExecutionJob).where(ExecutionJob.id == job_id)
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Execution job not found")

    verify_tenant_access(
        job.organization_id, job.workspace_id,
        current_user.get("organization_id"), current_user.get("workspace_id"),
    )

    # Load all results for this job
    stmt = (
        select(ExecutionResult)
        .options(selectinload(ExecutionResult.artifacts))
        .where(ExecutionResult.job_id == job_id)
    )
    res = await db.execute(stmt)
    results = res.scalars().all()

    total = len(results)
    passed = sum(1 for r in results if r.status == "passed")
    failed = sum(1 for r in results if r.status == "failed")
    skipped = sum(1 for r in results if r.status == "skipped")
    timed_out = sum(1 for r in results if r.status == "timed_out")

    durations = [r.duration_seconds for r in results if r.duration_seconds is not None]
    total_dur = sum(durations) if durations else None
    avg_dur = (sum(durations) / len(durations)) if durations else None

    slowest = None
    slowest_dur = None
    if results:
        by_dur = sorted(
            [r for r in results if r.duration_seconds is not None],
            key=lambda r: r.duration_seconds,
            reverse=True,
        )
        if by_dur:
            slowest = by_dur[0].test_name
            slowest_dur = by_dur[0].duration_seconds

    error_summary = [
        {"test_name": r.test_name, "error_message": r.error_message}
        for r in results
        if r.status == "failed" and r.error_message
    ]

    artifact_count = sum(len(r.artifacts) for r in results)

    return SuiteSummary(
        job_id=job.id,
        script_id=job.script_id,
        status=job.status,
        browser=job.browser,
        environment=results[0].environment if results else None,
        total_tests=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        timed_out=timed_out,
        pass_rate=round(passed / total, 4) if total > 0 else 0.0,
        total_duration_seconds=total_dur,
        avg_duration_seconds=avg_dur,
        slowest_test=slowest,
        slowest_duration_seconds=slowest_dur,
        error_summary=error_summary,
        artifact_count=artifact_count,
    )


# ══════════════════════════════════════════════════════════════════════
# Recorded Actions — sessions, batch submit, list, generate from recording
# ══════════════════════════════════════════════════════════════════════

VALID_ACTION_TYPES = {
    "navigate", "click", "fill", "select",
    "assert_text", "assert_visible", "assert_url",
    "wait", "screenshot", "keyboard",
    "hover", "check", "uncheck",
    "upload", "download",
}


@router.get("/recorded-actions/sessions", response_model=List[RecordingSessionOut])
async def list_recording_sessions(
    script_id: Optional[uuid.UUID] = Query(None, description="Filter by script"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all recording sessions with summary metadata."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("workspace_id")

    stmt = (
        select(
            RecordedAction.session_id,
            RecordedAction.script_id,
            func.count(RecordedAction.id).label("action_count"),
            func.min(RecordedAction.action_type).label("first_action_type"),
            func.max(RecordedAction.action_type).label("last_action_type"),
            func.bool_or(RecordedAction.is_sensitive).label("has_sensitive_actions"),
            func.min(RecordedAction.created_at).label("created_at"),
        )
        .where(
            RecordedAction.organization_id == org_id,
            RecordedAction.workspace_id == ws_id,
        )
        .group_by(RecordedAction.session_id, RecordedAction.script_id)
        .order_by(RecordedAction.session_id)
    )
    if script_id:
        stmt = stmt.where(RecordedAction.script_id == script_id)

    result = await db.execute(stmt)
    rows = result.all()

    return [
        RecordingSessionOut(
            session_id=row.session_id,
            script_id=row.script_id,
            action_count=row.action_count,
            first_action_type=row.first_action_type,
            last_action_type=row.last_action_type,
            has_sensitive_actions=row.has_sensitive_actions or False,
            created_at=row.created_at,
        )
        for row in rows
    ]

@router.post("/recorded-actions/batch", response_model=List[RecordedActionOut], status_code=status.HTTP_201_CREATED)
async def submit_recorded_actions_batch(
    payload: RecordedActionBatch,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Submit a batch of recorded actions from a browser recording session.

    Actions are stored in framework-neutral form and can later be
    converted to Playwright, Selenium, or Cypress code.
    """
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("workspace_id")

    # Validate action types
    invalid_types = set()
    for action_in in payload.actions:
        if action_in.action_type not in VALID_ACTION_TYPES:
            invalid_types.add(action_in.action_type)
    if invalid_types:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid action type(s): {', '.join(sorted(invalid_types))}. "
                   f"Valid types: {', '.join(sorted(VALID_ACTION_TYPES))}",
        )

    # Verify script exists if script_id is provided
    if payload.script_id:
        stmt = select(AutomationScript).where(AutomationScript.id == payload.script_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Automation script not found")

    actions = []
    for i, action_in in enumerate(payload.actions):
        # Auto-detect sensitive fields (password inputs, tokens, etc.)
        is_sensitive = action_in.is_sensitive
        if not is_sensitive and action_in.action_type == "fill":
            selector_lower = (action_in.selector or "").lower()
            label_lower = (action_in.label or "").lower()
            sensitive_indicators = [
                "password", "passwd", "pwd", "secret", "token",
                "api-key", "apikey", "credential", "auth",
            ]
            if any(s in selector_lower or s in label_lower for s in sensitive_indicators):
                is_sensitive = True

        action = RecordedAction(
            script_id=payload.script_id,
            session_id=payload.session_id,
            action_order=action_in.action_order if action_in.action_order > 0 else i,
            action_type=action_in.action_type,
            selector=action_in.selector,
            label=action_in.label,
            value=action_in.value,
            is_sensitive=is_sensitive,
            url=action_in.url,
            expected_value=action_in.expected_value,
            metadata_=action_in.metadata,
            organization_id=org_id,
            workspace_id=ws_id,
        )
        db.add(action)
        actions.append(action)

    await db.commit()
    for a in actions:
        await db.refresh(a)

    return actions


@router.get("/scripts/{script_id}/recorded-actions", response_model=List[RecordedActionOut])
async def list_recorded_actions(
    script_id: uuid.UUID,
    session_id: Optional[str] = Query(None, description="Filter by recording session"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List recorded actions for a script, optionally filtered by session."""
    stmt = select(RecordedAction).where(RecordedAction.script_id == script_id)
    if session_id:
        stmt = stmt.where(RecordedAction.session_id == session_id)
    stmt = stmt.order_by(RecordedAction.action_order)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/scripts/{script_id}/generate-from-recording", response_model=AutomationOut)
async def generate_from_recording(
    script_id: uuid.UUID,
    session_id: str = Query(..., description="Recording session to convert"),
    framework: str = Query("playwright", description="Target framework: playwright, selenium, cypress, robot"),
    base_url: Optional[str] = Query(None, description="Override base URL"),
    browser: str = Query("chromium", description="Target browser"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "automation_engineer")),
):
    """Convert recorded actions to an automation spec for the chosen framework.

    Takes all recorded actions from the specified session and generates
    production-quality test code for Playwright, Selenium, Cypress, or Robot Framework.
    """
    # Get the script
    stmt = select(AutomationScript).where(AutomationScript.id == script_id)
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Automation script not found")

    # Get recorded actions for this session
    actions_stmt = (
        select(RecordedAction)
        .where(
            RecordedAction.script_id == script_id,
            RecordedAction.session_id == session_id,
        )
        .order_by(RecordedAction.action_order)
    )
    actions_result = await db.execute(actions_stmt)
    actions = actions_result.scalars().all()

    if not actions:
        raise HTTPException(status_code=404, detail="No recorded actions found for this session")

    # Dispatch to the correct framework generator
    fw = framework.lower()
    if fw == "selenium":
        spec = generate_selenium_from_recorded(
            title=script.name,
            recorded_actions=actions,
            base_url=base_url or "",
        )
        script.framework = "selenium"
        script.language = "python"
    elif fw in ("robot", "robotframework"):
        spec = generate_robot_from_recorded(
            title=script.name,
            recorded_actions=actions,
            base_url=base_url or "",
        )
        script.framework = "robot"
        script.language = "robotframework"
    elif fw in ("appium", "appium-java", "appium-python"):
        # Appium mobile test generation
        lang = "java" if "java" in fw else "python"
        result = convert_to_appium(
            playwright_code="",  # Will be generated from actions
            language=lang,
            platform="both",
            test_name=script.name.replace(" ", ""),
        )
        spec = {
            "content": result.code,
            "file_name": f"{script.name.replace(' ', '_')}.{'java' if lang == 'java' else 'py'}",
            "framework": "appium",
            "language": lang,
        }
        script.framework = "appium"
        script.language = lang
    elif fw == "cypress":
        # Cypress uses the Playwright converter's neutral actions but renders differently
        # For now, fall back to Playwright and note the limitation
        spec = generate_playwright_from_recorded(
            title=script.name,
            recorded_actions=actions,
            base_url=base_url or "",
            browser=browser,
        )
        script.framework = "cypress"
        script.language = "javascript"
    else:
        # Default: Playwright
        spec = generate_playwright_from_recorded(
            title=script.name,
            recorded_actions=actions,
            base_url=base_url or "",
            browser=browser,
        )
        script.framework = "playwright"
        script.language = "typescript"

    # Update the script with the generated code
    script.code = spec["content"]
    script.status = ScriptStatus.draft.value

    # Create a new version snapshot
    max_ver_stmt = select(func.max(ScriptVersion.version)).where(ScriptVersion.script_id == script_id)
    max_ver_result = await db.execute(max_ver_stmt)
    max_ver = max_ver_result.scalar() or 0

    new_version = ScriptVersion(
        script_id=script_id,
        version=max_ver + 1,
        code=spec["content"],
        file_path=spec.get("file_name"),
        status=ScriptStatus.draft.value,
        changed_by=current_user.get("id") if isinstance(current_user, dict) else None,
        change_summary=f"Generated from recording session {session_id}",
        code_hash=spec.get("code_hash"),
        organization_id=script.organization_id,
        workspace_id=script.workspace_id,
    )
    db.add(new_version)
    script.version = max_ver + 1

    await db.commit()

    return AutomationOut(**spec)


# ══════════════════════════════════════════════════════════════════════
# Framework Configurations — CRUD
# ══════════════════════════════════════════════════════════════════════

@router.get("/framework-configs", response_model=List[FrameworkConfigurationOut])
async def list_framework_configs(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List framework configurations for the current tenant."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("workspace_id")

    stmt = select(FrameworkConfiguration).where(
        FrameworkConfiguration.organization_id == org_id,
        FrameworkConfiguration.workspace_id == ws_id,
    ).order_by(FrameworkConfiguration.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/framework-configs", response_model=FrameworkConfigurationOut, status_code=status.HTTP_201_CREATED)
async def create_framework_config(
    payload: FrameworkConfigurationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "automation_engineer")),
):
    """Create a new framework configuration."""
    org_id = payload.organization_id or current_user.get("organization_id")
    ws_id = payload.workspace_id or current_user.get("workspace_id")

    config = FrameworkConfiguration(
        name=payload.name,
        framework=payload.framework,
        config=payload.config or {},
        base_url=payload.base_url,
        is_active=payload.is_active,
        organization_id=org_id,
        workspace_id=ws_id,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


# ══════════════════════════════════════════════════════════════════════
# Page Objects — CRUD
# ══════════════════════════════════════════════════════════════════════

@router.get("/page-objects", response_model=List[PageObjectOut])
async def list_page_objects(
    framework_config_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List page objects, optionally filtered by framework config."""
    stmt = select(PageObject)
    if framework_config_id:
        stmt = stmt.where(PageObject.framework_config_id == framework_config_id)
    stmt = stmt.order_by(PageObject.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/page-objects", response_model=PageObjectOut, status_code=status.HTTP_201_CREATED)
async def create_page_object(
    payload: PageObjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "automation_engineer")),
):
    """Create a new page object."""
    org_id = payload.organization_id or current_user.get("organization_id")
    ws_id = payload.workspace_id or current_user.get("workspace_id")

    po = PageObject(
        framework_config_id=payload.framework_config_id,
        name=payload.name,
        description=payload.description,
        url_pattern=payload.url_pattern,
        code=payload.code,
        organization_id=org_id,
        workspace_id=ws_id,
    )
    db.add(po)
    await db.commit()
    await db.refresh(po)
    return po


# ══════════════════════════════════════════════════════════════════════
# Locators — CRUD
# ══════════════════════════════════════════════════════════════════════

@router.get("/locators", response_model=List[LocatorOut])
async def list_locators(
    page_object_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List locators, optionally filtered by page object."""
    stmt = select(Locator)
    if page_object_id:
        stmt = stmt.where(Locator.page_object_id == page_object_id)
    stmt = stmt.order_by(Locator.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/locators", response_model=LocatorOut, status_code=status.HTTP_201_CREATED)
async def create_locator(
    payload: LocatorCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "automation_engineer")),
):
    """Create a new locator."""
    org_id = payload.organization_id or current_user.get("organization_id")
    ws_id = payload.workspace_id or current_user.get("workspace_id")

    loc = Locator(
        page_object_id=payload.page_object_id,
        name=payload.name,
        strategy=payload.strategy,
        value=payload.value,
        is_dynamic=payload.is_dynamic,
        organization_id=org_id,
        workspace_id=ws_id,
    )
    db.add(loc)
    await db.commit()
    await db.refresh(loc)
    return loc


@router.put("/locators/{locator_id}", response_model=LocatorOut)
async def update_locator(
    locator_id: uuid.UUID,
    payload: LocatorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "automation_engineer")),
):
    """Update a locator."""
    stmt = select(Locator).where(Locator.id == locator_id)
    result = await db.execute(stmt)
    locator = result.scalar_one_or_none()
    if not locator:
        raise HTTPException(status_code=404, detail="Locator not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(locator, field, value)

    await db.commit()
    await db.refresh(locator)
    return locator


# ══════════════════════════════════════════════════════════════════════
# Live Execution — WebSocket
# ══════════════════════════════════════════════════════════════════════

import asyncio
import json


@router.websocket("/execution-jobs/{job_id}/ws")
async def execution_job_ws(websocket: WebSocket, job_id: str, token: Optional[str] = Query(None)):
    """WebSocket endpoint for live execution job status updates.

    Clients connect to receive real-time status changes, step completions,
    and log output for a specific execution job. The server subscribes to
    Redis pub/sub channels for the job and forwards messages to the client.

    Message format (server → client):
        {"type": "status", "data": {"status": "running", ...}}
        {"type": "step", "data": {"step_name": "...", "status": "passed", ...}}
        {"type": "log", "data": {"line": "...", "timestamp": "..."}}
        {"type": "complete", "data": {"status": "passed", "duration_ms": 12345}}
        {"type": "error", "data": {"message": "..."}}
        {"type": "heartbeat", "data": {}}
    """
    payload = verify_token(token or "")
    if not payload or payload.get("type") != "access":
        await websocket.close(code=1008)
        return

    await websocket.accept()

    redis = websocket.app.state.redis

    # Verify job exists
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(ExecutionJob).where(ExecutionJob.id == uuid.UUID(job_id))
            result = await db.execute(stmt)
            job = result.scalar_one_or_none()
            if not job:
                await websocket.send_json({"type": "error", "data": {"message": "Job not found"}})
                await websocket.close()
                return
            if not verify_tenant_access(
                job.organization_id,
                job.workspace_id,
                payload.get("organization_id") or payload.get("org_id"),
                payload.get("workspace_id"),
            ):
                await websocket.send_json({"type": "error", "data": {"message": "Access denied"}})
                await websocket.close()
                return
            # Send initial state
            await websocket.send_json({
                "type": "status",
                "data": {
                    "job_id": str(job.id),
                    "status": job.status,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                },
            })
    except Exception as exc:
        await websocket.send_json({"type": "error", "data": {"message": str(exc)}})
        await websocket.close()
        return

    # Subscribe to Redis channels for this job
    pubsub = redis.pubsub()
    job_channel = f"automation:job:{job_id}"
    cancel_channel = "automation:cancel"
    await pubsub.subscribe(job_channel, cancel_channel)

    # Heartbeat task — send periodic pings to keep connection alive
    async def heartbeat():
        while True:
            try:
                await websocket.send_json({"type": "heartbeat", "data": {}})
                await asyncio.sleep(15)
            except Exception:
                break

    heartbeat_task = asyncio.create_task(heartbeat())

    try:
        # Forward Redis pub/sub messages to WebSocket client
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    payload = json.loads(message["data"])
                    msg_type = payload.get("type", "status")
                    await websocket.send_json({"type": msg_type, "data": payload.get("data", payload)})
                except (json.JSONDecodeError, TypeError):
                    await websocket.send_json({"type": "log", "data": {"line": message["data"]}})

            # Check if client disconnected (WebSocketDisconnect raised on send)
            # This is handled by the try/except wrapper
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        heartbeat_task.cancel()
        try:
            await pubsub.unsubscribe(job_channel, cancel_channel)
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════
# Audit Log — query security audit events
# ══════════════════════════════════════════════════════════════════════

@router.get("/audit-log")
async def query_audit_log(
    job_id: Optional[uuid.UUID] = Query(None, description="Filter by execution job"),
    script_id: Optional[uuid.UUID] = Query(None, description="Filter by script"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, ge=1, le=1000),
    current_user=Depends(get_current_user),
):
    """Query audit log events for the current tenant.

    Returns security audit events filtered by organization, job, script,
    or event type. Only events belonging to the caller's organization
    are returned.
    """
    org_id = current_user.get("organization_id")
    events = get_audit_log(
        organization_id=org_id,
        job_id=job_id,
        event_type=event_type,
        limit=limit,
    )
    # Optionally filter by script_id (not natively supported by get_audit_log)
    if script_id:
        events = [e for e in events if e.script_id == script_id]

    return [
        {
            "event_type": e.event_type,
            "job_id": str(e.job_id) if e.job_id else None,
            "script_id": str(e.script_id) if e.script_id else None,
            "script_version_id": str(e.script_version_id) if e.script_version_id else None,
            "organization_id": str(e.organization_id) if e.organization_id else None,
            "workspace_id": str(e.workspace_id) if e.workspace_id else None,
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "actor_type": e.actor_type,
            "details": e.details,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        }
        for e in events
    ]


# ══════════════════════════════════════════════════════════════════════
# Phase 8: Appium / Mobile Test Conversion
# ══════════════════════════════════════════════════════════════════════

from pydantic import BaseModel as PydanticBaseModel


class AppiumConvertRequest(PydanticBaseModel):
    playwright_code: str
    language: str = "java"  # java | python
    platform: str = "both"  # android | ios | both
    test_name: str = "MobileTest"
    package_name: str = "com.example.app"


class AppiumConvertResponse(PydanticBaseModel):
    code: str
    language: str
    platform: str
    imports: List[str]
    warnings: List[str]
    estimated_accuracy: float


class AppiumConfigRequest(PydanticBaseModel):
    platform: str = "android"
    app_path: str = "/path/to/app.apk"
    device_name: str = "emulator-5554"
    appium_server: str = "http://localhost:4723/wd/hub"


@router.post("/convert/appium", response_model=AppiumConvertResponse)
async def convert_to_appium_endpoint(
    payload: AppiumConvertRequest,
    current_user=Depends(get_current_user),
):
    """Convert a Playwright test script to Appium (Java/Python).

    Supports Android and iOS targets. Returns the converted code along
    with required imports, warnings, and an estimated accuracy score.
    """
    result = convert_to_appium(
        playwright_code=payload.playwright_code,
        language=payload.language,
        platform=payload.platform,
        test_name=payload.test_name,
        package_name=payload.package_name,
    )
    return AppiumConvertResponse(
        code=result.code,
        language=result.language,
        platform=result.platform,
        imports=result.imports,
        warnings=result.warnings,
        estimated_accuracy=result.estimated_accuracy,
    )


@router.post("/convert/appium/config")
async def get_appium_config(
    payload: AppiumConfigRequest,
    current_user=Depends(get_current_user),
):
    """Generate Appium desired capabilities configuration."""
    import json
    config = generate_appium_config(
        platform=payload.platform,
        app_path=payload.app_path,
        device_name=payload.device_name,
        appium_server=payload.appium_server,
    )
    return json.loads(config)
