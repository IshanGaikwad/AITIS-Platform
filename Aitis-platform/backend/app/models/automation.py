"""Automation models â€” AutomationScript, FrameworkConfiguration, PageObject, Locator,
ScriptVersion, ExecutionJob, ExecutionResult, ExecutionStepResult, RecordedAction."""

import uuid
from typing import Optional
from enum import Enum
from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, Integer, Float, Boolean, Index
from sqlalchemy import Uuid
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, TenantMixin, AIGovernanceMixin


class ScriptLanguage(str, Enum):
    python = "python"
    typescript = "typescript"
    javascript = "javascript"
    java = "java"
    csharp = "csharp"


class ScriptStatus(str, Enum):
    draft = "draft"
    ready = "ready"
    needs_update = "needs_update"
    deprecated = "deprecated"


class FrameworkType(str, Enum):
    playwright = "playwright"
    selenium = "selenium"
    cypress = "cypress"
    appium = "appium"
    robot = "robot"
    pytest = "pytest"
    testng = "testng"
    junit = "junit"


class LocatorStrategy(str, Enum):
    css = "css"
    xpath = "xpath"
    id = "id"
    name = "name"
    data_testid = "data_testid"
    aria = "aria"
    text = "text"
    role = "role"


# â”€â”€ Phase 4 â€” Execution Enums â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class ExecutionJobStatus(str, Enum):
    """Extended status for automation execution jobs."""
    queued = "queued"
    provisioning = "provisioning"
    running = "running"
    passed = "passed"
    failed = "failed"
    cancelled = "cancelled"
    timed_out = "timed_out"
    infrastructure_error = "infrastructure_error"


class BrowserType(str, Enum):
    """Supported browser engines for Playwright execution."""
    chromium = "chromium"
    firefox = "firefox"
    webkit = "webkit"


class RecordedActionType(str, Enum):
    """Framework-neutral recorded action types."""
    navigate = "navigate"
    click = "click"
    fill = "fill"
    select = "select"
    assert_text = "assert_text"
    assert_visible = "assert_visible"
    assert_url = "assert_url"
    wait = "wait"
    screenshot = "screenshot"
    keyboard = "keyboard"
    hover = "hover"
    check = "check"
    uncheck = "uncheck"
    upload = "upload"
    download = "download"


# â”€â”€ Automation Script â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class AutomationScript(Base, UUIDMixin, TimestampMixin, TenantMixin, AIGovernanceMixin):
    __tablename__ = "automation_scripts"
    __table_args__ = (
        Index("ix_ascript_project", "project_id"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(String(20), default=ScriptLanguage.python.value)
    framework: Mapped[str] = mapped_column(String(20), default=FrameworkType.playwright.value)
    status: Mapped[str] = mapped_column(String(20), default=ScriptStatus.draft.value)
    code: Mapped[str] = mapped_column(Text, nullable=False, default="")
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_healed: Mapped[bool] = mapped_column(Boolean, default=False)
    healing_proposal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("healing_proposals.id", ondelete="SET NULL"), nullable=True
    )
    # Phase 4 â€” approved version for execution (only approved versions can run)
    approved_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("script_versions.id", ondelete="SET NULL"), nullable=True
    )
    # Phase 4 â€” traceability: which test case this script automates
    test_case_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships
    test_cases = relationship(
        "TestCase",
        back_populates="automation_script",
        foreign_keys="TestCase.automation_script_id",
        lazy="selectin",
    )
    # Phase 4 â€” version history
    versions = relationship(
        "ScriptVersion", back_populates="script", lazy="selectin",
        cascade="all, delete-orphan", order_by="ScriptVersion.version",
        foreign_keys="ScriptVersion.script_id",
    )
    # Phase 4 â€” approved version link
    approved_version = relationship("ScriptVersion", foreign_keys=[approved_version_id])
    # Phase 4 â€” execution jobs
    execution_jobs = relationship("ExecutionJob", back_populates="script", lazy="selectin")
    # Phase 4 â€” recorded actions (from session recorder)
    recorded_actions = relationship("RecordedAction", back_populates="script", lazy="selectin")


