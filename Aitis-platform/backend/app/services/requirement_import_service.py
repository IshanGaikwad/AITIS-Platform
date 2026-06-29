"""Requirement import service with provider abstraction."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.models import Requirement, AcceptanceCriterion, RequirementPriority, RequirementStatus, RequirementType


class RequirementPayload:
    """Standard payload for importing requirements."""
    
    def __init__(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        requirement_type: str = "functional",
        external_id: Optional[str] = None,
        source: str = "manual",
        source_metadata: Optional[Dict[str, Any]] = None,
        acceptance_criteria: Optional[List[str]] = None,
    ):
        self.title = title
        self.description = description
        self.priority = priority
        self.requirement_type = requirement_type
        self.external_id = external_id
        self.source = source
        self.source_metadata = source_metadata or {}
        self.acceptance_criteria = acceptance_criteria or []


class RequirementProvider(ABC):
    """Abstract base class for requirement import providers."""

    @abstractmethod
    async def import_requirement(
        self,
        payload: Dict[str, Any],
    ) -> RequirementPayload:
        """
        Convert provider-specific data to standard RequirementPayload.
        
        Args:
            payload: Provider-specific data (e.g., Jira issue JSON)
            
        Returns:
            RequirementPayload with standardized fields
        """
        pass


class JiraRequirementProvider(RequirementProvider):
    """Import requirements from Jira issues."""

    async def import_requirement(self, payload: Dict[str, Any]) -> RequirementPayload:
        """
        Convert Jira issue JSON to RequirementPayload.
        
        Expected Jira JSON structure:
        {
            "key": "PROJ-123",
            "fields": {
                "summary": "User story title",
                "description": "Description text",
                "priority": { "name": "High" },
                "issuetype": { "name": "Story" },
                "customfield_10001": "AC text\nAC text"  // Custom AC field
            }
        }
        """
        fields = payload.get("fields", {})
        
        # Extract title
        title = fields.get("summary", "Untitled")
        
        # Extract description
        description = fields.get("description")
        
        # Map Jira priority to AITIS priority
        jira_priority = fields.get("priority", {}).get("name", "Medium")
        priority_map = {
            "Highest": "critical",
            "High": "high",
            "Medium": "medium",
            "Low": "low",
            "Lowest": "low",
        }
        priority = priority_map.get(jira_priority, "medium")
        
        # Map Jira issue type to AITIS requirement type
        issue_type = fields.get("issuetype", {}).get("name", "Story")
        type_map = {
            "Story": "functional",
            "Bug": "functional",
            "Task": "functional",
            "Subtask": "functional",
            "Epic": "functional",
        }
        requirement_type = type_map.get(issue_type, "functional")
        
        # Extract acceptance criteria if available
        # Assuming they're in a custom field or in description with AC: prefix lines
        acceptance_criteria = []
        if description:
            lines = description.split("\n")
            for line in lines:
                if line.strip().startswith("AC:") or line.strip().startswith("Given"):
                    criteria_text = line.replace("AC:", "").strip()
                    if criteria_text:
                        acceptance_criteria.append(criteria_text)
        
        # Jira source metadata
        source_metadata = {
            "jira_key": payload.get("key"),
            "jira_id": payload.get("id"),
            "jira_link": f"https://jira.atlassian.net/browse/{payload.get('key')}",
        }
        
        return RequirementPayload(
            title=title,
            description=description,
            priority=priority,
            requirement_type=requirement_type,
            external_id=payload.get("key"),
            source="jira",
            source_metadata=source_metadata,
            acceptance_criteria=acceptance_criteria,
        )


class ManualRequirementProvider(RequirementProvider):
    """Import requirements from manual JSON paste."""

    async def import_requirement(self, payload: Dict[str, Any]) -> RequirementPayload:
        """
        Convert manually pasted JSON to RequirementPayload.
        
        Expected format:
        {
            "title": "User story title",
            "description": "Description",
            "priority": "high",
            "type": "functional",
            "acceptanceCriteria": ["AC 1", "AC 2"]
        }
        """
        return RequirementPayload(
            title=payload.get("title", "Untitled"),
            description=payload.get("description"),
            priority=payload.get("priority", "medium"),
            requirement_type=payload.get("type", "functional"),
            external_id=payload.get("externalId"),
            source="manual",
            source_metadata={},
            acceptance_criteria=payload.get("acceptanceCriteria", []),
        )


class RequirementImportService:
    """Orchestrate requirement imports from various providers."""

    _providers = {
        "jira": JiraRequirementProvider(),
        "manual": ManualRequirementProvider(),
    }

    @staticmethod
    def get_provider(provider_type: str) -> Optional[RequirementProvider]:
        """Get provider by type."""
        return RequirementImportService._providers.get(provider_type.lower())

    @staticmethod
    async def import_requirement(
        db: AsyncSession,
        organization_id: UUID,
        workspace_id: UUID,
        project_id: UUID,
        provider_type: str,
        payload: Dict[str, Any],
        imported_by_user_id: UUID,
    ) -> Optional[Requirement]:
        """
        Import a requirement using the specified provider.
        
        Args:
            db: Database session
            organization_id: Tenant organization
            workspace_id: Tenant workspace
            project_id: Target project
            provider_type: "jira", "manual", etc.
            payload: Provider-specific data
            imported_by_user_id: User performing import
            
        Returns:
            Created Requirement or None if import failed
        """
        provider = RequirementImportService.get_provider(provider_type)
        if not provider:
            return None

        try:
            req_payload = await provider.import_requirement(payload)
        except Exception:
            return None

        # Create requirement
        from app.services.story_service import create_requirement
        from app.schemas.requirement import RequirementCreate

        req_create = RequirementCreate(
            project_id=project_id,
            title=req_payload.title,
            description=req_payload.description,
            type=req_payload.requirement_type or "functional",
            priority=req_payload.priority or "medium",
            status="draft",
            source=req_payload.source,
            external_id=req_payload.external_id,
            source_metadata=req_payload.source_metadata,
            acceptanceCriteria=req_payload.acceptance_criteria or [],
            organization_id=organization_id,
            workspace_id=workspace_id,
        )

        requirement = await create_requirement(db=db, payload=req_create)

        return requirement
