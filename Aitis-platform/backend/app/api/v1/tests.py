"""Tests API — AI-powered test generation from requirements + intents."""

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.pipeline import StoryWithIntent
from app.schemas.testcase import TestCaseOut, TestGenerationResponse
from app.services.test_service import generate_legacy_tests_only, generate_test_suite

router = APIRouter()


@router.post("/generate", response_model=TestGenerationResponse)
async def generate_tests(
    payload: StoryWithIntent,
    current_user=Depends(get_current_user),
):
    """Generate a full test suite from a requirement + intent pair."""
    result = generate_test_suite(payload.story, payload.intent)
    return TestGenerationResponse(**result)


@router.post("/generate-legacy", response_model=list[TestCaseOut])
async def generate_tests_legacy(
    payload: StoryWithIntent,
    current_user=Depends(get_current_user),
):
    """Generate legacy-format test cases from a requirement + intent pair."""
    tests = generate_legacy_tests_only(payload.story, payload.intent)
    return [TestCaseOut(**item) for item in tests]