"""Project model â€” groups requirements, test suites, and artifacts."""

import uuid
from typing import Optional
from enum import Enum

from sqlalchemy import String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, TenantMixin


class ProjectStatus(str, Enum):
    active = "active"
    archived = "archived"


class Project(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_project_workspace_id", "workspace_id"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "PROJ"
    description: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ProjectStatus.active.value)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Owner of the project
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    
    # Tags for organizing projects
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=[])

    # Override workspace_id from TenantMixin to add ForeignKey constraint
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    workspace = relationship("Workspace", back_populates="projects")
    requirements = relationship("Requirement", back_populates="project", lazy="selectin")
    test_suites = relationship("TestSuite", back_populates="project", lazy="selectin")
    applications = relationship("Application", back_populates="project", cascade="all, delete-orphan", lazy="selectin")
    environments = relationship("Environment", back_populates="project", cascade="all, delete-orphan", lazy="selectin")
    defects = relationship("Defect", back_populates="project", lazy="selectin")
    owner = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Project {self.key}: {self.name}>"

