"""Test models â€” TestSuite, TestCase, TestStep, execution models, and Phase 2 manual-testing extensions."""

import uuid
from typing import Optional
from enum import Enum
from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, Integer, Float, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, TenantMixin, AIGovernanceMixin


# â”€â”€ Enums â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class TestType(str, Enum):
    manual = "manual"
    automated = "automated"
    bdd = "bdd"


class TestPriority(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class TestStatus(str, Enum):
    draft = "draft"
    ready = "ready"
    deprecated = "deprecated"


class ReviewStatus(str, Enum):
    """Phase 2 â€” manual test case review workflow."""
    pending = "pending"
    approved = "approved"
    changes_requested = "changes_requested"


class StepType(str, Enum):
    action = "action"
    verification = "verification"
    precondition = "precondition"


class ExecutionStatus(str, Enum):
    pending = "pending"
    running = "running"
    passed = "passed"
    failed = "failed"
    blocked = "blocked"
    skipped = "skipped"
    error = "error"


class ExecutionType(str, Enum):
    """Phase 2 â€” distinguishes manual vs automated execution runs."""
    manual = "manual"
    automated = "automated"


# â”€â”€ Test Suite Folder (Phase 2 â€” nested organisation) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class TestSuiteFolder(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Hierarchical folder for organising test suites.

    Supports arbitrary nesting via self-referential parent_id.
    """
    __tablename__ = "test_suite_folders"
    __table_args__ = (
        Index("ix_tsf_parent_id", "parent_id"),
        Index("ix_tsf_project_id", "project_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_suite_folders.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Self-referential
    parent = relationship("TestSuiteFolder", remote_side="TestSuiteFolder.id", back_populates="children")
    children = relationship(
        "TestSuiteFolder", back_populates="parent", lazy="selectin",
        cascade="all, delete-orphan", order_by="TestSuiteFolder.sort_order"
    )
    test_suites = relationship(
        "TestSuite", back_populates="folder", lazy="selectin",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TestSuiteFolder {self.name}>"


# â”€â”€ Test Suite â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class TestSuite(Base, UUIDMixin, TimestampMixin, TenantMixin, AIGovernanceMixin):
    __tablename__ = "test_suites"
    __table_args__ = (
        Index("ix_suite_project_id", "project_id"),
        Index("ix_suite_requirement_id", "requirement_id"),
        Index("ix_suite_folder_id", "folder_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requirements.id", ondelete="SET NULL"), nullable=True, index=True
    )
    folder_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_suite_folders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(20), default=TestType.automated.value)

    # Relationships
    project = relationship("Project", back_populates="test_suites")
    requirement = relationship("Requirement", back_populates="test_suites")
    folder = relationship("TestSuiteFolder", back_populates="test_suites")
    test_cases = relationship(
        "TestCase", back_populates="test_suite", lazy="selectin",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TestSuite {self.name}>"


# â”€â”€ Test Case (Phase 2 expanded) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class TestCase(Base, UUIDMixin, TimestampMixin, TenantMixin, AIGovernanceMixin):
    __tablename__ = "test_cases"
    __table_args__ = (
        Index("ix_tc_suite_id", "test_suite_id"),
        Index("ix_tc_owner_id", "owner_id"),
    )

    test_suite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(20), default=TestType.automated.value)
    priority: Mapped[str] = mapped_column(String(20), default=TestPriority.medium.value)
    status: Mapped[str] = mapped_column(String(20), default=TestStatus.draft.value)
    # Phase 2 â€” review workflow
    review_status: Mapped[str] = mapped_column(
        String(20), default=ReviewStatus.pending.value, nullable=False
    )
    # Phase 2 â€” ownership
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Phase 2 â€” tags (free-form list stored as JSON)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Phase 2 â€” version counter (incremented on every edit when versioning is enabled)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Phase 2 â€” many-to-many requirement traceability (array of requirement UUIDs)
    requirement_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    risk_tag: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ac_category: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    preconditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gherkin: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    automation_script_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("automation_scripts.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    test_suite = relationship("TestSuite", back_populates="test_cases")
    owner = relationship("User", foreign_keys=[owner_id])
    automation_script = relationship(
        "AutomationScript",
        back_populates="test_cases",
        foreign_keys=[automation_script_id],
    )
    steps = relationship(
        "TestStep", back_populates="test_case", lazy="selectin",
        cascade="all, delete-orphan", order_by="TestStep.order"
    )
    executions = relationship("TestCaseExecution", back_populates="test_case", lazy="selectin")
    versions = relationship(
        "TestCaseVersion", back_populates="test_case", lazy="selectin",
        cascade="all, delete-orphan", order_by="TestCaseVersion.version"
    )

    def __repr__(self) -> str:
        return f"<TestCase {self.slug}>"


# â”€â”€ Test Case Version (Phase 2 â€” version history) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class TestCaseVersion(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Immutable snapshot of a test case at a point in time."""
    __tablename__ = "test_case_versions"
    __table_args__ = (
        Index("ix_tcv_tc_id", "test_case_id"),
    )

    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    preconditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gherkin: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    requirement_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Snapshot of steps at this version
    steps_snapshot: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    change_summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    test_case = relationship("TestCase", back_populates="versions")

    def __repr__(self) -> str:
        return f"<TestCaseVersion {self.test_case_id} v{self.version}>"


# â”€â”€ Test Step (Phase 2 expanded) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class TestStep(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "test_steps"
    __table_args__ = (
        Index("ix_step_tc_id", "test_case_id"),
    )

    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    type: Mapped[str] = mapped_column(String(20), default=StepType.action.value)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    expected_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    test_case = relationship("TestCase", back_populates="steps")

    def __repr__(self) -> str:
        return f"<TestStep {self.order}: {self.action[:50]}>"


# â”€â”€ Test Execution (Phase 2 expanded for manual sessions) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class TestExecution(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "test_executions"
    __table_args__ = (
        Index("ix_exec_suite_id", "test_suite_id"),
        Index("ix_exec_executed_by", "executed_by"),
    )

    test_suite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    environment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Phase 2 â€” execution type discriminator
    execution_type: Mapped[str] = mapped_column(
        String(20), default=ExecutionType.automated.value, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default=ExecutionStatus.pending.value)
    # Phase 2 â€” who executed this run
    executed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Phase 2 â€” free-form notes about the execution session
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    executor = relationship("User", foreign_keys=[executed_by])
    case_executions = relationship("TestCaseExecution", back_populates="execution", lazy="selectin")


class TestCaseExecution(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "test_case_executions"
    __table_args__ = (
        Index("ix_tce_exec_id", "execution_id"),
    )

    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default=ExecutionStatus.pending.value)
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    artifacts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    execution = relationship("TestExecution", back_populates="case_executions")
    test_case = relationship("TestCase", back_populates="executions")
    step_executions = relationship("StepExecution", back_populates="case_execution", lazy="selectin")
    defect_drafts = relationship("DefectDraft", back_populates="case_execution", lazy="selectin")


class StepExecution(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "step_executions"
    __table_args__ = (
        Index("ix_se_tce_id", "case_execution_id"),
    )

    case_execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_case_executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_steps.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default=ExecutionStatus.pending.value)
    actual_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Phase 2 â€” manual execution comments
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    screenshot_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    case_execution = relationship("TestCaseExecution", back_populates="step_executions")


# â”€â”€ Defect Draft (Phase 2 â€” defect draft from failed steps) â”€â”€â”€â”€â”€â”€â”€â”€
class DefectDraft(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Draft defect created from a failed test step execution.

    Captures enough information to file a real bug later (e.g. to Jira).
    """
    __tablename__ = "defect_drafts"
    __table_args__ = (
        Index("ix_dd_case_execution_id", "case_execution_id"),
    )

    case_execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_case_executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    steps_to_reproduce: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    environment: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    labels: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Relationships
    case_execution = relationship("TestCaseExecution", back_populates="defect_drafts")

    def __repr__(self) -> str:
        return f"<DefectDraft {self.title}>"

