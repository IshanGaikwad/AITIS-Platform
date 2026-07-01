"""CI/CD Integration API — pipeline triggers, webhooks, and status reporting.

Phase 9: Provides endpoints for CI/CD pipeline integration including
webhook receivers, pipeline status tracking, and test result reporting
back to CI/CD systems (GitHub Actions, GitLab CI, Jenkins, Azure DevOps).
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.models.automation import AutomationScript, ExecutionJob, ExecutionJobStatus

router = APIRouter()


# ── Pydantic schemas ─────────────────────────────────────────────────
class PipelineTriggerRequest(BaseModel):
    """Request to trigger a test execution from CI/CD."""
    pipeline_id: str = Field(..., description="CI/CD pipeline ID (e.g., GitHub run ID)")
    pipeline_name: str = Field("CI Pipeline", description="Human-readable pipeline name")
    provider: str = Field("github", description="CI provider: github, gitlab, jenkins, azure")
    branch: str = Field("main", description="Git branch")
    commit_sha: Optional[str] = None
    commit_message: Optional[str] = None
    script_ids: List[str] = Field(default_factory=list, description="Specific scripts to run")
    environment_id: Optional[str] = None
    base_url: Optional[str] = None
    browser: str = "chromium"
    headless: bool = True
    timeout_seconds: int = 600
    callback_url: Optional[str] = Field(None, description="URL to POST results back to")


class PipelineTriggerResponse(BaseModel):
    pipeline_run_id: str
    jobs: List[dict]
    status: str
    message: str


class PipelineStatus(BaseModel):
    pipeline_run_id: str
    provider: str
    branch: str
    commit_sha: Optional[str] = None
    status: str  # running | passed | failed | cancelled
    total_jobs: int = 0
    passed_jobs: int = 0
    failed_jobs: int = 0
    duration_seconds: Optional[float] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    report_url: Optional[str] = None


class WebhookPayload(BaseModel):
    """Generic webhook payload from CI/CD providers."""
    event: str
    provider: str
    payload: dict = Field(default_factory=dict)


class WebhookResponse(BaseModel):
    received: bool = True
    event: str
    provider: str
    action: str


class TestReport(BaseModel):
    """Test execution report for CI/CD consumption."""
    pipeline_run_id: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    pass_rate: float = 0.0
    duration_ms: int = 0
    results: List[dict] = Field(default_factory=list)
    summary: str = ""


# ══════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════

@router.post("/trigger", response_model=PipelineTriggerResponse)
async def trigger_pipeline_execution(
    payload: PipelineTriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead", "automation_engineer")),
):
    """Trigger test execution from a CI/CD pipeline.

    Creates execution jobs for the specified scripts and returns
    a pipeline run ID for tracking.
    """
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("project_id")

    pipeline_run_id = str(uuid.uuid4())
    jobs_created = []

    # Determine which scripts to run
    if payload.script_ids:
        script_ids = [uuid.UUID(sid) for sid in payload.script_ids]
    else:
        # Run all approved scripts for the tenant
        result = await db.execute(
            select(AutomationScript.id).where(
                AutomationScript.organization_id == org_id,
                AutomationScript.project_id == ws_id,
                AutomationScript.status == "ready",
            )
        )
        script_ids = [row[0] for row in result.all()]

    for sid in script_ids:
        script = await db.get(AutomationScript, sid)
        if not script:
            continue

        job = ExecutionJob(
            script_id=sid,
            script_version_id=script.approved_version_id,
            status=ExecutionJobStatus.queued.value,
            environment_id=uuid.UUID(payload.environment_id) if payload.environment_id else None,
            base_url=payload.base_url,
            browser=payload.browser,
            headless=payload.headless,
            timeout_seconds=payload.timeout_seconds,
            max_retries=1,
            retry_count=0,
            queued_at=datetime.now(timezone.utc),
            triggered_by=current_user.get("id") if isinstance(current_user, dict) else None,
            organization_id=org_id,
            project_id=ws_id,
            # Store pipeline metadata
            metadata_={
                "pipeline_run_id": pipeline_run_id,
                "pipeline_id": payload.pipeline_id,
                "pipeline_name": payload.pipeline_name,
                "provider": payload.provider,
                "branch": payload.branch,
                "commit_sha": payload.commit_sha,
                "commit_message": payload.commit_message,
                "callback_url": payload.callback_url,
            },
        )
        db.add(job)
        jobs_created.append({
            "job_id": str(job.id),
            "script_id": str(sid),
            "script_name": script.name,
            "status": "queued",
        })

    await db.commit()

    return PipelineTriggerResponse(
        pipeline_run_id=pipeline_run_id,
        jobs=jobs_created,
        status="triggered",
        message=f"Triggered {len(jobs_created)} test jobs for pipeline {payload.pipeline_id}",
    )


@router.get("/status/{pipeline_run_id}", response_model=PipelineStatus)
async def get_pipeline_status(
    pipeline_run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get the status of a CI/CD pipeline test run."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("project_id")

    # Find all jobs for this pipeline run
    result = await db.execute(
        select(ExecutionJob).where(
            ExecutionJob.organization_id == org_id,
            ExecutionJob.project_id == ws_id,
            ExecutionJob.metadata_["pipeline_run_id"].as_string() == pipeline_run_id,
        )
    )
    jobs = result.scalars().all()

    if not jobs:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    total = len(jobs)
    passed = sum(1 for j in jobs if j.status == "passed")
    failed = sum(1 for j in jobs if j.status in ("failed", "error"))
    running = sum(1 for j in jobs if j.status in ("queued", "running"))

    # Determine overall status
    if running > 0:
        overall = "running"
    elif failed > 0:
        overall = "failed"
    elif passed == total:
        overall = "passed"
    else:
        overall = "cancelled"

    # Get metadata from first job
    meta = jobs[0].metadata_ or {} if jobs else {}

    # Calculate duration
    started = min((j.started_at for j in jobs if j.started_at), default=None)
    completed = max((j.finished_at for j in jobs if j.finished_at), default=None)
    duration = (completed - started).total_seconds() if started and completed else None

    return PipelineStatus(
        pipeline_run_id=pipeline_run_id,
        provider=meta.get("provider", "unknown"),
        branch=meta.get("branch", "main"),
        commit_sha=meta.get("commit_sha"),
        status=overall,
        total_jobs=total,
        passed_jobs=passed,
        failed_jobs=failed,
        duration_seconds=duration,
        started_at=started.isoformat() if started else None,
        completed_at=completed.isoformat() if completed else None,
    )


@router.get("/report/{pipeline_run_id}", response_model=TestReport)
async def get_pipeline_report(
    pipeline_run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a detailed test report for a CI/CD pipeline run."""
    org_id = current_user.get("organization_id")
    ws_id = current_user.get("project_id")

    result = await db.execute(
        select(ExecutionJob).where(
            ExecutionJob.organization_id == org_id,
            ExecutionJob.project_id == ws_id,
            ExecutionJob.metadata_["pipeline_run_id"].as_string() == pipeline_run_id,
        )
    )
    jobs = result.scalars().all()

    if not jobs:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    results_list = []
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_duration = 0

    for job in jobs:
        summary = job.result_summary if isinstance(job.result_summary, dict) else {}
        duration_ms = int((job.duration_seconds or 0) * 1000)
        total_tests += summary.get("total_cases", 0)
        total_passed += summary.get("passed", 0)
        total_failed += summary.get("failed", 0)
        total_skipped += summary.get("skipped", 0)
        total_duration += duration_ms

        results_list.append({
            "job_id": str(job.id),
            "script_id": str(job.script_id),
            "status": job.status,
            "summary": summary,
            "duration_ms": duration_ms,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.finished_at.isoformat() if job.finished_at else None,
        })

    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0.0

    return TestReport(
        pipeline_run_id=pipeline_run_id,
        total_tests=total_tests,
        passed=total_passed,
        failed=total_failed,
        skipped=total_skipped,
        pass_rate=round(pass_rate, 1),
        duration_ms=total_duration,
        results=results_list,
        summary=f"{total_passed}/{total_tests} passed ({pass_rate:.1f}%) — {total_failed} failed, {total_skipped} skipped",
    )


