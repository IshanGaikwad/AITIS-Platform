import base64
from typing import Any, Optional

import httpx

from app.core.config import settings


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

    async def get_projects(self) -> list[dict[str, Any]]:
        url = f"{self.base_url}/rest/api/3/project"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def get_issue(self, issue_key: str) -> dict[str, Any]:
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        params = {
            "fields": "summary,description,issuetype,priority,labels,components,status"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
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

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
