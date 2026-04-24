from fastapi import APIRouter

from app.schemas.pipeline import StoryWithIntent
from app.schemas.testcase import TestCaseOut, TestGenerationResponse
from app.services.test_service import generate_legacy_tests_only, generate_test_suite

router = APIRouter()


@router.post("/generate", response_model=TestGenerationResponse)
def generate_tests(payload: StoryWithIntent) -> TestGenerationResponse:
    result = generate_test_suite(payload.story, payload.intent)
    return TestGenerationResponse(**result)


@router.post("/generate-legacy", response_model=list[TestCaseOut])
def generate_tests_legacy(payload: StoryWithIntent) -> list[TestCaseOut]:
    tests = generate_legacy_tests_only(payload.story, payload.intent)
    return [TestCaseOut(**item) for item in tests]