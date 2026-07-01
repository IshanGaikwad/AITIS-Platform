"""LLM-backed full test-suite generation.

Produces manual test cases, Gherkin scenarios, and framework-specific automation
code from a requirement + acceptance criteria, honoring the requested framework.
Coverage is computed deterministically in Python rather than trusting the LLM.
"""

import json
from typing import Any, Dict, List

from app.services.ai.factory import get_ai_provider
from app.services.test_service import build_coverage_summary

SYSTEM_INSTRUCTION = (
    "You are a senior QA automation engineer. Given a user story and its acceptance "
    "criteria, you generate: (1) comprehensive MANUAL test cases covering the happy path, "
    "negative cases, boundary/edge cases, and security; (2) Gherkin scenarios; and "
    "(3) runnable AUTOMATION code written specifically for the requested framework. "
    "Map every test case to the acceptance-criteria ids it covers. "
    "Respond with a single JSON object and nothing else."
)

_OUTPUT_SHAPE = """Return a JSON object with exactly this shape:
{
  "tests": [
    {
      "id": "TC-001",
      "type": "Happy" | "Negative" | "Boundary" | "Security",
      "title": "string",
      "preconditions": ["string"],
      "steps": ["string", "string"],
      "expectedResult": "string",
      "rationale": "string",
      "coversAcceptanceCriteria": ["AC-1"],
      "priority": "High" | "Medium" | "Low",
      "riskTags": ["string"]
    }
  ],
  "scenarios": [
    { "id": "SC-001", "title": "string", "gherkin": "Feature: ...\\n  Scenario: ...\\n    Given ...\\n    When ...\\n    Then ..." }
  ],
  "automation": [
    { "file_name": "example.spec.ts", "content": "<runnable code for the requested framework>" }
  ]
}"""


def _ac_block(acceptance_criteria: List[str]) -> str:
    if not acceptance_criteria:
        return "(no acceptance criteria provided — infer reasonable ones from the description)"
    return "\n".join(f"AC-{i}: {ac}" for i, ac in enumerate(acceptance_criteria, start=1))


def _user_prompt(story: Dict[str, Any], framework: str, acceptance_criteria: List[str]) -> str:
    return (
        f"Automation framework: {framework}\n\n"
        f"User story title: {story.get('title', '')}\n"
        f"Jira ID: {story.get('jiraId', '') or 'N/A'}\n"
        f"Description: {story.get('description', '') or 'N/A'}\n\n"
        f"Acceptance criteria:\n{_ac_block(acceptance_criteria)}\n\n"
        f"{_OUTPUT_SHAPE}\n\n"
        f"Generate 4-8 manual test cases, 2-4 Gherkin scenarios, and 1-3 automation files "
        f"written specifically for {framework} (use realistic selectors, setup, and assertions "
        f"idiomatic to {framework}). Map each test to the AC ids above. Return JSON only."
    )


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _normalize_tests(raw_tests: Any, base: str) -> List[Dict[str, Any]]:
    tests: List[Dict[str, Any]] = []
    for i, t in enumerate(_as_list(raw_tests), start=1):
        if not isinstance(t, dict):
            continue
        steps = [str(s) for s in _as_list(t.get("steps")) if str(s).strip()]
        tests.append(
            {
                "id": str(t.get("id") or f"{base}-TC-{i:03d}"),
                "type": str(t.get("type") or "Happy"),
                "title": str(t.get("title") or f"Test case {i}"),
                "preconditions": [str(p) for p in _as_list(t.get("preconditions"))],
                "steps": steps or ["Execute the scenario"],
                "expectedResult": str(t.get("expectedResult") or "The expected behavior occurs"),
                "rationale": str(t.get("rationale") or ""),
                "coversAcceptanceCriteria": [str(a) for a in _as_list(t.get("coversAcceptanceCriteria"))],
                "priority": str(t.get("priority") or "Medium"),
                "riskTags": [str(r) for r in _as_list(t.get("riskTags"))],
            }
        )
    return tests


def _normalize_scenarios(raw_scenarios: Any) -> List[Dict[str, Any]]:
    scenarios: List[Dict[str, Any]] = []
    for i, s in enumerate(_as_list(raw_scenarios), start=1):
        if not isinstance(s, dict):
            continue
        gherkin = str(s.get("gherkin") or "").strip()
        if not gherkin:
            continue
        scenarios.append(
            {
                "id": str(s.get("id") or f"SC-{i:03d}"),
                "title": str(s.get("title") or f"Scenario {i}"),
                "gherkin": gherkin,
            }
        )
    return scenarios


def _normalize_automation(raw_automation: Any, framework: str) -> List[Dict[str, Any]]:
    artifacts: List[Dict[str, Any]] = []
    for i, a in enumerate(_as_list(raw_automation), start=1):
        if not isinstance(a, dict):
            continue
        content = str(a.get("content") or "").strip()
        if not content:
            continue
        artifacts.append(
            {
                "id": str(a.get("id") or f"AUTO-{i:03d}"),
                "file_name": str(a.get("file_name") or f"{framework.lower().replace(' ', '_')}_test_{i}.txt"),
                "content": content,
            }
        )
    return artifacts


async def generate_suite(story: Dict[str, Any], framework: str) -> Dict[str, Any]:
    """Generate a full test suite (tests + scenarios + automation + coverage) via the LLM."""
    acceptance_criteria = [str(a) for a in _as_list(story.get("acceptanceCriteria")) if str(a).strip()]
    base = (story.get("jiraId") or story.get("title") or "REQ").upper().replace(" ", "-")[:20]

    provider = get_ai_provider()
    response = await provider.generate_structured_data(
        prompt=_user_prompt(story, framework, acceptance_criteria),
        system_instruction=SYSTEM_INSTRUCTION,
    )

    try:
        data = json.loads(response.content)
    except (json.JSONDecodeError, TypeError):
        data = {}

    tests = _normalize_tests(data.get("tests"), base)
    scenarios = _normalize_scenarios(data.get("scenarios"))
    automation = _normalize_automation(data.get("automation"), framework)
    coverage = build_coverage_summary(tests, len(acceptance_criteria))

    intent = {
        "title": story.get("title", ""),
        "framework": framework,
        "acceptanceCriteriaCount": len(acceptance_criteria),
        "source": "llm",
        "model": response.model_name,
    }

    return {
        "intent": intent,
        "tests": tests,
        "scenarios": scenarios,
        "automation": automation,
        "coverage": coverage,
    }
