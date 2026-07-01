"""Base model with UUID primary key, timestamps, and common mixins."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy import Uuid
from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all models."""
    type_annotation_map = {
        dict: JSON,
    }


class UUIDMixin:
    """UUID primary key mixin."""
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """Created/updated timestamp mixin."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TenantMixin:
    """Multi-tenancy mixin â€” every row is scoped to an organization + project."""
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )


class AIGovernanceMixin:
    """AI governance metadata mixin â€” tracks provenance of AI-generated artifacts."""
    ai_input_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ai_model_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ai_prompt_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ai_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ai_assumptions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    ai_review_status: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="pending"
    )  # pending | approved | rejected | needs_revision
    ai_reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    ai_approval_rejection_reason: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    ai_final_edited_version: Mapped[Optional[bool]] = mapped_column(
        default=False
    )

