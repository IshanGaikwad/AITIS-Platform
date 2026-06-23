from fastapi import APIRouter

from app.api.v1 import stories, intents, tests, scenarios, automation, jira, auth, atlassian

router = APIRouter()

router.include_router(stories.router, prefix="/stories", tags=["stories"])
router.include_router(intents.router, prefix="/intents", tags=["intents"])
router.include_router(tests.router, prefix="/tests", tags=["tests"])
router.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
router.include_router(automation.router, prefix="/automation", tags=["automation"])
router.include_router(jira.router, prefix="/jira", tags=["jira"])
router.include_router(atlassian.router, prefix="/atlassian", tags=["atlassian"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])