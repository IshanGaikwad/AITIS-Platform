
"""Automation script generation service.

Generates framework-specific test automation code from a requirement + test case pair.
Supports Playwright (TypeScript), Selenium (Python), Cypress (JavaScript), and Robot Framework.

Phase 5: Selenium and Robot Framework now use real code generators (selenium_converter.py,
robot_converter.py) instead of skeleton-only comment generation.
"""

from typing import Optional

from app.services.playwright_converter import (
    generate_playwright_spec,
    generate_playwright_from_steps,
    generate_playwright_from_recorded,
)
from app.services.selenium_converter import (
    generate_selenium_spec,
    generate_selenium_from_recorded,
)
from app.services.robot_converter import (
    generate_robot_spec,
    generate_robot_from_recorded,
)


def _slug(text: str) -> str:
    """Convert text to a valid identifier slug."""
    return "".join(c if c.isalnum() else "_" for c in text).strip("_")[:60]


def generate_playwright(story, test) -> dict:
    """Generate Playwright TypeScript test from requirement + test case.

    Phase 4: Uses the real Playwright TypeScript converter that produces
    actual page.goto(), page.click(), page.fill(), expect() commands —
    not skeleton comments.
    """
    # Extract base_url from story metadata if available
    base_url = getattr(story, "base_url", "") or ""
    if not base_url and hasattr(story, "metadata"):
        meta = getattr(story, "metadata", {}) or {}
        base_url = meta.get("base_url", "")

    # Extract steps from test case
    steps = getattr(test, "steps", []) or []

    return generate_playwright_from_steps(
        title=test.title,
        test_case=test,
        steps=steps,
        base_url=base_url,
    )


def generate_selenium(story, test) -> dict:
    """Generate Selenium Python test from requirement + test case.

    Phase 5: Uses the real Selenium Python converter that produces
    actual driver.get(), driver.find_element(), WebDriverWait, etc.
    """
    base_url = getattr(story, "base_url", "") or ""
    if not base_url and hasattr(story, "metadata"):
        meta = getattr(story, "metadata", {}) or {}
        base_url = meta.get("base_url", "")

    steps = getattr(test, "steps", []) or []
    return generate_selenium_spec(
        title=test.title,
        test_case=test,
        steps=steps,
        base_url=base_url,
    )


def generate_robot(story, test) -> dict:
    """Generate Robot Framework .robot test suite from requirement + test case.

    Phase 5: Uses the real Robot Framework converter that produces
    complete .robot files with Settings, Variables, Keywords, and Test Cases.
    """
    base_url = getattr(story, "base_url", "") or ""
    if not base_url and hasattr(story, "metadata"):
        meta = getattr(story, "metadata", {}) or {}
        base_url = meta.get("base_url", "")

    steps = getattr(test, "steps", []) or []
    return generate_robot_spec(
        title=test.title,
        test_case=test,
        steps=steps,
        base_url=base_url,
    )


def generate_cypress(story, test) -> dict:
    """Generate Cypress JavaScript test from requirement + test case.

    Phase 5: Enhanced Cypress generator with real cy.visit(), cy.get(),
    cy.click(), cy.type(), cy.should() commands.
    """
    test_slug = _slug(test.title)
    file_name = f"{test_slug}.cy.js"

    # Extract base_url
    base_url = getattr(story, "base_url", "") or ""
    if not base_url and hasattr(story, "metadata"):
        meta = getattr(story, "metadata", {}) or {}
        base_url = meta.get("base_url", "")

    step_lines: list[str] = []
    for i, step in enumerate(getattr(test, "steps", []) or []):
        action = getattr(step, "action", None) or (step.get("action") if isinstance(step, dict) else f"Step {i+1}")
        expected = getattr(step, "expectedResult", None) or (step.get("expectedResult") if isinstance(step, dict) else None)
        test_data = getattr(step, "test_data", None) or (step.get("test_data") if isinstance(step, dict) else None)
        selector = test_data.get("selector") if isinstance(test_data, dict) else None
        label = test_data.get("label") if isinstance(test_data, dict) else None

        sel = selector or (f"contains('{label}')" if label else "body")
        step_lines.append(f"    // Step {i+1}: {action}")

        # Heuristic action mapping for Cypress
        action_lower = action.lower()
        if any(kw in action_lower for kw in ("navigate", "go to", "open", "visit")):
            url = test_data.get("url", "/") if isinstance(test_data, dict) else "/"
            step_lines.append(f"    cy.visit('{url}')")
        elif any(kw in action_lower for kw in ("click", "press", "tap")):
            step_lines.append(f"    cy.get('{sel}').click()")
        elif any(kw in action_lower for kw in ("fill", "enter", "type", "input")):
            val = test_data.get("value", "") if isinstance(test_data, dict) else ""
            step_lines.append(f"    cy.get('{sel}').clear().type('{val}')")
        elif any(kw in action_lower for kw in ("select", "choose")):
            val = test_data.get("value", "") if isinstance(test_data, dict) else ""
            step_lines.append(f"    cy.get('{sel}').select('{val}')")
        elif any(kw in action_lower for kw in ("check", "toggle")):
            step_lines.append(f"    cy.get('{sel}').check()")
        elif any(kw in action_lower for kw in ("uncheck", "deselect")):
            step_lines.append(f"    cy.get('{sel}').uncheck()")
        elif any(kw in action_lower for kw in ("visible", "displayed", "shown")):
            step_lines.append(f"    cy.get('{sel}').should('be.visible')")
        elif any(kw in action_lower for kw in ("hover",)):
            step_lines.append(f"    cy.get('{sel}').trigger('mouseover')")
        elif any(kw in action_lower for kw in ("wait",)):
            step_lines.append(f"    cy.wait(1000)")
        elif expected:
            step_lines.append(f"    cy.get('{sel}').should('contain', '{expected}')")
        else:
            step_lines.append(f"    // TODO: implement — {action}")

    steps_block = "\n".join(step_lines) if step_lines else "    // TODO: implement test steps"

    content = f"""describe('{test.title}', () => {{
  beforeEach(() => {{
    cy.visit('{base_url or "/"}')
  }})

  it('{test.title}', () => {{
{steps_block}
  }})
}})
"""
    return {
        "id": test.id.replace("TC", "AUTO") if isinstance(test.id, str) else f"AUTO-{test.id}",
        "title": test.title,
        "framework": "cypress",
        "language": "JavaScript",
        "file_name": file_name,
        "content": content,
    }


def generate_automation(story, test, framework: Optional[str] = None) -> dict:
    """Generate automation script for the given framework.

    Defaults to Playwright if no framework is specified or recognised.
    Phase 5: All frameworks (Playwright, Selenium, Cypress, Robot) use real generators.
    """
    fw = (framework or getattr(story, "framework", None) or "playwright").lower()
    generators = {
        "playwright": generate_playwright,
        "selenium": generate_selenium,
        "cypress": generate_cypress,
        "robot": generate_robot,
        "robotframework": generate_robot,
    }
    generator = generators.get(fw, generate_playwright)
    return generator(story, test)
