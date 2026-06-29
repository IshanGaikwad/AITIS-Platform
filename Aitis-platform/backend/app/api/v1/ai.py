from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.core.security import get_current_user
from app.services.ai.analysis_service import RequirementAnalysisService, RequirementAnalysisResult
from app.services.ai.generation_service import TestGenerationService, TestGenerationResult, GeneratedTestCase
from app.services.ai.coverage_service import CoverageService, CoverageAnalysisResult

router = APIRouter(tags=["AI Services"])

# Request Models
class AnalysisRequest(BaseModel):
    requirement_text: str
    context: Optional[Dict[str, Any]] = None

class GenerationRequest(BaseModel):
    requirement_text: str
    acceptance_criteria: List[str]
    context: Optional[Dict[str, Any]] = None

class CoverageRequest(BaseModel):
    acceptance_criteria: List[Dict[str, str]]
    test_cases: List[Dict[str, Any]]

@router.post("/analyze-requirement", response_model=RequirementAnalysisResult)
async def analyze_requirement(request: AnalysisRequest, current_user=Depends(get_current_user)):
    """
    Analyze a requirement for quality, ambiguity, and testability.
    """
    try:
        service = RequirementAnalysisService()
        result = await service.analyze_requirement(
            requirement_text=request.requirement_text,
            context=request.context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Analysis failed: {str(e)}")

@router.post("/generate-tests", response_model=TestGenerationResult)
async def generate_tests(request: GenerationRequest, current_user=Depends(get_current_user)):
    """
    Generate draft manual test cases from a requirement and its ACs.
    """
    try:
        service = TestGenerationService()
        result = await service.generate_tests(
            requirement_text=request.requirement_text,
            acceptance_criteria=request.acceptance_criteria,
            context=request.context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Test Generation failed: {str(e)}")

@router.post("/analyze-coverage", response_model=CoverageAnalysisResult)
async def analyze_coverage(request: CoverageRequest, current_user=Depends(get_current_user)):
    """
    Detect duplicate tests and identify coverage gaps in the test suite.
    """
    try:
        service = CoverageService()
        result = await service.analyze_coverage(
            acceptance_criteria=request.acceptance_criteria,
            test_cases=request.test_cases
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Coverage Analysis failed: {str(e)}")
