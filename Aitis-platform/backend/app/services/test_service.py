import re
from typing import Any, Dict, List, Tuple

from app.schemas.intent import IntentOut
from app.schemas.story import StoryIn


def slugify(text: str) -> str:
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", text.lower()))


def build_base_id(story: StoryIn) -> str:
    return slugify(story.jiraId or story.title).upper()


def classify_acceptance_criterion(ac_text: str) -> str:
    lower = ac_text.lower()

    if any(token in lower for token in ["unauthorized", "forbidden", "permission", "access denied"]):
        return "Security"

    if any(token in lower for token in ["locked", "expired", "inactive", "session", "token", "timeout", "reused"]):
        return "State"

    if any(token in lower for token in ["blank", "empty", "required", "format", "validation"]):
        return "Validation"

    if any(token in lower for token in ["invalid", "error", "cannot", "fail", "denied", "rejected"]):
        return "Negative"

    return "Positive"


def default_preconditions(intent: IntentOut) -> List[str]:
    return intent.preconditions if intent.preconditions else ["User is on the relevant page", "System is available"]


def infer_default_valid_inputs(intent: IntentOut) -> str:
    if not intent.inputs:
        return "valid input data"
    return " and ".join([f"valid {item}" for item in intent.inputs])


def make_test(
    *,
    base_id: str,
    counter: Dict[str, int],
    bucket: str,
    title: str,
    test_type: str,
    preconditions: List[str],
    steps: List[str],
    expected_result: str,
    rationale: str,
    ac_ids: List[str],
    priority: str,
    risk_tags: List[str],
) -> Dict[str, Any]:
    counter[bucket] = counter.get(bucket, 0) + 1
    return {
        "id": f"{base_id}-TC-{bucket}-{counter[bucket]:03d}",
        "type": test_type,
        "title": title,
        "preconditions": preconditions,
        "steps": steps,
        "expectedResult": expected_result,
        "rationale": rationale,
        "coversAcceptanceCriteria": ac_ids,
        "priority": priority,
        "riskTags": risk_tags,
    }


def add_unique_test(container: List[Dict[str, Any]], test: Dict[str, Any], seen_titles: set) -> None:
    key = test["title"].strip().lower()
    if key not in seen_titles:
        seen_titles.add(key)
        container.append(test)


