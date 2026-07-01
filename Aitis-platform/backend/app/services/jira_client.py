import base64
from typing import Any, Optional

import httpx

from app.core.config import settings

# Module-level shared client for connection pooling
_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """Return a shared httpx.AsyncClient with connection pooling."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _client


async def close_http_client() -> None:
    """Close the shared client — call on app shutdown."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
    _client = None


class JiraClient:
    def __init__(self):
        if not settings.jira_base_url or not settings.jira_email or not settings.jira_api_token:
            raise ValueError("Jira configuration is incomplete")

        self.base_url = settings.jira_base_url.rstrip("/")

        token = f"{settings.jira_email}:{settings.jira_api_token}"
        encoded = base64.b64encode(token.encode("utf-8")).decode("utf-8")

        self.headers = {
            "Authorization": f"Basic {encoded}",
            "Accept": "application/json",
        }

    async def get_workspaces(self) -> list[dict[str, Any]]:
        url = f"{self.base_url}/rest/api/3/workspace"
        client = await get_http_client()
        response = await client.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    async def get_issue(self, issue_key: str) -> dict[str, Any]:
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        params = {
            "fields": "summary,description,issuetype,priority,labels,components,status"
        }
        client = await get_http_client()
        response = await client.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    async def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        next_page_token: Optional[str] = None,
        fields: str = "summary,description,issuetype,priority,labels,components,status",
    ) -> dict[str, Any]:
        url = f"{self.base_url}/rest/api/3/search/jql"

        params: dict[str, Any] = {
            "jql": jql,
            "maxResults": max_results,
            "fields": fields,
        }

        if next_page_token:
            params["nextPageToken"] = next_page_token

        client = await get_http_client()
        response = await client.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
