"""Pydantic schemas for test case generation — AI pipeline output models.

These are NOT database models — they represent the output of the AI test
generation pipeline (test_service.py). They use string IDs (e.g. "TC-HP-001")
because they are generated artifacts, not persisted entities.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _split_preconditions(value):
    """The DB stores preconditions as newline-joined text; expose it as a list."""
    if isinstance(value, str):
        return [line for line in value.splitlines() if line.strip()]
    return value


# ═══════════════════════════════════════════════════════════════════════
# AI Pipeline Output Schemas (non-persisted)
# ═══════════════════════════════════════════════════════════════════════

class TestCasePipelineOut(BaseModel):
    id: str
    type: str
    title: str
    preconditions: List[str]
    steps: List[str]
    expectedResult: str
    rationale: str
    coversAcceptanceCriteria: List[str] = Field(default_factory=list)
    priority: str = "Medium"
    riskTags: List[str] = Field(default_factory=list)


class CoverageSummary(BaseModel):
    totalAcceptanceCriteria: int
    coveredAcceptanceCriteria: int
    coveragePercent: float
    uncoveredAcceptanceCriteria: List[str] = Field(default_factory=list)
    mapping: Dict[str, List[str]] = Field(default_factory=dict)


class TestGenerationResponse(BaseModel):
    tests: List[TestCasePipelineOut]
    coverage: CoverageSummary


# ── Full LLM generation (manual + automation, framework-aware) ──
class StoryGenerateRequest(BaseModel):
    """Bare requirement the frontend posts to /api/tests/generate."""
    jiraId: str = ""
    title: str = Field(..., min_length=1)
    description: str = ""
    acceptanceCriteria: List[str] = Field(default_factory=list)
    framework: str = "Playwright"


class ScenarioOut(BaseModel):
    id: str
    title: str
    gherkin: str


class AutomationArtifactOut(BaseModel):
    id: str
    file_name: str
    content: str


class FullGenerationResponse(BaseModel):
    intent: Dict[str, object] = Field(default_factory=dict)
    tests: List[TestCasePipelineOut] = Field(default_factory=list)
    scenarios: List[ScenarioOut] = Field(default_factory=list)
    automation: List[AutomationArtifactOut] = Field(default_factory=list)
    coverage: CoverageSummary


# ═══════════════════════════════════════════════════════════════════════
# Test Suite Folder Schemas
# ═══════════════════════════════════════════════════════════════════════

class TestSuiteFolderCreate(BaseModel):
    workspace_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    sort_order: int = 0
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None


class TestSuiteFolderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    sort_order: Optional[int] = None


class TestSuiteFolderOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    name: str
    description: Optional[str] = None
    sort_order: int
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    children: List["TestSuiteFolderOut"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════
# Test Suite Schemas (Phase 2 expanded)
# ═══════════════════════════════════════════════════════════════════════

class TestSuiteCreate(BaseModel):
    workspace_id: uuid.UUID
    requirement_id: Optional[uuid.UUID] = None
    folder_id: Optional[uuid.UUID] = None
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    type: str = Field("manual", description="manual | automated | bdd")
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None


class TestSuiteUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    folder_id: Optional[uuid.UUID] = None


class TestSuiteOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    requirement_id: Optional[uuid.UUID] = None
    folder_id: Optional[uuid.UUID] = None
    name: str
    description: Optional[str] = None
    type: str
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════
# Test Step Schemas
# ═══════════════════════════════════════════════════════════════════════

class TestStepCreate(BaseModel):
    order: int = 0
    type: str = Field("action", description="action | expected | precondition | cleanup")
    action: str = Field(..., min_length=1)
    expected_result: Optional[str] = None
    description: Optional[str] = None
    test_data: Optional[dict] = None


class TestStepUpdate(BaseModel):
    order: Optional[int] = None
    type: Optional[str] = None
    action: Optional[str] = None
    expected_result: Optional[str] = None
    description: Optional[str] = None
    test_data: Optional[dict] = None


class TestStepOut(BaseModel):
    id: uuid.UUID
    test_case_id: uuid.UUID
    order: int
    type: str
    action: str
    expected_result: Optional[str] = None
    description: Optional[str] = None
    test_data: Optional[dict] = None
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════
# Test Case Schemas (Phase 2 expanded)
# ═══════════════════════════════════════════════════════════════════════

class TestCaseCreate(BaseModel):
    test_suite_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    type: str = Field("manual", description="manual | automated | bdd")
    priority: str = Field("medium", description="critical | high | medium | low")
    status: str = Field("draft", description="draft | ready | deprecated")
    preconditions: Optional[List[str]] = None
    gherkin: Optional[str] = None
    tags: Optional[List[str]] = None
    requirement_ids: Optional[List[uuid.UUID]] = None
    owner_id: Optional[uuid.UUID] = None
    review_status: str = Field("pending", description="pending | approved | changes_requested")
    steps: Optional[List[TestStepCreate]] = None
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None


class TestCaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    preconditions: Optional[List[str]] = None
    gherkin: Optional[str] = None
    tags: Optional[List[str]] = None
    requirement_ids: Optional[List[uuid.UUID]] = None
    owner_id: Optional[uuid.UUID] = None
    review_status: Optional[str] = None
    change_summary: Optional[str] = Field(None, description="Brief description of what changed")


class TestCaseOut(BaseModel):
    _split_pc = field_validator("preconditions", mode="before")(_split_preconditions)

    id: uuid.UUID
    test_suite_id: uuid.UUID
    title: str
    slug: str
    description: Optional[str] = None
    type: str
    priority: str
    status: str
    review_status: str
    version: int
    preconditions: Optional[List[str]] = None
    gherkin: Optional[str] = None
    tags: Optional[List[str]] = None
    requirement_ids: Optional[List[uuid.UUID]] = None
    owner_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    steps: List[TestStepOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TestCaseBulkUpdate(BaseModel):
    """Bulk update multiple test cases with the same changes."""
    ids: List[uuid.UUID]
    priority: Optional[str] = None
    status: Optional[str] = None
    review_status: Optional[str] = None
    owner_id: Optional[uuid.UUID] = None
    tags: Optional[List[str]] = None
    add_tags: Optional[List[str]] = None
    remove_tags: Optional[List[str]] = None


class TestCaseClone(BaseModel):
    """Clone a test case into a target suite."""
    target_suite_id: uuid.UUID
    new_title: Optional[str] = None
    copy_steps: bool = True


# ═══════════════════════════════════════════════════════════════════════
# Test Case Version Schemas
# ═══════════════════════════════════════════════════════════════════════

class TestCaseVersionOut(BaseModel):
    id: uuid.UUID
    test_case_id: uuid.UUID
    version: int
    title: str
    description: Optional[str] = None
    type: str
    priority: str
    status: str
    preconditions: Optional[str] = None
    gherkin: Optional[str] = None
    tags: Optional[list] = None
    requirement_ids: Optional[list] = None
    steps_snapshot: Optional[list] = None
    changed_by: Optional[uuid.UUID] = None
    change_summary: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════
# Test Execution Schemas (Phase 2 — manual execution)
# ═══════════════════════════════════════════════════════════════════════

class TestExecutionCreate(BaseModel):
    test_suite_id: uuid.UUID
    environment: Optional[str] = None
    environment_id: Optional[uuid.UUID] = Field(
        None, description="Resolved to the Environment's base_url for automated runs"
    )
    execution_type: str = Field("manual", description="manual | automated")
    notes: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None


class TestExecutionUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    environment: Optional[str] = None


class TestExecutionOut(BaseModel):
    id: uuid.UUID
    test_suite_id: uuid.UUID
    environment: Optional[str] = None
    execution_type: str
    status: str
    executed_by: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    summary: Optional[dict] = None
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Enriched for list/UI display (populated by the list-all endpoint)
    test_suite_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════
# Test Case Execution Schemas
# ═══════════════════════════════════════════════════════════════════════

class TestCaseExecutionOut(BaseModel):
    id: uuid.UUID
    execution_id: uuid.UUID
    test_case_id: uuid.UUID
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    artifacts: Optional[dict] = None
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    step_executions: List["StepExecutionOut"] = Field(default_factory=list)
    # Enriched test case details for UI display
    test_case_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════
# Step Execution Schemas (manual result recording)
# ═══════════════════════════════════════════════════════════════════════

class StepExecutionUpdate(BaseModel):
    """Record the result of a single step during manual execution."""
    status: str = Field(..., description="passed | failed | blocked | skipped")
    actual_result: Optional[str] = None
    comment: Optional[str] = None
    screenshot_url: Optional[str] = None


class StepExecutionOut(BaseModel):
    id: uuid.UUID
    case_execution_id: uuid.UUID
    step_id: uuid.UUID
    status: str
    actual_result: Optional[str] = None
    comment: Optional[str] = None
    screenshot_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Enriched step details for UI display
    step_action: Optional[str] = None
    step_expected_result: Optional[str] = None
    step_order: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════
# Defect Draft Schemas
# ═══════════════════════════════════════════════════════════════════════

class DefectDraftCreate(BaseModel):
    """Create a defect draft from a failed step execution."""
    case_execution_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    severity: str = Field("medium", description="critical | high | medium | low")
    steps_to_reproduce: Optional[str] = None
    environment: Optional[str] = None
    labels: Optional[List[str]] = None
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None


class DefectDraftOut(BaseModel):
    id: uuid.UUID
    case_execution_id: uuid.UUID
    external_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    severity: str
    status: str
    steps_to_reproduce: Optional[str] = None
    environment: Optional[str] = None
    labels: Optional[list] = None
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════
# CSV Import/Export Schemas
# ═══════════════════════════════════════════════════════════════════════

class CSVImportResult(BaseModel):
    total_rows: int
    imported: int
    skipped: int
    errors: List[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
# Requirement Coverage Schemas
# ═══════════════════════════════════════════════════════════════════════

class RequirementCoverageItem(BaseModel):
    requirement_id: uuid.UUID
    requirement_title: Optional[str] = None
    test_case_count: int
    covered: bool
    test_cases: List[dict] = Field(default_factory=list)


class RequirementCoverageReport(BaseModel):
    workspace_id: uuid.UUID
    total_requirements: int
    covered_requirements: int
    coverage_percent: float
    items: List[RequirementCoverageItem] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
# Legacy DB schemas (kept for backward compat)
# ═══════════════════════════════════════════════════════════════════════

class TestCaseDBCreate(BaseModel):
    test_suite_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=500)
    type: str = Field("manual", description="manual | automated | bdd")
    priority: str = Field("medium", description="critical | high | medium | low")
    status: str = Field("draft", description="draft | ready | deprecated")
    risk_tag: Optional[str] = None
    ac_category: Optional[str] = None
    preconditions: Optional[List[str]] = None
    gherkin: Optional[str] = None
    tags: Optional[List[str]] = None
    requirement_ids: Optional[List[uuid.UUID]] = None
    steps: Optional[List[TestStepCreate]] = None
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None


class TestCaseDBOut(BaseModel):
    _split_pc = field_validator("preconditions", mode="before")(_split_preconditions)

    id: uuid.UUID
    test_suite_id: uuid.UUID
    title: str
    slug: str
    type: str
    priority: str
    status: str
    risk_tag: Optional[str] = None
    ac_category: Optional[str] = None
    preconditions: Optional[List[str]] = None
    gherkin: Optional[str] = None
    tags: Optional[List[str]] = None
    requirement_ids: Optional[List[uuid.UUID]] = None
    steps: List[TestStepOut] = Field(default_factory=list)
    organization_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    model_config = ConfigDict(from_attributes=True)