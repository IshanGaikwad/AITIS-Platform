
import re
from app.schemas.story import StoryCreate

def generate_intent(story: StoryCreate):
    actor = re.search(r"As a ([^,]+)", story.description)
    goal = re.search(r"I want to (.+?) so that", story.description)
    lower = f"{story.title} {story.description}".lower()

    inputs = [x for x in ["email", "password", "token"] if x in lower]
    rules = []
    if "blank" in lower:
        rules.append("Required fields must not be empty")
    if "invalid" in lower:
        rules.append("Invalid values should be rejected")

    return {
        "actor": actor.group(1) if actor else "User",
        "goal": goal.group(1) if goal else story.title,
        "preconditions": ["User is on the relevant page"],
        "inputs": inputs,
        "businessRules": rules,
        "successOutcome": "Primary action succeeds",
        "failureOutcomes": ["Validation or error message displayed"],
    }
