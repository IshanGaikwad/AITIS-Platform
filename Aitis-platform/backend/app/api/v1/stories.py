import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.story import StoryCreate, StoryOut, StoryUpdate
from app.services.story_service import (
    create_story,
    delete_story,
    get_story,
    list_stories,
    update_story,
)

router = APIRouter()

SAMPLE_STORY = {
    "id": 0,
    "jiraId": "AUTH-123",
    "title": "User login with email and password",
    "description": "As a registered user, I want to log in using my email and password so that I can access my dashboard.",
    "acceptanceCriteria": [
        "User can log in with valid email and password",
        "User sees an error message for invalid password",
        "User cannot log in with blank fields",
        "Locked users should see an account locked message",
    ],
    "framework": "Playwright",
}


def normalize_story(story) -> StoryOut:
    return StoryOut(
        id=story.id,
        jiraId=story.jira_id,
        title=story.title,
        description=story.description,
        acceptanceCriteria=json.loads(story.acceptance_criteria),
        framework=story.framework,
    )


@router.get("/sample", response_model=StoryOut)
def get_sample_story():
    return StoryOut(**SAMPLE_STORY)


@router.get("", response_model=list[StoryOut])
def get_all_stories(db: Session = Depends(get_db)):
    stories = list_stories(db)
    return [normalize_story(item) for item in stories]


@router.get("/{story_id}", response_model=StoryOut)
def get_story_by_id(story_id: int, db: Session = Depends(get_db)):
    story = get_story(db, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return normalize_story(story)


@router.post("", response_model=StoryOut)
def create_new_story(payload: StoryCreate, db: Session = Depends(get_db)):
    story = create_story(db, payload)
    return normalize_story(story)


@router.put("/{story_id}", response_model=StoryOut)
def update_existing_story(story_id: int, payload: StoryUpdate, db: Session = Depends(get_db)):
    story = update_story(db, story_id, payload)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return normalize_story(story)


@router.delete("/{story_id}")
def delete_existing_story(story_id: int, db: Session = Depends(get_db)):
    success = delete_story(db, story_id)
    if not success:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"success": True}