"""Shared test fixtures for the AITIS backend test suite."""

import asyncio
import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.security import create_tokens_for_user
from app.models.base import Base


# ── Event loop ──────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Mock database session ───────────────────────────────────────────
@pytest_asyncio.fixture
async def mock_db() -> AsyncMock:
    """Return a mock AsyncSession that does not touch the real DB."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.scalar_one_or_none = AsyncMock(return_value=None)
    session.scalars = AsyncMock()
    return session


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Disposable integration DB session.

    These tests require a real PostgreSQL-compatible test database because the
    models use PostgreSQL UUID/JSONB types. Set TEST_DATABASE_URL to run them.
    """
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run database integration tests")

    engine = create_async_engine(database_url, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with Session() as session:
        yield session
        await session.rollback()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ── Fake user ───────────────────────────────────────────────────────
@pytest.fixture
def fake_user() -> MagicMock:
    """Return a mock User with typical JWT claims."""
    import uuid

    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.is_active = True
    return user


# ── JWT tokens ───────────────────────────────────────────────────────
@pytest.fixture
def auth_headers(fake_user) -> dict:
    """Return Authorization headers with a valid JWT for the fake user."""
    tokens = create_tokens_for_user(
        user_id=str(fake_user.id),
        org_id="00000000-0000-0000-0000-000000000001",
        workspace_id="00000000-0000-0000-0000-000000000002",
        role="qa_lead",
    )
    return {"Authorization": f"Bearer {tokens['access_token']}"}
