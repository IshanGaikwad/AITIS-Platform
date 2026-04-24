from fastapi import APIRouter

from app.schemas.testcase import TestCaseOut
from app.schemas.scenario import ScenarioOut
from app.services.scenario_service import to_gherkin

router = APIRouter()


@router.post("/generate", response_model=ScenarioOut)
def generate(payload: TestCaseOut) -> ScenarioOut:
    gherkin_text = to_gherkin(payload)

    return ScenarioOut(
        id=payload.id.replace("TC", "SC"),
        title=payload.title,
        gherkin=gherkin_text,
    )