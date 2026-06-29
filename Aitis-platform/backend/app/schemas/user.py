"""Pydantic schemas for User and Auth entities — UUID-based, multi-tenant JWT claims."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── User ────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    picture: Optional[str] = None
    provider: str
    provider_id: str
    is_active: bool = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    picture: Optional[str] = None
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: Optional[str] = None
    picture: Optional[str] = None
    provider: str
    provider_id: str
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Auth / Token ───────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    role: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class WorkspaceSelect(BaseModel):
    """Request body for selecting an active workspace context."""
    workspace_id: uuid.UUID
    user_id: Optional[int] = None