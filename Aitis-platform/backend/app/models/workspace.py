"""Workspace model â€” groups requirements, test suites, and artifacts."""

import uuid
from typing import Optional
from enum import Enum

from sqlalchemy import String, ForeignKey, Index
from sqlalchemy import Uuid
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, TenantMixin


class WorkspaceStatus(str, Enum):
    active = "active"
    archived = "archived"


class Workspace(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "workspaces"
    __table_args__ = (
        Index("ix_workspace_project_id", "project_id"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "PROJ"
    description: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=WorkspaceStatus.active.value)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Owner of the workspace
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    
    # Tags for organizing workspaces
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=[])

    # Override project_id from TenantMixin to add ForeignKey constraint
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    # NOTE: child relationships use cascade="all, delete-orphan" so deleting a
    # workspace removes its dependent rows. Without it the ORM tries to NULL the
    # children's NOT NULL workspace_id and the delete fails with IntegrityError.
    project = relationship("Project", back_populates="workspaces")
    requirements = relationship("Requirement", back_populates="workspace", cascade="all, delete-orphan", lazy="selectin")
    test_suites = relationship("TestSuite", back_populates="workspace", cascade="all, delete-orphan", lazy="selectin")
    applications = relationship("Application", back_populates="workspace", cascade="all, delete-orphan", lazy="selectin")
    environments = relationship("Environment", back_populates="workspace", cascade="all, delete-orphan", lazy="selectin")
    defects = relationship("Defect", back_populates="workspace", cascade="all, delete-orphan", lazy="selectin")
    owner = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Workspace {self.key}: {self.name}>"

