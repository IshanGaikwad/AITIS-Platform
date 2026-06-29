"""Tests for the PermissionService — RBAC matrix and dependency factories."""

import pytest
from unittest.mock import patch, AsyncMock

from app.services.permission_service import (
    Action,
    Resource,
    PERMISSION_MATRIX,
    PermissionService,
    require_permission,
    require_org_member,
)


# ── Matrix structure ─────────────────────────────────────────────────
class TestPermissionMatrix:
    """Validate the permission matrix is well-formed."""

    def test_all_roles_have_entries(self):
        from app.models.tenant import Role

        for role in Role:
            assert role.value in PERMISSION_MATRIX, f"Missing matrix entry for role: {role.value}"

    def test_all_resources_have_entries(self):
        from app.models.tenant import Role

        for role in Role:
            for resource in Resource:
                assert resource.value in PERMISSION_MATRIX[role.value], (
                    f"Missing resource '{resource.value}' for role '{role.value}'"
                )

    def test_manage_implies_all_actions(self):
        """If a role has 'manage' on a resource, has_permission should return True for any action."""
        for role_str, resources in PERMISSION_MATRIX.items():
            for resource_str, actions in resources.items():
                if "manage" in actions:
                    for action in Action:
                        assert PermissionService.has_permission(role_str, resource_str, action.value)


# ── has_permission ──────────────────────────────────────────────────
class TestHasPermission:
    def test_org_owner_can_do_anything(self):
        assert PermissionService.has_permission("org_owner", "stories", "delete")
        assert PermissionService.has_permission("org_owner", "organizations", "manage")

    def test_viewer_cannot_create(self):
        assert not PermissionService.has_permission("viewer", "stories", "create")
        assert not PermissionService.has_permission("viewer", "test_cases", "update")

    def test_viewer_can_read(self):
        assert PermissionService.has_permission("viewer", "stories", "read")
        assert PermissionService.has_permission("viewer", "reports", "read")

    def test_unknown_role_denied(self):
        assert not PermissionService.has_permission("superadmin", "stories", "read")

    def test_unknown_resource_denied(self):
        assert not PermissionService.has_permission("org_owner", "nonexistent", "read")

    def test_qa_lead_can_manage_stories(self):
        assert PermissionService.has_permission("qa_lead", "stories", "create")
        assert PermissionService.has_permission("qa_lead", "stories", "delete")

    def test_manual_tester_can_execute(self):
        assert PermissionService.has_permission("manual_tester", "test_cases", "execute")
        assert not PermissionService.has_permission("manual_tester", "test_cases", "delete")

    def test_automation_engineer_manages_automation(self):
        assert PermissionService.has_permission("automation_engineer", "automation", "manage")
        assert not PermissionService.has_permission("automation_engineer", "invitations", "create")


# ── get_permissions ─────────────────────────────────────────────────
class TestGetPermissions:
    def test_manage_expands_to_all(self):
        perms = PermissionService.get_permissions("org_owner", "stories")
        assert "create" in perms
        assert "delete" in perms
        assert "manage" in perms

    def test_viewer_stories_readonly(self):
        perms = PermissionService.get_permissions("viewer", "stories")
        assert perms == {"read"}


# ── get_role_permissions ────────────────────────────────────────────
class TestGetRolePermissions:
    def test_returns_full_map(self):
        perms = PermissionService.get_role_permissions("qa_lead")
        assert isinstance(perms, dict)
        assert "stories" in perms
        assert "manage" in perms["stories"]

    def test_unknown_role_empty(self):
        perms = PermissionService.get_role_permissions("nonexistent")
        assert perms == {}
