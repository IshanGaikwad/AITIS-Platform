"""Selenium Python converter — renders framework-neutral test actions to real Selenium Python code.

This service converts:
  1. Manual test steps (TestCase → TestStep) into Selenium Python (pytest)
  2. Recorded actions (RecordedAction) into Selenium Python
  3. Gherkin scenarios into Selenium Python

The output is production-quality Selenium WebDriver Python code with real commands
(driver.get, driver.find_element, WebDriverWait, expected_conditions, etc.).
"""

import re
from typing import Optional

from app.models.automation import RecordedActionType


# ── Helpers ─────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    """Convert text to a valid Python identifier slug."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")[:60]
    if slug and slug[0].isdigit():
        slug = f"test_{slug}"
    return slug or "unnamed_test"


def _py_escape(s: str) -> str:
    """Escape a string for Python single-quoted string literal."""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")


def _selector_selenium(selector: Optional[str], label: Optional[str] = None) -> tuple[str, str]:
    """Convert a framework-neutral selector to a Selenium (By, value) tuple.

    Returns (by_strategy, value) suitable for driver.find_element(By.X, value).
    """
    if not selector:
        if label:
            return ("By.XPATH", f"//*[contains(text(),'{_py_escape(label)}')]")
        return ("By.TAG_NAME", "body")

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
        "css": ("By.CSS_SELECTOR", value),
        "xpath": ("By.XPATH", value),
        "id": ("By.ID", value),
        "name": ("By.NAME", value),
        "data_testid": ("By.CSS_SELECTOR", f"[data-testid='{value}']"),
        "data-testid": ("By.CSS_SELECTOR", f"[data-testid='{value}']"),
        "text": ("By.XPATH", f"//*[contains(text(),'{_py_escape(value)}')]"),
        "aria": ("By.CSS_SELECTOR", f"[aria-label='{value}']"),
        "label": ("By.CSS_SELECTOR", f"[aria-label='{value}']"),
        "role": ("By.XPATH", f"//*[@role='{value}']"),
    }
    return strategy_map.get(strategy, ("By.CSS_SELECTOR", value))


def _mask_sensitive_py(value: Optional[str], is_sensitive: bool) -> str:
    """Mask sensitive values — replace with env var reference."""
    if not value:
        return "''"
    if is_sensitive:
        return "os.environ.get('SECRET_VALUE', '')"
    return f"'{_py_escape(value)}'"


def _find_element(selector: Optional[str], label: Optional[str] = None, var_name: str = "el") -> str:
    """Generate a Selenium find_element line."""
    by, val = _selector_selenium(selector, label)
    return f"    {var_name} = driver.find_element({by}, '{_py_escape(val)}')"


# ── Selenium Python Renderer ────────────────────────────────────────

