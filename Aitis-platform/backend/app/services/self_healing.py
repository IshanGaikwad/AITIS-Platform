"""Self-Healing Service — AI-powered test script healing.

Phase 7: Automatically detects broken selectors in failing tests and
proposes fixes. Generates healing proposals that can be reviewed and
applied by the user.
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from app.services.failure_classifier import (
    FailureCategory,
    classify_failure,
)


@dataclass
class SelectorFix:
    """A proposed fix for a broken selector."""
    original_selector: str
    proposed_selector: str
    selector_type: str  # css, xpath, text, role, testid
    confidence: float
    reasoning: str


@dataclass
class HealingProposal:
    """A complete healing proposal for a failing test script."""
    script_id: str
    original_code: str
    proposed_code: str
    changes: List[SelectorFix]
    explanation: str
    confidence_score: float
    failure_category: FailureCategory


# ── Selector healing strategies ─────────────────────────────────────

def _heal_css_selector(selector: str, page_context: Optional[str] = None) -> List[SelectorFix]:
    """Generate alternative CSS selectors for a broken selector."""
    fixes = []

    # Strategy 1: Convert class-based to data-testid
    if re.match(r'^\.\w+', selector) or re.match(r'^\w+\.\w+', selector):
        # Suggest data-testid based on class name
        class_names = re.findall(r'\.([\w-]+)', selector)
        if class_names:
            testid = class_names[0].replace('--', '-').replace('__', '-')
            fixes.append(SelectorFix(
                original_selector=selector,
                proposed_selector=f'[data-testid="{testid}"]',
                selector_type="testid",
                confidence=0.7,
                reasoning=f"Class-based selectors are fragile. Using data-testid based on class '{class_names[0]}'.",
            ))

    # Strategy 2: Convert complex CSS to simpler form
    if '>' in selector or selector.count(' ') > 2:
        # Extract the last part of a complex selector
        parts = re.split(r'\s+>?\s*', selector)
        if len(parts) > 1:
            last_part = parts[-1]
            fixes.append(SelectorFix(
                original_selector=selector,
                proposed_selector=last_part,
                selector_type="css",
                confidence=0.5,
                reasoning="Simplified complex selector to its last component. May need refinement.",
            ))

    # Strategy 3: Add text-based fallback
    if 'button' in selector.lower() or 'btn' in selector.lower():
        fixes.append(SelectorFix(
            original_selector=selector,
            proposed_selector=f'button:has-text("{selector}")',
            selector_type="text",
            confidence=0.4,
            reasoning="Added text-based fallback for button selector.",
        ))

    return fixes


def _heal_xpath_selector(selector: str, page_context: Optional[str] = None) -> List[SelectorFix]:
    """Generate alternative selectors for a broken XPath."""
    fixes = []

    # Strategy 1: Convert XPath to CSS
    if selector.startswith('//'):
        # Simple XPath to CSS conversion
        css = selector
        css = re.sub(r'//(\w+)', r'\1', css)
        css = re.sub(r'\[@(\w+)="([^"]*)"\]', r'[\1="\2"]', css)
        css = re.sub(r'/\[', ' > [', css)
        css = re.sub(r'/(\w+)', r' > \1', css)

        if css != selector:
            fixes.append(SelectorFix(
                original_selector=selector,
                proposed_selector=css,
                selector_type="css",
                confidence=0.6,
                reasoning="Converted XPath to equivalent CSS selector. CSS selectors are generally more robust.",
            ))

    # Strategy 2: Suggest text-based selector
    text_match = re.search(r'text\(\)\s*=\s*["\']([^"\']+)["\']', selector)
    if text_match:
        text = text_match.group(1)
        fixes.append(SelectorFix(
            original_selector=selector,
            proposed_selector=f'text="{text}"',
            selector_type="text",
            confidence=0.8,
            reasoning=f"Using Playwright text selector for element containing '{text}'.",
        ))

    return fixes


def _heal_role_selector(selector: str, page_context: Optional[str] = None) -> List[SelectorFix]:
    """Generate alternatives for role-based selectors."""
    fixes = []

    # Extract role and name
    role_match = re.match(r'role=(\w+)\[name="([^"]*)"\]', selector)
    if role_match:
        role, name = role_match.group(1), role_match.group(2)
        # Suggest getByRole equivalent
        fixes.append(SelectorFix(
            original_selector=selector,
            proposed_selector=f'getByRole("{role}", {{ name: "{name}" }})',
            selector_type="role",
            confidence=0.9,
            reasoning="Using Playwright getByRole API for better accessibility-based selection.",
        ))

    return fixes


def heal_selector(
    selector: str,
    error_message: str,
    page_context: Optional[str] = None,
) -> List[SelectorFix]:
    """Generate healing proposals for a broken selector.

    Args:
        selector: The original selector that failed.
        error_message: The error message from the test failure.
        page_context: Optional page HTML/text context for smarter healing.

    Returns:
        List of SelectorFix proposals, sorted by confidence descending.
    """
    all_fixes: List[SelectorFix] = []

    # Determine selector type
    if selector.startswith('//') or selector.startswith('('):
        all_fixes.extend(_heal_xpath_selector(selector, page_context))
    elif selector.startswith('role='):
        all_fixes.extend(_heal_role_selector(selector, page_context))
    else:
        all_fixes.extend(_heal_css_selector(selector, page_context))

    # Generic fallback: suggest text-based selector if error mentions text
    if not all_fixes and re.search(r'(?i)text|label|content', error_message):
        all_fixes.append(SelectorFix(
            original_selector=selector,
            proposed_selector=f'text=',
            selector_type="text",
            confidence=0.3,
            reasoning="Consider using a text-based selector. Replace with actual visible text.",
        ))

    # Sort by confidence descending
    all_fixes.sort(key=lambda f: f.confidence, reverse=True)
    return all_fixes


def generate_healing_proposal(
    script_code: str,
    error_message: str,
    stack_trace: Optional[str] = None,
    script_id: Optional[str] = None,
) -> Optional[HealingProposal]:
    """Generate a complete healing proposal for a failing test script.

    Analyzes the error, finds the likely broken selector in the code,
    and proposes fixes.

    Args:
        script_code: The full test script source code.
        error_message: The error message from the test failure.
        stack_trace: Optional stack trace.
        script_id: Optional script ID for tracking.

    Returns:
        HealingProposal if fixes could be generated, None otherwise.
    """
    # Classify the failure
    classification = classify_failure(error_message, stack_trace)

    # Only attempt healing for element/selector-related failures
    healable_categories = {
        FailureCategory.ELEMENT_NOT_FOUND,
        FailureCategory.STALE_ELEMENT,
        FailureCategory.TIMEOUT,
    }
    if classification.category not in healable_categories:
        return None

    # Extract selectors from the error message
    selector_patterns = [
        r'(?i)selector[:\s]+["\']([^"\']+)["\']',
        r'(?i)locator[:\s]+["\']([^"\']+)["\']',
        r'(?i)waiting for (.+?) (?:to be|failed)',
        r'(?i)\.(?:locator|waitForSelector|fill|click|type)\(["\']([^"\']+)["\']',
    ]

    broken_selector = None
    for pattern in selector_patterns:
        match = re.search(pattern, error_message)
        if match:
            broken_selector = match.group(1)
            break

    # If not in error, try to find in stack trace
    if not broken_selector and stack_trace:
        for pattern in selector_patterns:
            match = re.search(pattern, stack_trace)
            if match:
                broken_selector = match.group(1)
                break

    if not broken_selector:
        return None

    # Generate fixes for the broken selector
    fixes = heal_selector(broken_selector, error_message)

    if not fixes:
        return None

    # Apply the best fix to the code
    best_fix = fixes[0]
    proposed_code = script_code.replace(broken_selector, best_fix.proposed_selector)

    # Calculate overall confidence
    avg_confidence = sum(f.confidence for f in fixes) / len(fixes)

    return HealingProposal(
        script_id=script_id or str(uuid.uuid4()),
        original_code=script_code,
        proposed_code=proposed_code,
        changes=fixes,
        explanation=(
            f"Detected {classification.category.value}: {classification.explanation}\n"
            f"Best fix: {best_fix.reasoning}"
        ),
        confidence_score=round(avg_confidence, 2),
        failure_category=classification.category,
    )


def apply_healing(
    script_code: str,
    fixes: List[SelectorFix],
    auto_apply: bool = False,
) -> str:
    """Apply healing fixes to a script.

    Args:
        script_code: The original script code.
        fixes: List of selector fixes to apply.
        auto_apply: If True, apply all fixes. If False, apply only high-confidence fixes.

    Returns:
        The healed script code.
    """
    result = script_code
    for fix in fixes:
        if auto_apply or fix.confidence >= 0.7:
            if fix.original_selector in result:
                result = result.replace(fix.original_selector, fix.proposed_selector)
    return result