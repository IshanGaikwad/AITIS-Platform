
"""Pydantic schema for the AI generation pipeline — requirement + intent pair."""

from pydantic import BaseModel

from app.schemas.requirement import RequirementCreate
from app.schemas.intent import IntentOut


class StoryWithIntent(BaseModel):
    story: RequirementCreate
    intent: IntentOut
