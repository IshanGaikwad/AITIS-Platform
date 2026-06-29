from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from app.services.ai.factory import get_ai_provider

class DuplicateTest(BaseModel):
    """Represents a generated test that is a duplicate of an existing one"""
    generated_test_title: str
    existing_test_id: str
    similarity_score: float = Field(..., ge=0, le=1)
    reason: str = Field(..., description="Why these two tests are considered duplicates")

class CoverageGap(BaseModel):
    """Represents a gap in test coverage for a specific Acceptance Criterion"""
    ac_id: str
    ac_text: str
    gap_description: str = Field(..., description="What part of the AC is not covered by existing tests")
    suggested_test_scenario: str = Field(..., description="A high-level scenario to fill the gap")

class CoverageAnalysisResult(BaseModel):
    """The result of the duplicate detection and coverage analysis"""
    duplicates: List[DuplicateTest] = Field(default_factory=list)
    coverage_gaps: List[CoverageGap] = Field(default_factory=list)
    overall_coverage_percentage: float = Field(..., ge=0, le=100)
    summary: str = Field(..., description="Overall assessment of test coverage and redundancy")

class CoverageService:
    """
    Service responsible for detecting duplicate test cases and analyzing 
    coverage gaps between requirements/ACs and the test suite.
    """

    def __init__(self):
        self.ai_provider = get_ai_provider()

    async def detect_duplicates(
        self, 
        generated_tests: List[Any], 
        existing_tests: List[Any]
    ) -> List[DuplicateTest]:
        """
        Compares generated tests against existing tests to find duplicates.
        """
        if not generated_tests or not existing_tests:
            return []

        # We use the AI to perform semantic comparison rather than simple text matching
        system_instruction = (
            "You are a QA Audit Expert. Your task is to identify duplicate test cases. "
            "Two tests are duplicates if they verify the same behavior, even if the wording is different. "
            "Focus on the intent, preconditions, and expected results."
        )

        # To avoid token limits, we can batch the comparison or use a specific prompt
        # For this implementation, we'll provide the lists and ask for duplicates
        existing_tests_str = "\n".join([f"ID: {t.get('id', t.get('test_id', 'unknown'))} | Title: {t.get('title', '')} | Steps: {t.get('steps', '')}" for t in existing_tests])
        generated_tests_str = "\n".join([f"Title: {t.get('title', '')} | Steps: {t.get('steps', '')}" for t in generated_tests])

        prompt = (
            f"Existing Tests:\n{existing_tests_str}\n\n"
            f"Generated Tests:\n{generated_tests_str}\n\n"
            "Identify which generated tests are duplicates of existing ones. "
            "Return a list of duplicates with similarity scores and reasons."
        )

        # We expect a list of DuplicateTest objects
        # In a real scenario, we'd use a wrapper model like DuplicateDetectionResponse(duplicates=List[DuplicateTest])
        class DuplicateDetectionResponse(BaseModel):
            duplicates: List[DuplicateTest]

        response = await self.ai_provider.generate_structured_data(
            prompt=prompt,
            system_instruction=system_instruction,
            response_model=DuplicateDetectionResponse
        )

        import json
        try:
            data = json.loads(response.content)
            return data.get("duplicates", [])
        except Exception:
            return []

    async def analyze_coverage(
        self, 
        acceptance_criteria: List[Dict[str, str]], 
        test_cases: List[Any]
    ) -> CoverageAnalysisResult:
        """
        Analyzes the test suite to find gaps in coverage for the given Acceptance Criteria.
        """
        system_instruction = (
            "You are a Test Coverage Analyst. Your goal is to ensure 100% coverage of "
            "Acceptance Criteria (AC). Analyze the provided ACs and the existing test suite "
            "to identify any ACs that are partially or completely uncovered."
        )

        ac_str = "\n".join([f"ID: {ac.get('id', ac.get('ac_id', 'unknown'))} | Text: {ac.get('text', '')}" for ac in acceptance_criteria])
        tests_str = "\n".join([f"ID: {t.get('id', t.get('test_id', 'unknown'))} | Title: {t.get('title', '')} | Steps: {t.get('steps', '')}" for t in test_cases])

        prompt = (
            f"Acceptance Criteria:\n{ac_str}\n\n"
            f"Existing Test Cases:\n{tests_str}\n\n"
            "Perform a gap analysis. For each AC, determine if it is fully covered. "
            "If not, describe the gap and suggest a test scenario."
        )

        response = await self.ai_provider.generate_structured_data(
            prompt=prompt,
            system_instruction=system_instruction,
            response_model=CoverageAnalysisResult
        )

        import json
        try:
            data = json.loads(response.content)
            return CoverageAnalysisResult(**data)
        except Exception:
            return CoverageAnalysisResult(
                duplicates=[],
                coverage_gaps=[],
                overall_coverage_percentage=0.0,
                summary="Coverage analysis failed. Manual audit required."
            )
