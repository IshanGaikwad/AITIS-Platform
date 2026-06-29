"""Execution Worker — Pulls jobs from Redis queue, runs Playwright in Docker.

This is a standalone async process (run via `python -m app.services.execution_worker`)
that:
1. Connects to Redis and the database
2. Polls the execution queue for pending jobs
3. Spawns ephemeral Docker containers with Playwright
4. Streams stdout/stderr and collects artifacts
5. Writes results back to the database
6. Publishes status updates via Redis pub/sub

Architecture:
    ┌──────────┐    Redis Queue    ┌──────────────┐    Docker API    ┌──────────────┐
    │  FastAPI  │ ──────────────▶  │  Worker      │ ──────────────▶ │  Container   │
    │  Backend  │                  │  Process     │                  │  (Playwright) │
    └──────────┘ ◀──────────────  └──────────────┘ ◀──────────────  └──────────────┘
                   Redis Pub/Sub     Worker Heartbeat   Artifacts + Results
"""

import asyncio
import json
import logging
import os
import signal
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Docker SDK
try:
    import docker
    from docker.errors import DockerException, APIError, NotFound
    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False

# Redis
from redis import asyncio as aioredis

# Database
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Models
from app.models.automation import (
    AutomationScript,
    ExecutionJob,
    ExecutionJobStatus,
    ExecutionResult,
    ExecutionStepResult,
    ScriptVersion,
)
from app.core.config import settings
from app.services.execution_queue import (
    ExecutionQueue,
    get_queue,
    CANCEL_CHANNEL,
    JOB_STATUS_PREFIX,
)
from app.services.execution_security import (
    validate_script,
    create_execution_token,
    record_audit_event,
    AuditEvent,
    AuditEventType,
    sanitize_environment_vars,
    verify_tenant_access,
    get_container_network_config,
)

logger = logging.getLogger("aitis.execution_worker")

# ── Worker State ──────────────────────────────────────────────────────

WORKER_ID = f"worker-{uuid.uuid4().hex[:8]}"
_shutdown_event = asyncio.Event()
_cancelled_jobs: set[str] = set()


# ── Docker Container Manager ──────────────────────────────────────────

