"""Tests API — AI-powered test generation from requirements.

Generates manual test cases, Gherkin scenarios, and framework-specific automation
code. Uses the configured LLM (Groq) when available, with a deterministic
rule-based fallback so the endpoint works without any API key.
"""

import logging

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.security import get_current_user
from app.schemas.pipeline import StoryWithIntent
from app.schemas.testcase import (
    FullGenerationResponse,
    StoryGenerateRequest,
    TestCasePipelineOut,
)
from app.services import fallback_generator
from app.services.test_service import generate_legacy_tests_only

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate", response_model=FullGenerationResponse)
async def generate_tests(
    payload: StoryGenerateRequest,
    current_user=Depends(get_current_user),
):
    """Generate a full test suite (manual + Gherkin + framework automation) from a requirement.

    Uses the configured LLM provider when an API key is set; otherwise falls back to
    the deterministic rule-based generator. Either way the response honors `framework`.
    """
    story = payload.model_dump()

    if settings.ai_enabled:
        try:
            from app.services.ai.llm_test_generator import generate_suite as llm_generate

            result = await llm_generate(story, payload.framework)
            # If the LLM returned nothing usable, fall back rather than return empty
            if result.get("tests") or result.get("automation"):
                return FullGenerationResponse(**result)
            logger.warning("LLM generation returned empty result; using heuristic fallback")
        except Exception as exc:  # noqa: BLE001 — never fail generation on LLM error
            logger.warning("LLM generation failed (%s); using heuristic fallback", exc)

    return FullGenerationResponse(**fallback_generator.generate_suite(story, payload.framework))


@router.post("/generate-legacy", response_model=list[TestCasePipelineOut])
async def generate_tests_legacy(
    payload: StoryWithIntent,
    current_user=Depends(get_current_user),
):
    """Generate legacy-format test cases from a requirement + intent pair."""
    tests = generate_legacy_tests_only(payload.story, payload.intent)
    return [TestCasePipelineOut(**item) for item in tests]
