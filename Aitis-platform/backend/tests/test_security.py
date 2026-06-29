"""Tests for core security — JWT creation, verification, and role checks."""

import pytest
from unittest.mock import MagicMock

from app.core.security import (
    create_tokens_for_user,
    verify_token,
    require_role,
)


class TestJWTTokens:
    def test_create_and_verify(self):
        tokens = create_tokens_for_user(
            user_id="00000000-0000-0000-0000-000000000001",
            org_id="00000000-0000-0000-0000-000000000002",
            workspace_id="00000000-0000-0000-0000-000000000003",
            role="qa_lead",
        )
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        payload = verify_token(tokens["access_token"])
        assert payload is not None
        assert payload["sub"] == "00000000-0000-0000-0000-000000000001"
        assert payload["role"] == "qa_lead"
        assert payload["org_id"] == "00000000-0000-0000-0000-000000000002"

    def test_invalid_token_returns_none(self):
        payload = verify_token("this.is.not.a.valid.token")
        assert payload is None


class TestRequireRole:
    def test_factory_returns_dependency(self):
        dep = require_role("org_owner", "administrator")
        assert callable(dep)

    def test_factory_with_single_role(self):
        dep = require_role("viewer")
        assert callable(dep)
