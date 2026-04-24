from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.story import StoryCreate, StoryOut
from app.services.jira_client import JiraClient
from app.services.jira_normalizer import jira_issue_to_story_payload
from app.services.story_service import create_story

router = APIRouter()


@router.get("/projects")
async def get_projects():
    client = JiraClient()
    return await client.get_projects()


@router.get("/issues/{issue_key}")
async def get_issue(issue_key: str):
    client = JiraClient()
    return await client.get_issue(issue_key)


@router.get("/search")
async def search_issues(jql: str, maxResults: int = 25, nextPageToken: str | None = None):
    client = JiraClient()
    return await client.search_issues(
        jql=jql,
        max_results=maxResults,
        next_page_token=nextPageToken,
    )


@router.post("/import/{issue_key}", response_model=StoryOut)
async def import_issue(issue_key: str, db: Session = Depends(get_db)):
    client = JiraClient()

    try:
        issue = await client.get_issue(issue_key)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch Jira issue: {exc}")

    payload = jira_issue_to_story_payload(issue)
    story = create_story(db, StoryCreate(**payload))

    return StoryOut(
        id=story.id,
        jiraId=story.jira_id,
        title=story.title,
        description=story.description,
        acceptanceCriteria=payload["acceptanceCriteria"],
        framework=story.framework,
    )


@router.post("/import/search", response_model=list[StoryOut])
async def import_search_results(jql: str, db: Session = Depends(get_db)):
    client = JiraClient()

    try:
        search_result = await client.search_issues(jql=jql, max_results=25)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to search Jira issues: {exc}")

    issues = search_result.get("issues", [])
    imported: list[StoryOut] = []

    for issue in issues:
        payload = jira_issue_to_story_payload(issue)
        story = create_story(db, StoryCreate(**payload))
        imported.append(
            StoryOut(
                id=story.id,
                jiraId=story.jira_id,
                title=story.title,
                description=story.description,
                acceptanceCriteria=payload["acceptanceCriteria"],
                framework=story.framework,
            )
        )

    return imported
