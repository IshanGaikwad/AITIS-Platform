from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.base import Base

_is_sqlite = settings.database_url.startswith("sqlite")

# Sync engine for Alembic migrations
if _is_sqlite:
    _sync_url = settings.database_url.replace("+aiosqlite", "")
    sync_engine = create_engine(_sync_url, echo=settings.app_env == "development", connect_args={"check_same_thread": False})
else:
    sync_engine = create_engine(
        settings.database_url.replace("+asyncpg", "+psycopg2").replace("postgresql+asyncpg", "postgresql"),
        echo=settings.app_env == "development",
    )

# Async engine for application runtime
_async_kwargs = {"echo": settings.app_env == "development"}
if not _is_sqlite:
    _async_kwargs["pool_size"] = 20
    _async_kwargs["max_overflow"] = 10

async_engine = create_async_engine(settings.database_url, **_async_kwargs)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    """Async database session dependency."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db():
    """Sync database session for migrations/scripts."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
