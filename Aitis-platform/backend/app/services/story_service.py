import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models.story import Story
from app.schemas.story import StoryCreate, StoryUpdate


def list_stories(db: Session):
    return db.query(Story).order_by(Story.id.desc()).all()


def get_story(db: Session, story_id: int) -> Optional[Story]:
    return db.query(Story).filter(Story.id == story_id).first()


def create_story(db: Session, payload: StoryCreate) -> Story:
    story = Story(
        jira_id=payload.jiraId,
        title=payload.title,
        description=payload.description,
        acceptance_criteria=json.dumps(payload.acceptanceCriteria),
        framework=payload.framework,
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


def update_story(db: Session, story_id: int, payload: StoryUpdate) -> Optional[Story]:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        return None

    story.jira_id = payload.jiraId
    story.title = payload.title
    story.description = payload.description
    story.acceptance_criteria = json.dumps(payload.acceptanceCriteria)
    story.framework = payload.framework

    db.commit()
    db.refresh(story)
    return story


def delete_story(db: Session, story_id: int) -> bool:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        return False

    db.delete(story)
    db.commit()
    return True