class ContainerManager:
    """Manages ephemeral Docker containers for Playwright execution."""

    def __init__(self):
        if not HAS_DOCKER:
            raise RuntimeError("Docker SDK not installed. Run: pip install docker")
        self.client = docker.DockerClient(base_url=settings.docker_socket)
        self.image = settings.execution_container_image
        self.cpu_limit = settings.execution_cpu_limit
        self.memory_limit = settings.execution_memory_limit
        self.network_mode = settings.execution_network_mode
        self.artifacts_dir = settings.execution_artifacts_dir

    async def spawn(
        self,
        job_id: str,
        script_code: str,
        base_url: Optional[str],
        browser: str = "chromium",
        headless: bool = True,
        timeout_seconds: int = 300,
        environment_vars: Optional[dict] = None,
        execution_token: Optional[str] = None,
    ) -> dict:
        """Spawn an ephemeral Docker container to run a Playwright test.

        Returns a dict with container_id, exit_code, stdout, stderr, duration_seconds.
        Security: environment_vars should already be sanitized via
        sanitize_environment_vars() before being passed here.
        """
        # Prepare workspace directory
        workspace = Path(self.artifacts_dir) / job_id
        workspace.mkdir(parents=True, exist_ok=True)

        # Write the test script into the workspace
        spec_file = workspace / "test.spec.ts"
        spec_file.write_text(script_code, encoding="utf-8")

        # Write a runner script
        runner = workspace / "run.sh"
        runner.write_text(
            _generate_runner_script(spec_file.name, browser, headless, base_url, timeout_seconds),
            encoding="utf-8",
        )

        # Container environment variables (already sanitized by caller)
        env = {
            "PLAYWRIGHT_BROWSERS_PATH": "/ms-playwright",
            "NODE_TLS_REJECT_UNAUTHORIZED": "0" if settings.app_env == "development" else "1",
        }
        if execution_token:
            env["AITIS_EXECUTION_TOKEN"] = execution_token
        if environment_vars:
            # Inject secrets as environment variables (prefixed with SECRET_)
            for k, v in environment_vars.items():
                env[f"SECRET_{k.upper()}"] = v

        # Container labels for tracking
        labels = {
            "aitis.job_id": job_id,
            "aitis.worker_id": WORKER_ID,
            "aitis.managed": "true",
        }

        # ── Security: Get network config from execution_security ──
        network_config = get_container_network_config(
            allowed_networks=settings.execution_allowed_networks,
        )
        # Use the network_mode from config if set, otherwise fall back to settings
        container_network_mode = network_config.get("network_mode", self.network_mode)

        loop = asyncio.get_event_loop()

        try:
            # Pull image if not available (async to avoid blocking)
            await loop.run_in_executor(None, self._ensure_image)

            # ── Audit: container spawning ─────────────────────────
            record_audit_event(AuditEvent(
                event_type=AuditEventType.container_spawned,
                job_id=uuid.UUID(job_id) if len(job_id) >= 32 else None,
                actor_type="worker",
                details={"image": self.image, "network": container_network_mode},
            ))

            # Create and start container
            container = await loop.run_in_executor(
                None,
                lambda: self.client.containers.run(
                    image=self.image,
                    command=f"bash /workspace/run.sh",
                    detach=True,
                    name=f"aitis-exec-{job_id[:12]}",
                    environment=env,
                    labels=labels,
                    mounts=[
                        docker.types.Mount(
                            target="/workspace",
                            source=str(workspace),
                            type="bind",
                        ),
                    ],
                    cpu_count=1,
                    mem_limit=self.memory_limit,
                    network_mode=container_network_mode,
                    # Security: no new privileges, read-only root filesystem where possible
                    security_opt=["no-new-privileges"],
                    # Auto-remove container after it finishes
                    auto_remove=False,
                ),
            )

            container_id = container.id
            logger.info("Container %s started for job %s", container_id[:12], job_id)

            # Wait for container to finish (with timeout)
            start_time = datetime.now(timezone.utc)
            try:
                exit_result = await asyncio.wait_for(
                    loop.run_in_executor(None, container.wait),
                    timeout=timeout_seconds + 30,  # Extra buffer for setup/teardown
                )
                exit_code = exit_result.get("StatusCode", -1)
            except asyncio.TimeoutError:
                logger.warning("Container for job %s timed out, killing...", job_id)
                await loop.run_in_executor(None, container.kill)
                exit_code = -1

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            # Collect logs
            try:
                stdout_logs = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr_logs = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            except Exception:
                stdout_logs = ""
                stderr_logs = ""

            # Collect artifacts (screenshots, traces, etc.)
            artifacts = self._collect_artifacts(workspace, job_id)

            # Remove container
            try:
                await loop.run_in_executor(None, container.remove, True)
            except Exception:
                pass

            return {
                "container_id": container_id,
                "exit_code": exit_code,
                "stdout": stdout_logs,
                "stderr": stderr_logs,
                "duration_seconds": duration,
                "artifacts": artifacts,
            }

        except (DockerException, APIError) as exc:
            logger.error("Docker error for job %s: %s", job_id, exc)
            return {
                "container_id": None,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(exc),
                "duration_seconds": 0,
                "artifacts": [],
                "error": str(exc),
            }

    def _ensure_image(self):
        """Ensure the Docker image is available locally."""
        try:
            self.client.images.get(self.image)
        except docker.errors.ImageNotFound:
            logger.info("Pulling Docker image: %s ...", self.image)
            self.client.images.pull(self.image)

    def _collect_artifacts(self, workspace: Path, job_id: str) -> list[dict]:
        """Collect artifacts from the container workspace."""
        artifacts = []
        artifacts_dir = workspace / "artifacts"
        if artifacts_dir.exists():
            for f in artifacts_dir.rglob("*"):
                if f.is_file():
                    artifacts.append({
                        "name": f.name,
                        "path": str(f.relative_to(workspace)),
                        "size": f.stat().st_size,
                        "job_id": job_id,
                    })
        # Also check for test-results directory (Playwright default output)
        results_dir = workspace / "test-results"
        if results_dir.exists():
            for f in results_dir.rglob("*"):
                if f.is_file():
                    artifacts.append({
                        "name": f.name,
                        "path": str(f.relative_to(workspace)),
                        "size": f.stat().st_size,
                        "job_id": job_id,
                    })
        return artifacts

    async def kill_container(self, container_id: str) -> bool:
        """Kill a running container by ID."""
        loop = asyncio.get_event_loop()
        try:
            container = await loop.run_in_executor(
                None, lambda: self.client.containers.get(container_id)
            )
            await loop.run_in_executor(None, container.kill)
            logger.info("Killed container %s", container_id[:12])
            return True
        except NotFound:
            logger.warning("Container %s not found (may have already exited)", container_id[:12])
            return False
        except Exception as exc:
            logger.error("Error killing container %s: %s", container_id[:12], exc)
            return False


