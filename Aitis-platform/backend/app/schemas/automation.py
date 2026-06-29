"""Pydantic schemas for automation generation and DB-backed automation entities."""

import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.requirement import RequirementCreate
from app.schemas.testcase import TestCaseOut


# ── AI Pipeline schemas (generation output) ─────────────────────────
class AutomationRequest(BaseModel):
    story: RequirementCreate
    test_case: TestCaseOut


class AutomationOut(BaseModel):
    id: str
    title: str
    framework: str
    language: str
    file_name: str
    content: str


# ── Database-backed Automation Script schemas ───────────────────────
class AutomationScriptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    language: str = Field("typescript", description="python | typescript | javascript | java | csharp")
    framework: str = Field("playwright", description="playwright | selenium | cypress | appium | robot | pytest | testng | junit")
    status: str = Field("draft", description="draft | ready | needs_update | deprecated")
    code: str = ""
    file_path: Optional[str] = None
    version: int = 1
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class AutomationScriptUpdate(BaseModel):
    name: Optional[str] = None
    language: Optional[str] = None
    framework: Optional[str] = None
    status: Optional[str] = None
    code: Optional[str] = None
    file_path: Optional[str] = None
    version: Optional[int] = None


class AutomationScriptOut(BaseModel):
    id: uuid.UUID
    name: str
    language: str
    framework: str
    status: str
    code: str
    file_path: Optional[str] = None
    version: int
    is_healed: bool = False
    healing_proposal_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Framework Configuration schemas ─────────────────────────────────
class FrameworkConfigurationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    framework: str = Field("playwright")
    config: Optional[dict] = None
    base_url: Optional[str] = None
    is_active: bool = True
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class FrameworkConfigurationOut(BaseModel):
    id: uuid.UUID
    name: str
    framework: str
    config: Optional[dict] = None
    base_url: Optional[str] = None
    is_active: bool = True
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Page Object schemas ────────────────────────────────────────────
class PageObjectCreate(BaseModel):
    framework_config_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    url_pattern: Optional[str] = None
    code: str = ""
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class PageObjectOut(BaseModel):
    id: uuid.UUID
    framework_config_id: uuid.UUID
    name: str
    description: Optional[str] = None
    url_pattern: Optional[str] = None
    code: str
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Locator schemas ─────────────────────────────────────────────────
class LocatorCreate(BaseModel):
    page_object_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=200)
    strategy: str = Field("css", description="css | xpath | id | name | data_testid | aria | text | role")
    value: str
    is_dynamic: bool = False
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class LocatorUpdate(BaseModel):
    name: Optional[str] = None
    strategy: Optional[str] = None
    value: Optional[str] = None
    is_dynamic: Optional[bool] = None


class LocatorOut(BaseModel):
    id: uuid.UUID
    page_object_id: uuid.UUID
    name: str
    strategy: str
    value: str
    is_dynamic: bool = False
    is_healed: bool = False
    original_value: Optional[str] = None
    confidence_score: Optional[float] = None
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ══════════════════════════════════════════════════════════════════════
# Phase 4 — Script Version, Execution, and Recorder schemas
# ══════════════════════════════════════════════════════════════════════

# ── Script Version schemas ──────────────────────────────────────────
class ScriptVersionCreate(BaseModel):
    """Request body to create a new script version (snapshot)."""
    code: str = ""
    file_path: Optional[str] = None
    change_summary: Optional[str] = Field(None, max_length=500)


class ScriptVersionOut(BaseModel):
    id: uuid.UUID
    script_id: uuid.UUID
    version: int
    code: str
    file_path: Optional[str] = None
    status: str
    changed_by: Optional[uuid.UUID] = None
    change_summary: Optional[str] = None
    code_hash: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ScriptVersionSummary(BaseModel):
    """Lightweight version listing (no code body)."""
    id: uuid.UUID
    script_id: uuid.UUID
    version: int
    status: str
    change_summary: Optional[str] = None
    code_hash: Optional[str] = None
    changed_by: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScriptVersionDiff(BaseModel):
    """Diff between two script versions."""
    from_version: int
    to_version: int
    from_code: str
    to_code: str
    unified_diff: str


# ── Execution Job schemas ───────────────────────────────────────────
class ExecutionJobCreate(BaseModel):
    """Submit a script for execution."""
    script_id: uuid.UUID
    script_version_id: Optional[uuid.UUID] = Field(
        None, description="Specific version to run; defaults to approved version"
    )
    environment_id: Optional[uuid.UUID] = None
    base_url: Optional[str] = Field(None, max_length=1024)
    browser: str = Field("chromium", description="chromium | firefox | webkit")
    headless: bool = True
    timeout_seconds: int = Field(300, ge=30, le=3600)
    max_retries: int = Field(0, ge=0, le=5)


