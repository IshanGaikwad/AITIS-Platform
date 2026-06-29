"""Invitation model â€” org/workspace invite flow with token-based acceptance."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class InvitationStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    expired = "expired"
    revoked = "revoked"


class Invitation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invitations"
    __table_args__ = (
        Index("ix_invitations_token", "token", unique=True),
        Index("ix_invitations_org_id", "organization_id"),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=InvitationStatus.pending.value
    )

    # Who sent the invitation
    invited_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Target scope â€” org-level or workspace-level invite
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True
    )

    # Role to assign on acceptance
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="viewer")

    # Timestamps for invite lifecycle
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # The user who accepted (set on acceptance)
    accepted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    inviter = relationship("User", foreign_keys=[invited_by], lazy="selectin")
    acceptor = relationship("User", foreign_keys=[accepted_by], lazy="selectin")
    organization = relationship("Organization", lazy="selectin")
    workspace = relationship("Workspace", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Invitation {self.email} status={self.status}>"