# â”€â”€ Script Version (Phase 4 â€” immutable version snapshots) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class ScriptVersion(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Immutable snapshot of an automation script at a point in time.

    Mirrors the TestCaseVersion pattern â€” every save creates a new version,
    preserving the full code and metadata for audit, diff, and rollback.
    """
    __tablename__ = "script_versions"
    __table_args__ = (
        Index("ix_sv_script_id", "script_id"),
    )

    script_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("automation_scripts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False, default="")
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ScriptStatus.draft.value)
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    change_summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Snapshot of code hash for integrity verification
    code_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    script = relationship(
        "AutomationScript",
        back_populates="versions",
        foreign_keys=[script_id],
    )


# â”€â”€ Execution Job (Phase 4 â€” queued automation runs) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class ExecutionJob(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Represents a single automation execution run submitted to the worker queue.

    The job lifecycle: queued â†’ provisioning â†’ running â†’ (passed|failed|cancelled|timed_out|infrastructure_error)
    """
    __tablename__ = "execution_jobs"
    __table_args__ = (
        Index("ix_ej_script_id", "script_id"),
        Index("ix_ej_status", "status"),
        Index("ix_ej_project", "project_id"),
    )

    script_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("automation_scripts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    script_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("script_versions.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(25), default=ExecutionJobStatus.queued.value, nullable=False
    )
    # Execution environment
    environment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("environments.id", ondelete="SET NULL"), nullable=True
    )
    base_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    browser: Mapped[str] = mapped_column(String(20), default=BrowserType.chromium.value)
    headless: Mapped[bool] = mapped_column(Boolean, default=True)
    # Execution controls
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Container / worker metadata
    container_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    worker_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    workspace_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Timing
    queued_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Who triggered this execution
    triggered_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Short-lived execution token (not the user's session token)
    execution_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Structured result summary
    result_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Free-form metadata (e.g. CI/CD pipeline provenance). Column name "metadata"
    # is mapped to the reserved-safe attribute ``metadata_``.
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    # Error details
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    script = relationship("AutomationScript", back_populates="execution_jobs")
    script_version = relationship("ScriptVersion")
    results = relationship(
        "ExecutionResult", back_populates="job", lazy="selectin",
        cascade="all, delete-orphan"
    )
    artifacts = relationship(
        "ExecutionArtifact", back_populates="execution_job", lazy="selectin",
        cascade="all, delete-orphan"
    )


# â”€â”€ Execution Result (Phase 4 â€” per-test results) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class ExecutionResult(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Result of a single test within an execution job.

    Maps to a single test case / test block within the automation script.
    """
    __tablename__ = "execution_results"
    __table_args__ = (
        Index("ix_er_job_id", "job_id"),
        Index("ix_er_test_case_id", "test_case_id"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("execution_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_case_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    test_name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(25), default=ExecutionJobStatus.queued.value)
    browser: Mapped[str] = mapped_column(String(20), default=BrowserType.chromium.value)
    environment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Standard output / error from the test process
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Structured result JSON from Playwright reporter
    result_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    job = relationship("ExecutionJob", back_populates="results")
    step_results = relationship(
        "ExecutionStepResult", back_populates="result", lazy="selectin",
        cascade="all, delete-orphan"
    )
    artifacts = relationship(
        "ExecutionArtifact", back_populates="execution_result", lazy="selectin",
        cascade="all, delete-orphan"
    )


# â”€â”€ Execution Step Result (Phase 4 â€” step-level results) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class ExecutionStepResult(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Step-level result within an execution result.

    Captures individual step pass/fail, duration, and artifacts.
    """
    __tablename__ = "execution_step_results"
    __table_args__ = (
        Index("ix_esr_result_id", "result_id"),
    )

    result_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("execution_results.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_name: Mapped[str] = mapped_column(String(500), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(25), default=ExecutionJobStatus.queued.value)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actual_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    screenshot_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Relationships
    result = relationship("ExecutionResult", back_populates="step_results")


# â”€â”€ Recorded Action (Phase 4 â€” framework-neutral recorder) â”€â”€â”€â”€â”€â”€â”€â”€â”€
class RecordedAction(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Framework-neutral recorded user action from the browser recorder.

    Actions are stored in a framework-neutral form and can be rendered
    to any supported framework (Playwright, Selenium, Cypress, etc.).
    Sensitive field values (passwords, tokens) are never stored in plaintext.
    """
    __tablename__ = "recorded_actions"
    __table_args__ = (
        Index("ix_ra_script_id", "script_id"),
        Index("ix_ra_session_id", "session_id"),
    )

    script_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("automation_scripts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    action_type: Mapped[str] = mapped_column(
        String(30), default=RecordedActionType.navigate.value, nullable=False
    )
    # Target element selector (framework-neutral)
    selector: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Human-readable label for the target element
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Value for fill/select/keyboard actions â€” masked if sensitive
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Whether this field contains sensitive data (passwords, tokens, etc.)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    # URL for navigate actions
    url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    # Expected value for assertions
    expected_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Additional metadata (coordinates, modifiers, etc.)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Relationships
    script = relationship("AutomationScript", back_populates="recorded_actions")


# â”€â”€ Framework Configuration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class FrameworkConfiguration(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "framework_configurations"
    __table_args__ = (
        Index("ix_fwconfig_project", "project_id"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    framework: Mapped[str] = mapped_column(String(20), default=FrameworkType.playwright.value)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    base_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    page_objects = relationship("PageObject", back_populates="framework_config", lazy="selectin")


# â”€â”€ Page Object â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class PageObject(Base, UUIDMixin, TimestampMixin, TenantMixin, AIGovernanceMixin):
    __tablename__ = "page_objects"
    __table_args__ = (
        Index("ix_po_framework_config_id", "framework_config_id"),
    )

    framework_config_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("framework_configurations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url_pattern: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    code: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Relationships
    framework_config = relationship("FrameworkConfiguration", back_populates="page_objects")
    locators = relationship("Locator", back_populates="page_object", lazy="selectin", cascade="all, delete-orphan")


# â”€â”€ Locator â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class Locator(Base, UUIDMixin, TimestampMixin, TenantMixin, AIGovernanceMixin):
    __tablename__ = "locators"
    __table_args__ = (
        Index("ix_locator_page_object_id", "page_object_id"),
    )

    page_object_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("page_objects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    strategy: Mapped[str] = mapped_column(String(20), default=LocatorStrategy.css.value)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    is_dynamic: Mapped[bool] = mapped_column(Boolean, default=False)
    is_healed: Mapped[bool] = mapped_column(Boolean, default=False)
    original_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Relationships
    page_object = relationship("PageObject", back_populates="locators")