@router.post("/webhook", response_model=WebhookResponse)
async def receive_webhook(
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    """Receive webhook events from CI/CD providers.

    Handles events like push, pull_request, merge_request from
    GitHub, GitLab, Jenkins, and Azure DevOps.
    """
    provider = payload.provider.lower()
    event = payload.event
    data = payload.payload

    action = "logged"

    if provider == "github":
        if event == "push":
            action = "push_received"
        elif event == "pull_request":
            pr_action = data.get("action", "opened")
            action = f"pr_{pr_action}"
        elif event == "check_run":
            action = "check_run_updated"

    elif provider == "gitlab":
        if event == "push":
            action = "push_received"
        elif event == "merge_request":
            mr_action = data.get("object_attributes", {}).get("action", "open")
            action = f"mr_{mr_action}"

    elif provider == "jenkins":
        action = f"jenkins_{event}"

    elif provider == "azure":
        if event == "git.push":
            action = "push_received"
        elif event == "git.pullrequest":
            action = "pr_updated"

    # Log the webhook event (could store in DB for audit)
    import logging
    logging.getLogger("aitis.cicd").info(
        "Webhook received: provider=%s event=%s action=%s",
        provider, event, action,
    )

    return WebhookResponse(
        received=True,
        event=event,
        provider=provider,
        action=action,
    )


@router.get("/providers")
async def list_supported_providers(
    current_user=Depends(get_current_user),
):
    """List supported CI/CD providers and their capabilities."""
    return {
        "providers": [
            {
                "name": "github",
                "label": "GitHub Actions",
                "webhook_events": ["push", "pull_request", "check_run", "workflow_run"],
                "supports_trigger": True,
                "supports_status_report": True,
            },
            {
                "name": "gitlab",
                "label": "GitLab CI",
                "webhook_events": ["push", "merge_request", "pipeline"],
                "supports_trigger": True,
                "supports_status_report": True,
            },
            {
                "name": "jenkins",
                "label": "Jenkins",
                "webhook_events": ["build_started", "build_completed"],
                "supports_trigger": True,
                "supports_status_report": True,
            },
            {
                "name": "azure",
                "label": "Azure DevOps",
                "webhook_events": ["git.push", "git.pullrequest", "build.complete"],
                "supports_trigger": True,
                "supports_status_report": True,
            },
            {
                "name": "circleci",
                "label": "CircleCI",
                "webhook_events": ["workflow_completed", "job_completed"],
                "supports_trigger": False,
                "supports_status_report": True,
            },
        ]
    }


@router.get("/config/github-actions")
async def generate_github_actions_config(
    workspace_name: str = Query("aitis-tests"),
    scripts_glob: str = Query("tests/**/*.spec.ts"),
    base_url: str = Query("https://api.aitis.dev"),
    current_user=Depends(get_current_user),
):
    """Generate a GitHub Actions workflow YAML for AITIS integration."""
    yaml_content = f"""# AITIS Test Intelligence — GitHub Actions Integration
# Generated by AITIS Platform

name: AITIS Test Execution

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      browser:
        description: 'Browser to run tests'
        required: true
        default: 'chromium'
        type: choice
        options:
          - chromium
          - firefox
          - webkit

jobs:
  aitis-tests:
    name: Run AITIS Tests
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Trigger AITIS Test Execution
        id: aitis
        uses: aitis-platform/test-action@v1
        with:
          api_url: '{base_url}'
          api_token: ${{{{ secrets.AITIS_API_TOKEN }}}}
          workspace_id: ${{{{ secrets.AITIS_WORKSPACE_ID }}}}
          scripts_glob: '{scripts_glob}'
          browser: ${{{{ inputs.browser || 'chromium' }}}}
          headless: true
          wait_for_results: true

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: aitis-test-results
          path: aitis-results/

      - name: Report status
        if: always()
        run: |
          echo "Test Results: ${{{{ steps.aitis.outputs.result }}}}"
          echo "Pass Rate: ${{{{ steps.aitis.outputs.pass_rate }}}}%"
          echo "Report URL: ${{{{ steps.aitis.outputs.report_url }}}}"
"""
    return {"filename": f".github/workflows/{workspace_name}.yml", "content": yaml_content}


@router.get("/config/gitlab-ci")
async def generate_gitlab_ci_config(
    workspace_name: str = Query("aitis-tests"),
    scripts_glob: str = Query("tests/**/*.spec.ts"),
    base_url: str = Query("https://api.aitis.dev"),
    current_user=Depends(get_current_user),
):
    """Generate a GitLab CI configuration for AITIS integration."""
    yaml_content = f"""# AITIS Test Intelligence — GitLab CI Integration
# Generated by AITIS Platform

stages:
  - test
  - report

aitis-tests:
  stage: test
  image: node:20
  timeout: 30m
  script:
    - npm ci
    - |
      curl -X POST "{base_url}/api/cicd/trigger" \\
        -H "Authorization: Bearer $AITIS_API_TOKEN" \\
        -H "Content-Type: application/json" \\
        -d '{{
          "pipeline_id": "$CI_PIPELINE_ID",
          "pipeline_name": "$CI_PROJECT_NAME",
          "provider": "gitlab",
          "branch": "$CI_COMMIT_BRANCH",
          "commit_sha": "$CI_COMMIT_SHA",
          "commit_message": "$CI_COMMIT_MESSAGE",
          "scripts_glob": "{scripts_glob}",
          "callback_url": "{base_url}/api/cicd/webhook"
        }}' \\
        -o aitis-response.json
    - cat aitis-response.json
  artifacts:
    when: always
    paths:
      - aitis-response.json
      - aitis-results/
    reports:
      junit: aitis-results/*.xml
"""
    return {"filename": ".gitlab-ci.yml", "content": yaml_content}