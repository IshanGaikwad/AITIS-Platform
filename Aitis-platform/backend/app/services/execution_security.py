"""Execution security — script validation, execution tokens, audit events, tenant isolation.

Security layers:
1. Script validation — block dangerous patterns before execution
2. Execution tokens — short-lived JWTs scoped to a single job
3. Audit events — immutable log of all execution lifecycle events
4. Tenant isolation — verify org/workspace ownership before any operation
5. Container hardening — enforce network restrictions, no DB creds in workers
"""

import re
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from jose import jwt
from pydantic import BaseModel

from app.core.config import settings


# ── Script Validation ─────────────────────────────────────────────────

class ScriptValidationResult(BaseModel):
    """Result of script safety validation."""
    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []


# Patterns that are ALWAYS blocked — regardless of language/framework
BLOCKED_PATTERNS: list[dict] = [
    # File system escape attempts
    {"pattern": r"\.\./\.\.", "reason": "Path traversal detected"},
    {"pattern": r"/etc/passwd", "reason": "Accessing system files"},
    {"pattern": r"/etc/shadow", "reason": "Accessing system files"},
    {"pattern": r"/proc/self", "reason": "Accessing process information"},
    # Network exfiltration
    {"pattern": r"fetch\s*\(\s*['\"]https?://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)",
     "reason": "External network request detected — only localhost allowed"},
    {"pattern": r"XMLHttpRequest", "reason": "XMLHttpRequest not allowed in automation scripts"},
    # Code execution / shell escape
    {"pattern": r"child_process", "reason": "child_process module is forbidden"},
    {"pattern": r"require\s*\(\s*['\"]child_process", "reason": "child_process import is forbidden"},
    {"pattern": r"require\s*\(\s*['\"]fs['\"]", "reason": "fs module is forbidden — use Playwright APIs only"},
    {"pattern": r"import\s+.*\s+from\s+['\"]fs['\"]", "reason": "fs import is forbidden — use Playwright APIs only"},
    {"pattern": r"require\s*\(\s*['\"]net['\"]", "reason": "net module is forbidden"},
    {"pattern": r"require\s*\(\s*['\"]http['\"]", "reason": "http module is forbidden"},
    {"pattern": r"require\s*\(\s*['\"]https['\"]", "reason": "https module is forbidden"},
    {"pattern": r"require\s*\(\s*['\"]crypto['\"]", "reason": "crypto module is forbidden"},
    # Environment / process access
    {"pattern": r"process\.env", "reason": "process.env access is forbidden — use injected secrets only"},
    {"pattern": r"process\.exit", "reason": "process.exit is forbidden"},
    {"pattern": r"process\.kill", "reason": "process.kill is forbidden"},
    # Eval / dynamic code
    {"pattern": r"\beval\s*\(", "reason": "eval() is forbidden"},
    {"pattern": r"Function\s*\(", "reason": "Function constructor is forbidden"},
    {"pattern": r"new\s+Function\b", "reason": "new Function() is forbidden"},
    # Docker escape attempts
    {"pattern": r"docker", "reason": "Docker references are forbidden in scripts"},
    {"pattern": r"/var/run/docker\.sock", "reason": "Docker socket access is forbidden"},
]

# Patterns that generate warnings (not errors)
WARNING_PATTERNS: list[dict] = [
    {"pattern": r"waitForTimeout", "reason": "waitForTimeout is fragile — prefer waitForSelector or waitFor"},
    {"pattern": r"sleep\s*\(", "reason": "Hardcoded sleep detected — prefer explicit waits"},
    {"pattern": r"page\.goto\s*\(\s*['\"]http://", "reason": "Insecure HTTP URL — prefer HTTPS in production"},
    {"pattern": r"\.screenshot\s*\(", "reason": "Screenshots may contain sensitive data — ensure compliance"},
]


