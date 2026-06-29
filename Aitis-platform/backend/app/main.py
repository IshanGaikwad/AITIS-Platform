import asyncio
import logging
import os
import warnings
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis import asyncio as aioredis
from sqlalchemy import text

from app.api.routes import router
from app.core.config import settings
from app.db.database import async_engine

warnings.filterwarnings("ignore", message="authlib.jose module is deprecated")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger("aitis")

    startup_warnings = settings.validate_startup()
    for warning in startup_warnings:
        logger.warning("CONFIG: %s", warning)

    # Auto-create all tables in development (idempotent — safe to run on every start)
    if settings.app_env == "development":
        try:
            from app.db.database import Base
            import app.models as _models  # noqa: F401 — register all models
            _ = _models
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("DB: tables verified/created")
        except Exception as exc:
            logger.warning("DB: could not auto-create tables — %s", exc)

    app.state.redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
        protocol=2,
    )
    try:
        await app.state.redis.ping()
    except Exception:
        logger.warning("Redis unavailable - caching disabled")

    yield

    await app.state.redis.aclose()
    await async_engine.dispose()

    from app.services.atlassian_client import close_http_client as close_atlassian_client
    from app.services.jira_client import close_http_client as close_jira_client

    await close_jira_client()
    await close_atlassian_client()


app = FastAPI(
    title="AITIS - AI Test Intelligence System",
    version="1.0.0",
    description="AI-powered testing intelligence platform with multi-tenancy, RBAC, and AI governance.",
    lifespan=lifespan,
)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3004",
    "http://127.0.0.1:3004",
    "http://frontend:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

env = os.getenv("ENV", "development")
if env == "production":
    origins.extend([
        os.getenv("FRONTEND_URL", "https://your-domain.com"),
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    checks = {"api": "ok"}

    try:
        await app.state.redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"

    try:
        async def _check_database():
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

        await asyncio.wait_for(_check_database(), timeout=2)
        checks["database"] = "ok"
    except Exception as _db_exc:
        checks["database"] = f"unavailable: {type(_db_exc).__name__}: {_db_exc}"

    status = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
    return {"status": status, "checks": checks}


app.include_router(router, prefix="/api")
