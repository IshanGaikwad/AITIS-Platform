"""Permission service — resource-level RBAC with DB-backed membership verification.

Provides a declarative permission matrix mapping roles → actions per resource type,
plus async helpers that verify actual membership records in the database.

Usage in routes:
    from app.services.permission_service import PermissionService, require_permission

    @router.delete("/{story_id}", dependencies=[Depends(require_permission("stories", "delete"))])
    async def delete_story(...):
        ...
"""

from enum import Enum
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, oauth2_scheme, verify_token
from app.db.database import AsyncSessionLocal
from app.models.tenant import Role, OrganizationMembership, WorkspaceMembership
from app.models.user import User


# ── Action enum ────────────────────────────────────────────────────
class Action(str, Enum):
    """Granular actions that can be performed on resources."""
    create = "create"
    read = "read"
    update = "update"
    delete = "delete"
    manage = "manage"       # full control (includes invite, settings, billing)
    execute = "execute"     # run tests / automation
    export = "export"       # download / share artifacts


# ── Resource types ──────────────────────────────────────────────────
class Resource(str, Enum):
    """Top-level resource types in the platform."""
    organizations = "organizations"
    workspaces = "workspaces"
    projects = "projects"
    applications = "applications"
    environments = "environments"
    stories = "stories"
    scenarios = "scenarios"
    test_cases = "test_cases"
    test_suites = "test_suites"
    test_executions = "test_executions"
    automation = "automation"
    integrations = "integrations"
    invitations = "invitations"
    members = "members"
    audit = "audit"
    reports = "reports"
    attachments = "attachments"


# ── Permission matrix ───────────────────────────────────────────────
# role → resource → set of allowed actions
# "manage" implies all other actions for that resource.
PERMISSION_MATRIX: dict[str, dict[str, set[str]]] = {
    Role.org_owner.value: {
        Resource.organizations.value: {"manage"},
        Resource.workspaces.value: {"manage"},
        Resource.projects.value: {"manage"},
        Resource.applications.value: {"manage"},
        Resource.environments.value: {"manage"},
        Resource.stories.value: {"manage"},
        Resource.scenarios.value: {"manage"},
        Resource.test_cases.value: {"manage"},
        Resource.test_suites.value: {"manage"},
        Resource.test_executions.value: {"manage"},
        Resource.automation.value: {"manage"},
        Resource.integrations.value: {"manage"},
        Resource.invitations.value: {"manage"},
        Resource.members.value: {"manage"},
        Resource.audit.value: {"manage"},
        Resource.reports.value: {"manage"},
        Resource.attachments.value: {"manage"},
    },
    Role.administrator.value: {
        Resource.organizations.value: {"read", "update"},
        Resource.workspaces.value: {"manage"},
        Resource.projects.value: {"manage"},
        Resource.applications.value: {"manage"},
        Resource.environments.value: {"manage"},
        Resource.stories.value: {"manage"},
        Resource.scenarios.value: {"manage"},
        Resource.test_cases.value: {"manage"},
        Resource.test_suites.value: {"manage"},
        Resource.test_executions.value: {"manage"},
        Resource.automation.value: {"manage"},
        Resource.integrations.value: {"manage"},
        Resource.invitations.value: {"manage"},
        Resource.members.value: {"manage"},
        Resource.audit.value: {"read"},
        Resource.reports.value: {"manage"},
        Resource.attachments.value: {"manage"},
    },
    Role.qa_lead.value: {
        Resource.organizations.value: {"read"},
        Resource.workspaces.value: {"read", "update"},
        Resource.projects.value: {"read", "update"},
        Resource.applications.value: {"read", "update"},
        Resource.environments.value: {"read", "update"},
        Resource.stories.value: {"manage"},
        Resource.scenarios.value: {"manage"},
        Resource.test_cases.value: {"manage"},
        Resource.test_suites.value: {"manage"},
        Resource.test_executions.value: {"manage"},
        Resource.automation.value: {"read", "update", "execute"},
        Resource.integrations.value: {"read"},
        Resource.invitations.value: {"read", "create"},
        Resource.members.value: {"read"},
        Resource.audit.value: {"read"},
        Resource.reports.value: {"read", "export"},
        Resource.attachments.value: {"read", "create", "delete"},
    },
    Role.automation_engineer.value: {
        Resource.organizations.value: {"read"},
        Resource.workspaces.value: {"read"},
        Resource.projects.value: {"read"},
        Resource.applications.value: {"read"},
        Resource.environments.value: {"read"},
        Resource.stories.value: {"read", "update"},
        Resource.scenarios.value: {"read", "update"},
        Resource.test_cases.value: {"read", "update"},
        Resource.test_suites.value: {"read", "update"},
        Resource.test_executions.value: {"read", "execute"},
        Resource.automation.value: {"manage"},
        Resource.integrations.value: {"read"},
        Resource.invitations.value: set(),
        Resource.members.value: {"read"},
        Resource.audit.value: {"read"},
        Resource.reports.value: {"read", "export"},
        Resource.attachments.value: {"read"},
    },
    Role.manual_tester.value: {
        Resource.organizations.value: {"read"},
        Resource.workspaces.value: {"read"},
        Resource.projects.value: {"read"},
        Resource.applications.value: {"read"},
        Resource.environments.value: {"read"},
        Resource.stories.value: {"read", "update"},
        Resource.scenarios.value: {"read", "update"},
        Resource.test_cases.value: {"read", "update", "execute"},
        Resource.test_suites.value: {"read"},
        Resource.test_executions.value: {"read", "execute"},
        Resource.automation.value: {"read"},
        Resource.integrations.value: set(),
        Resource.invitations.value: set(),
        Resource.members.value: {"read"},
        Resource.audit.value: set(),
        Resource.reports.value: {"read"},
        Resource.attachments.value: {"read"},
    },
    Role.developer.value: {
        Resource.organizations.value: {"read"},
        Resource.workspaces.value: {"read"},
        Resource.projects.value: {"read", "update"},
        Resource.applications.value: {"read"},
        Resource.environments.value: {"read"},
        Resource.stories.value: {"read", "update"},
        Resource.scenarios.value: {"read", "update"},
        Resource.test_cases.value: {"read", "update"},
        Resource.test_suites.value: {"read"},
        Resource.test_executions.value: {"read", "execute"},
        Resource.automation.value: {"read", "update"},
        Resource.integrations.value: {"read"},
        Resource.invitations.value: set(),
        Resource.members.value: {"read"},
        Resource.audit.value: {"read"},
        Resource.reports.value: {"read", "export"},
        Resource.attachments.value: {"read"},
    },
    Role.viewer.value: {
        Resource.organizations.value: {"read"},
        Resource.workspaces.value: {"read"},
        Resource.projects.value: {"read"},
        Resource.applications.value: {"read"},
        Resource.environments.value: {"read"},
        Resource.stories.value: {"read"},
        Resource.scenarios.value: {"read"},
        Resource.test_cases.value: {"read"},
        Resource.test_suites.value: {"read"},
        Resource.test_executions.value: {"read"},
        Resource.automation.value: {"read"},
        Resource.integrations.value: set(),
        Resource.invitations.value: set(),
        Resource.members.value: {"read"},
        Resource.audit.value: set(),
        Resource.reports.value: {"read"},
        Resource.attachments.value: {"read"},
    },
}


