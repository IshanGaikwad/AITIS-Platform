def to_gherkin(test):
    if isinstance(test, dict):
        title = test.get("title", "Generated scenario")
        preconditions = test.get("preconditions", [])
        steps = test.get("steps", [])
        expected_result = test.get("expectedResult", "Expected result")
    else:
        title = getattr(test, "title", "Generated scenario")
        preconditions = getattr(test, "preconditions", [])
        steps = getattr(test, "steps", [])
        expected_result = getattr(test, "expectedResult", "Expected result")

    given = preconditions[0] if preconditions else "User is on the relevant page"
    when = " and ".join(steps[1:-1]) if len(steps) > 2 else (steps[1] if len(steps) > 1 else "the user performs the action")
    and_step = steps[-1] if steps else "the user submits the action"

    return (
        f"Scenario: {title}\n"
        f"  Given {given}\n"
        f"  When {when}\n"
        f"  And {and_step}\n"
        f"  Then {expected_result}"
    )