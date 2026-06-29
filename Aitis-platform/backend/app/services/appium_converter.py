"""Appium Converter — Playwright-to-Appium test script converter.

Phase 8: Converts Playwright test scripts to Appium (Java/Python) for
mobile web and native app testing. Supports both Android and iOS targets.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AppiumConversionResult:
    """Result of converting a Playwright script to Appium."""
    code: str
    language: str  # java | python
    platform: str  # android | ios | both
    imports: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    estimated_accuracy: float = 0.0  # 0.0 - 1.0


# ── Playwright → Appium command mappings ────────────────────────────

# Playwright method → (Appium Java, Appium Python, platform hint)
COMMAND_MAP: dict = {
    # Navigation
    "page.goto(": (
        'driver.get("',
        'driver.get("',
        "both",
    ),
    "page.goBack(": (
        "driver.navigate().back();",
        "driver.back()",
        "both",
    ),
    "page.goForward(": (
        "driver.navigate().forward();",
        "driver.forward()",
        "both",
    ),
    "page.reload(": (
        "driver.navigate().refresh();",
        "driver.refresh()",
        "both",
    ),

    # Element finding
    "page.locator(": (
        'driver.findElement(By.',
        'driver.find_element(By.',
        "both",
    ),
    "page.getByRole(": (
        'driver.findElement(By.',
        'driver.find_element(By.',
        "both",
    ),
    "page.getByText(": (
        'driver.findElement(By.',
        'driver.find_element(By.',
        "both",
    ),
    "page.getByLabel(": (
        'driver.findElement(By.',
        'driver.find_element(By.',
        "both",
    ),
    "page.getByPlaceholder(": (
        'driver.findElement(By.',
        'driver.find_element(By.',
        "both",
    ),
    "page.getByTestId(": (
        'driver.findElement(By.',
        'driver.find_element(By.',
        "both",
    ),

    # Interactions
    ".click(": (
        ".click();",
        ".click()",
        "both",
    ),
    ".fill(": (
        ".sendKeys(",
        ".send_keys(",
        "both",
    ),
    ".type(": (
        ".sendKeys(",
        ".send_keys(",
        "both",
    ),
    ".clear(": (
        ".clear();",
        ".clear()",
        "both",
    ),
    ".press(": (
        ".sendKeys(Keys.",
        ".send_keys(Keys.",
        "both",
    ),
    ".check(": (
        ".click(); // check",
        ".click()  # check",
        "both",
    ),
    ".uncheck(": (
        ".click(); // uncheck",
        ".click()  # uncheck",
        "both",
    ),
    ".selectOption(": (
        ".sendKeys(",
        ".send_keys(",
        "both",
    ),
    ".hover(": (
        "// hover: use Actions class",
        "# hover: use ActionChains",
        "both",
    ),
    ".dblclick(": (
        "// doubleClick: use Actions class",
        "# doubleClick: use ActionChains",
        "both",
    ),

    # Mobile-specific gestures
    ".swipe(": (
        "new TouchAction(driver).press(startX, startY).waitAction(Duration.ofMillis(500)).moveTo(endX, endY).release().perform();",
        "TouchAction(driver).press(x=start_x, y=start_y).wait(500).move_to(x=end_x, y=end_y).release().perform()",
        "both",
    ),
    ".scroll(": (
        "driver.findElement(AppiumBy.androidUIAutomator(\"new UiScrollable(new UiSelector()).scrollIntoView(",
        "driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, 'new UiScrollable(new UiSelector()).scrollIntoView(",
        "android",
    ),
    ".pinch(": (
        "// pinch: use MultiTouchAction",
        "# pinch: use MultiAction",
        "both",
    ),
    ".zoom(": (
        "// zoom: use MultiTouchAction",
        "# zoom: use MultiAction",
        "both",
    ),

    # Assertions
    "expect(": (
        "Assert.",
        "assert ",
        "both",
    ),
    ".toBeVisible(": (
        ".isDisplayed()",
        ".is_displayed()",
        "both",
    ),
    ".toBeHidden(": (
        ".isDisplayed() == false",
        "not .is_displayed()",
        "both",
    ),
    ".toBeEnabled(": (
        ".isEnabled()",
        ".is_enabled()",
        "both",
    ),
    ".toHaveText(": (
        ".getText()",
        ".text",
        "both",
    ),
    ".toHaveValue(": (
        ".getAttribute(\"value\")",
        ".get_attribute(\"value\")",
        "both",
    ),
    ".toHaveURL(": (
        ".getCurrentUrl()",
        ".current_url",
        "both",
    ),
    ".toHaveTitle(": (
        ".getTitle()",
        ".title",
        "both",
    ),

    # Waits
    "page.waitForSelector(": (
        "new WebDriverWait(driver, Duration.ofSeconds(10)).until(ExpectedConditions.presenceOfElementLocated(By.",
        "WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.",
        "both",
    ),
    "page.waitForLoadState(": (
        "driver.manage().timeouts().pageLoadTimeout(Duration.ofSeconds(30));",
        "driver.set_page_load_timeout(30)",
        "both",
    ),
    "page.waitForTimeout(": (
        "Thread.sleep(",
        "time.sleep(",
        "both",
    ),
    "page.waitForResponse(": (
        "// waitForResponse: use WebDriverWait with custom ExpectedCondition",
        "# waitForResponse: use WebDriverWait with custom condition",
        "both",
    ),

    # Screenshots
    "page.screenshot(": (
        "TakesScreenshot ts = (TakesScreenshot) driver;\nFile src = ts.getScreenshotAs(OutputType.FILE);",
        "driver.get_screenshot_as_file(",
        "both",
    ),

    # Context/Device
    "context.newPage(": (
        "// newPage: Appium creates one session per test",
        "# newPage: Appium creates one session per test",
        "both",
    ),
    "page.close(": (
        "driver.quit();",
        "driver.quit()",
        "both",
    ),
}


# ── Selector conversion ─────────────────────────────────────────────

def _convert_selector(selector: str, language: str) -> str:
    """Convert a Playwright selector to Appium By locator."""
    # Remove quotes
    sel = selector.strip().strip("'").strip('"').strip("`")

    # CSS selector
    if sel.startswith(".") or sel.startswith("#") or re.match(r'^\w+', sel):
        if language == "java":
            return f'By.cssSelector("{sel}")'
        else:
            return f'By.CSS_SELECTOR, "{sel}"'

    # XPath
    if sel.startswith("//") or sel.startswith("("):
        if language == "java":
            return f'By.xpath("{sel}")'
        else:
            return f'By.XPATH, "{sel}"'

    # Text selector
    if sel.startswith("text="):
        text = sel[5:]
        if language == "java":
            return f'By.xpath("//*[contains(@text, \'{text}\')]")'
        else:
            return f'By.XPATH, "//*[contains(@text, \'{text}\')]"'

    # Accessibility ID
    if sel.startswith("~"):
        aid = sel[1:]
        if language == "java":
            return f'AppiumBy.accessibilityId("{aid}")'
        else:
            return f'AppiumBy.ACCESSIBILITY_ID, "{aid}"'

    # data-testid
    if "data-testid" in sel:
        match = re.search(r'data-testid[=~"\'*^$|]+([^"\'\]\)]+)', sel)
        if match:
            tid = match.group(1).strip('"\'')
            if language == "java":
                return f'AppiumBy.accessibilityId("{tid}")'
            else:
                return f'AppiumBy.ACCESSIBILITY_ID, "{tid}"'

    # Fallback: use as accessibility ID
    if language == "java":
        return f'AppiumBy.accessibilityId("{sel}")'
    else:
        return f'AppiumBy.ACCESSIBILITY_ID, "{sel}"'


# ── Main conversion ─────────────────────────────────────────────────

def convert_to_appium(
    playwright_code: str,
    language: str = "java",
    platform: str = "both",
    test_name: str = "MobileTest",
    package_name: str = "com.example.app",
) -> AppiumConversionResult:
    """Convert a Playwright test script to Appium.

    Args:
        playwright_code: The Playwright test script source.
        language: Target language — 'java' or 'python'.
        platform: Target platform — 'android', 'ios', or 'both'.
        test_name: Name for the generated test class/function.
        package_name: App package name (Android) or bundle ID (iOS).

    Returns:
        AppiumConversionResult with the converted code.
    """
    warnings: List[str] = []
    converted_lines: List[str] = []
    imports: List[str] = []

    # Generate imports
    if language == "java":
        imports = [
            "import io.appium.java_client.AppiumDriver;",
            "import io.appium.java_client.AppiumBy;",
            "import io.appium.java_client.android.AndroidDriver;",
            "import io.appium.java_client.ios.IOSDriver;",
            "import io.appium.java_client.TouchAction;",
            "import io.appium.java_client.touch.WaitOptions;",
            "import io.appium.java_client.touch.offset.PointOption;",
            "import org.openqa.selenium.By;",
            "import org.openqa.selenium.WebElement;",
            "import org.openqa.selenium.remote.DesiredCapabilities;",
            "import org.openqa.selenium.support.ui.ExpectedConditions;",
            "import org.openqa.selenium.support.ui.WebDriverWait;",
            "import org.openqa.selenium.OutputType;",
            "import org.openqa.selenium.TakesScreenshot;",
            "import org.junit.jupiter.api.*;",
            "import org.junit.jupiter.api.Assertions.*;",
            "import java.net.URL;",
            "import java.time.Duration;",
            "import java.io.File;",
            "import java.io.IOException;",
            "import org.apache.commons.io.FileUtils;",
        ]
    else:
        imports = [
            "import pytest",
            "from appium import webdriver",
            "from appium.webdriver.common.appiumby import AppiumBy",
            "from selenium.webdriver.common.by import By",
            "from selenium.webdriver.support.ui import WebDriverWait",
            "from selenium.webdriver.support import expected_conditions as EC",
            "from selenium.webdriver.common.action_chains import ActionChains",
            "from appium.webdriver.common.touch_action import TouchAction",
            "import time",
        ]

    # Build class/function header
    if language == "java":
        converted_lines.append(f"public class {test_name} {{")
        converted_lines.append("    private AppiumDriver driver;")
        converted_lines.append("")
        converted_lines.append("    @BeforeEach")
        converted_lines.append("    public void setUp() throws Exception {")
        converted_lines.append("        DesiredCapabilities caps = new DesiredCapabilities();")
        if platform in ("android", "both"):
            converted_lines.append(f'        caps.setCapability("appPackage", "{package_name}");')
            converted_lines.append('        caps.setCapability("platformName", "Android");')
            converted_lines.append('        caps.setCapability("automationName", "UiAutomator2");')
        if platform in ("ios", "both"):
            converted_lines.append('        caps.setCapability("platformName", "iOS");')
            converted_lines.append('        caps.setCapability("automationName", "XCUITest");')
            converted_lines.append(f'        caps.setCapability("bundleId", "{package_name}");')
        converted_lines.append('        driver = new AndroidDriver<>(new URL("http://localhost:4723/wd/hub"), caps);')
        converted_lines.append("    }")
        converted_lines.append("")
        converted_lines.append("    @Test")
        converted_lines.append(f"    public void {test_name.lower()}() {{")
    else:
        converted_lines.append(f"class {test_name}:")
        converted_lines.append("")
        converted_lines.append("    @pytest.fixture(autouse=True)")
        converted_lines.append("    def setup(self):")
        converted_lines.append("        caps = {")
        if platform in ("android", "both"):
            converted_lines.append(f'            "appPackage": "{package_name}",')
            converted_lines.append('            "platformName": "Android",')
            converted_lines.append('            "automationName": "UiAutomator2",')
        if platform in ("ios", "both"):
            converted_lines.append('            "platformName": "iOS",')
            converted_lines.append('            "automationName": "XCUITest",')
            converted_lines.append(f'            "bundleId": "{package_name}",')
        converted_lines.append("        }")
        converted_lines.append('        self.driver = webdriver.Remote("http://localhost:4723/wd/hub", caps)')
        converted_lines.append("        yield")
        converted_lines.append("        self.driver.quit()")
        converted_lines.append("")
        converted_lines.append(f"    def test_{test_name.lower()}(self):")

    # Process each line
    lines = playwright_code.split("\n")
    conversion_count = 0
    total_commands = 0

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.start("//") or stripped.start("#"):
            continue

        # Skip import lines
        if stripped.startswith("import ") or stripped.startswith("from "):
            continue

        # Skip test/describe wrappers
        if stripped.startswith("test(") or stripped.startswith("describe(") or stripped.startswith("it("):
            continue

        # Skip fixture/beforeEach
        if stripped.startswith("test.beforeEach") or stripped.startswith("beforeEach"):
            continue

        indent = "        " if language == "java" else "        "

        # Try to convert known commands
        converted = False
        for pw_cmd, (java_cmd, py_cmd, plat) in COMMAND_MAP.items():
            if pw_cmd in stripped:
                total_commands += 1
                cmd = java_cmd if language == "java" else py_cmd

                # Handle selector conversion for locator/findElement patterns
                if "locator(" in pw_cmd or "getBy" in pw_cmd:
                    # Extract the selector argument
                    sel_match = re.search(r'\(([^)]+)\)', stripped)
                    if sel_match:
                        sel_arg = sel_match.group(1)
                        converted_sel = _convert_selector(sel_arg, language)
                        if language == "java":
                            cmd = cmd + converted_sel + ")"
                        else:
                            cmd = cmd + converted_sel + ")"
                    else:
                        cmd = cmd + "/* TODO: selector */)"

                # Handle fill/type → sendKeys
                if ".fill(" in stripped or ".type(" in stripped:
                    val_match = re.search(r'\.(?:fill|type)\(([^)]+)\)', stripped)
                    if val_match:
                        val = val_match.group(1).strip().strip("'").strip('"')
                        cmd = cmd + f'"{val}");'

                # Handle assertions
                if "expect(" in stripped:
                    # Convert expect(locator).toBeVisible() → Assert.assertTrue(locator.isDisplayed())
                    exp_match = re.search(r'expect\(([^)]+)\)\.(\w+)\(', stripped)
                    if exp_match:
                        locator = exp_match.group(1)
                        assertion = exp_match.group(2)
                        if language == "java":
                            cmd = f"Assert.{assertion}("
                        else:
                            cmd = f"assert "

                converted_lines.append(f"{indent}{cmd}")
                conversion_count += 1
                converted = True
                break

        if not converted and any(kw in stripped for kw in ["await ", "const ", "let ", "var "]):
            # Skip JS/TS variable declarations
            continue

        if not converted:
            # Keep as comment for manual review
            converted_lines.append(f"{indent}// TODO: {stripped}")
            warnings.append(f"Could not convert: {stripped}")

    # Close method/class
    if language == "java":
        converted_lines.append("    }")
        converted_lines.append("")
        converted_lines.append("    @AfterEach")
        converted_lines.append("    public void tearDown() {")
        converted_lines.append("        if (driver != null) {")
        converted_lines.append("            driver.quit();")
        converted_lines.append("        }")
        converted_lines.append("    }")
        converted_lines.append("}")

    # Calculate accuracy
    accuracy = conversion_count / total_commands if total_commands > 0 else 0.0

    # Add warnings for mobile-specific concerns
    if "page.goto(" in playwright_code:
        warnings.append(
            "page.goto() converted to driver.get(). For native apps, "
            "consider using deep links or app navigation instead."
        )
    if "page.waitForLoadState" in playwright_code:
        warnings.append(
            "waitForLoadState converted to pageLoadTimeout. "
            "For native apps, use WebDriverWait with element presence instead."
        )

    return AppiumConversionResult(
        code="\n".join(converted_lines),
        language=language,
        platform=platform,
        imports=imports,
        warnings=warnings,
        estimated_accuracy=round(accuracy, 2),
    )


def generate_appium_config(
    platform: str = "android",
    app_path: str = "/path/to/app.apk",
    device_name: str = "emulator-5554",
    appium_server: str = "http://localhost:4723/wd/hub",
) -> str:
    """Generate Appium desired capabilities configuration.

    Args:
        platform: 'android' or 'ios'.
        app_path: Path to the app (.apk or .app).
        device_name: Device name or UDID.
        appium_server: Appium server URL.

    Returns:
        JSON configuration string.
    """
    import json

    if platform == "android":
        caps = {
            "platformName": "Android",
            "automationName": "UiAutomator2",
            "deviceName": device_name,
            "app": app_path,
            "appPackage": "com.example.app",
            "appActivity": ".MainActivity",
            "noReset": False,
            "fullReset": False,
            "newCommandTimeout": 300,
        }
    else:
        caps = {
            "platformName": "iOS",
            "automationName": "XCUITest",
            "deviceName": device_name,
            "udid": device_name,
            "app": app_path,
            "bundleId": "com.example.app",
            "noReset": False,
            "fullReset": False,
            "newCommandTimeout": 300,
            "wdaLaunchTimeout": 120000,
        }

    return json.dumps({"server": appium_server, "capabilities": caps}, indent=2)