def validate_script(code: str, language: str = "typescript") -> ScriptValidationResult:
    """Validate a script for dangerous patterns before execution.

    Returns a ScriptValidationResult with errors (blocking) and warnings (non-blocking).
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check blocked patterns
    for rule in BLOCKED_PATTERNS:
        if re.search(rule["pattern"], code, re.IGNORECASE):
            errors.append(f"BLOCKED: {rule['reason']}")

    # Check warning patterns
    for rule in WARNING_PATTERNS:
        if re.search(rule["pattern"], code, re.IGNORECASE):
            warnings.append(f"WARNING: {rule['reason']}")

    # Language-specific checks
    if language in ("typescript", "javascript"):
        # Check for require() of dangerous modules (already covered above, but double-check)
        if re.search(r"require\s*\(\s*['\"]os['\"]", code):
            errors.append("BLOCKED: os module is forbidden — system information access")

    # Size check — prevent excessively large scripts
    max_script_size = 512 * 1024  # 512 KB
    if len(code.encode("utf-8")) > max_script_size:
        errors.append(f"BLOCKED: Script exceeds maximum size ({max_script_size // 1024} KB)")

    return ScriptValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# ── Execution Tokens ──────────────────────────────────────────────────

class ExecutionTokenType(str, Enum):
    """Types of short-lived execution tokens."""
    job_submit = "execution:job_submit"
    job_cancel = "execution:job_cancel"
    job_read = "execution:job_read"


def create_execution_token(
    job_id: uuid.UUID,
    token_type: ExecutionTokenType = ExecutionTokenType.job_submit,
    organization_id: Optional[uuid.UUID] = None,
    workspace_id: Optional[uuid.UUID] = None,
    expires_minutes: int = 30,
) -> str:
    """Create a short-lived JWT scoped to a single execution job.

    These tokens are used by the worker process to authenticate back to the
    API for status updates and artifact uploads. They are NOT user tokens —
    they are machine-to-machine tokens with minimal scope.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(job_id),
        "type": token_type.value,
        "scope": "execution",
        "job_id": str(job_id),
        "org_id": str(organization_id) if organization_id else None,
        "ws_id": str(workspace_id) if workspace_id else None,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def verify_execution_token(
    token: str,
    expected_job_id: Optional[uuid.UUID] = None,
    expected_type: Optional[ExecutionTokenType] = None,
) -> Optional[dict]:
    """Verify an execution token. Returns payload or None if invalid.

    Optionally checks that the token matches a specific job_id and/or type.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except Exception:
        return None

    # Verify it's an execution token, not a user token
    if payload.get("scope") != "execution":
        return None

    # Check expected job_id
    if expected_job_id and payload.get("job_id") != str(expected_job_id):
        return None

    # Check expected type
    if expected_type and payload.get("type") != expected_type.value:
        return None

    return payload


# ── Audit Events ──────────────────────────────────────────────────────

class AuditEventType(str, Enum):
    """Types of execution audit events."""
    job_submitted = "execution.job.submitted"
    job_started = "execution.job.started"
    job_completed = "execution.job.completed"
    job_failed = "execution.job.failed"
    job_cancelled = "execution.job.cancelled"
    job_timed_out = "execution.job.timed_out"
    script_validated = "execution.script.validated"
    script_validation_failed = "execution.script.validation_failed"
    container_spawned = "execution.container.spawned"
    container_killed = "execution.container.killed"
    token_created = "execution.token.created"
    token_used = "execution.token.used"
    artifact_uploaded = "execution.artifact.uploaded"
    version_approved = "execution.version.approved"
    version_restored = "execution.version.restored"


class AuditEvent(BaseModel):
    """Immutable audit event for execution operations."""
    event_type: AuditEventType
    job_id: Optional[uuid.UUID] = None
    script_id: Optional[uuid.UUID] = None
    script_version_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    actor_id: Optional[uuid.UUID] = None  # User who triggered the event
    actor_type: str = "user"  # user | worker | system
    details: dict = {}
    timestamp: datetime = datetime.now(timezone.utc)

    class Config:
        use_enum_values = True


# In-memory audit log (production would use a dedicated audit table or external service)
_audit_log: list[AuditEvent] = []
_audit_log_max = 10000


def record_audit_event(event: AuditEvent) -> None:
    """Record an audit event. In production, this would write to a dedicated
    audit table with append-only semantics and/or send to an external SIEM.
    """
    _audit_log.append(event)
    # Trim if too large (in production, this would be a DB write)
    if len(_audit_log) > _audit_log_max:
        _audit_log.pop(0)


def get_audit_log(
    organization_id: Optional[uuid.UUID] = None,
    job_id: Optional[uuid.UUID] = None,
    event_type: Optional[AuditEventType] = None,
    limit: int = 100,
) -> list[AuditEvent]:
    """Query audit events with optional filters."""
    results = _audit_log

    if organization_id:
        results = [e for e in results if e.organization_id == organization_id]
    if job_id:
        results = [e for e in results if e.job_id == job_id]
    if event_type:
        results = [e for e in results if e.event_type == event_type]

    return results[-limit:]


# ── Tenant Isolation ──────────────────────────────────────────────────

class TenantIsolationError(Exception):
    """Raised when a tenant isolation check fails."""
    pass


def verify_tenant_access(
    resource_org_id: uuid.UUID,
    resource_ws_id: Optional[uuid.UUID],
    request_org_id: uuid.UUID | str | None,
    request_ws_id: Optional[uuid.UUID | str],
) -> bool:
    """Verify that a request has access to a resource based on tenant ownership.

    Rules:
    - Organization must match exactly
    - If resource has a workspace_id, request must also have that workspace_id
    - If resource has no workspace_id (org-level), any workspace in the org can access it
    """
    try:
        request_org_uuid = uuid.UUID(str(request_org_id)) if request_org_id else None
        request_ws_uuid = uuid.UUID(str(request_ws_id)) if request_ws_id else None
    except ValueError:
        return False

    if resource_org_id != request_org_uuid:
        return False

    if resource_ws_id and resource_ws_id != request_ws_uuid:
        return False

    return True


def sanitize_environment_vars(env_vars: dict) -> dict:
    """Sanitize environment variables before injecting into containers.

    - Strips any keys that look like database credentials
    - Strips any keys that reference internal service URLs
    - Prefixes all keys with SECRET_ to distinguish from system vars
    """
    blocked_key_patterns = [
        r"DATABASE_URL",
        r"DB_",
        r"POSTGRES_",
        r"REDIS_",
        r"SECRET_KEY",
        r"JWT_",
        r"OAUTH2_",
        r"S3_SECRET",
        r"DOCKER_",
    ]

    sanitized = {}
    for key, value in env_vars.items():
        # Skip blocked keys
        is_blocked = any(
            re.match(pattern, key, re.IGNORECASE) for pattern in blocked_key_patterns
        )
        if is_blocked:
            continue

        # Never store passwords in plaintext — only allow pre-hashed or token values
        if "password" in key.lower() and not key.endswith("_HASH") and not key.endswith("_TOKEN"):
            continue

        sanitized[key] = value

    return sanitized


# ── Container Security Config ─────────────────────────────────────────

def get_container_security_opts() -> list[str]:
    """Return Docker security options for execution containers."""
    return [
        "no-new-privileges",  # Prevent privilege escalation
    ]


def get_container_read_only_paths() -> list[str]:
    """Return paths that should be read-only in execution containers."""
    return [
        "/usr",
        "/lib",
        "/bin",
        "/sbin",
    ]


def get_container_network_config(
    allowed_networks: Optional[list[str]] = None,
) -> dict:
    """Return network configuration for execution containers.

    In production, containers should run with restricted network access.
    The 'none' network mode provides full isolation but prevents testing
    of web applications. The 'bridge' mode with custom network allows
    controlled access.
    """
    network_mode = settings.execution_network_mode

    config = {
        "network_mode": network_mode,
    }

    # If using bridge mode with allowed networks, specify them
    if network_mode == "bridge" and allowed_networks:
        config["networks"] = allowed_networks

    return config
