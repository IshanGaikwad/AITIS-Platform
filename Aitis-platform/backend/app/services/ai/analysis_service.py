from typing import List, Dict, Any
from pydantic import BaseModel, Field
from app.services.ai.factory import get_ai_provider
from app.services.ai.base import AIResponse

class AnalysisIssue(BaseModel):
    """Represents a specific quality issue found in a requirement"""
    issue_type: str = Field(..., description="Type of issue: Ambiguity, Missing AC, Contradiction, Unverifiable")
    description: str = Field(..., description="Detailed explanation of the issue")
    severity: str = Field(..., description="Severity: Low, Medium, High")
    suggestion: str = Field(..., description="Suggested improvement to fix the issue")
    location: str = Field(..., description="The specific part of the requirement where the issue was found")

class RequirementAnalysisResult(BaseModel):
    """The final result of the AI requirement analysis"""
    overall_score: float = Field(..., ge=0, le=10, description="Quality score from 0 to 10")
    issues: List[AnalysisIssue] = Field(default_factory=list)
    summary: str = Field(..., description="High-level summary of the requirement quality")
    is_ready_for_test_generation: bool = Field(..., description="Whether the requirement is high enough quality to generate tests")

class RequirementAnalysisService:
    """
    Service responsible for analyzing the quality of requirements using AI.
    Detects ambiguity, missing acceptance criteria, and contradictions.
    """

    def __init__(self):
        self.ai_provider = get_ai_provider()

    async def analyze_requirement(self, requirement_text: str, context: Dict[str, Any] = None) -> RequirementAnalysisResult:
        """
        Analyzes a requirement for quality issues.
        """
        system_instruction = (
            "You are an expert Requirements Engineer and QA Lead. Your task is to analyze "
            "software requirements for quality, clarity, and testability. "
            "Look for: \n"
            "1. Ambiguity: Vague terms like 'fast', 'user-friendly', 'efficient'.\n"
            "2. Missing Acceptance Criteria: Lack of clear 'Given/When/Then' or success conditions.\n"
            "3. Contradictions: Requirements that conflict with each other.\n"
            "4. Unverifiability: Requirements that cannot be proven true or false via testing.\n\n"
            "Provide a structured analysis including an overall score (0-10) and a list of specific issues."
        )

        prompt = f"Analyze the following requirement:\n\n{requirement_text}"
        if context:
            prompt += f"\n\nAdditional Context:\n{context}"

        # Use structured data generation to ensure we get a RequirementAnalysisResult
        response = await self.ai_provider.generate_structured_data(
            prompt=prompt,
            system_instruction=system_instruction,
            response_model=RequirementAnalysisResult
        )

        # The AIResponse.content should contain the JSON string or the parsed object 
        # depending on the provider implementation. 
        # For our abstraction, we assume the provider handles the Pydantic parsing 
        # and puts the result in content or metadata.
        # In a real scenario, we'd parse response.content into RequirementAnalysisResult.
        
        # For the Mock provider, it returns a string. We'll handle the conversion here.
        # In production, the AIProvider.generate_structured_data would return the model instance.
        
        import json
        try:
            data = json.loads(response.content)
            return RequirementAnalysisResult(**data)
        except Exception:
            # Fallback for mock or malformed responses
            return RequirementAnalysisResult(
                overall_score=5.0,
                issues=[],
                summary="Analysis failed or returned non-JSON content. Manual review required.",
                is_ready_for_test_generation=False
            )
