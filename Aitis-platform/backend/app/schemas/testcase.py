from typing import Dict, List

from pydantic import BaseModel, Field


class TestCaseOut(BaseModel):
    id: str
    type: str
    title: str
    preconditions: List[str]
    steps: List[str]
    expectedResult: str
    rationale: str

    coversAcceptanceCriteria: List[str] = Field(default_factory=list)
    priority: str = "Medium"
    riskTags: List[str] = Field(default_factory=list)


class CoverageSummary(BaseModel):
    totalAcceptanceCriteria: int
    coveredAcceptanceCriteria: int
    coveragePercent: float
    uncoveredAcceptanceCriteria: List[str] = Field(default_factory=list)
    mapping: Dict[str, List[str]] = Field(default_factory=dict)


class TestGenerationResponse(BaseModel):
    tests: List[TestCaseOut]
    coverage: CoverageSummary