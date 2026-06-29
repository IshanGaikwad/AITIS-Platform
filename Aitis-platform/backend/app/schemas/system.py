"""Pydantic schemas for Integration, AuditEvent, Notification, and related entities."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Integration ─────────────────────────────────────────────────────
class IntegrationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., description="jira | confluence | github | gitlab | slack | teams | jenkins | github_actions | circleci | s3 | custom")
    config: Optional[dict] = None
    base_url: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = Field(None, description="active | inactive | error")
    config: Optional[dict] = None
    base_url: Optional[str] = None


class IntegrationOut(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    status: str = "active"
    config: Optional[dict] = None
    base_url: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    sync_error: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Secret Reference ────────────────────────────────────────────────
class SecretReferenceCreate(BaseModel):
    integration_id: uuid.UUID
    key: str = Field(..., min_length=1, max_length=200)
    vault_path: str
    description: Optional[str] = None


class SecretReferenceOut(BaseModel):
    id: uuid.UUID
    integration_id: uuid.UUID
    key: str
    vault_path: str
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Audit Event ─────────────────────────────────────────────────────
class AuditEventOut(BaseModel):
    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    action: str
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    changes: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Notification ─────────────────────────────────────────────────────
class NotificationCreate(BaseModel):
    user_id: uuid.UUID
    type: str = Field("info", description="info | warning | error | success")
    title: str = Field(..., min_length=1, max_length=200)
    message: str
    action_url: Optional[str] = None
    metadata: Optional[dict] = None


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None


class NotificationOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    title: str
    message: str
    is_read: bool = False
    action_url: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Defect ──────────────────────────────────────────────────────────
class DefectCreate(BaseModel):
    project_id: uuid.UUID
    case_execution_id: Optional[uuid.UUID] = None
    external_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=500)
    description: str
    severity: str = Field("major", description="blocker | critical | major | minor | trivial")
    status: str = Field("open", description="open | in_progress | resolved | closed | wont_fix")
    steps_to_reproduce: Optional[str] = None
    environment: Optional[str] = None
    labels: Optional[list] = None
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class DefectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    environment: Optional[str] = None
    labels: Optional[list] = None


class DefectOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    case_execution_id: Optional[uuid.UUID] = None
    external_id: Optional[str] = None
    title: str
    description: str
    severity: str
    status: str
    steps_to_reproduce: Optional[str] = None
    environment: Optional[str] = None
    labels: Optional[list] = None
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Healing Proposal ────────────────────────────────────────────────
class HealingProposalCreate(BaseModel):
    locator_id: uuid.UUID
    script_id: uuid.UUID
    original_code: str
    proposed_code: str
    explanation: Optional[str] = None
    confidence_score: Optional[float] = None
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None


class HealingProposalOut(BaseModel):
    id: uuid.UUID
    locator_id: uuid.UUID
    script_id: uuid.UUID
    status: str = "proposed"
    original_code: str
    proposed_code: str
    explanation: Optional[str] = None
    confidence_score: Optional[float] = None
    applied_at: Optional[datetime] = None
    reverted_at: Optional[datetime] = None
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
