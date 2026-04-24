
from fastapi import APIRouter
from app.schemas.automation import AutomationRequest, AutomationOut
from app.services.automation_service import generate_playwright

router = APIRouter()

@router.post("/generate", response_model=AutomationOut)
def generate(payload: AutomationRequest):
    return generate_playwright(payload.story, payload.test_case)
