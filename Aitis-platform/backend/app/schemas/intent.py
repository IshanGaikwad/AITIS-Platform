
from pydantic import BaseModel

class IntentOut(BaseModel):
    actor: str
    goal: str
    preconditions: list[str]
    inputs: list[str]
    businessRules: list[str]
    successOutcome: str
    failureOutcomes: list[str]
