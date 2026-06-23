from typing import Any

import httpx


class AtlassianClient:
    def __init__(self, access_token: str):
        if not access_token:
            raise ValueError("Atlassian access token is required")

        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    async def get_accessible_resources(self) -> list[dict[str, Any]]:
        url = "https://api.atlassian.com/oauth/token/accessible-resources"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def get_jira_issue(self, cloud_id: str, issue_key: str) -> dict[str, Any]:
        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue/{issue_key}"
        params = {
            "fields": "summary,description,issuetype,priority,labels,components,status",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    async def search_jira(self, cloud_id: str, jql: str, max_results: int = 50) -> dict[str, Any]:
        url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/search"
        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": "summary,description,issuetype,priority,labels,components,status",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    async def search_confluence_content(self, site_id: str, cql: str, limit: int = 25) -> dict[str, Any]:
        url = f"https://api.atlassian.com/ex/confluence/{site_id}/wiki/rest/api/content/search"
        params = {
            "cql": cql,
            "limit": limit,
            "expand": "space,body.storage",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
