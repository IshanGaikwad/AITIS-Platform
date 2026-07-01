import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.core.security import get_current_user
from app.models.user import User
from app.services.atlassian_client import AtlassianClient

router = APIRouter()


def get_atlassian_token(
    x_atlassian_token: str | None = Header(None, alias="X-Atlassian-Token"),
) -> str:
    """Extract the Atlassian OAuth access token.

    This is a 3LO OAuth token issued by Atlassian — distinct from the app's
    own JWT in the Authorization header. It must be supplied via the
    ``X-Atlassian-Token`` header.
    """
    if not x_atlassian_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Atlassian OAuth token missing. Provide it in the "
                "'X-Atlassian-Token' header after completing the Atlassian "
                "OAuth flow."
            ),
        )
    return x_atlassian_token


def _upstream_error(exc: Exception) -> HTTPException:
    """Translate an httpx upstream failure into a clean 502."""
    if isinstance(exc, httpx.HTTPStatusError):
        return HTTPException(
            status_code=502,
            detail=f"Atlassian returned {exc.response.status_code}: {exc.response.text[:200]}",
        )
    return HTTPException(status_code=502, detail=f"Could not reach Atlassian: {exc}")


@router.get("/resources")
async def get_accessible_resources(
    token: str = Depends(get_atlassian_token),
    current_user: User = Depends(get_current_user),
):
    client = AtlassianClient(token)
    try:
        return await client.get_accessible_resources()
    except httpx.HTTPError as exc:
        raise _upstream_error(exc)


@router.get("/jira/issues/{issue_key}")
async def get_jira_issue(
    issue_key: str,
    cloud_id: str = Query(..., description="Atlassian Jira cloud ID from accessible resources"),
    token: str = Depends(get_atlassian_token),
    current_user: User = Depends(get_current_user),
):
    client = AtlassianClient(token)
    try:
        return await client.get_jira_issue(cloud_id, issue_key)
    except httpx.HTTPError as exc:
        raise _upstream_error(exc)


@router.get("/jira/search")
async def search_jira_issues(
    cloud_id: str = Query(..., description="Atlassian Jira cloud ID from accessible resources"),
    jql: str = Query(..., description="JQL query string"),
    max_results: int = Query(25, description="Maximum number of results"),
    token: str = Depends(get_atlassian_token),
    current_user: User = Depends(get_current_user),
):
    client = AtlassianClient(token)
    try:
        return await client.search_jira(cloud_id, jql, max_results=max_results)
    except httpx.HTTPError as exc:
        raise _upstream_error(exc)


@router.get("/confluence/search")
async def search_confluence_content(
    site_id: str = Query(..., description="Atlassian Confluence site ID from accessible resources"),
    cql: str = Query(..., description="Confluence CQL query string"),
    limit: int = Query(25, description="Maximum number of results"),
    token: str = Depends(get_atlassian_token),
    current_user: User = Depends(get_current_user),
):
    client = AtlassianClient(token)
    try:
        return await client.search_confluence_content(site_id, cql, limit=limit)
    except httpx.HTTPError as exc:
        raise _upstream_error(exc)
