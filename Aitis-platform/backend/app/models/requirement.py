"""Requirement and AcceptanceCriterion models â€” core domain entities."""

import uuid
from typing import Optional
from enum import Enum

from sqlalchemy import String, Text, ForeignKey, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, TenantMixin, AIGovernanceMixin


class RequirementType(str, Enum):
    functional = "functional"
    non_functional = "non_functional"
    business_rule = "business_rule"
    constraint = "constraint"


class RequirementPriority(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class RequirementStatus(str, Enum):
    draft = "draft"
    reviewed = "reviewed"
    approved = "approved"
    deprecated = "deprecated"


# â”€â”€ Requirement â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class Requirement(Base, UUIDMixin, TimestampMixin, TenantMixin, AIGovernanceMixin):
    __tablename__ = "requirements"
    __table_args__ = (
        Index("ix_requirement_project_id", "project_id"),
        Index("ix_requirement_workspace_id", "workspace_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Jira key etc.
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(30), default=RequirementType.functional.value)
    priority: Mapped[str] = mapped_column(String(20), default=RequirementPriority.medium.value)
    status: Mapped[str] = mapped_column(String(20), default=RequirementStatus.draft.value)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # jira, manual, import
    source_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    project = relationship("Project", back_populates="requirements")
    acceptance_criteria = relationship(
        "AcceptanceCriterion", back_populates="requirement", lazy="selectin",
        cascade="all, delete-orphan"
    )
    test_suites = relationship("TestSuite", back_populates="requirement", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Requirement {self.external_id or self.id}: {self.title}>"


# â”€â”€ Acceptance Criterion â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class ACCategory(str, Enum):
    security = "security"
    state = "state"
    validation = "validation"
    negative = "negative"
    positive = "positive"


class AcceptanceCriterion(Base, UUIDMixin, TimestampMixin, TenantMixin, AIGovernanceMixin):
    __tablename__ = "acceptance_criteria"
    __table_args__ = (
        Index("ix_ac_requirement_id", "requirement_id"),
    )

    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_ai_generated: Mapped[bool] = mapped_column(default=False)

    # Relationships
    requirement = relationship("Requirement", back_populates="acceptance_criteria")

    def __repr__(self) -> str:
        return f"<AC {self.id}: {self.text[:50]}>"

