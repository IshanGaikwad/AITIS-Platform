"""Jira API — Import Jira issues as Requirements with async DB + RBAC."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.schemas.requirement import RequirementCreate, RequirementOut
from app.services.jira_client import JiraClient
from app.services.jira_normalizer import jira_issue_to_story_payload
from app.services.story_service import create_requirement

router = APIRouter()


@router.get("/projects")
async def get_projects(current_user=Depends(get_current_user)):
    client = JiraClient()
    return await client.get_projects()


@router.get("/issues/{issue_key}")
async def get_issue(issue_key: str, current_user=Depends(get_current_user)):
    client = JiraClient()
    return await client.get_issue(issue_key)


@router.get("/search")
async def search_issues(
    jql: str,
    maxResults: int = 25,
    nextPageToken: str | None = None,
    current_user=Depends(get_current_user),
):
    client = JiraClient()
    return await client.search_issues(
        jql=jql,
        max_results=maxResults,
        next_page_token=nextPageToken,
    )


@router.post("/import/{issue_key}", response_model=RequirementOut)
async def import_issue(
    issue_key: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead")),
):
    """Import a single Jira issue as a Requirement. Requires admin or QA lead role."""
    client = JiraClient()

    try:
        issue = await client.get_issue(issue_key)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch Jira issue: {exc}")

    payload = jira_issue_to_story_payload(issue)
    # Inject tenant context from JWT
    payload.setdefault("organization_id", current_user.get("organization_id"))
    payload.setdefault("workspace_id", current_user.get("workspace_id"))

    req = await create_requirement(db, RequirementCreate(**payload))
    return req


@router.post("/import/search", response_model=list[RequirementOut])
async def import_search_results(
    jql: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead")),
):
    """Import Jira search results as Requirements. Requires admin or QA lead role."""
    client = JiraClient()

    try:
        search_result = await client.search_issues(jql=jql, max_results=25)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to search Jira issues: {exc}")

    issues = search_result.get("issues", [])
    imported: list = []

    for issue in issues:
        payload = jira_issue_to_story_payload(issue)
        payload.setdefault("organization_id", current_user.get("organization_id"))
        payload.setdefault("workspace_id", current_user.get("workspace_id"))
        req = await create_requirement(db, RequirementCreate(**payload))
        imported.append(req)

    return imported
