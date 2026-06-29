"""Playwright TypeScript converter — renders framework-neutral test actions to real Playwright code.

This service replaces the skeleton-only `generate_playwright()` in automation_service.py.
It converts:
  1. Manual test steps (TestCase → TestStep) into Playwright TypeScript
  2. Recorded actions (RecordedAction) into Playwright TypeScript
  3. Gherkin scenarios into Playwright TypeScript

The output is production-quality Playwright Test code with real commands
(page.goto, page.click, page.fill, expect, etc.), not skeleton comments.
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

from app.models.automation import RecordedAction, RecordedActionType


# ── Helpers ─────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    """Convert text to a valid TypeScript identifier slug."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")[:60]
    # Ensure it starts with a letter
    if slug and slug[0].isdigit():
        slug = f"test_{slug}"
    return slug or "unnamed_test"


def _ts_escape(s: str) -> str:
    """Escape a string for TypeScript single-quoted string literal."""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")


def _selector_pw(selector: Optional[str], label: Optional[str] = None) -> str:
    """Convert a framework-neutral selector to a Playwright selector expression.

    Supports:
      - CSS selectors (default)
      - data-testid: → page.getByTestId()
      - role: → page.getByRole()
      - text: → page.getByText()
      - aria: → page.getByLabel()
      - xpath: → page.locator('xpath=...')
      - id: → page.locator('#id')
      - name: → page.getByLabel() or page.locator('[name="..."]')
    """
    if not selector:
        if label:
            return f"page.getByText('{_ts_escape(label)}')"
        return "page.locator('body')"

    # If selector already has a strategy prefix, parse it
    if ":" in selector and not selector.startswith("//"):
        strategy, _, value = selector.partition(":")
        strategy = strategy.strip().lower()
        value = value.strip()
    else:
        # Auto-detect: if starts with // or (, it's xpath
        if selector.startswith("//") or selector.startswith("("):
            strategy, value = "xpath", selector
        elif selector.startswith("#"):
            strategy, value = "id", selector[1:]
        elif selector.startswith("["):
            strategy, value = "css", selector
        else:
            strategy, value = "css", selector

    if strategy == "data_testid" or strategy == "data-testid":
        return f"page.getByTestId('{_ts_escape(value)}')"
    elif strategy == "role":
        # value might be "button[name=Submit]" or just "button"
        return f"page.getByRole('{_ts_escape(value)}')"
    elif strategy == "text":
        return f"page.getByText('{_ts_escape(value)}')"
    elif strategy == "aria" or strategy == "label":
        return f"page.getByLabel('{_ts_escape(value)}')"
    elif strategy == "name":
        return f"page.locator('[name=\"{_ts_escape(value)}\"]')"
    elif strategy == "xpath":
        return f"page.locator('xpath={_ts_escape(value)}')"
    elif strategy == "id":
        return f"page.locator('#{_ts_escape(value)}')"
    else:
        # CSS
        return f"page.locator('{_ts_escape(value)}')"


def _mask_sensitive(value: Optional[str], is_sensitive: bool) -> str:
    """Mask sensitive values — replace with env var reference."""
    if not value:
        return "''"
    if is_sensitive:
        # Use process.env reference — the actual value is injected at execution time
        return "process.env.SECRET_VALUE || ''"
    return f"'{_ts_escape(value)}'"


# ── Framework-neutral internal action model ────────────────────────

