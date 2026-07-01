"""Scenarios API — Convert test cases to Gherkin scenarios."""

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.scenario import ScenarioOut
from app.schemas.testcase import TestCasePipelineOut
from app.services.scenario_service import to_gherkin

router = APIRouter()


@router.post("/generate", response_model=ScenarioOut)
async def generate(
    payload: TestCasePipelineOut,
    current_user=Depends(get_current_user),
):
    """Convert a test case into a Gherkin scenario."""
    gherkin_text = to_gherkin(payload)
    return ScenarioOut(
        id=payload.id.replace("TC", "SC"),
        title=payload.title,
        gherkin=gherkin_text,
    )