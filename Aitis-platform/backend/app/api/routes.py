"""AITIS API v1 router registry — all route modules mounted here."""

from fastapi import APIRouter

from app.api.v1 import (
    ai,
    analytics,
    applications,
    attachments,
    atlassian,
    audit_events,
    auth,
    automation,
    cicd,
    dashboard,
    defects,
    environments,
    executions,
    folders,
    governance,
    healing,
    intents,
    invitations,
    jira,
    organizations,
    workspaces,
    scenarios,
    sso,
    stories,
    test_suites,
    tests,
    traceability,
    projects,
)

router = APIRouter()

# ── Tenant & Identity ──────────────────────────────────────────────────────
router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(invitations.router, prefix="/invitations", tags=["invitations"])

# ── Workspace & Requirements ──────────────────────────────────────────────────
router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
router.include_router(applications.router, prefix="", tags=["applications"])
router.include_router(environments.router, prefix="", tags=["environments"])
router.include_router(attachments.router, prefix="", tags=["attachments"])
router.include_router(stories.router, prefix="/requirements", tags=["requirements"])
# Legacy /stories prefix kept for backward compatibility
router.include_router(stories.router, prefix="/stories", tags=["stories (legacy)"])

# ── AI Intelligence ────────────────────────────────────────────────────────
router.include_router(ai.router, prefix="/ai", tags=["AI Services"])
router.include_router(intents.router, prefix="/intents", tags=["intents"])
router.include_router(tests.router, prefix="/tests", tags=["tests"])
router.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
router.include_router(automation.router, prefix="/automation", tags=["automation"])

# ── Test Management ─────────────────────────────────────────────────────────
router.include_router(folders.router, prefix="/folders", tags=["folders"])
router.include_router(test_suites.router, prefix="/test-suites", tags=["test-suites"])
router.include_router(executions.router, prefix="/executions", tags=["executions"])

# ── Integrations ────────────────────────────────────────────────────────────
router.include_router(jira.router, prefix="/jira", tags=["jira"])
router.include_router(atlassian.router, prefix="/atlassian", tags=["atlassian"])

# ── System ──────────────────────────────────────────────────────────────────
router.include_router(audit_events.router, prefix="/audit-events", tags=["audit-events"])

# ── Phase 7: Healing & Flakiness ────────────────────────────────────────────
router.include_router(healing.router, prefix="/healing", tags=["healing"])

# ── Phase 6: Dashboards, Defects, Traceability ──────────────────────────────
router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
router.include_router(defects.router, prefix="/defects", tags=["defects"])
router.include_router(traceability.router, prefix="/traceability", tags=["traceability"])

# ── Phase 9: CI/CD, SSO, Governance ─────────────────────────────────────────
router.include_router(cicd.router, prefix="/cicd", tags=["cicd"])
router.include_router(sso.router, prefix="/sso", tags=["sso"])
router.include_router(governance.router, prefix="/governance", tags=["governance"])