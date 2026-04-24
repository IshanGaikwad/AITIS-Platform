from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class StoryBase(BaseModel):
    jiraId: Optional[str] = None
    title: str
    description: str
    acceptanceCriteria: List[str]
    framework: str = "Playwright"


class StoryIn(StoryBase):
    pass


class StoryCreate(StoryBase):
    pass


class StoryUpdate(StoryBase):
    pass


class StoryOut(StoryBase):
    id: int | None = None

    model_config = ConfigDict(from_attributes=True)