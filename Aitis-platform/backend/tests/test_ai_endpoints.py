import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from app.api.routes import router
from app.core.security import get_current_user

# Setup a minimal app for testing AI endpoints
app = FastAPI()
app.include_router(router, prefix="/api")
app.dependency_overrides[get_current_user] = lambda: {
    "sub": "00000000-0000-0000-0000-000000000001",
    "user_id": "00000000-0000-0000-0000-000000000001",
    "organization_id": "00000000-0000-0000-0000-000000000002",
    "workspace_id": "00000000-0000-0000-0000-000000000003",
    "role": "qa_lead",
}

@pytest.fixture
def ai_client():
    """Provides an AsyncClient for the AI endpoints."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

@pytest.mark.asyncio
async def test_analyze_requirement_endpoint(ai_client):
    """Verify /ai/analyze-requirement returns structured analysis."""
    response = await ai_client.post(
        "/api/ai/analyze-requirement",
        json={"requirement_text": "The system shall be fast."},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "overall_score" in data
    assert "issues" in data

@pytest.mark.asyncio
async def test_generate_tests_endpoint(ai_client):
    """Verify /ai/generate-tests returns a list of draft test cases."""
    response = await ai_client.post(
        "/api/ai/generate-tests",
        json={
            "requirement_text": "User must be able to login with valid credentials.",
            "acceptance_criteria": ["Valid credentials redirect to dashboard"],
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "test_cases" in data
    assert len(data["test_cases"]) > 0
    assert data["test_cases"][0]["type"] in ["Positive", "Negative", "Boundary"]

@pytest.mark.asyncio
async def test_analyze_coverage_endpoint(ai_client):
    """Verify /ai/analyze-coverage identifies gaps."""
    response = await ai_client.post(
        "/api/ai/analyze-coverage",
        json={
            "acceptance_criteria": [{"id": "AC-1", "text": "Valid login succeeds"}],
            "test_cases": [{"id": "TC-1", "title": "Valid login"}],
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "coverage_gaps" in data
    assert "duplicates" in data
