"""Pydantic schemas for Invitation entities."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── Invitation ─────────────────────────────────────────────────────
class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = Field(
        default="viewer",
        description="One of: org_owner, administrator, qa_lead, automation_engineer, manual_tester, developer, viewer",
    )
    organization_id: uuid.UUID
    project_id: Optional[uuid.UUID] = Field(
        None, description="If set, user is also added to this project on acceptance"
    )
    expires_in_days: int = Field(default=7, ge=1, le=30, description="Days until invitation expires")


class InvitationOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    token: str
    status: str
    invited_by: uuid.UUID
    organization_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    role: str
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    accepted_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class InvitationAccept(BaseModel):
    """Body for accepting an invitation — just the token."""
    token: str = Field(..., min_length=1)


class InvitationBulkCreate(BaseModel):
    """Bulk invite — same org/project/role, multiple emails."""
    emails: list[EmailStr] = Field(..., min_length=1, max_length=50)
    role: str = Field(default="viewer")
    organization_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    expires_in_days: int = Field(default=7, ge=1, le=30)
