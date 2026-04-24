import re
from typing import Any, Dict, List


def adf_to_text(node: Any) -> str:
    """Convert Jira ADF (Atlassian Document Format) to plain text."""
    if not node:
        return ""

    if isinstance(node, str):
        return node

    if isinstance(node, list):
        return "".join(adf_to_text(item) for item in node)

    if not isinstance(node, dict):
        return ""

    node_type = node.get("type")
    content = node.get("content", [])

    if node_type == "text":
        return node.get("text", "")

    if node_type in {"paragraph", "heading"}:
        return adf_to_text(content) + "\n"

    if node_type in {"bulletList", "orderedList"}:
        return "".join(adf_to_text(item) for item in content)

    if node_type == "listItem":
        return "- " + adf_to_text(content)

    return adf_to_text(content)


def normalize_acceptance_criteria(text: str) -> List[str]:
    """Extract likely acceptance criteria from a Jira description."""
    if not text.strip():
        return []

    normalized = text.replace("\r\n", "\n").strip()
    lines = [line.strip() for line in normalized.split("\n")]

    # 1) Look for an explicit Acceptance Criteria section
    ac_heading_index = next(
        (
            idx
            for idx, line in enumerate(lines)
            if re.match(r"^acceptance criteria:?$", line, re.IGNORECASE)
        ),
        -1,
    )

    if ac_heading_index >= 0:
        collected: List[str] = []

        for idx in range(ac_heading_index + 1, len(lines)):
            line = lines[idx].strip()

            if not line:
                if collected:
                    break
                continue

            if line.endswith(":") and collected:
                break

            cleaned = re.sub(r"^\s*[-*•]\s*", "", line)
            cleaned = re.sub(r"^\s*\d+[.)-]?\s*", "", cleaned).strip()

            if cleaned:
                collected.append(cleaned)

        if collected:
            return collected

    # 2) Fallback: pull out bullet/numbered lines anywhere
    candidates: List[str] = []
    for line in lines:
        if re.match(r"^(\d+[.)-]?|[-*•])\s+", line):
            cleaned = re.sub(r"^\s*[-*•]\s*", "", line)
            cleaned = re.sub(r"^\s*\d+[.)-]?\s*", "", cleaned).strip()
            if cleaned:
                candidates.append(cleaned)

    if candidates:
        return candidates

    # 3) Final fallback: split into meaningful sentences
    sentences = [
        sentence.strip().rstrip(".")
        for sentence in re.split(r"\.\s+|\n+", normalized)
        if len(sentence.strip()) > 12
    ]

    return sentences


def jira_issue_to_story_payload(issue: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a Jira issue JSON into your internal Story payload shape."""
    fields = issue.get("fields", {})

    description_raw = fields.get("description")
    description_text = adf_to_text(description_raw).strip()

    acceptance_criteria = normalize_acceptance_criteria(description_text)

    return {
        "jiraId": issue.get("key", ""),
        "title": fields.get("summary", ""),
        "description": description_text,
        "acceptanceCriteria": acceptance_criteria,
        "framework": "Playwright",
    }