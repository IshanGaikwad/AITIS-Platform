"""Robot Framework converter — renders framework-neutral test actions to Robot Framework .robot files.

This service converts:
  1. Manual test steps (TestCase → TestStep) into Robot Framework test suites
  2. Recorded actions (RecordedAction) into Robot Framework test suites
  3. Gherkin scenarios into Robot Framework test suites

The output is production-quality Robot Framework .robot files with:
  - *** Settings *** (Library imports, Suite Setup/Teardown)
  - *** Variables *** (BASE_URL, credentials via env vars)
  - *** Keywords *** (reusable keyword definitions)
  - *** Test Cases *** (test cases with [Tags], [Setup], steps)
"""

import re
from typing import Optional

from app.models.automation import RecordedActionType


# ── Helpers ─────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    """Convert text to a valid Robot Framework test name."""
    slug = re.sub(r"[^a-zA-Z0-9\s]+", "", text).strip()[:80]
    return slug or "Unnamed Test"


def _rf_escape(s: str) -> str:
    """Escape a string for Robot Framework argument."""
    # Robot Framework uses two spaces as separator; escape accordingly
    return s.replace("\\", "\\\\")


def _selector_rf(selector: Optional[str], label: Optional[str] = None) -> str:
    """Convert a framework-neutral selector to a Robot Framework SeleniumLibrary locator.

    Returns a string like: css:div.container  or  xpath://button[@id='submit']
    """
    if not selector:
        if label:
            return f"xpath://*[contains(text(),'{_rf_escape(label)}')]"
        return "css:body"

    if ":" in selector and not selector.startswith("//"):
        strategy, _, value = selector.partition(":")
        strategy = strategy.strip().lower()
        value = value.strip()
    else:
        if selector.startswith("//") or selector.startswith("("):
            strategy, value = "xpath", selector
        elif selector.startswith("#"):
            strategy, value = "id", selector[1:]
        elif selector.startswith("["):
            strategy, value = "css", selector
        else:
            strategy, value = "css", selector

    strategy_map = {
        "css": f"css:{value}",
        "xpath": f"xpath:{value}",
        "id": f"id:{value}",
        "name": f"name:{value}",
        "data_testid": f"css:[data-testid='{value}']",
        "data-testid": f"css:[data-testid='{value}']",
        "text": f"xpath://*[contains(text(),'{_rf_escape(value)}')]",
        "aria": f"css:[aria-label='{value}']",
        "label": f"css:[aria-label='{value}']",
        "role": f"xpath://*[@role='{value}']",
    }
    return strategy_map.get(strategy, f"css:{value}")


def _mask_sensitive_rf(value: Optional[str], is_sensitive: bool) -> str:
    """Mask sensitive values — replace with Robot Framework variable."""
    if not value:
        return "${EMPTY}"
    if is_sensitive:
        return "%{SECRET_VALUE}"
    return value


# ── Robot Framework Renderer ────────────────────────────────────────