def generate_direct_ac_tests(
    story: StoryIn,
    intent: IntentOut,
    ac_id: str,
    ac_text: str,
    base_id: str,
    counter: Dict[str, int],
) -> List[Dict[str, Any]]:
    tests: List[Dict[str, Any]] = []
    lower = ac_text.lower()
    preconditions = default_preconditions(intent)
    valid_input_phrase = infer_default_valid_inputs(intent)

    classification = classify_acceptance_criterion(ac_text)

    if classification == "Positive":
        tests.append(
            make_test(
                base_id=base_id,
                counter=counter,
                bucket="HP",
                title=f"{story.title} - validate {ac_id.lower()}",
                test_type="Happy",
                preconditions=preconditions,
                steps=[
                    "Navigate to the target page",
                    f"Enter {valid_input_phrase}",
                    "Submit the action",
                ],
                expected_result=ac_text,
                rationale=f"Direct validation for {ac_id}: {ac_text}",
                ac_ids=[ac_id],
                priority="High",
                risk_tags=["Functional", "Happy Path", "AC Direct"],
            )
        )

    elif classification == "Negative":
        if "invalid password" in lower:
            tests.append(
                make_test(
                    base_id=base_id,
                    counter=counter,
                    bucket="NEG",
                    title=f"{story.title} - invalid password",
                    test_type="Negative",
                    preconditions=preconditions,
                    steps=[
                        "Navigate to the target page",
                        "Enter valid email",
                        "Enter invalid password",
                        "Submit the action",
                    ],
                    expected_result=ac_text,
                    rationale=f"Direct negative validation for {ac_id}",
                    ac_ids=[ac_id],
                    priority="High",
                    risk_tags=["Validation", "Negative", "Authentication", "AC Direct"],
                )
            )
        else:
            tests.append(
                make_test(
                    base_id=base_id,
                    counter=counter,
                    bucket="NEG",
                    title=f"{story.title} - negative validation for {ac_id.lower()}",
                    test_type="Negative",
                    preconditions=preconditions,
                    steps=[
                        "Navigate to the target page",
                        "Enter invalid or unsupported input data",
                        "Submit the action",
                    ],
                    expected_result=ac_text,
                    rationale=f"Direct negative validation for {ac_id}: {ac_text}",
                    ac_ids=[ac_id],
                    priority="High",
                    risk_tags=["Negative", "Validation", "AC Direct"],
                )
            )

    elif classification == "Validation":
        if any(token in lower for token in ["blank", "empty", "required"]):
            tests.append(
                make_test(
                    base_id=base_id,
                    counter=counter,
                    bucket="EDGE",
                    title=f"{story.title} - blank required fields",
                    test_type="Edge",
                    preconditions=preconditions,
                    steps=[
                        "Navigate to the target page",
                        "Leave required fields blank",
                        "Submit the action",
                    ],
                    expected_result=ac_text,
                    rationale=f"Blank/required-field validation for {ac_id}",
                    ac_ids=[ac_id],
                    priority="High",
                    risk_tags=["Validation", "Boundary", "Required Fields", "AC Direct"],
                )
            )

        if "format" in lower and ("email" in lower or "email" in [item.lower() for item in intent.inputs]):
            tests.append(
                make_test(
                    base_id=base_id,
                    counter=counter,
                    bucket="EDGE",
                    title=f"{story.title} - invalid email format",
                    test_type="Edge",
                    preconditions=preconditions,
                    steps=[
                        "Navigate to the target page",
                        "Enter an invalid email format",
                        "Enter other required valid fields",
                        "Submit the action",
                    ],
                    expected_result=ac_text,
                    rationale=f"Format validation for {ac_id}",
                    ac_ids=[ac_id],
                    priority="Medium",
                    risk_tags=["Validation", "Format", "Email", "AC Direct"],
                )
            )

    elif classification == "State":
        if "locked" in lower:
            tests.append(
                make_test(
                    base_id=base_id,
                    counter=counter,
                    bucket="STATE",
                    title=f"{story.title} - locked user blocked",
                    test_type="Negative",
                    preconditions=preconditions,
                    steps=[
                        "Navigate to the target page",
                        "Enter credentials for a locked user",
                        "Submit the action",
                    ],
                    expected_result=ac_text,
                    rationale=f"State-based validation for locked account in {ac_id}",
                    ac_ids=[ac_id],
                    priority="High",
                    risk_tags=["State", "Negative", "Authentication", "AC Direct"],
                )
            )
        elif "expired" in lower or "token" in lower:
            tests.append(
                make_test(
                    base_id=base_id,
                    counter=counter,
                    bucket="STATE",
                    title=f"{story.title} - expired token blocked",
                    test_type="Negative",
                    preconditions=preconditions,
                    steps=[
                        "Navigate to the target page or link",
                        "Use an expired or invalid token",
                        "Submit the action",
                    ],
                    expected_result=ac_text,
                    rationale=f"State/token validation for {ac_id}",
                    ac_ids=[ac_id],
                    priority="High",
                    risk_tags=["State", "Token", "Negative", "AC Direct"],
                )
            )
        else:
            tests.append(
                make_test(
                    base_id=base_id,
                    counter=counter,
                    bucket="STATE",
                    title=f"{story.title} - state validation for {ac_id.lower()}",
                    test_type="Negative",
                    preconditions=preconditions,
                    steps=[
                        "Navigate to the target page",
                        "Use data in an invalid state",
                        "Submit the action",
                    ],
                    expected_result=ac_text,
                    rationale=f"State-based validation for {ac_id}",
                    ac_ids=[ac_id],
                    priority="Medium",
                    risk_tags=["State", "Negative", "AC Direct"],
                )
            )

    elif classification == "Security":
        tests.append(
            make_test(
                base_id=base_id,
                counter=counter,
                bucket="SEC",
                title=f"{story.title} - unauthorized access blocked",
                test_type="Security",
                preconditions=preconditions,
                steps=[
                    "Navigate to the protected flow without valid authorization",
                    "Attempt to perform the action",
                ],
                expected_result=ac_text,
                rationale=f"Security validation for {ac_id}",
                ac_ids=[ac_id],
                priority="High",
                risk_tags=["Security", "Authorization", "AC Direct"],
            )
        )

    return tests


