
"""Pydantic schema for AI-generated intent extraction."""

from pydantic import BaseModel, Field


class IntentOut(BaseModel):
    actor: str
    goal: str
    preconditions: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    businessRules: list[str] = Field(default_factory=list)
    successOutcome: str
    failureOutcomes: list[str] = Field(default_factory=list)
