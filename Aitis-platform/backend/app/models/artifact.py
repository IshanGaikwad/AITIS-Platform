"""Artifact, Defect, and Healing models."""

import uuid
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import String, Text, ForeignKey, Integer, Float, Index, DateTime
from sqlalchemy import Uuid
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, TenantMixin, AIGovernanceMixin


class ArtifactType(str, Enum):
    screenshot = "screenshot"
    video = "video"
    log = "log"
    trace = "trace"
    har = "har"
    coverage = "coverage"
    console_log = "console_log"
    network_log = "network_log"
    stdout = "stdout"
    stderr = "stderr"
    result_json = "result_json"
    other = "other"


class DefectSeverity(str, Enum):
    blocker = "blocker"
    critical = "critical"
    major = "major"
    minor = "minor"
    trivial = "trivial"


class DefectStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"
    wont_fix = "wont_fix"


class HealingStatus(str, Enum):
    proposed = "proposed"
    approved = "approved"
    rejected = "rejected"
    applied = "applied"
    reverted = "reverted"


# â”€â”€ Execution Artifact â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class ExecutionArtifact(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "execution_artifacts"
    __table_args__ = (
        Index("ix_artifact_case_exec_id", "case_execution_id"),
        Index("ix_artifact_job_id", "execution_job_id"),
        Index("ix_artifact_result_id", "execution_result_id"),
    )

    case_execution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("test_case_executions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Phase 4 â€” link to automation execution job
    execution_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("execution_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Phase 4 â€” link to specific execution result within a job
    execution_result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("execution_results.id", ondelete="SET NULL"), nullable=True, index=True
    )
    artifact_type: Mapped[str] = mapped_column(String(20), default=ArtifactType.screenshot.value)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)  # S3 key or local path
    content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Phase 4 â€” relationships
    execution_job = relationship("ExecutionJob", back_populates="artifacts")
    execution_result = relationship("ExecutionResult", back_populates="artifacts")


# â”€â”€ Defect â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class Defect(Base, UUIDMixin, TimestampMixin, TenantMixin, AIGovernanceMixin):
    __tablename__ = "defects"
    __table_args__ = (
        Index("ix_defect_workspace_id", "workspace_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_execution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("test_case_executions.id", ondelete="SET NULL"), nullable=True
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Jira key
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default=DefectSeverity.major.value)
    status: Mapped[str] = mapped_column(String(20), default=DefectStatus.open.value)
    steps_to_reproduce: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    environment: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    labels: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)

    # Relationships
    workspace = relationship("Workspace", back_populates="defects")


# â”€â”€ Healing Proposal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class HealingProposal(Base, UUIDMixin, TimestampMixin, TenantMixin, AIGovernanceMixin):
    __tablename__ = "healing_proposals"
    __table_args__ = (
        Index("ix_heal_project", "project_id"),
    )

    locator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("locators.id", ondelete="SET NULL"), nullable=True
    )
    script_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("automation_scripts.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default=HealingStatus.proposed.value)
    original_code: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_code: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reverted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