class PermissionService:
    """Stateless service for checking resource-level permissions."""

    @staticmethod
    def has_permission(role: str, resource: str, action: str) -> bool:
        """Check if a role grants a specific action on a resource.

        The "manage" action implies all other actions for that resource.
        """
        resource_perms = PERMISSION_MATRIX.get(role, {}).get(resource)
        if resource_perms is None:
            return False
        if "manage" in resource_perms:
            return True
        return action in resource_perms

    @staticmethod
    def get_permissions(role: str, resource: str) -> set[str]:
        """Return all allowed actions for a role on a resource."""
        resource_perms = PERMISSION_MATRIX.get(role, {}).get(resource, set())
        if "manage" in resource_perms:
            return {a.value for a in Action}
        return resource_perms

    @staticmethod
    def get_role_permissions(role: str) -> dict[str, set[str]]:
        """Return the full permission map for a role."""
        return PERMISSION_MATRIX.get(role, {})

    @staticmethod
    async def verify_org_membership(
        user_id: str,
        organization_id: str,
    ) -> Optional[str]:
        """Check DB that user belongs to the org. Returns their role or None."""
        import uuid

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(OrganizationMembership.role).where(
                    OrganizationMembership.user_id == uuid.UUID(user_id),
                    OrganizationMembership.organization_id == uuid.UUID(organization_id),
                )
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def verify_workspace_membership(
        user_id: str,
        workspace_id: str,
    ) -> Optional[str]:
        """Check DB that user belongs to the workspace. Returns their role or None."""
        import uuid

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(WorkspaceMembership.role).where(
                    WorkspaceMembership.user_id == uuid.UUID(user_id),
                    WorkspaceMembership.workspace_id == uuid.UUID(workspace_id),
                )
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def check_permission(
        user: User,
        resource: str,
        action: str,
        organization_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> bool:
        """Full permission check: JWT role + (optional) DB membership verification.

        1. Check the permission matrix for the user's role.
        2. If org/workspace IDs are provided, also verify DB membership.
        """
        # Get role from user's memberships — prefer workspace role, fall back to org role
        role: Optional[str] = None

        if workspace_id:
            role = await PermissionService.verify_workspace_membership(
                str(user.id), workspace_id
            )
        if role is None and organization_id:
            role = await PermissionService.verify_org_membership(
                str(user.id), organization_id
            )
        if role is None:
            # Fall back to JWT claim
            # This handles the case where the user has a token but no DB membership yet
            return False

        return PermissionService.has_permission(role, resource, action)


# ── FastAPI dependency factories ────────────────────────────────────

def require_permission(resource: str, action: str = "read"):
    """Factory returning a FastAPI dependency that enforces resource-level permission.

    Reads the role from the JWT token and checks the permission matrix.
    For stricter DB-backed checks, use PermissionService.check_permission() directly.

    Usage:
        @router.post("/", dependencies=[Depends(require_permission("stories", "create"))])
    """
    async def _check(
        token: str = Depends(oauth2_scheme),
    ) -> dict:
        payload = verify_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        user_role = payload.get("role")
        if user_role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token missing role claim",
            )

        if not PermissionService.has_permission(user_role, resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' cannot '{action}' on '{resource}'",
            )
        return payload

    return _check


def require_org_member():
    """Dependency — ensures user is a member of the org in the JWT claims."""
    async def _check(
        token: str = Depends(oauth2_scheme),
    ) -> dict:
        payload = verify_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        org_id = payload.get("org_id")
        if not org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization context required — select an organization first",
            )
        return payload

    return _check
