"""Pydantic schemas for Workspace entity."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    key: str = Field(..., min_length=1, max_length=10, pattern=r"^[A-Z][A-Z0-9]*$")
    description: Optional[str] = None
    project_id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    settings: Optional[dict] = None


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field(None, description="active | archived")
    settings: Optional[dict] = None


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    name: str
    key: str
    description: Optional[str] = None
    status: str = "active"
    project_id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    settings: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
