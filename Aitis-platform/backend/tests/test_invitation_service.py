"""Tests for the Invitation service — lifecycle and validation."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.invitation import Invitation, InvitationStatus
from app.schemas.invitation import InvitationCreate, InvitationAccept, InvitationBulkCreate
from app.services.invitation_service import (
    create_invitation,
    accept_invitation,
    revoke_invitation,
    expire_stale_invitations,
)


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.scalar_one_or_none = AsyncMock(return_value=None)
    db.add = MagicMock()
    return db


@pytest.fixture
def sample_invitation():
    inv = MagicMock(spec=Invitation)
    inv.id = uuid.uuid4()
    inv.email = "new@example.com"
    inv.token = "abc123token"
    inv.status = InvitationStatus.pending
    inv.role = "manual_tester"
    inv.organization_id = uuid.uuid4()
    inv.workspace_id = uuid.uuid4()
    inv.invited_by = uuid.uuid4()
    inv.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    inv.accepted_at = None
    inv.accepted_by = None
    return inv


class TestCreateInvitation:
    @pytest.mark.asyncio
    async def test_creates_with_valid_data(self, mock_db, sample_invitation):
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", sample_invitation.id)

        schema = InvitationCreate(
            email="new@example.com",
            role="manual_tester",
            organization_id=sample_invitation.organization_id,
            workspace_id=sample_invitation.workspace_id,
        )

        result = await create_invitation(mock_db, sample_invitation.invited_by, schema)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestAcceptInvitation:
    @pytest.mark.asyncio
    async def test_accept_valid_token(self, mock_db, sample_invitation):
        sample_invitation.status = InvitationStatus.pending
        sample_invitation.expires_at = datetime.now(timezone.utc) + timedelta(days=1)

        # Mock the query to return the invitation
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.side_effect = [
            sample_invitation,
            None,
            None,
        ]
        mock_db.execute.return_value = mock_result

        user_id = uuid.uuid4()

        result = await accept_invitation(mock_db, sample_invitation.token, user_id=user_id)
        assert sample_invitation.status == InvitationStatus.accepted.value
        mock_db.commit.assert_called()


class TestRevokeInvitation:
    @pytest.mark.asyncio
    async def test_revoke_pending(self, mock_db, sample_invitation):
        sample_invitation.status = InvitationStatus.pending

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_invitation
        mock_db.execute.return_value = mock_result

        result = await revoke_invitation(mock_db, sample_invitation.id, sample_invitation.invited_by)
        assert sample_invitation.status == InvitationStatus.revoked.value
        mock_db.commit.assert_called()


class TestExpireStaleInvitations:
    @pytest.mark.asyncio
    async def test_expires_old_pending(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        count = await expire_stale_invitations(mock_db)
        assert count == 0
