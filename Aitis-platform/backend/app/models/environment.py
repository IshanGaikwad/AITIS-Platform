"""Environment model for deployment environments (dev, staging, prod, etc.)"""

import uuid
from enum import Enum
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, TenantMixin


class EnvironmentType(str, Enum):
    """Supported environment types."""
    DEVELOPMENT = "development"
    QA = "qa"
    UAT = "uat"
    STAGING = "staging"
    PRODUCTION = "production"
    CUSTOM = "custom"


class Environment(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Represents a deployment environment (dev, QA, staging, production, etc.)."""

    __tablename__ = "environments"

    # Foreign keys
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    environment_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EnvironmentType.DEVELOPMENT.value
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Environment variables stored as JSON list of {name, secret_reference_id} objects
    # Do NOT store actual values - only references to SecretReference objects
    environment_variables: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)

    # Health check foundation
    health_check_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    health_check_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    project = relationship(
        "Project",
        back_populates="environments",
        lazy="selectin"
    )

    application = relationship(
        "Application",
        back_populates="environments",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Environment(id={self.id}, name={self.name}, type={self.environment_type})>"

