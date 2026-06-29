"""Requirement version history tracking service."""

from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Requirement


class RequirementVersionService:
    """Track and manage requirement version history."""

    @staticmethod
    async def create_version_snapshot(
        db: AsyncSession,
        requirement: Requirement,
        changed_by_user_id: UUID,
        change_reason: Optional[str] = None,
    ) -> dict:
        """
        Create a version snapshot of the current requirement state.
        Stores full snapshot in requirement.source_metadata['versions'].
        """
        if not requirement.source_metadata:
            requirement.source_metadata = {}

        if "versions" not in requirement.source_metadata:
            requirement.source_metadata["versions"] = []

        version_snapshot = {
            "version": requirement.version,
            "title": requirement.title,
            "description": requirement.description,
            "type": requirement.type,
            "priority": requirement.priority,
            "status": requirement.status,
            "changed_by": str(changed_by_user_id),
            "changed_at": datetime.utcnow().isoformat(),
            "reason": change_reason or "No reason provided",
            # Store AC list at this version
            "acceptance_criteria": [
                {
                    "id": str(ac.id),
                    "text": ac.text,
                    "category": ac.category,
                    "order": ac.order,
                }
                for ac in requirement.acceptance_criteria
            ]
        }

        requirement.source_metadata["versions"].append(version_snapshot)
        
        # Increment version
        requirement.version += 1

        await db.commit()
        await db.refresh(requirement)
        return version_snapshot

    @staticmethod
    async def get_version_history(
        requirement: Requirement,
    ) -> list[dict]:
        """Retrieve complete version history for a requirement."""
        if not requirement.source_metadata or "versions" not in requirement.source_metadata:
            return []
        return requirement.source_metadata["versions"]

    @staticmethod
    async def get_version(
        requirement: Requirement,
        version_number: int,
    ) -> Optional[dict]:
        """Retrieve a specific version snapshot."""
        history = await RequirementVersionService.get_version_history(requirement)
        for snapshot in history:
            if snapshot["version"] == version_number:
                return snapshot
        return None

    @staticmethod
    async def compare_versions(
        requirement: Requirement,
        version_1: int,
        version_2: int,
    ) -> Optional[dict]:
        """
        Compare two versions and return differences.
        Returns dict with 'from_version', 'to_version', 'changes' (list of changed fields).
        """
        v1 = await RequirementVersionService.get_version(requirement, version_1)
        v2 = await RequirementVersionService.get_version(requirement, version_2)

        if not v1 or not v2:
            return None

        changes = []
        
        # Check each field for changes
        for field in ["title", "description", "type", "priority", "status"]:
            if v1.get(field) != v2.get(field):
                changes.append({
                    "field": field,
                    "old_value": v1.get(field),
                    "new_value": v2.get(field),
                })

        # Check AC changes
        if v1.get("acceptance_criteria") != v2.get("acceptance_criteria"):
            changes.append({
                "field": "acceptance_criteria",
                "old_count": len(v1.get("acceptance_criteria", [])),
                "new_count": len(v2.get("acceptance_criteria", [])),
            })

        return {
            "from_version": version_1,
            "to_version": version_2,
            "changes": changes,
            "changed_by": v2.get("changed_by"),
            "changed_at": v2.get("changed_at"),
        }
