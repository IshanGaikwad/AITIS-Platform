"""Jira API — Import Jira issues as Requirements with async DB + RBAC."""

import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.schemas.requirement import RequirementCreate, RequirementOut
from app.services.jira_client import JiraClient
from app.services.jira_normalizer import jira_issue_to_story_payload
from app.services.story_service import create_requirement

router = APIRouter()


def _build_jira_client() -> JiraClient:
    """Construct a JiraClient, returning a clean 503 when not configured."""
    try:
        return JiraClient()
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Jira integration is not configured. Set JIRA_BASE_URL, "
                "JIRA_EMAIL, and JIRA_API_TOKEN in the backend environment."
            ),
        ) from exc


def _upstream_error(exc: Exception) -> HTTPException:
    """Translate an httpx upstream failure into a clean 502."""
    if isinstance(exc, httpx.HTTPStatusError):
        return HTTPException(
            status_code=502,
            detail=f"Jira returned {exc.response.status_code}: {exc.response.text[:200]}",
        )
    return HTTPException(status_code=502, detail=f"Could not reach Jira: {exc}")


@router.get("/workspaces")
async def get_workspaces(current_user=Depends(get_current_user)):
    client = _build_jira_client()
    try:
        return await client.get_workspaces()
    except httpx.HTTPError as exc:
        raise _upstream_error(exc)


@router.get("/issues/{issue_key}")
async def get_issue(issue_key: str, current_user=Depends(get_current_user)):
    client = _build_jira_client()
    try:
        return await client.get_issue(issue_key)
    except httpx.HTTPError as exc:
        raise _upstream_error(exc)


@router.get("/search")
async def search_issues(
    jql: str,
    maxResults: int = 25,
    nextPageToken: str | None = None,
    current_user=Depends(get_current_user),
):
    client = _build_jira_client()
    try:
        return await client.search_issues(
            jql=jql,
            max_results=maxResults,
            next_page_token=nextPageToken,
        )
    except httpx.HTTPError as exc:
        raise _upstream_error(exc)


@router.post("/import/{issue_key}", response_model=RequirementOut)
async def import_issue(
    issue_key: str,
    workspace_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead")),
):
    """Import a single Jira issue as a Requirement. Requires admin or QA lead role."""
    if workspace_id is None:
        raise HTTPException(status_code=422, detail="workspace_id is required to import a requirement")

    client = _build_jira_client()

    try:
        issue = await client.get_issue(issue_key)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch Jira issue: {exc}")

    payload = jira_issue_to_story_payload(issue)
    # Target workspace + tenant context
    payload["workspace_id"] = workspace_id
    payload.setdefault("organization_id", current_user.get("organization_id"))
    payload.setdefault("project_id", current_user.get("project_id"))

    req = await create_requirement(db, RequirementCreate(**payload))
    return req


@router.post("/import/search", response_model=list[RequirementOut])
async def import_search_results(
    jql: str,
    workspace_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead")),
):
    """Import Jira search results as Requirements. Requires admin or QA lead role."""
    if workspace_id is None:
        raise HTTPException(status_code=422, detail="workspace_id is required to import requirements")

    client = _build_jira_client()

    try:
        search_result = await client.search_issues(jql=jql, max_results=25)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to search Jira issues: {exc}")

    issues = search_result.get("issues", [])
    imported: list = []

    for issue in issues:
        payload = jira_issue_to_story_payload(issue)
        payload["workspace_id"] = workspace_id
        payload.setdefault("organization_id", current_user.get("organization_id"))
        payload.setdefault("project_id", current_user.get("project_id"))
        req = await create_requirement(db, RequirementCreate(**payload))
        imported.append(req)

    return imported
