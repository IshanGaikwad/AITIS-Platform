"""Pydantic schemas for Requirement and AcceptanceCriterion entities."""

import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


# ── Requirement ─────────────────────────────────────────────────────
class RequirementCreate(BaseModel):
    """Schema for creating a requirement — compatible with legacy StoryCreate fields."""
    workspace_id: Optional[uuid.UUID] = None
    external_id: Optional[str] = Field(None, description="Jira key or other external ID (e.g. AUTH-123)")
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    type: str = Field("functional", description="functional | non_functional | business_rule | constraint")
    priority: str = Field("medium", description="critical | high | medium | low")
    status: str = Field("draft", description="draft | reviewed | approved | deprecated")
    source: Optional[str] = None
    source_metadata: Optional[dict] = None
    acceptanceCriteria: List[str] = Field(default_factory=list, description="AC text lines — legacy compat")
    framework: str = Field("Playwright", description="Target automation framework")
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None

    @property
    def jiraId(self) -> Optional[str]:
        """Legacy alias for external_id — used by test_service, intent_service, etc."""
        return self.external_id


class RequirementUpdate(BaseModel):
    external_id: Optional[str] = None
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    source_metadata: Optional[dict] = None
    acceptanceCriteria: Optional[List[str]] = None
    framework: Optional[str] = None


class RequirementOut(BaseModel):
    id: uuid.UUID
    workspace_id: Optional[uuid.UUID] = None
    external_id: Optional[str] = None
    title: str
    description: str
    type: str
    priority: str
    status: str
    source: Optional[str] = None
    source_metadata: Optional[dict] = None
    version: int = 1
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    acceptanceCriteria: List[str] = Field(default_factory=list)
    framework: str = "Playwright"
    created_at: datetime
    updated_at: Optional[datetime] = None

    # AI governance
    ai_input_source: Optional[str] = None
    ai_model_id: Optional[str] = None
    ai_prompt_version: Optional[str] = None
    ai_timestamp: Optional[datetime] = None
    ai_assumptions: Optional[dict] = None
    ai_confidence: Optional[float] = None
    ai_review_status: str = "pending"
    ai_reviewer_id: Optional[uuid.UUID] = None
    ai_approval_rejection_reason: Optional[str] = None
    ai_final_edited_version: bool = False

    model_config = ConfigDict(from_attributes=True)


# ── Acceptance Criterion ────────────────────────────────────────────
class AcceptanceCriterionCreate(BaseModel):
    requirement_id: uuid.UUID
    text: str = Field(..., min_length=1)
    category: str = Field("positive", description="security | state | validation | negative | positive")
    order: int = 0
    is_ai_generated: bool = False
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None


class AcceptanceCriterionUpdate(BaseModel):
    text: Optional[str] = None
    category: Optional[str] = None
    order: Optional[int] = None
    is_ai_generated: Optional[bool] = None


class AcceptanceCriterionOut(BaseModel):
    id: uuid.UUID
    requirement_id: uuid.UUID
    text: str
    category: str
    order: int
    is_ai_generated: bool
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # AI governance
    ai_input_source: Optional[str] = None
    ai_model_id: Optional[str] = None
    ai_prompt_version: Optional[str] = None
    ai_timestamp: Optional[datetime] = None
    ai_assumptions: Optional[dict] = None
    ai_confidence: Optional[float] = None
    ai_review_status: str = "pending"
    ai_reviewer_id: Optional[uuid.UUID] = None
    ai_approval_rejection_reason: Optional[str] = None
    ai_final_edited_version: bool = False

    model_config = ConfigDict(from_attributes=True)
