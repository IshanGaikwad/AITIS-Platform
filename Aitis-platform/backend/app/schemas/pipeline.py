
from pydantic import BaseModel
from app.schemas.story import StoryCreate
from app.schemas.intent import IntentOut

class StoryWithIntent(BaseModel):
    story: StoryCreate
    intent: IntentOut
