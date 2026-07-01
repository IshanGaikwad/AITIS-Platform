"""Pydantic schemas for Organization, Project, and Membership entities."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Role ───────────────────────────────────────────────────────────
class RoleOut(BaseModel):
    value: str
    label: str

    model_config = ConfigDict(from_attributes=True)


# ── Organization ───────────────────────────────────────────────────
class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    slug: str = Field(..., min_length=1, max_length=60, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    logo_url: Optional[str] = None
    settings: Optional[dict] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    slug: Optional[str] = Field(None, min_length=1, max_length=60, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    logo_url: Optional[str] = None
    settings: Optional[dict] = None


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    settings: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Organization Membership ────────────────────────────────────────
class OrganizationMembershipCreate(BaseModel):
    user_id: uuid.UUID
    role: str = Field(..., description="One of: org_owner, administrator, qa_lead, automation_engineer, manual_tester, developer, viewer")


class OrganizationMembershipOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Project ──────────────────────────────────────────────────────
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    slug: str = Field(..., min_length=1, max_length=60, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    organization_id: uuid.UUID
    description: Optional[str] = None
    settings: Optional[dict] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    slug: Optional[str] = Field(None, min_length=1, max_length=60, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: Optional[str] = None
    settings: Optional[dict] = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    organization_id: uuid.UUID
    description: Optional[str] = None
    settings: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Project Membership ───────────────────────────────────────────
class ProjectMembershipCreate(BaseModel):
    user_id: uuid.UUID
    role: str = Field(..., description="One of: org_owner, administrator, qa_lead, automation_engineer, manual_tester, developer, viewer")


class ProjectMembershipOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
