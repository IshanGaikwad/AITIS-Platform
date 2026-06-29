"""Initial AITIS schema — all tables

Revision ID: 001_initial
Revises: None
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

from app.models.base import Base  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enable pgvector extension ───────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── Users ────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), unique=True, index=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("picture", sa.Text, nullable=True),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("provider_id", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Organizations ────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, index=True, nullable=False),
        sa.Column("logo_url", sa.Text, nullable=True),
        sa.Column("settings", pg.JSONB, server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Organization Memberships ─────────────────────────────────────────
    op.create_table(
        "organization_memberships",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(30), nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_org_membership"),
    )

    # ── Workspaces ──────────────────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("settings", pg.JSONB, server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "slug", name="uq_workspace_org_slug"),
    )

    # ── Workspace Memberships ───────────────────────────────────────────
    op.create_table(
        "workspace_memberships",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(30), nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "workspace_id", name="uq_ws_membership"),
    )

    # ── Projects ────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("key", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("settings", pg.JSONB, server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Requirements ────────────────────────────────────────────────────
    op.create_table(
        "requirements",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("project_id", pg.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("external_id", sa.String(50), nullable=True, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("type", sa.String(30), server_default="functional", nullable=False),
        sa.Column("priority", sa.String(20), server_default="medium", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("source_metadata", pg.JSONB, nullable=True),
        sa.Column("version", sa.Integer, server_default="1", nullable=False),
        # AI Governance
        sa.Column("ai_input_source", sa.String(100), nullable=True),
        sa.Column("ai_model_id", sa.String(100), nullable=True),
        sa.Column("ai_prompt_version", sa.String(50), nullable=True),
        sa.Column("ai_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_assumptions", pg.JSONB, nullable=True),
        sa.Column("ai_confidence", sa.Float, nullable=True),
        sa.Column("ai_review_status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("ai_reviewer_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("ai_approval_rejection_reason", sa.Text, nullable=True),
        sa.Column("ai_final_edited_version", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Acceptance Criteria ─────────────────────────────────────────────
    op.create_table(
        "acceptance_criteria",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("requirement_id", pg.UUID(as_uuid=True), sa.ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("category", sa.String(30), nullable=True),
        sa.Column("order", sa.Integer, server_default="0", nullable=False),
        sa.Column("is_ai_generated", sa.Boolean, server_default=sa.text("false"), nullable=False),
        # AI Governance
        sa.Column("ai_input_source", sa.String(100), nullable=True),
        sa.Column("ai_model_id", sa.String(100), nullable=True),
        sa.Column("ai_prompt_version", sa.String(50), nullable=True),
        sa.Column("ai_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_assumptions", pg.JSONB, nullable=True),
        sa.Column("ai_confidence", sa.Float, nullable=True),
        sa.Column("ai_review_status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("ai_reviewer_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("ai_approval_rejection_reason", sa.Text, nullable=True),
        sa.Column("ai_final_edited_version", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Test Suites ─────────────────────────────────────────────────────
    op.create_table(
        "test_suites",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("project_id", pg.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("requirement_id", pg.UUID(as_uuid=True), sa.ForeignKey("requirements.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("type", sa.String(20), server_default="automated", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Automation Scripts (created BEFORE test_cases because test_cases FK references it;
    #      healing_proposal_id FK added later due to circular dependency) ──
    op.create_table(
        "automation_scripts",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("language", sa.String(30), server_default="typescript", nullable=False),
        sa.Column("framework", sa.String(50), server_default="playwright", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("code", sa.Text, nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("version", sa.Integer, server_default="1", nullable=False),
        sa.Column("is_healed", sa.Boolean, server_default=sa.text("false"), nullable=False),
        # healing_proposal_id FK added after healing_proposals table is created
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Test Cases (references automation_scripts) ──────────────────────
    op.create_table(
        "test_cases",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("test_suite_id", pg.UUID(as_uuid=True), sa.ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("type", sa.String(20), server_default="manual", nullable=False),
        sa.Column("priority", sa.String(20), server_default="medium", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("risk_tag", sa.String(100), nullable=True),
        sa.Column("ac_category", sa.String(30), nullable=True),
        sa.Column("preconditions", pg.JSONB, nullable=True),
        sa.Column("gherkin", sa.Text, nullable=True),
        sa.Column("automation_script_id", pg.UUID(as_uuid=True), sa.ForeignKey("automation_scripts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Test Steps ──────────────────────────────────────────────────────
    op.create_table(
        "test_steps",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("test_case_id", pg.UUID(as_uuid=True), sa.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order", sa.Integer, nullable=False),
        sa.Column("type", sa.String(20), server_default="action", nullable=False),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("expected_result", sa.Text, nullable=True),
        sa.Column("test_data", pg.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Framework Configurations ────────────────────────────────────────
    op.create_table(
        "framework_configurations",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("framework", sa.String(50), server_default="playwright", nullable=False),
        sa.Column("config", pg.JSONB, server_default="{}", nullable=False),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Page Objects ────────────────────────────────────────────────────
    op.create_table(
        "page_objects",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("framework_config_id", pg.UUID(as_uuid=True), sa.ForeignKey("framework_configurations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("url_pattern", sa.String(500), nullable=True),
        sa.Column("code", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Locators ────────────────────────────────────────────────────────
    op.create_table(
        "locators",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("page_object_id", pg.UUID(as_uuid=True), sa.ForeignKey("page_objects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("strategy", sa.String(30), server_default="css", nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("is_dynamic", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("is_healed", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("original_value", sa.Text, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Test Executions ─────────────────────────────────────────────────
    op.create_table(
        "test_executions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("test_suite_id", pg.UUID(as_uuid=True), sa.ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("environment", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("summary", pg.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Test Case Executions ───────────────────────────────────────────
    op.create_table(
        "test_case_executions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("execution_id", pg.UUID(as_uuid=True), sa.ForeignKey("test_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_case_id", pg.UUID(as_uuid=True), sa.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("stack_trace", sa.Text, nullable=True),
        sa.Column("artifacts", pg.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Step Executions ─────────────────────────────────────────────────
    op.create_table(
        "step_executions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_execution_id", pg.UUID(as_uuid=True), sa.ForeignKey("test_case_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", pg.UUID(as_uuid=True), sa.ForeignKey("test_steps.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("actual_result", sa.Text, nullable=True),
        sa.Column("screenshot_url", sa.Text, nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Execution Artifacts ─────────────────────────────────────────────
    op.create_table(
        "execution_artifacts",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_execution_id", pg.UUID(as_uuid=True), sa.ForeignKey("test_case_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_type", sa.String(30), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=True),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("size_bytes", sa.BigInteger, nullable=True),
        sa.Column("metadata", pg.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Defects ─────────────────────────────────────────────────────────
    op.create_table(
        "defects",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("project_id", pg.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("case_execution_id", pg.UUID(as_uuid=True), sa.ForeignKey("test_case_executions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("external_id", sa.String(50), nullable=True, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("severity", sa.String(20), server_default="medium", nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("steps_to_reproduce", sa.Text, nullable=True),
        sa.Column("environment", sa.String(200), nullable=True),
        sa.Column("labels", pg.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Healing Proposals ───────────────────────────────────────────────
    op.create_table(
        "healing_proposals",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("locator_id", pg.UUID(as_uuid=True), sa.ForeignKey("locators.id", ondelete="SET NULL"), nullable=True),
        sa.Column("script_id", pg.UUID(as_uuid=True), sa.ForeignKey("automation_scripts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), server_default="proposed", nullable=False),
        sa.Column("original_code", sa.Text, nullable=True),
        sa.Column("proposed_code", sa.Text, nullable=True),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Circular FK resolution: automation_scripts.healing_proposal_id → healing_proposals.id ──
    op.add_column(
        "automation_scripts",
        sa.Column("healing_proposal_id", pg.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_automation_scripts_healing_proposal_id",
        "automation_scripts",
        "healing_proposals",
        ["healing_proposal_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ── Integrations ────────────────────────────────────────────────────
    op.create_table(
        "integrations",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("config", pg.JSONB, server_default="{}", nullable=False),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Secret References ──────────────────────────────────────────────
    op.create_table(
        "secret_references",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("integration_id", pg.UUID(as_uuid=True), sa.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("vault_path", sa.String(500), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Audit Events ───────────────────────────────────────────────────
    op.create_table(
        "audit_events",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("changes", pg.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("metadata", pg.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Notifications ──────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("is_read", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("action_url", sa.String(500), nullable=True),
        sa.Column("metadata", pg.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── Indexes ─────────────────────────────────────────────────────────
    op.create_index("ix_test_cases_slug", "test_cases", ["slug"], unique=True)
    op.create_index("ix_requirements_project", "requirements", ["project_id"])
    op.create_index("ix_acceptance_criteria_requirement", "acceptance_criteria", ["requirement_id"])
    op.create_index("ix_test_cases_suite", "test_cases", ["test_suite_id"])
    op.create_index("ix_test_steps_case_order", "test_steps", ["test_case_id", "order"])
    op.create_index("ix_audit_events_org_action", "audit_events", ["organization_id", "action"])
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "is_read"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("notifications")
    op.drop_table("audit_events")
    op.drop_table("secret_references")
    op.drop_table("integrations")
    # Drop circular FK first, then healing_proposals, then automation_scripts
    op.drop_constraint("fk_automation_scripts_healing_proposal_id", "automation_scripts", type_="foreignkey")
    op.drop_column("automation_scripts", "healing_proposal_id")
    op.drop_table("healing_proposals")
    op.drop_table("defects")
    op.drop_table("execution_artifacts")
    op.drop_table("step_executions")
    op.drop_table("test_case_executions")
    op.drop_table("test_executions")
    op.drop_table("locators")
    op.drop_table("page_objects")
    op.drop_table("framework_configurations")
    op.drop_table("test_steps")
    op.drop_table("test_cases")
    op.drop_table("automation_scripts")
    op.drop_table("test_suites")
    op.drop_table("acceptance_criteria")
    op.drop_table("requirements")
    op.drop_table("projects")
    op.drop_table("workspace_memberships")
    op.drop_table("workspaces")
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