class RobotRenderer:
    """Renders framework-neutral actions to Robot Framework .robot files.

    Generates a complete, runnable Robot Framework test suite with:
      - SeleniumLibrary imports
      - Variable definitions
      - Reusable keywords
      - Test cases with proper structure
    """

    def __init__(self, base_url: str = "", browser: str = "chrome"):
        self.base_url = base_url
        self.browser = browser

    def render_suite(
        self,
        title: str,
        actions: list,
        preconditions: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> str:
        """Render a complete Robot Framework .robot test suite from neutral actions."""
        slug = _slug(title)
        lines: list[str] = []

        # ── *** Settings *** ──────────────────────────────────────
        lines.append("*** Settings ***")
        lines.append("Documentation    " + title)
        if preconditions:
            lines.append("...              Preconditions: " + preconditions)
        lines.append("Library          SeleniumLibrary")
        lines.append("Library          OperatingSystem")
        lines.append("Library          Collections")
        lines.append("Suite Setup      Open Browser To Home Page")
        lines.append("Suite Teardown   Close All Browsers")
        lines.append("")

        # ── *** Variables *** ─────────────────────────────────────
        lines.append("*** Variables ***")
        if self.base_url:
            lines.append(f"${{BASE_URL}}    {self.base_url}")
        else:
            lines.append("${BASE_URL}    %{BASE_URL=http://localhost:3000}")
        lines.append(f"${{BROWSER}}     {self.browser}")
        lines.append("${TIMEOUT}      10s")
        lines.append("")

        # ── *** Keywords *** ──────────────────────────────────────
        lines.append("*** Keywords ***")
        lines.append("")
        lines.append("Open Browser To Home Page")
        lines.append(f"    Open Browser    ${{BASE_URL}}    ${{BROWSER}}")
        lines.append("    Maximize Browser Window")
        lines.append("    Set Selenium Timeout    ${TIMEOUT}")
        lines.append("")

        # Generate reusable keywords from action patterns
        self._render_keywords(lines, actions)
        lines.append("")

        # ── *** Test Cases *** ────────────────────────────────────
        lines.append("*** Test Cases ***")
        lines.append("")

        # Main test case
        test_name = slug
        lines.append(test_name)
        if tags:
            tags_str = "    ".join(tags)
            lines.append(f"    [Tags]    {tags_str}")
        lines.append(f"    [Documentation]    {title}")

        # Navigate first if needed
        first_navigate = next((a for a in actions if getattr(a, "action_type", "") in ("navigate", RecordedActionType.navigate.value)), None)
        if first_navigate and getattr(first_navigate, "url", None):
            url = first_navigate.url
            if not url.startswith("http://") and not url.startswith("https://"):
                url = f"${{BASE_URL}}{url}"
            lines.append(f"    Go To    {url}")

        # Render each action
        for action in actions:
            rendered = self._render_action(action)
            if rendered:
                if getattr(action, "step_comment", None):
                    lines.append(f"    # {action.step_comment}")
                lines.extend(rendered)

        lines.append("")
        return "\n".join(lines)

    def _render_keywords(self, lines: list[str], actions: list):
        """Extract reusable keyword patterns from actions."""
        # Group common patterns into keywords
        seen_patterns = set()
        for action in actions:
            at = getattr(action, "action_type", "")
            label = getattr(action, "label", None)
            if at in (RecordedActionType.fill.value, "fill") and label:
                kw_name = f"Fill {label.replace(' ', ' ')}"
                if kw_name not in seen_patterns:
                    seen_patterns.add(kw_name)
                    sel = getattr(action, "selector", None)
                    locator = _selector_rf(sel, label)
                    lines.append(kw_name)
                    lines.append("    [Arguments]    ${value}")
                    lines.append(f"    Input Text    {locator}    ${{value}}")
                    lines.append("")

            elif at in (RecordedActionType.click.value, "click") and label:
                kw_name = f"Click {label.replace(' ', ' ')}"
                if kw_name not in seen_patterns:
                    seen_patterns.add(kw_name)
                    sel = getattr(action, "selector", None)
                    locator = _selector_rf(sel, label)
                    lines.append(kw_name)
                    lines.append(f"    Click Element    {locator}")
                    lines.append("")

    def _render_action(self, action) -> list[str]:
        """Render a single neutral action to Robot Framework lines."""
        at = getattr(action, "action_type", "")
        sel = getattr(action, "selector", None)
        label = getattr(action, "label", None)
        val = getattr(action, "value", None)
        is_sensitive = getattr(action, "is_sensitive", False)
        url = getattr(action, "url", None)
        expected = getattr(action, "expected_value", None)
        metadata = getattr(action, "metadata", {}) or {}
        locator = _selector_rf(sel, label)
        lines: list[str] = []

        if at in (RecordedActionType.navigate.value, "navigate"):
            url = url or "/"
            if url.startswith("http://") or url.startswith("https://"):
                lines.append(f"    Go To    {url}")
            else:
                lines.append(f"    Go To    ${{BASE_URL}}{url}")

        elif at in (RecordedActionType.click.value, "click"):
            lines.append(f"    Wait Until Element Is Visible    {locator}")
            lines.append(f"    Click Element    {locator}")

        elif at in (RecordedActionType.fill.value, "fill"):
            masked = _mask_sensitive_rf(val, is_sensitive)
            lines.append(f"    Wait Until Element Is Visible    {locator}")
            lines.append(f"    Input Text    {locator}    {masked}")

        elif at in (RecordedActionType.select.value, "select"):
            masked = _mask_sensitive_rf(val, is_sensitive)
            lines.append(f"    Wait Until Element Is Visible    {locator}")
            lines.append(f"    Select From List By Label    {locator}    {masked}")

        elif at in (RecordedActionType.assert_text.value, "assert_text"):
            check = expected or val or ""
            lines.append(f"    Wait Until Element Is Visible    {locator}")
            lines.append(f"    Element Should Contain    {locator}    {check}")

        elif at in (RecordedActionType.assert_visible.value, "assert_visible"):
            lines.append(f"    Wait Until Element Is Visible    {locator}")
            lines.append(f"    Element Should Be Visible    {locator}")

        elif at in (RecordedActionType.assert_url.value, "assert_url"):
            check = expected or url or ""
            if check.startswith("http"):
                lines.append(f"    Location Should Be    {check}")
            else:
                lines.append(f"    Location Should Be    ${{BASE_URL}}{check}")

        elif at in (RecordedActionType.wait.value, "wait"):
            ms = metadata.get("milliseconds", 1000)
            lines.append(f"    Sleep    {ms / 1000}s")

        elif at in (RecordedActionType.screenshot.value, "screenshot"):
            path = metadata.get("path", "screenshot.png")
            lines.append(f"    Capture Page Screenshot    {path}")

        elif at in (RecordedActionType.keyboard.value, "keyboard"):
            if val:
                lines.append(f"    Press Keys    None    {val.upper()}")

        elif at in (RecordedActionType.hover.value, "hover"):
            lines.append(f"    Mouse Over    {locator}")

        elif at in (RecordedActionType.check.value, "check"):
            lines.append(f"    Select Checkbox    {locator}")

        elif at in (RecordedActionType.uncheck.value, "uncheck"):
            lines.append(f"    Unselect Checkbox    {locator}")

        elif at in (RecordedActionType.upload.value, "upload"):
            lines.append(f"    Choose File    {locator}    {val or ''}")

        elif at in (RecordedActionType.download.value, "download"):
            lines.append("    # Download handling requires browser-specific configuration")

        else:
            lines.append(f"    # TODO: implement action type '{at}'")

        return lines


# ── Conversion functions ────────────────────────────────────────────

def generate_robot_spec(
    title: str,
    test_case,
    steps: list,
    base_url: str = "",
) -> dict:
    """Generate a Robot Framework .robot test suite from test case + steps.

    Uses the same NeutralAction pipeline as Playwright, then renders
    through the RobotRenderer.
    """
    from app.services.playwright_converter import test_steps_to_actions

    actions = test_steps_to_actions(test_case, steps)
    renderer = RobotRenderer(base_url=base_url)
    code = renderer.render_suite(title=title, actions=actions)

    slug = _slug(title)
    file_name = f"{slug.replace(' ', '_').lower()}.robot"

    return {
        "title": title,
        "framework": "robot",
        "language": "robotframework",
        "file_name": file_name,
        "content": code,
    }


def generate_robot_from_recorded(
    title: str,
    recorded_actions: list,
    base_url: str = "",
) -> dict:
    """Generate a Robot Framework .robot test suite from recorded actions."""
    from app.services.playwright_converter import NeutralAction

    actions = []
    for ra in recorded_actions:
        actions.append(NeutralAction(
            action_type=getattr(ra, "action_type", ""),
            selector=getattr(ra, "selector", None),
            label=getattr(ra, "label", None),
            value=getattr(ra, "value", None),
            is_sensitive=getattr(ra, "is_sensitive", False),
            url=getattr(ra, "url", None),
            expected_value=getattr(ra, "expected_value", None),
            metadata=getattr(ra, "metadata_", None),
        ))

    renderer = RobotRenderer(base_url=base_url)
    code = renderer.render_suite(title=title, actions=actions)

    slug = _slug(title)
    file_name = f"{slug.replace(' ', '_').lower()}.robot"

    return {
        "title": title,
        "framework": "robot",
        "language": "robotframework",
        "file_name": file_name,
        "content": code,
    }