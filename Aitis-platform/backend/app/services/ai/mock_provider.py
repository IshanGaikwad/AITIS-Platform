import asyncio
import json
import random
from typing import Any, Dict, List, Optional
from app.services.ai.base import AIProvider, AIResponse

class MockAIProvider(AIProvider):
    """
    Deterministic Mock AI Provider for testing.
    Returns predictable responses based on keywords in the prompt.
    """
    
    async def generate_text(
        self, 
        prompt: str, 
        system_instruction: str, 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AIResponse:
        # Simulate network latency
        await asyncio.sleep(0.1)
        
        # Deterministic response based on prompt content
        if "ambiguity" in prompt.lower():
            content = "The requirement contains ambiguity regarding the 'user role' definition. Please clarify if this applies to all users or only administrators."
        elif "test case" in prompt.lower():
            content = "Generated Test Case: Verify that the user cannot login with an expired password."
        else:
            content = f"Mock AI response to: {prompt[:50]}..."

        return AIResponse(
            content=content,
            confidence=0.95,
            model_name="mock-gpt-4",
            provider="mock",
            tokens_used=100,
            metadata={"latency_ms": 100}
        )

    async def generate_structured_data(
        self, 
        prompt: str, 
        system_instruction: str, 
        response_model: Any,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None
    ) -> AIResponse:
        await asyncio.sleep(0.1)
        
        # Return deterministic mock data based on the response_model type name
        model_name = getattr(response_model, '__name__', str(response_model))
        
        if model_name == 'RequirementAnalysisResult':
            content = json.dumps({
                "overall_score": 7.5,
                "issues": [
                    {
                        "issue_type": "Ambiguity",
                        "description": "The term 'fast' is subjective and unverifiable",
                        "severity": "High",
                        "suggestion": "Replace 'fast' with a measurable SLA, e.g. 'response under 200ms'",
                        "location": "The system shall be fast"
                    }
                ],
                "summary": "Requirement contains ambiguous terminology that should be quantified.",
                "is_ready_for_test_generation": False
            })
        elif model_name == 'TestGenerationResult':
            content = json.dumps({
                "test_cases": [
                    {
                        "title": "Verify login with valid credentials",
                        "type": "Positive",
                        "priority": "High",
                        "preconditions": ["User account exists", "Application is accessible"],
                        "steps": ["Navigate to login page", "Enter valid username and password", "Click login button"],
                        "expected_result": "User is successfully logged in and redirected to dashboard",
                        "rationale": "Validates the primary happy path for user authentication",
                        "mapped_ac": ["AC-1"]
                    },
                    {
                        "title": "Verify error message for invalid credentials",
                        "type": "Negative",
                        "priority": "High",
                        "preconditions": ["User account exists", "Application is accessible"],
                        "steps": ["Navigate to login page", "Enter valid username and invalid password", "Click login button"],
                        "expected_result": "Error message is displayed indicating invalid credentials",
                        "rationale": "Validates that the system properly rejects invalid authentication attempts",
                        "mapped_ac": ["AC-2"]
                    }
                ],
                "coverage_summary": "2 test cases generated covering valid and invalid login scenarios.",
                "suggestions": ["Add boundary test for maximum password length", "Add security test for SQL injection in login fields"]
            })
        elif model_name == 'CoverageAnalysisResult':
            content = json.dumps({
                "duplicates": [],
                "coverage_gaps": [
                    {
                        "ac_id": "AC-2",
                        "ac_text": "Given invalid credentials, user sees error message",
                        "gap_description": "No test verifies the error message content for invalid credentials",
                        "suggested_test_scenario": "Enter invalid credentials and verify the specific error message displayed"
                    }
                ],
                "overall_coverage_percentage": 50.0,
                "summary": "Partial coverage: valid login is covered, invalid credential error message verification is missing."
            })
        elif model_name == 'DuplicateDetectionResponse':
            content = json.dumps({
                "duplicates": [
                    {
                        "generated_test_title": "Login with valid credentials",
                        "existing_test_id": "TC-1",
                        "similarity_score": 0.95,
                        "reason": "Both tests verify login with valid credentials"
                    }
                ]
            })
        elif model_name == 'StackDetectionResult':
            # No LLM credentials configured — fall back to the heuristic signal line
            # that stack_detection_service embeds in every prompt, rather than
            # fabricating a framework guess we have no basis for.
            signals_line = next(
                (line for line in prompt.splitlines() if line.startswith("Heuristic signals")),
                "Heuristic signals already detected: no strong signature detected",
            )
            detected = signals_line.split(":", 1)[1].strip() if ":" in signals_line else ""
            content = json.dumps({
                "frontend_framework": None,
                "backend_hints": None,
                "language": None,
                "css_framework": None,
                "confidence": 0.2 if detected and detected != "no strong signature detected" else 0.0,
                "summary": f"AI provider not configured — heuristic signals only: {detected}",
                "suggested_application_type": "WEB",
            })
        else:
            content = "{}"
        
        return AIResponse(
            content=content,
            confidence=0.9,
            model_name="mock-gpt-4-structured",
            provider="mock",
            tokens_used=150,
            metadata={"model": model_name}
        )
