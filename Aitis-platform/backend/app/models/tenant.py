"""Organization and Project models â€” multi-tenancy foundation."""

import uuid
from typing import Optional
from enum import Enum

from sqlalchemy import String, ForeignKey, UniqueConstraint, Index
from sqlalchemy import Uuid
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


# â”€â”€ Role Enum â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class Role(str, Enum):
    org_owner = "org_owner"
    administrator = "administrator"
    qa_lead = "qa_lead"
    automation_engineer = "automation_engineer"
    manual_tester = "manual_tester"
    developer = "developer"
    viewer = "viewer"


# â”€â”€ Organization â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class Organization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    # Relationships
    memberships = relationship("OrganizationMembership", back_populates="organization", lazy="selectin")
    projects = relationship("Project", back_populates="organization", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Organization {self.slug}>"


class OrganizationMembership(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_user_org"),
        Index("ix_org_members_org_id", "organization_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default=Role.viewer.value)

    # Relationships
    user = relationship("User", back_populates="memberships")
    organization = relationship("Organization", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<OrgMembership user={self.user_id} org={self.organization_id} role={self.role}>"


# â”€â”€ Project â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_org_project_slug"),
        Index("ix_project_org_id", "organization_id"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="projects")
    memberships = relationship("ProjectMembership", back_populates="project", lazy="selectin")
    workspaces = relationship("Workspace", back_populates="project", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Project {self.slug}>"


class ProjectMembership(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "project_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_user_project"),
        Index("ix_ws_members_ws_id", "project_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default=Role.viewer.value)

    # Relationships
    user = relationship("User", back_populates="project_memberships")
    project = relationship("Project", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<WsMembership user={self.user_id} ws={self.project_id} role={self.role}>"

