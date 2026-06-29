"""Legacy Story model â€” DEPRECATED. Use Requirement + AcceptanceCriterion instead.

This file is kept only for backward compatibility during migration.
All new code should use app.models.requirement.Requirement and
app.models.requirement.AcceptanceCriterion.
"""

# Re-export for any legacy imports
from app.models.requirement import Requirement as Story  # noqa: F401