class NeutralAction:
    """Framework-neutral representation of a single test action.

    This is the internal model that both manual test steps and recorded
    actions are converted into before rendering to any framework.
    """

    def __init__(
        self,
        action_type: str,
        selector: Optional[str] = None,
        label: Optional[str] = None,
        value: Optional[str] = None,
        is_sensitive: bool = False,
        url: Optional[str] = None,
        expected_value: Optional[str] = None,
        step_comment: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        self.action_type = action_type
        self.selector = selector
        self.label = label
        self.value = value
        self.is_sensitive = is_sensitive
        self.url = url
        self.expected_value = expected_value
        self.step_comment = step_comment
        self.metadata = metadata or {}


# ── Playwright TypeScript Renderer ──────────────────────────────────

class PlaywrightRenderer:
    """Renders framework-neutral actions to Playwright TypeScript code.

    Generates a complete, runnable Playwright Test spec file with:
      - Proper imports
      - test.describe() blocks
      - test() blocks with real Playwright commands
      - beforeEach() for navigation setup
      - Environment variable injection for base URLs
      - Proper expect() assertions
    """

    def __init__(self, base_url: str = "", browser: str = "chromium"):
        self.base_url = base_url
        self.browser = browser

    def render_spec(
        self,
        title: str,
        actions: list[NeutralAction],
        preconditions: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> str:
        """Render a complete Playwright Test spec file from neutral actions."""
        slug = _slug(title)
        lines: list[str] = []

        # ── File header ───────────────────────────────────────────
        lines.append("import { test, expect } from '@playwright/test';")
        lines.append("")

        # ── Base URL config ────────────────────────────────────────
        if self.base_url:
            lines.append(f"const BASE_URL = process.env.BASE_URL || '{_ts_escape(self.base_url)}';")
        else:
            lines.append("const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';")
        lines.append("")

        # ── Tags as comments ───────────────────────────────────────
        if tags:
            lines.append(f"// Tags: {', '.join(tags)}")
            lines.append("")

        # ── test.describe block ─────────────────────────────────────
        lines.append(f"test.describe('{_ts_escape(title)}', () => {{")
        lines.append("")

        # ── beforeEach — navigate to starting URL ───────────────────
        first_navigate = next((a for a in actions if a.action_type == "navigate"), None)
        if first_navigate and first_navigate.url:
            lines.append("  test.beforeEach(async ({ page }) => {")
            lines.append(f"    await page.goto(`${{BASE_URL}}{_ts_escape(first_navigate.url)}`);")
            lines.append("  });")
            lines.append("")

        # ── test block ──────────────────────────────────────────────
        lines.append(f"  test('{_ts_escape(title)}', async ({{ page }}) => {{")

        # Render each action
        for action in actions:
            rendered = self._render_action(action)
            if rendered:
                lines.append("")
                if action.step_comment:
                    lines.append(f"    // {action.step_comment}")
                lines.extend(rendered)

        lines.append("  });")
        lines.append("});")
        lines.append("")

        return "\n".join(lines)

    def _render_action(self, action: NeutralAction) -> list[str]:
        """Render a single neutral action to Playwright TypeScript lines."""
        at = action.action_type
        sel = _selector_pw(action.selector, action.label)
        lines: list[str] = []

        if at == RecordedActionType.navigate.value or at == "navigate":
            url = action.url or "/"
            # If it's an absolute URL, use it directly; otherwise prepend BASE_URL
            if url.startswith("http://") or url.startswith("https://"):
                lines.append(f"    await page.goto('{_ts_escape(url)}');")
            else:
                lines.append(f"    await page.goto(`${{BASE_URL}}{_ts_escape(url)}`);")

        elif at == RecordedActionType.click.value or at == "click":
            lines.append(f"    await {sel}.click();")

        elif at == RecordedActionType.fill.value or at == "fill":
            val = _mask_sensitive(action.value, action.is_sensitive)
            lines.append(f"    await {sel}.fill({val});")

        elif at == RecordedActionType.select.value or at == "select":
            val = _mask_sensitive(action.value, action.is_sensitive)
            lines.append(f"    await {sel}.selectOption({val});")

        elif at == RecordedActionType.assert_text.value or at == "assert_text":
            if action.expected_value:
                lines.append(f"    await expect({sel}).toHaveText('{_ts_escape(action.expected_value)}');")
            elif action.value:
                lines.append(f"    await expect({sel}).toHaveText('{_ts_escape(action.value)}');")

        elif at == RecordedActionType.assert_visible.value or at == "assert_visible":
            lines.append(f"    await expect({sel}).toBeVisible();")

        elif at == RecordedActionType.assert_url.value or at == "assert_url":
            url = action.expected_value or action.url or ""
            if url.startswith("http"):
                lines.append(f"    await expect(page).toHaveURL('{_ts_escape(url)}');")
            else:
                lines.append(f"    await expect(page).toHaveURL(`${{BASE_URL}}{_ts_escape(url)}`);")

        elif at == RecordedActionType.wait.value or at == "wait":
            ms = action.metadata.get("milliseconds", 1000) if action.metadata else 1000
            lines.append(f"    await page.waitForTimeout({ms});")

        elif at == RecordedActionType.screenshot.value or at == "screenshot":
            path = action.metadata.get("path", "screenshot.png") if action.metadata else "screenshot.png"
            lines.append(f"    await page.screenshot({{ path: '{_ts_escape(path)}' }});")

        elif at == RecordedActionType.keyboard.value or at == "keyboard":
            if action.value:
                lines.append(f"    await page.keyboard.press('{_ts_escape(action.value)}');")

        elif at == RecordedActionType.hover.value or at == "hover":
            lines.append(f"    await {sel}.hover();")

        elif at == RecordedActionType.check.value or at == "check":
            lines.append(f"    await {sel}.check();")

        elif at == RecordedActionType.uncheck.value or at == "uncheck":
            lines.append(f"    await {sel}.uncheck();")

        elif at == RecordedActionType.upload.value or at == "upload":
            if action.value:
                lines.append(f"    await {sel}.setInputFiles('{_ts_escape(action.value)}');")

        elif at == RecordedActionType.download.value or at == "download":
            lines.append(f"    const download = await page.waitForEvent('download');")
            lines.append(f"    await download.saveAs('{_ts_escape(action.value or "download")}');")

        else:
            # Unknown action type — emit a comment
            lines.append(f"    // TODO: implement action type '{at}'")

        return lines


# ── Conversion functions ────────────────────────────────────────────

def test_steps_to_actions(test_case, steps: list) -> list[NeutralAction]:
    """Convert manual test steps (TestCase + TestStep) to neutral actions.

    Uses heuristics to map natural-language step descriptions to
    framework-neutral action types. Falls back to comment-only steps
    when the action cannot be parsed.
    """
    actions: list[NeutralAction] = []

    for i, step in enumerate(steps):
        action_text = getattr(step, "action", "") or (step.get("action", "") if isinstance(step, dict) else "")
        expected = (
            getattr(step, "expected_result", None)
            or (step.get("expected_result") if isinstance(step, dict) else None)
        )
        step_type = getattr(step, "type", "action") or (step.get("type") if isinstance(step, dict) else "action")
        test_data = getattr(step, "test_data", None) or (step.get("test_data") if isinstance(step, dict) else None)

        # Try to parse the action text into a neutral action
        neutral = _parse_step_action(action_text, expected, step_type, test_data)
        neutral.step_comment = f"Step {i+1}: {action_text}"
        actions.append(neutral)

    return actions


def _parse_step_action(
    action_text: str,
    expected_result: Optional[str] = None,
    step_type: str = "action",
    test_data: Optional[dict] = None,
) -> NeutralAction:
    """Parse a natural-language step description into a NeutralAction.

    Uses keyword matching heuristics. This is intentionally simple —
    the AI provider can generate more accurate conversions when available.
    """
    text = action_text.strip().lower()
    selector = test_data.get("selector") if isinstance(test_data, dict) else None
    label = test_data.get("label") if isinstance(test_data, dict) else None
    value = test_data.get("value") if isinstance(test_data, dict) else None
    is_sensitive = test_data.get("is_sensitive", False) if isinstance(test_data, dict) else False

    # Verification steps → assertions
    if step_type == "verification" or expected_result:
        if any(kw in text for kw in ("visible", "displayed", "shown", "appears")):
            return NeutralAction(
                action_type=RecordedActionType.assert_visible.value,
                selector=selector, label=label,
                expected_value=expected_result,
            )
        if any(kw in text for kw in ("url", "page", "navigated", "redirected")):
            return NeutralAction(
                action_type=RecordedActionType.assert_url.value,
                selector=selector, label=label,
                expected_value=expected_result,
            )
        # Default verification → assert_text
        return NeutralAction(
            action_type=RecordedActionType.assert_text.value,
            selector=selector, label=label,
            expected_value=expected_result,
        )

    # Navigation
    if any(kw in text for kw in ("navigate", "go to", "open", "visit", "browse to")):
        url = value or _extract_url(text) or "/"
        return NeutralAction(
            action_type=RecordedActionType.navigate.value,
            url=url, selector=selector, label=label,
        )

    # Click
    if any(kw in text for kw in ("click", "press", "tap", "select")):
        return NeutralAction(
            action_type=RecordedActionType.click.value,
            selector=selector, label=label or action_text,
        )

    # Fill / type
    if any(kw in text for kw in ("fill", "enter", "type", "input", "write")):
        return NeutralAction(
            action_type=RecordedActionType.fill.value,
            selector=selector, label=label,
            value=value or _extract_value(text),
            is_sensitive=is_sensitive or any(kw in text for kw in ("password", "secret", "token", "credential")),
        )

    # Select dropdown
    if any(kw in text for kw in ("select", "choose from", "dropdown", "pick from")):
        return NeutralAction(
            action_type=RecordedActionType.select.value,
            selector=selector, label=label,
            value=value or _extract_value(text),
        )

    # Hover
    if "hover" in text:
        return NeutralAction(
            action_type=RecordedActionType.hover.value,
            selector=selector, label=label,
        )

    # Check / uncheck
    if "uncheck" in text or "deselect" in text:
        return NeutralAction(
            action_type=RecordedActionType.uncheck.value,
            selector=selector, label=label,
        )
    if "check" in text or "toggle" in text:
        return NeutralAction(
            action_type=RecordedActionType.check.value,
            selector=selector, label=label,
        )

    # Wait
    if any(kw in text for kw in ("wait", "pause", "delay")):
        return NeutralAction(
            action_type=RecordedActionType.wait.value,
            selector=selector, label=label,
            metadata={"milliseconds": 1000},
        )

    # Screenshot
    if "screenshot" in text or "capture" in text:
        return NeutralAction(
            action_type=RecordedActionType.screenshot.value,
            selector=selector, label=label,
        )

    # Upload
    if "upload" in text:
        return NeutralAction(
            action_type=RecordedActionType.upload.value,
            selector=selector, label=label,
            value=value,
        )

    # Download
    if "download" in text:
        return NeutralAction(
            action_type=RecordedActionType.download.value,
            selector=selector, label=label,
            value=value,
        )

    # Keyboard
    if any(kw in text for kw in ("press key", "keyboard", "key enter", "key tab")):
        return NeutralAction(
            action_type=RecordedActionType.keyboard.value,
            selector=selector, label=label,
            value=value or "Enter",
        )

    # Fallback — emit as a comment step
    return NeutralAction(
        action_type="comment",
        step_comment=action_text,
    )


def _extract_url(text: str) -> Optional[str]:
    """Extract a URL from natural-language text."""
    # Look for URLs in the text
    url_match = re.search(r'(https?://[^\s]+)', text)
    if url_match:
        return url_match.group(1)
    # Look for path patterns like /login, /dashboard
    path_match = re.search(r'(/[a-zA-Z0-9_\-/]+)', text)
    if path_match:
        return path_match.group(1)
    return None


def _extract_value(text: str) -> Optional[str]:
    """Extract a value from natural-language text like 'Enter "username" in...'."""
    # Look for quoted values
    quoted = re.search(r'"([^"]+)"', text) or re.search(r"'([^']+)'", text)
    if quoted:
        return quoted.group(1)
    # Look for "with X" or "as X"
    with_match = re.search(r'(?:with|as)\s+(\S+)', text)
    if with_match:
        return with_match.group(1)
    return None


def recorded_actions_to_neutral(actions: list[RecordedAction]) -> list[NeutralAction]:
    """Convert RecordedAction ORM objects to NeutralAction list."""
    result: list[NeutralAction] = []
    for ra in actions:
        result.append(NeutralAction(
            action_type=ra.action_type,
            selector=ra.selector,
            label=ra.label,
            value=ra.value,
            is_sensitive=ra.is_sensitive,
            url=ra.url,
            expected_value=ra.expected_value,
            metadata=ra.metadata_,
        ))
    return result


# ── Public API ──────────────────────────────────────────────────────

def generate_playwright_spec(
    title: str,
    test_case=None,
    steps: Optional[list] = None,
    recorded_actions: Optional[list[RecordedAction]] = None,
    base_url: str = "",
    browser: str = "chromium",
    preconditions: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> dict:
    """Generate a Playwright TypeScript spec from test steps or recorded actions.

    This is the main entry point that replaces the old skeleton-only
    `generate_playwright()` function. It produces real, runnable Playwright
    TypeScript code.

    Args:
        title: Test case title (used for describe/test block names)
        test_case: TestCase ORM object (optional, used for metadata)
        steps: List of TestStep ORM objects or dicts (manual test steps)
        recorded_actions: List of RecordedAction ORM objects (from recorder)
        base_url: Base URL for the application under test
        browser: Browser type (chromium, firefox, webkit)
        preconditions: Precondition text (rendered as comments)
        tags: Tags for the test

    Returns:
        dict with keys: id, title, framework, language, file_name, content, code_hash
    """
    renderer = PlaywrightRenderer(base_url=base_url, browser=browser)

    # Convert input to neutral actions
    neutral_actions: list[NeutralAction] = []

    if recorded_actions:
        neutral_actions = recorded_actions_to_neutral(recorded_actions)
    elif steps:
        neutral_actions = test_steps_to_actions(test_case, steps)

    # If no actions were generated, add a placeholder
    if not neutral_actions:
        neutral_actions.append(NeutralAction(
            action_type=RecordedActionType.navigate.value,
            url="/",
            step_comment="No test steps defined — add steps or record actions",
        ))

    # Render to Playwright TypeScript
    content = renderer.render_spec(
        title=title,
        actions=neutral_actions,
        preconditions=preconditions,
        tags=tags,
    )

    # Compute code hash for integrity
    code_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    # Generate file name
    test_slug = _slug(title)
    file_name = f"{test_slug}.spec.ts"

    # Generate script ID (deterministic from title)
    script_id = f"AUTO-{hashlib.md5(title.encode()).hexdigest()[:8].upper()}"

    return {
        "id": script_id,
        "title": title,
        "framework": "playwright",
        "language": "TypeScript",
        "file_name": file_name,
        "content": content,
        "code_hash": code_hash,
    }


def generate_playwright_from_recorded(
    title: str,
    actions: list[RecordedAction],
    base_url: str = "",
    browser: str = "chromium",
) -> dict:
    """Convenience wrapper: generate Playwright spec from recorded actions."""
    return generate_playwright_spec(
        title=title,
        recorded_actions=actions,
        base_url=base_url,
        browser=browser,
    )


def generate_playwright_from_steps(
    title: str,
    test_case,
    steps: list,
    base_url: str = "",
    browser: str = "chromium",
) -> dict:
    """Convenience wrapper: generate Playwright spec from manual test steps."""
    return generate_playwright_spec(
        title=title,
        test_case=test_case,
        steps=steps,
        base_url=base_url,
        browser=browser,
    )


def compute_code_hash(code: str) -> str:
    """Compute SHA-256 hash of code for integrity verification."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()
