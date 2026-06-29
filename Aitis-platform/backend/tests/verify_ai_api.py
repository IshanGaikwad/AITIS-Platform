import asyncio
import httpx
from httpx import ASGITransport
from fastapi import FastAPI
from app.api.routes import router
from app.core.config import settings

# Setup a minimal app for testing AI endpoints
app = FastAPI()
app.include_router(router, prefix="/api")

async def run_test():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("Testing /ai/analyze-requirement...")
        payload = {
            "requirement_text": "The system shall be fast.",
            "context": None
        }
        response = await client.post("/api/ai/analyze-requirement", json=payload)
        print(f"Status: {response.status_code}, Body: {response.json()}")
        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data
        assert "issues" in data
        assert "is_ready_for_test_generation" in data

        print("\nTesting /ai/generate-tests...")
        payload = {
            "requirement_text": "User must be able to login with valid credentials.",
            "acceptance_criteria": [
                "Given valid credentials, user is logged in",
                "Given invalid credentials, user sees error message"
            ],
            "context": None
        }
        response = await client.post("/api/ai/generate-tests", json=payload)
        print(f"Status: {response.status_code}, Body: {response.json()}")
        assert response.status_code == 200
        data = response.json()
        assert "test_cases" in data
        assert "coverage_summary" in data

        print("\nTesting /ai/analyze-coverage...")
        payload = {
            "acceptance_criteria": [
                {"id": "AC-1", "text": "Given valid credentials, user is logged in"},
                {"id": "AC-2", "text": "Given invalid credentials, user sees error message"}
            ],
            "test_cases": [
                {"id": "TC-1", "title": "Login with valid credentials", "steps": "Enter valid username and password, click login"},
                {"id": "TC-2", "title": "Login with invalid password", "steps": "Enter valid username and wrong password, click login"}
            ]
        }
        response = await client.post("/api/ai/analyze-coverage", json=payload)
        print(f"Status: {response.status_code}, Body: {response.json()}")
        assert response.status_code == 200
        data = response.json()
        assert "duplicates" in data
        assert "coverage_gaps" in data
        assert "overall_coverage_percentage" in data

        print("\n✅ All AI endpoints verified successfully!")

if __name__ == "__main__":
    asyncio.run(run_test())
