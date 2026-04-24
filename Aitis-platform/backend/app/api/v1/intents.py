
from fastapi import APIRouter
from app.schemas.intent import IntentOut
from app.schemas.story import StoryCreate
from app.services.intent_service import generate_intent

router = APIRouter()

@router.post("/generate", response_model=IntentOut)
def generate(payload: StoryCreate):
    return generate_intent(payload)