class ExecutionJobOut(BaseModel):
    id: uuid.UUID
    script_id: uuid.UUID
    script_version_id: Optional[uuid.UUID] = None
    status: str
    environment_id: Optional[uuid.UUID] = None
    base_url: Optional[str] = None
    browser: str
    headless: bool = True
    timeout_seconds: int = 300
    max_retries: int = 0
    retry_count: int = 0
    container_id: Optional[str] = None
    worker_id: Optional[str] = None
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    triggered_by: Optional[uuid.UUID] = None
    result_summary: Optional[dict] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ExecutionJobSummary(BaseModel):
    """Lightweight job listing."""
    id: uuid.UUID
    script_id: uuid.UUID
    status: str
    browser: str
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Execution Result schemas ───────────────────────────────────────
class ExecutionResultOut(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    test_case_id: Optional[uuid.UUID] = None
    test_name: str
    status: str
    browser: str
    environment: Optional[str] = None
    retry_count: int = 0
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    result_json: Optional[dict] = None
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ExecutionStepResultOut(BaseModel):
    id: uuid.UUID
    result_id: uuid.UUID
    step_name: str
    step_order: int
    status: str
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    actual_result: Optional[str] = None
    screenshot_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecutionResultDetail(ExecutionResultOut):
    """Full result with step-level details and artifact links."""
    step_results: List[ExecutionStepResultOut] = []
    artifact_links: List[dict] = Field(
        default_factory=list,
        description="List of artifact metadata dicts: {id, artifact_type, name, size_bytes, content_type}"
    )


# ── Suite Summary schema ──────────────────────────────────────────
class SuiteSummary(BaseModel):
    """Aggregate summary of all test results within an execution job."""
    job_id: uuid.UUID
    script_id: uuid.UUID
    status: str
    browser: str
    environment: Optional[str] = None
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    timed_out: int = 0
    pass_rate: float = 0.0
    total_duration_seconds: Optional[float] = None
    avg_duration_seconds: Optional[float] = None
    slowest_test: Optional[str] = None
    slowest_duration_seconds: Optional[float] = None
    error_summary: List[dict] = Field(
        default_factory=list,
        description="List of {test_name, error_message} for failed tests"
    )
    artifact_count: int = 0


# ── Recorded Action schemas ────────────────────────────────────────
class RecordedActionCreate(BaseModel):
    """A single recorded action from the browser recorder."""
    session_id: str = Field(..., min_length=1, max_length=100)
    action_order: int = Field(0, ge=0)
    action_type: str = Field(
        "navigate",
        description="navigate|click|fill|select|assert_text|assert_visible|assert_url|"
                    "wait|screenshot|keyboard|hover|check|uncheck|upload|download"
    )
    selector: Optional[str] = None
    label: Optional[str] = Field(None, max_length=255)
    value: Optional[str] = None
    is_sensitive: bool = False
    url: Optional[str] = Field(None, max_length=1024)
    expected_value: Optional[str] = None
    metadata: Optional[dict] = None


class RecordedActionOut(BaseModel):
    id: uuid.UUID
    script_id: Optional[uuid.UUID] = None
    session_id: str
    action_order: int
    action_type: str
    selector: Optional[str] = None
    label: Optional[str] = None
    value: Optional[str] = None
    is_sensitive: bool = False
    url: Optional[str] = None
    expected_value: Optional[str] = None
    metadata: Optional[dict] = None
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def mask_sensitive_values(self) -> "RecordedActionOut":
        """Mask values marked as sensitive (passwords, tokens, etc.)."""
        if self.is_sensitive and self.value:
            self.value = "••••••••"
        return self


class RecordedActionBatch(BaseModel):
    """Batch of recorded actions from a single recording session."""
    script_id: Optional[uuid.UUID] = None
    session_id: str = Field(..., min_length=1, max_length=100)
    actions: List[RecordedActionCreate]


class RecordingSessionOut(BaseModel):
    """Summary of a recording session."""
    session_id: str
    script_id: Optional[uuid.UUID] = None
    action_count: int = 0
    first_action_type: Optional[str] = None
    last_action_type: Optional[str] = None
    has_sensitive_actions: bool = False
    created_at: Optional[datetime] = None


# ── Automation Script extended (Phase 4 additions) ─────────────────
class AutomationScriptDetail(AutomationScriptOut):
    """Extended script output with Phase 4 fields."""
    approved_version_id: Optional[uuid.UUID] = None
    test_case_id: Optional[uuid.UUID] = None
    versions: List[ScriptVersionSummary] = []
    execution_jobs: List[ExecutionJobSummary] = []
