"""Legacy story schemas — deprecated, re-exported from requirement schemas.

The 'Story' concept is now 'Requirement'. These aliases exist for backward
compatibility with the AI generation pipeline (test_service, intent_service, etc.).
"""

from app.schemas.requirement import (
    RequirementCreate as StoryCreate,
    RequirementCreate as StoryIn,
    RequirementOut as StoryOut,
    RequirementUpdate as StoryUpdate,
)

__all__ = ["StoryCreate", "StoryIn", "StoryOut", "StoryUpdate"]