class SeleniumRenderer:
    """Renders framework-neutral actions to Selenium Python (pytest) code.

    Generates a complete, runnable pytest test file with:
      - Proper imports (pytest, selenium, WebDriverWait, expected_conditions)
      - Fixture-based driver setup/teardown
      - Real Selenium WebDriver commands
      - Explicit waits for reliability
      - Assertions using pytest
    """

    def __init__(self, base_url: str = "", browser: str = "chrome"):
        self.base_url = base_url
        self.browser = browser

    def render_spec(
        self,
        title: str,
        actions: list,
        preconditions: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> str:
        """Render a complete Selenium Python test file from neutral actions."""
        slug = _slug(title)
        lines: list[str] = []

        # ── File header ───────────────────────────────────────────
        lines.append('"""')
        lines.append(f"Test: {title}")
        if preconditions:
            lines.append(f"Preconditions: {preconditions}")
        if tags:
            lines.append(f"Tags: {', '.join(tags)}")
        lines.append('"""')
        lines.append("")
        lines.append("import os")
        lines.append("import pytest")
        lines.append("from selenium import webdriver")
        lines.append("from selenium.webdriver.common.by import By")
        lines.append("from selenium.webdriver.support.ui import WebDriverWait")
        lines.append("from selenium.webdriver.support import expected_conditions as EC")
        lines.append("from selenium.webdriver.chrome.options import Options")
        lines.append("from selenium.webdriver.chrome.service import Service")
        lines.append("")

        # ── Base URL ──────────────────────────────────────────────
        if self.base_url:
            lines.append(f"BASE_URL = os.environ.get('BASE_URL', '{_py_escape(self.base_url)}')")
        else:
            lines.append("BASE_URL = os.environ.get('BASE_URL', 'http://localhost:3000')")
        lines.append("")

        # ── Fixture ───────────────────────────────────────────────
        lines.append("")
        lines.append("@pytest.fixture(scope='function')")
        lines.append("def driver():")
        lines.append("    \"\"\"Set up and tear down the WebDriver.\"\"\"")
        lines.append("    options = Options()")
        lines.append("    if os.environ.get('HEADLESS', 'true').lower() == 'true':")
        lines.append("        options.add_argument('--headless=new')")
        lines.append("    options.add_argument('--no-sandbox')")
        lines.append("    options.add_argument('--disable-dev-shm-usage')")
        lines.append("    options.add_argument('--window-size=1920,1080')")
        lines.append("")
        lines.append("    driver = webdriver.Chrome(options=options)")
        lines.append("    driver.implicitly_wait(10)")
        lines.append("    yield driver")
        lines.append("    driver.quit()")
        lines.append("")

        # ── Test class ────────────────────────────────────────────
        class_name = f"Test{slug.replace('_', ' ').title().replace(' ', '')}"
        lines.append("")
        lines.append(f"class {class_name}:")
        lines.append(f'    """{title}"""')
        lines.append("")

        # ── Test method ───────────────────────────────────────────
        lines.append(f"    def test_{slug}(self, driver):")
        lines.append(f'        """{title}"""')

        # Navigate first if needed
        first_navigate = next((a for a in actions if getattr(a, "action_type", "") in ("navigate", RecordedActionType.navigate.value)), None)
        if first_navigate and getattr(first_navigate, "url", None):
            url = first_navigate.url
            if url.startswith("http://") or url.startswith("https://"):
                lines.append(f"        driver.get('{_py_escape(url)}')")
            else:
                lines.append(f"        driver.get(f'{{BASE_URL}}{_py_escape(url)}')")
        elif self.base_url:
            lines.append(f"        driver.get(BASE_URL)")

        # Render each action
        for action in actions:
            rendered = self._render_action(action)
            if rendered:
                if getattr(action, "step_comment", None):
                    lines.append(f"        # {action.step_comment}")
                lines.extend(rendered)

        lines.append("")
        return "\n".join(lines)

    def _render_action(self, action) -> list[str]:
        """Render a single neutral action to Selenium Python lines."""
        at = getattr(action, "action_type", "")
        sel = getattr(action, "selector", None)
        label = getattr(action, "label", None)
        val = getattr(action, "value", None)
        is_sensitive = getattr(action, "is_sensitive", False)
        url = getattr(action, "url", None)
        expected = getattr(action, "expected_value", None)
        metadata = getattr(action, "metadata", {}) or {}
        lines: list[str] = []

        if at in (RecordedActionType.navigate.value, "navigate"):
            url = url or "/"
            if url.startswith("http://") or url.startswith("https://"):
                lines.append(f"        driver.get('{_py_escape(url)}')")
            else:
                lines.append(f"        driver.get(f'{{BASE_URL}}{_py_escape(url)}')")

        elif at in (RecordedActionType.click.value, "click"):
            by, val_sel = _selector_selenium(sel, label)
            lines.append(f"        el = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(({by}, '{_py_escape(val_sel)}')))")
            lines.append("        el.click()")

        elif at in (RecordedActionType.fill.value, "fill"):
            by, val_sel = _selector_selenium(sel, label)
            masked = _mask_sensitive_py(val, is_sensitive)
            lines.append(f"        el = WebDriverWait(driver, 10).until(EC.presence_of_element_located(({by}, '{_py_escape(val_sel)}')))")
            lines.append("        el.clear()")
            lines.append(f"        el.send_keys({masked})")

        elif at in (RecordedActionType.select.value, "select"):
            by, val_sel = _selector_selenium(sel, label)
            masked = _mask_sensitive_py(val, is_sensitive)
            lines.append(f"        el = WebDriverWait(driver, 10).until(EC.presence_of_element_located(({by}, '{_py_escape(val_sel)}')))")
            lines.append("        from selenium.webdriver.support.ui import Select")
            lines.append("        Select(el).select_by_visible_text({masked})")

        elif at in (RecordedActionType.assert_text.value, "assert_text"):
            by, val_sel = _selector_selenium(sel, label)
            check = expected or val or ""
            lines.append(f"        el = WebDriverWait(driver, 10).until(EC.presence_of_element_located(({by}, '{_py_escape(val_sel)}')))")
            lines.append(f"        assert '{_py_escape(check)}' in el.text, f'Expected text containing \\\"{_py_escape(check)}\\\"'")

        elif at in (RecordedActionType.assert_visible.value, "assert_visible"):
            by, val_sel = _selector_selenium(sel, label)
            lines.append(f"        el = WebDriverWait(driver, 10).until(EC.visibility_of_element_located(({by}, '{_py_escape(val_sel)}')))")
            lines.append("        assert el.is_displayed()")

        elif at in (RecordedActionType.assert_url.value, "assert_url"):
            check = expected or url or ""
            if check.startswith("http"):
                lines.append(f"        assert driver.current_url == '{_py_escape(check)}'")
            else:
                lines.append(f"        assert driver.current_url == f'{{BASE_URL}}{_py_escape(check)}'")

        elif at in (RecordedActionType.wait.value, "wait"):
            ms = metadata.get("milliseconds", 1000)
            lines.append(f"        import time; time.sleep({ms / 1000})")

        elif at in (RecordedActionType.screenshot.value, "screenshot"):
            path = metadata.get("path", "screenshot.png")
            lines.append(f"        driver.save_screenshot('{_py_escape(path)}')")

        elif at in (RecordedActionType.keyboard.value, "keyboard"):
            if val:
                lines.append(f"        from selenium.webdriver.common.keys import Keys")
                lines.append(f"        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.{val.upper()})")

        elif at in (RecordedActionType.hover.value, "hover"):
            by, val_sel = _selector_selenium(sel, label)
            lines.append(f"        el = driver.find_element({by}, '{_py_escape(val_sel)}')")
            lines.append("        from selenium.webdriver.common.action_chains import ActionChains")
            lines.append("        ActionChains(driver).move_to_element(el).perform()")

        elif at in (RecordedActionType.check.value, "check"):
            by, val_sel = _selector_selenium(sel, label)
            lines.append(f"        el = driver.find_element({by}, '{_py_escape(val_sel)}')")
            lines.append("        if not el.is_selected(): el.click()")

        elif at in (RecordedActionType.uncheck.value, "uncheck"):
            by, val_sel = _selector_selenium(sel, label)
            lines.append(f"        el = driver.find_element({by}, '{_py_escape(val_sel)}')")
            lines.append("        if el.is_selected(): el.click()")

        elif at in (RecordedActionType.upload.value, "upload"):
            by, val_sel = _selector_selenium(sel, label)
            lines.append(f"        el = driver.find_element({by}, '{_py_escape(val_sel)}')")
            lines.append(f"        el.send_keys(os.path.abspath('{_py_escape(val or '')}'))")

        elif at in (RecordedActionType.download.value, "download"):
            lines.append("        # Download handling requires browser-specific configuration")
            lines.append("        # See: https://www.selenium.dev/documentation/webdriver/downloads/")

        else:
            lines.append(f"        # TODO: implement action type '{at}'")

        return lines


# ── Conversion functions ────────────────────────────────────────────

def generate_selenium_spec(
    title: str,
    test_case,
    steps: list,
    base_url: str = "",
) -> dict:
    """Generate a Selenium Python test spec from test case + steps.

    Uses the same NeutralAction pipeline as Playwright, then renders
    through the SeleniumRenderer.
    """
    from app.services.playwright_converter import test_steps_to_actions

    actions = test_steps_to_actions(test_case, steps)
    renderer = SeleniumRenderer(base_url=base_url)
    code = renderer.render_spec(title=title, actions=actions)

    slug = _slug(title)
    file_name = f"test_{slug}.py"

    return {
        "title": title,
        "framework": "selenium",
        "language": "python",
        "file_name": file_name,
        "content": code,
    }


def generate_selenium_from_recorded(
    title: str,
    recorded_actions: list,
    base_url: str = "",
) -> dict:
    """Generate a Selenium Python test spec from recorded actions."""
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

    renderer = SeleniumRenderer(base_url=base_url)
    code = renderer.render_spec(title=title, actions=actions)

    slug = _slug(title)
    file_name = f"test_{slug}.py"

    return {
        "title": title,
        "framework": "selenium",
        "language": "python",
        "file_name": file_name,
        "content": code,
    }