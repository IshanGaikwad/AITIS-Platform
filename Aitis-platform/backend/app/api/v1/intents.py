
"""Intents API — AI-powered intent extraction from requirements."""

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.intent import IntentOut
from app.schemas.requirement import RequirementCreate
from app.services.intent_service import generate_intent

router = APIRouter()


@router.post("/generate", response_model=IntentOut)
async def generate(
    payload: RequirementCreate,
    current_user=Depends(get_current_user),
):
    """Extract testing intent from a requirement description."""
    return generate_intent(payload)
