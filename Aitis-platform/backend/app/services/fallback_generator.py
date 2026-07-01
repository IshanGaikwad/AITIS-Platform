"""Deterministic fallback test-suite generator (no LLM required).

Produces the same full shape as the LLM path — manual tests, Gherkin scenarios,
and framework-specific automation — using the rule-based test_service plus simple
per-framework code templates. Keeps the platform fully functional without an API key.
"""

from types import SimpleNamespace
from typing import Any, Dict, List

from app.services.test_service import generate_test_suite


def _gherkin_for(test: Dict[str, Any], feature: str) -> str:
    steps = test.get("steps") or []
    when = "\n    And ".join(steps) if steps else "the action is performed"
    given = (test.get("preconditions") or ["the system is ready"])[0]
    return (
        f"Feature: {feature}\n"
        f"  Scenario: {test.get('title', 'Scenario')}\n"
        f"    Given {given}\n"
        f"    When {when}\n"
        f"    Then {test.get('expectedResult', 'the expected result occurs')}"
    )


def _automation_for(framework: str, feature: str, tests: List[Dict[str, Any]]) -> Dict[str, Any]:
    fw = (framework or "playwright").lower()
    titles = [t.get("title", "test") for t in tests][:6]

    if "cypress" in fw:
        body = "\n".join(f"  it('{t}', () => {{\n    // TODO: implement\n  }});" for t in titles)
        return {"file_name": "spec.cy.js", "content": f"describe('{feature}', () => {{\n{body}\n}});"}
    if "selenium" in fw:
        body = "\n".join(f"    def test_{i}(self):\n        # {t}\n        pass" for i, t in enumerate(titles, 1))
        return {
            "file_name": "test_suite.py",
            "content": f"import unittest\nfrom selenium import webdriver\n\n\nclass {feature.title().replace(' ', '')}Tests(unittest.TestCase):\n    def setUp(self):\n        self.driver = webdriver.Chrome()\n\n{body}\n\n    def tearDown(self):\n        self.driver.quit()",
        }
    if "robot" in fw:
        cases = "\n".join(f"{t}\n    Log    TODO: implement" for t in titles)
        return {"file_name": "suite.robot", "content": f"*** Settings ***\nLibrary    SeleniumLibrary\n\n*** Test Cases ***\n{cases}"}
    if "api" in fw:
        body = "\n".join(f"  it('{t}', async () => {{\n    // TODO: call the API and assert\n  }});" for t in titles)
        return {"file_name": "api.test.js", "content": f"const request = require('supertest');\n\ndescribe('{feature} API', () => {{\n{body}\n}});"}

    # Default: Playwright
    body = "\n".join(f"  test('{t}', async ({{ page }}) => {{\n    // TODO: implement\n  }});" for t in titles)
    return {"file_name": "spec.spec.ts", "content": f"import {{ test, expect }} from '@playwright/test';\n\ntest.describe('{feature}', () => {{\n{body}\n}});"}


def generate_suite(story: Dict[str, Any], framework: str) -> Dict[str, Any]:
    """Generate a full suite without an LLM, honoring the target framework."""
    acceptance_criteria = [str(a) for a in (story.get("acceptanceCriteria") or []) if str(a).strip()]
    story_obj = SimpleNamespace(
        title=story.get("title", "") or "Requirement",
        jiraId=story.get("jiraId", "") or "",
        acceptanceCriteria=acceptance_criteria,
    )
    intent_obj = SimpleNamespace(preconditions=[], inputs=[])

    base = generate_test_suite(story_obj, intent_obj)  # {tests, coverage}
    tests = base["tests"]
    feature = story_obj.title

    scenarios = [
        {"id": f"SC-{i:03d}", "title": t.get("title", f"Scenario {i}"), "gherkin": _gherkin_for(t, feature)}
        for i, t in enumerate(tests[:4], start=1)
    ]
    automation = [{"id": "AUTO-001", **_automation_for(framework, feature, tests)}]

    return {
        "intent": {
            "title": feature,
            "framework": framework,
            "acceptanceCriteriaCount": len(acceptance_criteria),
            "source": "heuristic",
        },
        "tests": tests,
        "scenarios": scenarios,
        "automation": automation,
        "coverage": base["coverage"],
    }