def _generate_runner_script(
    spec_file: str,
    browser: str,
    headless: bool,
    base_url: Optional[str],
    timeout_seconds: int,
) -> str:
    """Generate a bash runner script for the Docker container."""
    headless_flag = "" if headless else "--headed"
    base_url_env = f'export BASE_URL="{base_url or ""}"'

    return f"""#!/bin/bash
set -euo pipefail

# ── AITIS Playwright Runner ──────────────────────────────────────
# Generated by execution_worker — do not edit manually

{base_url_env}
export BROWSER="{browser}"
export TIMEOUT="{timeout_seconds}"

# Install dependencies and run
cd /workspace

# Run Playwright test
npx playwright test {spec_file} \\
    --project={browser} \\
    {headless_flag} \\
    --timeout={timeout_seconds}000 \\
    --reporter=json,list \\
    --output=/workspace/artifacts/ \\
    2>&1 | tee /workspace/artifacts/test-output.log

EXIT_CODE=${{PIPESTATUS[0]}}

# Copy Playwright artifacts
if [ -d "test-results" ]; then
    cp -r test-results/* /workspace/artifacts/ 2>/dev/null || true
fi

exit $EXIT_CODE
"""


# ── Result Writer ─────────────────────────────────────────────────────

async def write_results(
    session: AsyncSession,
    job_id: uuid.UUID,
    container_result: dict,
) -> None:
    """Write execution results to the database."""
    exit_code = container_result.get("exit_code", -1)
    status = ExecutionJobStatus.passed.value if exit_code == 0 else ExecutionJobStatus.failed.value
    if container_result.get("error"):
        status = ExecutionJobStatus.infrastructure_error.value

    # Update the ExecutionJob
    job_stmt = select(ExecutionJob).where(ExecutionJob.id == job_id)
    result = await session.execute(job_stmt)
    job = result.scalar_one_or_none()
    if not job:
        logger.error("Job %s not found in database — cannot write results", job_id)
        return

    job.status = status
    job.container_id = container_result.get("container_id")
    job.finished_at = datetime.now(timezone.utc)
    job.duration_seconds = container_result.get("duration_seconds")
    job.error_message = container_result.get("error")
    job.result_summary = {
        "exit_code": exit_code,
        "artifacts_count": len(container_result.get("artifacts", [])),
    }

    # Parse Playwright JSON report for step-level results
    stdout = container_result.get("stdout", "")
    stderr = container_result.get("stderr", "")
    step_results = _parse_playwright_output(stdout)

    # Create ExecutionResult
    exec_result = ExecutionResult(
        job_id=job_id,
        test_name=job_id.hex[:8],  # Will be updated from report
        status=status,
        browser=job.browser if job else "chromium",
        environment=str(job.environment_id) if job and job.environment_id else None,
        duration_seconds=container_result.get("duration_seconds", 0),
        error_message=container_result.get("error"),
        stack_trace=stderr[:10000] if stderr else None,
        stdout=stdout[:50000] if stdout else None,
        stderr=stderr[:50000] if stderr else None,
        result_json=step_results.get("report_json"),
        organization_id=job.organization_id,
        workspace_id=job.workspace_id,
    )
    session.add(exec_result)
    await session.flush()  # Get the result ID

    # Create step-level results
    for i, step in enumerate(step_results.get("steps", [])):
        step_result = ExecutionStepResult(
            result_id=exec_result.id,
            step_name=step.get("title", f"Step {i + 1}"),
            step_order=i + 1,
            status=step.get("status", "unknown"),
            duration_seconds=step.get("duration", 0) / 1000,  # ms → seconds
            error_message=step.get("error"),
            actual_result=step.get("expected"),
            screenshot_url=step.get("screenshot"),
            organization_id=job.organization_id,
            workspace_id=job.workspace_id,
        )
        session.add(step_result)

    await session.commit()
    logger.info("Results written for job %s (status=%s)", job_id, status)