def generate_inferred_tests(
    story: StoryIn,
    intent: IntentOut,
    base_id: str,
    counter: Dict[str, int],
    existing_titles: set,
) -> List[Dict[str, Any]]:
    tests: List[Dict[str, Any]] = []
    preconditions = default_preconditions(intent)
    input_set = {item.lower() for item in intent.inputs}

    def add(test: Dict[str, Any]):
        add_unique_test(tests, test, existing_titles)

    # inferred format validation
    if "email" in input_set:
        add(
            make_test(
                base_id=base_id,
                counter=counter,
                bucket="EDGE",
                title=f"{story.title} - invalid email format inferred",
                test_type="Edge",
                preconditions=preconditions,
                steps=[
                    "Navigate to the target page",
                    "Enter an invalid email format",
                    "Enter valid values for all other required fields",
                    "Submit the action",
                ],
                expected_result="Format validation message is displayed and the action is blocked",
                rationale="Inferred email-format validation based on detected input field",
                ac_ids=[],
                priority="Medium",
                risk_tags=["Validation", "Format", "Email", "Inferred"],
            )
        )

    # inferred blank fields
    if intent.inputs:
        add(
            make_test(
                base_id=base_id,
                counter=counter,
                bucket="EDGE",
                title=f"{story.title} - all required fields blank inferred",
                test_type="Edge",
                preconditions=preconditions,
                steps=[
                    "Navigate to the target page",
                    "Leave all required fields blank",
                    "Submit the action",
                ],
                expected_result="Required field validation messages are displayed",
                rationale="Inferred required-field validation based on detected inputs",
                ac_ids=[],
                priority="Medium",
                risk_tags=["Validation", "Boundary", "Required Fields", "Inferred"],
            )
        )

    # inferred whitespace handling
    if "email" in input_set or "password" in input_set:
        add(
            make_test(
                base_id=base_id,
                counter=counter,
                bucket="EDGE",
                title=f"{story.title} - leading or trailing spaces inferred",
                test_type="Edge",
                preconditions=preconditions,
                steps=[
                    "Navigate to the target page",
                    "Enter input values with leading or trailing spaces",
                    "Submit the action",
                ],
                expected_result="System trims or validates spacing correctly according to business rules",
                rationale="Inferred whitespace handling validation",
                ac_ids=[],
                priority="Low",
                risk_tags=["Edge", "Input Handling", "Inferred"],
            )
        )

    return tests


def build_coverage_summary(tests: List[Dict[str, Any]], total_acs: int) -> Dict[str, Any]:
    all_ac_ids = [f"AC-{index}" for index in range(1, total_acs + 1)]

    covered_map: Dict[str, List[str]] = {ac_id: [] for ac_id in all_ac_ids}

    for test in tests:
        for ac_id in test.get("coversAcceptanceCriteria", []):
            covered_map.setdefault(ac_id, []).append(test["id"])

    covered_ac_ids = [ac_id for ac_id, test_ids in covered_map.items() if test_ids]
    uncovered_ac_ids = [ac_id for ac_id in all_ac_ids if ac_id not in covered_ac_ids]

    coverage_percent = 0.0
    if total_acs > 0:
        coverage_percent = round((len(covered_ac_ids) / total_acs) * 100, 2)

    return {
        "totalAcceptanceCriteria": total_acs,
        "coveredAcceptanceCriteria": len(covered_ac_ids),
        "coveragePercent": coverage_percent,
        "uncoveredAcceptanceCriteria": uncovered_ac_ids,
        "mapping": covered_map,
    }


def generate_test_suite(story: StoryIn, intent: IntentOut) -> Dict[str, Any]:
    base_id = build_base_id(story)
    counter: Dict[str, int] = {}
    tests: List[Dict[str, Any]] = []
    seen_titles: set = set()

    # Direct AC-driven generation
    for index, ac_text in enumerate(story.acceptanceCriteria, start=1):
        ac_id = f"AC-{index}"
        direct_tests = generate_direct_ac_tests(
            story=story,
            intent=intent,
            ac_id=ac_id,
            ac_text=ac_text,
            base_id=base_id,
            counter=counter,
        )

        if not direct_tests:
            # fallback generic direct validation if AC didn't match rules
            direct_tests = [
                make_test(
                    base_id=base_id,
                    counter=counter,
                    bucket="HP",
                    title=f"{story.title} - validate {ac_id.lower()}",
                    test_type="Happy",
                    preconditions=default_preconditions(intent),
                    steps=[
                        "Navigate to the target page",
                        f"Enter {infer_default_valid_inputs(intent)}",
                        "Submit the action",
                    ],
                    expected_result=ac_text,
                    rationale=f"Fallback direct validation for {ac_id}",
                    ac_ids=[ac_id],
                    priority="Medium",
                    risk_tags=["Functional", "AC Direct"],
                )
            ]

        for item in direct_tests:
            add_unique_test(tests, item, seen_titles)

    # Inferred extra coverage
    inferred_tests = generate_inferred_tests(
        story=story,
        intent=intent,
        base_id=base_id,
        counter=counter,
        existing_titles=seen_titles,
    )

    tests.extend(inferred_tests)

    coverage = build_coverage_summary(tests, len(story.acceptanceCriteria))

    return {
        "tests": tests,
        "coverage": coverage,
    }


def generate_legacy_tests_only(story: StoryIn, intent: IntentOut) -> List[Dict[str, Any]]:
    return generate_test_suite(story, intent)["tests"]