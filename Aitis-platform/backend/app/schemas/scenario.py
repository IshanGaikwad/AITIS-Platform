
from pydantic import BaseModel


class ScenarioOut(BaseModel):
    id: str
    title: str
    gherkin: str
