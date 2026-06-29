"""Failure Classification Service — ML-based failure categorization.

Phase 7: Classifies test failures into categories (element not found,
timeout, assertion failure, network error, etc.) using pattern matching
and heuristics. Provides actionable insights for debugging.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class FailureCategory(str, Enum):
    """Root cause categories for test failures."""
    ELEMENT_NOT_FOUND = "element_not_found"
    TIMEOUT = "timeout"
    ASSERTION_FAILURE = "assertion_failure"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    DATABASE_ERROR = "database_error"
    CONFIGURATION_ERROR = "configuration_error"
    RACE_CONDITION = "race_condition"
    STALE_ELEMENT = "stale_element"
    JAVASCRIPT_ERROR = "javascript_error"
    VISUAL_MISMATCH = "visual_mismatch"
    DATA_VALIDATION = "data_validation"
    ENVIRONMENT_ISSUE = "environment_issue"
    UNKNOWN = "unknown"


@dataclass
class FailureClassification:
    """Result of classifying a test failure."""
    category: FailureCategory
    confidence: float  # 0.0 - 1.0
    explanation: str
    suggested_fix: str
    is_flaky_indicator: bool = False
    matched_patterns: List[str] = field(default_factory=list)


# ── Pattern definitions ─────────────────────────────────────────────

FAILURE_PATTERNS: List[tuple] = [
    # (regex, category, explanation_template, suggested_fix_template, is_flaky)
    (
        r"(?i)(element|selector|locator).*not\s*(found|visible|present|exist)",
        FailureCategory.ELEMENT_NOT_FOUND,
        "The test could not locate a UI element on the page.",
        "Verify the selector is correct. Consider using data-testid attributes. "
        "Add explicit waits (waitForSelector) before interacting with the element.",
        True,
    ),
    (
        r"(?i)(stale\s*element|element\s*is\s*no\s*longer|detached\s*from\s*DOM)",
        FailureCategory.STALE_ELEMENT,
        "The element reference became stale (page re-rendered after the element was found).",
        "Re-query the element before interacting. Use locator-based selectors "
        "instead of element handles. Add waitForLoadState after navigation.",
        True,
    ),
    (
        r"(?i)(timeout|timed?\s*out|exceeded\s*\d+\s*(ms|seconds|s)\s*timeout)",
        FailureCategory.TIMEOUT,
        "The operation exceeded the configured timeout.",
        "Increase the timeout value. Check if the page is loading slowly. "
        "Verify network conditions. Consider using waitForResponse for API-dependent flows.",
        True,
    ),
    (
        r"(?i)(assert|expect|should|assertion).*(failed|error|not\s*equal|not\s*match)",
        FailureCategory.ASSERTION_FAILURE,
        "An assertion/expectation was not met — the actual value differed from expected.",
        "Review the expected value. Check if the test data is correct. "
        "Verify the application behavior matches the specification.",
        False,
    ),
    (
        r"(?i)(network|fetch|request|response|HTTP|status\s*code|ECONNREFUSED|ENOTFOUND|socket|DNS)",
        FailureCategory.NETWORK_ERROR,
        "A network request failed — the server may be unreachable or returned an error.",
        "Check if the target server is running. Verify network connectivity. "
        "Check for CORS issues. Verify API endpoint URLs.",
        True,
    ),
    (
        r"(?i)(auth|login|unauthorized|forbidden|401|403|token|session|credential)",
        FailureCategory.AUTHENTICATION_ERROR,
        "Authentication or authorization failed during the test.",
        "Verify test credentials are valid and not expired. "
        "Check if the auth token/session is being properly set up in test hooks.",
        False,
    ),
    (
        r"(?i)(database|DB|sql|query|connection\s*pool|deadlock|constraint)",
        FailureCategory.DATABASE_ERROR,
        "A database operation failed.",
        "Check database connectivity. Verify test data setup/teardown. "
        "Look for unique constraint violations or deadlocks.",
        False,
    ),
    (
        r"(?i)(config|configuration|env|environment|variable|setting|property).*(missing|invalid|not\s*set|not\s*defined)",
        FailureCategory.CONFIGURATION_ERROR,
        "A required configuration value is missing or invalid.",
        "Check environment variables and configuration files. "
        "Ensure all required settings are defined for the test environment.",
        False,
    ),
    (
        r"(?i)(race\s*condition|concurrent|parallel|interleav|non[- ]deterministic)",
        FailureCategory.RACE_CONDITION,
        "A race condition caused non-deterministic behavior.",
        "Add proper synchronization. Use waitForFunction or polling. "
        "Consider serializing operations that depend on shared state.",
        True,
    ),
    (
        r"(?i)(javascript|JS\s*error|ReferenceError|TypeError|SyntaxError|eval|script)",
        FailureCategory.JAVASCRIPT_ERROR,
        "A JavaScript error occurred in the browser.",
        "Check browser console logs. Verify the application JS is error-free. "
        "Look for unhandled promise rejections or undefined references.",
        False,
    ),
    (
        r"(?i)(visual|screenshot|snapshot|pixel|diff|mismatch|looks\s*different)",
        FailureCategory.VISUAL_MISMATCH,
        "A visual regression was detected — the page looks different from the baseline.",
        "Review the visual diff. Determine if the change is intentional. "
        "Update the baseline screenshot if the change is expected.",
        False,
    ),
    (
        r"(?i)(validation|invalid|format|schema|type\s*error|parse|deserialize)",
        FailureCategory.DATA_VALIDATION,
        "Data validation failed — input/output data did not match expected format.",
        "Check the test data format. Verify API response schema. "
        "Ensure data types match between test and application.",
        False,
    ),
    (
        r"(?i)(environment|deploy|version|build|release|staging|production)",
        FailureCategory.ENVIRONMENT_ISSUE,
        "The test environment may have an issue (wrong version, deployment problem).",
        "Verify the environment is running the expected version. "
        "Check deployment status. Ensure test data is seeded correctly.",
        False,
    ),
]


def classify_failure(
    error_message: str,
    stack_trace: Optional[str] = None,
    test_name: Optional[str] = None,
) -> FailureClassification:
    """Classify a test failure from its error message and stack trace.

    Args:
        error_message: The error message from the test run.
        stack_trace: Optional stack trace for additional context.
        test_name: Optional test name for context.

    Returns:
        FailureClassification with category, confidence, explanation, and suggested fix.
    """
    combined = error_message
    if stack_trace:
        combined += "\n" + stack_trace
    if test_name:
        combined += "\n" + test_name

    best_match: Optional[tuple] = None
    best_score = 0
    matched_patterns: List[str] = []

    for pattern, category, explanation, fix, is_flaky in FAILURE_PATTERNS:
        matches = re.findall(pattern, combined, re.IGNORECASE | re.MULTILINE)
        if matches:
            # Score based on number of matches and pattern specificity
            score = len(matches) * 10 + len(pattern) * 0.1
            if score > best_score:
                best_score = score
                best_match = (category, explanation, fix, is_flaky)
            matched_patterns.append(pattern)

    if best_match:
        category, explanation, fix, is_flaky = best_match
        confidence = min(0.95, 0.5 + best_score * 0.05)
        return FailureClassification(
            category=category,
            confidence=round(confidence, 2),
            explanation=explanation,
            suggested_fix=fix,
            is_flaky_indicator=is_flaky,
            matched_patterns=matched_patterns,
        )

    return FailureClassification(
        category=FailureCategory.UNKNOWN,
        confidence=0.3,
        explanation="Could not automatically classify this failure. Manual review recommended.",
        suggested_fix="Review the full error message and stack trace. "
                      "Check application logs and test execution video/screenshots.",
        is_flaky_indicator=False,
        matched_patterns=[],
    )


def detect_flakiness(
    execution_history: List[dict],
    threshold: float = 0.3,
) -> dict:
    """Detect if a test is flaky based on execution history.

    A test is considered flaky if it has a mix of pass/fail results
    without code changes between runs.

    Args:
        execution_history: List of execution results with at least
            'status' (pass/fail) and 'timestamp' fields.
        threshold: Flakiness threshold (0.0-1.0). A test is flaky if
            its failure rate is between (0, threshold) — i.e., it fails
            sometimes but not always.

    Returns:
        Dict with is_flaky, flakiness_score, failure_rate, and recommendation.
    """
    if len(execution_history) < 3:
        return {
            "is_flaky": False,
            "flakiness_score": 0.0,
            "failure_rate": 0.0,
            "total_runs": len(execution_history),
            "recommendation": "Need at least 3 runs to assess flakiness.",
        }

    total = len(execution_history)
    failures = sum(1 for e in execution_history if e.get("status") in ("failed", "error", "timed_out"))
    failure_rate = failures / total if total > 0 else 0.0

    # Flaky: fails sometimes but not always (failure rate between 0 and threshold)
    is_flaky = 0.0 < failure_rate < threshold

    # Flakiness score: higher when failure rate is close to 0.5 (most unpredictable)
    flakiness_score = 1.0 - abs(failure_rate - 0.5) * 2  # 0 at 0% or 100%, 1 at 50%

    recommendation = ""
    if is_flaky:
        if failure_rate < 0.2:
            recommendation = (
                "Low flakiness — test fails occasionally. Check for timing issues, "
                "network dependencies, or shared state between tests."
            )
        elif failure_rate < 0.4:
            recommendation = (
                "Moderate flakiness — investigate root cause. Common causes: "
                "race conditions, stale selectors, environment variability."
            )
        else:
            recommendation = (
                "High flakiness — test is unreliable. Consider rewriting with "
                "more robust selectors, better waits, and isolated test data."
            )
    elif failure_rate == 0.0:
        recommendation = "Test is consistently passing — no flakiness detected."
    elif failure_rate >= threshold:
        recommendation = "Test is consistently failing — likely a real bug, not flakiness."

    return {
        "is_flaky": is_flaky,
        "flakiness_score": round(flakiness_score, 2),
        "failure_rate": round(failure_rate, 2),
        "total_runs": total,
        "failures": failures,
        "recommendation": recommendation,
    }


def generate_flakiness_report(
    test_results: List[dict],
) -> dict:
    """Generate a flakiness report for a set of test results.

    Args:
        test_results: List of dicts with test_name, status, error_message,
            stack_trace, timestamp.

    Returns:
        Dict with summary, flaky_tests, and recommendations.
    """
    from collections import defaultdict

    # Group by test name
    by_test: dict = defaultdict(list)
    for r in test_results:
        by_test[r.get("test_name", "unknown")].append(r)

    flaky_tests = []
    stable_tests = []
    failing_tests = []

    for test_name, runs in by_test.items():
        flake_result = detect_flakiness(runs)
        if flake_result["is_flaky"]:
            # Classify the most recent failure
            last_failure = next(
                (r for r in reversed(runs) if r.get("status") in ("failed", "error")),
                None,
            )
            classification = None
            if last_failure:
                classification = classify_failure(
                    error_message=last_failure.get("error_message", ""),
                    stack_trace=last_failure.get("stack_trace"),
                    test_name=test_name,
                )

            flaky_tests.append({
                "test_name": test_name,
                "flakiness_score": flake_result["flakiness_score"],
                "failure_rate": flake_result["failure_rate"],
                "total_runs": flake_result["total_runs"],
                "classification": {
                    "category": classification.category.value if classification else "unknown",
                    "confidence": classification.confidence if classification else 0.0,
                    "explanation": classification.explanation if classification else "",
                } if classification else None,
            })
        elif flake_result["failure_rate"] == 0.0:
            stable_tests.append(test_name)
        else:
            failing_tests.append({
                "test_name": test_name,
                "failure_rate": flake_result["failure_rate"],
                "total_runs": flake_result["total_runs"],
            })

    total = len(by_test)
    flaky_count = len(flaky_tests)

    return {
        "summary": {
            "total_tests": total,
            "flaky_tests": flaky_count,
            "stable_tests": len(stable_tests),
            "consistently_failing": len(failing_tests),
            "flakiness_rate": round(flaky_count / total * 100, 1) if total > 0 else 0.0,
        },
        "flaky_tests": sorted(flaky_tests, key=lambda x: x["flakiness_score"], reverse=True),
        "consistently_failing": failing_tests,
        "recommendation": (
            f"{flaky_count} of {total} tests are flaky. "
            "Focus on tests with high flakiness scores first. "
            "Common fixes: use data-testid selectors, add proper waits, isolate test data."
        ) if flaky_count > 0 else "All tests are stable — no flakiness detected.",
    }