def _parse_playwright_output(stdout: str) -> dict:
    """Parse Playwright JSON reporter output for step-level results.

    Playwright's JSON reporter outputs a JSON array of test results.
    We extract suites, tests, and attachments from it.
    """
    steps = []
    report_json = None

    # Try to find JSON output in stdout
    # Playwright JSON reporter writes to a file, but we can also parse
    # the structured output from the list reporter
    try:
        # Look for JSON array in output
        json_start = stdout.rfind("[")
        json_end = stdout.rfind("]")
        if json_start >= 0 and json_end > json_start:
            potential_json = stdout[json_start:json_end + 1]
            report_json = json.loads(potential_json)
            for suite in report_json if isinstance(report_json, list) else []:
                for test in suite.get("tests", []):
                    for result in test.get("results", []):
                        steps.append({
                            "title": test.get("title", "Unknown"),
                            "status": result.get("status", "unknown"),
                            "duration": result.get("duration", 0),
                            "error": result.get("error", {}).get("message") if isinstance(result.get("error"), dict) else result.get("error"),
                            "expected": result.get("expected"),
                            "screenshot": None,
                        })
    except (json.JSONDecodeError, KeyError, TypeError):
        # If we can't parse JSON, create a single step from the output
        if stdout.strip():
            steps.append({
                "title": "Test execution",
                "status": "completed",
                "duration": 0,
                "error": None,
                "expected": None,
                "screenshot": None,
            })

    return {"steps": steps, "report_json": report_json}


# ── Worker Main Loop ──────────────────────────────────────────────────

