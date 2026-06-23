from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.services.atlassian_client import AtlassianClient

router = APIRouter()


def get_atlassian_token(authorization: str | None = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", 1)[1]


@router.get("/resources")
async def get_accessible_resources(token: str = Depends(get_atlassian_token)):
    client = AtlassianClient(token)
    return await client.get_accessible_resources()


@router.get("/jira/issues/{issue_key}")
async def get_jira_issue(
    issue_key: str,
    cloud_id: str = Query(..., description="Atlassian Jira cloud ID from accessible resources"),
    token: str = Depends(get_atlassian_token),
):
    client = AtlassianClient(token)
    return await client.get_jira_issue(cloud_id, issue_key)


@router.get("/jira/search")
async def search_jira_issues(
    cloud_id: str = Query(..., description="Atlassian Jira cloud ID from accessible resources"),
    jql: str = Query(..., description="JQL query string"),
    max_results: int = Query(25, description="Maximum number of results"),
    token: str = Depends(get_atlassian_token),
):
    client = AtlassianClient(token)
    return await client.search_jira(cloud_id, jql, max_results=max_results)


@router.get("/confluence/search")
async def search_confluence_content(
    site_id: str = Query(..., description="Atlassian Confluence site ID from accessible resources"),
    cql: str = Query(..., description="Confluence CQL query string"),
    limit: int = Query(25, description="Maximum number of results"),
    token: str = Depends(get_atlassian_token),
):
    client = AtlassianClient(token)
    return await client.search_confluence_content(site_id, cql, limit=limit)
