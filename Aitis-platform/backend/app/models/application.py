"""Application model for deployment targets (web, mobile, etc.)"""

import uuid
from enum import Enum
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, Integer
from sqlalchemy import Uuid
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, TenantMixin


class ApplicationType(str, Enum):
    """Supported application types."""
    WEB = "WEB"
    MOBILE_WEB = "MOBILE_WEB"
    ANDROID = "ANDROID"
    IOS = "IOS"
    HYBRID = "HYBRID"


class Application(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Represents an application/deployment target within a workspace."""

    __tablename__ = "applications"

    # Foreign keys
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    application_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ApplicationType.WEB.value
    )
    repository_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Additional metadata (e.g., package names for mobile apps, framework info, etc.)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True, default=dict)

    # Relationships
    workspace = relationship(
        "Workspace",
        back_populates="applications",
        lazy="selectin"
    )

    environments = relationship(
        "Environment",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Application(id={self.id}, name={self.name}, type={self.application_type})>"