class ExecutionWorker:
    """Main worker loop — polls Redis queue, runs containers, writes results."""

    def __init__(self):
        self.worker_id = WORKER_ID
        self.queue: Optional[ExecutionQueue] = None
        self.redis: Optional[aioredis.Redis] = None
        self.container_mgr: Optional[ContainerManager] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._cancel_listener: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Initialize connections and start the worker loop."""
        logger.info("Starting AITIS Execution Worker %s ...", self.worker_id)

        # Redis
        self.redis = aioredis.from_url(settings.redis_url, decode_responses=True, protocol=2)
        await self.redis.ping()
        logger.info("Connected to Redis")

        # Execution queue
        self.queue = get_queue(self.redis, max_concurrent=settings.execution_max_concurrent)

        # Docker
        try:
            self.container_mgr = ContainerManager()
            logger.info("Docker client initialized (image=%s)", settings.execution_container_image)
        except Exception as exc:
            logger.error("Failed to initialize Docker client: %s", exc)
            logger.error("Worker will run in DRY-RUN mode (no containers will be spawned)")
            self.container_mgr = None

        # Database
        engine = create_async_engine(settings.database_url, pool_size=5, max_overflow=10)
        self.session_factory = async_sessionmaker(engine, expire_on_commit=False)

        # Start cancel listener
        self._cancel_listener = asyncio.create_task(self._listen_for_cancellations())

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Register signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop = asyncio.get_event_loop()
                loop.add_signal_handler(sig, lambda: _shutdown_event.set())
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass

        logger.info("Worker %s ready — polling for jobs...", self.worker_id)

        # ── Main Loop ─────────────────────────────────────────────
        while not _shutdown_event.is_set():
            try:
                job = await self.queue.dequeue_job(self.worker_id)
                if job:
                    asyncio.create_task(self._execute_job(job))
                else:
                    # No job available — brief sleep to avoid busy-wait
                    await asyncio.sleep(0.5)
            except Exception as exc:
                logger.error("Error in worker loop: %s", exc, exc_info=True)
                await asyncio.sleep(1)

        # ── Shutdown ──────────────────────────────────────────────
        logger.info("Worker %s shutting down...", self.worker_id)
        if self._cancel_listener:
            self._cancel_listener.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        await self.redis.aclose()
        logger.info("Worker %s stopped.", self.worker_id)

    async def _execute_job(self, job_payload: dict) -> None:
        """Execute a single job: fetch script, spawn container, write results."""
        job_id = uuid.UUID(job_payload["job_id"])
        script_version_id = uuid.UUID(job_payload["script_version_id"])

        logger.info("Executing job %s (script_version=%s)", job_id, script_version_id)

        async with self.session_factory() as session:
            # Fetch the script version code
            ver_stmt = select(ScriptVersion).where(ScriptVersion.id == script_version_id)
            ver_result = await session.execute(ver_stmt)
            version = ver_result.scalar_one_or_none()
            if not version:
                logger.error("Script version %s not found", script_version_id)
                await self.queue.update_job_status(job_id, "infrastructure_error", {
                    "error": "Script version not found",
                })
                return

            # Fetch the job for configuration
            job_stmt = select(ExecutionJob).where(ExecutionJob.id == job_id)
            job_result = await session.execute(job_stmt)
            job = job_result.scalar_one_or_none()
            if not job:
                logger.error("Job %s not found in database", job_id)
                return

            # Update job status to running
            job.status = ExecutionJobStatus.running.value
            job.started_at = datetime.now(timezone.utc)
            job.worker_id = self.worker_id
            await session.commit()

            # ── Audit: job started ────────────────────────────────
            record_audit_event(AuditEvent(
                event_type=AuditEventType.job_started,
                job_id=job_id,
                script_id=job.script_id,
                organization_id=job.organization_id,
                workspace_id=job.workspace_id,
                actor_type="worker",
                details={"worker_id": self.worker_id},
            ))

            await self.queue.update_job_status(job_id, "running", {
                "worker_id": self.worker_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
            })

            # Publish status update for WebSocket clients
            await self._publish_job_update(job_id, "status", {
                "status": "running",
                "worker_id": self.worker_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
            })

            # Check if job was cancelled while waiting
            if str(job_id) in _cancelled_jobs:
                _cancelled_jobs.discard(str(job_id))
                job.status = ExecutionJobStatus.cancelled.value
                job.finished_at = datetime.now(timezone.utc)
                await session.commit()
                await self.queue.update_job_status(job_id, "cancelled")
                await self._publish_job_update(job_id, "status", {
                    "status": "cancelled",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                })
                # ── Audit: job cancelled ──────────────────────────
                record_audit_event(AuditEvent(
                    event_type=AuditEventType.job_cancelled,
                    job_id=job_id,
                    organization_id=job.organization_id,
                    workspace_id=job.workspace_id,
                    actor_type="worker",
                ))
                logger.info("Job %s was cancelled before execution", job_id)
                return

            # ── Security: Validate script before execution ─────────
            validation = validate_script(version.code, language="typescript")
            record_audit_event(AuditEvent(
                event_type=AuditEventType.script_validated if validation.is_valid else AuditEventType.script_validation_failed,
                job_id=job_id,
                script_id=job.script_id,
                script_version_id=script_version_id,
                organization_id=job.organization_id,
                workspace_id=job.workspace_id,
                actor_type="worker",
                details={"is_valid": validation.is_valid, "errors": validation.errors, "warnings": validation.warnings},
            ))

            if not validation.is_valid:
                logger.error("Script validation failed for job %s: %s", job_id, validation.errors)
                job.status = ExecutionJobStatus.failed.value
                job.finished_at = datetime.now(timezone.utc)
                job.error_message = f"Script validation failed: {'; '.join(validation.errors)}"
                await session.commit()
                await self.queue.update_job_status(job_id, "failed", {"error": job.error_message})
                await self._publish_job_update(job_id, "status", {
                    "status": "failed",
                    "error": job.error_message,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                })
                return

            # ── Security: Verify tenant isolation ──────────────────
            if job.organization_id:
                script_stmt = select(AutomationScript).where(AutomationScript.id == job.script_id)
                script_result = await session.execute(script_stmt)
                script = script_result.scalar_one_or_none()
                if script and not verify_tenant_access(
                    resource_org_id=script.organization_id or uuid.UUID(int=0),
                    resource_ws_id=script.workspace_id,
                    request_org_id=job.organization_id,
                    request_ws_id=job.workspace_id,
                ):
                    logger.error("Tenant isolation violation: job %s org=%s ws=%s accessing script org=%s ws=%s",
                                job_id, job.organization_id, job.workspace_id,
                                script.organization_id, script.workspace_id)
                    job.status = ExecutionJobStatus.failed.value
                    job.finished_at = datetime.now(timezone.utc)
                    job.error_message = "Tenant isolation violation — script does not belong to this organization/workspace"
                    await session.commit()
                    await self.queue.update_job_status(job_id, "failed", {"error": job.error_message})
                    await self._publish_job_update(job_id, "status", {
                        "status": "failed",
                        "error": job.error_message,
                        "finished_at": datetime.now(timezone.utc).isoformat(),
                    })
                    return

            # ── Security: Create short-lived execution token ──────
            exec_token = create_execution_token(
                job_id=job_id,
                organization_id=job.organization_id,
                workspace_id=job.workspace_id,
                expires_minutes=max(job.timeout_seconds or settings.execution_timeout_default // 60, 10),
            )
            record_audit_event(AuditEvent(
                event_type=AuditEventType.token_created,
                job_id=job_id,
                organization_id=job.organization_id,
                workspace_id=job.workspace_id,
                actor_type="worker",
                details={"token_type": "execution:job_submit"},
            ))

            # ── Security: Sanitize environment variables ──────────
            safe_env_vars = sanitize_environment_vars(job.environment_vars or {})

            # Spawn Docker container
            if self.container_mgr:
                container_result = await self.container_mgr.spawn(
                    job_id=str(job_id),
                    script_code=version.code,
                    base_url=job.base_url,
                    browser=job.browser or "chromium",
                    headless=job.headless if job.headless is not None else True,
                    timeout_seconds=job.timeout_seconds or settings.execution_timeout_default,
                    environment_vars=safe_env_vars,
                    execution_token=exec_token,
                )
            else:
                # Dry-run mode — no Docker available
                container_result = {
                    "container_id": None,
                    "exit_code": -1,
                    "stdout": "Worker running in dry-run mode — Docker not available",
                    "stderr": "",
                    "duration_seconds": 0,
                    "artifacts": [],
                    "error": "Docker SDK not available",
                }

            # Write results to database
            await write_results(session, job_id, container_result)

            # Update Redis queue status
            final_status = container_result.get("exit_code", -1) == 0 and "passed" or "failed"
            if container_result.get("error"):
                final_status = "infrastructure_error"
            await self.queue.update_job_status(job_id, final_status)

            # Publish final status for WebSocket clients
            await self._publish_job_update(job_id, "status", {
                "status": final_status,
                "exit_code": container_result.get("exit_code", -1),
                "duration_seconds": container_result.get("duration_seconds", 0),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error": container_result.get("error"),
            })

            # ── Audit: job completed ───────────────────────────────
            audit_type = (
                AuditEventType.job_completed if final_status == "passed"
                else AuditEventType.job_failed if final_status == "failed"
                else AuditEventType.job_failed  # infrastructure_error, etc.
            )
            record_audit_event(AuditEvent(
                event_type=audit_type,
                job_id=job_id,
                script_id=job.script_id,
                organization_id=job.organization_id,
                workspace_id=job.workspace_id,
                actor_type="worker",
                details={
                    "status": final_status,
                    "exit_code": container_result.get("exit_code", -1),
                    "duration_seconds": container_result.get("duration_seconds", 0),
                },
            ))

            # Publish step results for WebSocket clients
            step_results = _parse_playwright_output(container_result.get("stdout", ""))
            if step_results.get("steps"):
                await self._publish_job_update(job_id, "steps", {
                    "steps": step_results["steps"],
                    "total": len(step_results["steps"]),
                })

            # Publish log output for WebSocket clients
            if container_result.get("stdout"):
                await self._publish_job_update(job_id, "log", {
                    "stream": "stdout",
                    "text": container_result["stdout"][:50000],
                })
            if container_result.get("stderr"):
                await self._publish_job_update(job_id, "log", {
                    "stream": "stderr",
                    "text": container_result["stderr"][:50000],
                })

            logger.info("Job %s completed (status=%s, duration=%.1fs)",
                        job_id, final_status, container_result.get("duration_seconds", 0))

    async def _listen_for_cancellations(self) -> None:
        """Subscribe to Redis cancel channel and track cancelled jobs."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(CANCEL_CHANNEL)
        logger.info("Listening for cancellation signals on %s", CANCEL_CHANNEL)

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    job_id = data.get("job_id")
                    if job_id:
                        _cancelled_jobs.add(job_id)
                        logger.info("Received cancellation for job %s", job_id)

                        # If container is running, kill it
                        if self.container_mgr:
                            # Look up container by job label
                            try:
                                containers = self.container_mgr.client.containers.list(
                                    filters={"label": f"aitis.job_id={job_id}"}
                                )
                                for c in containers:
                                    await asyncio.get_event_loop().run_in_executor(
                                        None, c.kill
                                    )
                                    logger.info("Killed container %s for cancelled job %s",
                                                c.id[:12], job_id)
                            except Exception as exc:
                                logger.error("Error killing container for job %s: %s", job_id, exc)
                except (json.JSONDecodeError, KeyError) as exc:
                    logger.error("Invalid cancel message: %s", exc)

    async def _heartbeat_loop(self) -> None:
        """Periodically send worker heartbeat to Redis."""
        while not _shutdown_event.is_set():
            try:
                await self.queue.worker_heartbeat(self.worker_id, {
                    "pid": os.getpid(),
                })
            except Exception as exc:
                logger.error("Heartbeat error: %s", exc)
            await asyncio.sleep(10)

    async def _publish_job_update(
        self, job_id: uuid.UUID, msg_type: str, data: dict
    ) -> None:
        """Publish a job status update to the Redis pub/sub channel.

        The WebSocket endpoint at /execution-jobs/{job_id}/ws subscribes to
        ``automation:job:{job_id}`` and forwards messages to connected clients.
        """
        channel = f"automation:job:{job_id}"
        payload = json.dumps({
            "type": msg_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.worker_id,
        })
        try:
            await self.redis.publish(channel, payload)
        except Exception as exc:
            logger.error("Failed to publish update for job %s: %s", job_id, exc)


# ── CLI Entry Point ───────────────────────────────────────────────────

def main():
    """Run the execution worker as a standalone process."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("AITIS Execution Worker starting...")

    if not HAS_DOCKER:
        logger.warning("Docker SDK not installed — worker will run in dry-run mode")
        logger.warning("Install with: pip install docker")

    worker = ExecutionWorker()
    asyncio.run(worker.start())


if __name__ == "__main__":
    main()
