"""Add Phase 4 automation execution models

Revision ID: 003_phase4_automation
Revises: 002_application_environment
Create Date: 2025-06-25 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg


# revision identifiers, used by Alembic.
revision: str = "003_phase4_automation"
down_revision: Union[str, None] = "002_phase2_manual_testing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ScriptVersion, ExecutionJob, ExecutionResult, ExecutionStepResult,
    RecordedAction tables. Extend AutomationScript with approved_version_id and
    test_case_id. Extend ExecutionArtifact with execution_job_id and
    execution_result_id."""

    # ── Extend automation_scripts ────────────────────────────────────────
    op.add_column(
        "automation_scripts",
        sa.Column("approved_version_id", pg.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "automation_scripts",
        sa.Column("test_case_id", pg.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_ascript_approved_version_id",
        "automation_scripts",
        "script_versions",
        ["approved_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_ascript_test_case_id",
        "automation_scripts",
        "test_cases",
        ["test_case_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_ascript_test_case_id",
        "automation_scripts",
        ["test_case_id"],
    )

    # ── Create script_versions table ─────────────────────────────────────
    op.create_table(
        "script_versions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("script_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("code", sa.Text, nullable=False, server_default=""),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("changed_by", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("change_summary", sa.String(500), nullable=True),
        sa.Column("code_hash", sa.String(64), nullable=True),
        # UUIDMixin
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # TenantMixin
        sa.Column("organization_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["script_id"], ["automation_scripts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_sv_script_id", "script_versions", ["script_id"])

    # ── Create execution_jobs table ──────────────────────────────────────
    op.create_table(
        "execution_jobs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("script_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("script_version_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(25), nullable=False, server_default="queued"),
        sa.Column("environment_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("base_url", sa.String(1024), nullable=True),
        sa.Column("browser", sa.String(20), nullable=False, server_default="chromium"),
        sa.Column("headless", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default=sa.text("300")),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("container_id", sa.String(100), nullable=True),
        sa.Column("worker_id", sa.String(100), nullable=True),
        sa.Column("workspace_path", sa.String(500), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("triggered_by", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("execution_token", sa.String(255), nullable=True),
        sa.Column("result_summary", pg.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("stack_trace", sa.Text, nullable=True),
        # UUIDMixin
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # TenantMixin
        sa.Column("organization_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["script_id"], ["automation_scripts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["script_version_id"], ["script_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["triggered_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ej_script_id", "execution_jobs", ["script_id"])
    op.create_index("ix_ej_status", "execution_jobs", ["status"])
    op.create_index("ix_ej_workspace", "execution_jobs", ["workspace_id"])

    # ── Create execution_results table ───────────────────────────────────
    op.create_table(
        "execution_results",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("test_case_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("test_name", sa.String(500), nullable=False),
        sa.Column("status", sa.String(25), nullable=False, server_default="queued"),
        sa.Column("browser", sa.String(20), nullable=False, server_default="chromium"),
        sa.Column("environment", sa.String(50), nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("stack_trace", sa.Text, nullable=True),
        sa.Column("stdout", sa.Text, nullable=True),
        sa.Column("stderr", sa.Text, nullable=True),
        sa.Column("result_json", pg.JSONB, nullable=True),
        # UUIDMixin
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # TenantMixin
        sa.Column("organization_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["execution_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_er_job_id", "execution_results", ["job_id"])
    op.create_index("ix_er_test_case_id", "execution_results", ["test_case_id"])

    # ── Create execution_step_results table ─────────────────────────────
    op.create_table(
        "execution_step_results",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("result_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("step_name", sa.String(500), nullable=False),
        sa.Column("step_order", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(25), nullable=False, server_default="queued"),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("actual_result", sa.Text, nullable=True),
        sa.Column("screenshot_url", sa.String(1024), nullable=True),
        # UUIDMixin
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # TenantMixin
        sa.Column("organization_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["result_id"], ["execution_results.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_esr_result_id", "execution_step_results", ["result_id"])

    # ── Create recorded_actions table ────────────────────────────────────
    op.create_table(
        "recorded_actions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("script_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.String(100), nullable=False),
        sa.Column("action_order", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("action_type", sa.String(30), nullable=False, server_default="navigate"),
        sa.Column("selector", sa.Text, nullable=True),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("value", sa.Text, nullable=True),
        sa.Column("is_sensitive", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("url", sa.String(1024), nullable=True),
        sa.Column("expected_value", sa.Text, nullable=True),
        sa.Column("metadata", pg.JSONB, nullable=True),
        # UUIDMixin
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # TenantMixin
        sa.Column("organization_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["script_id"], ["automation_scripts.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ra_script_id", "recorded_actions", ["script_id"])
    op.create_index("ix_ra_session_id", "recorded_actions", ["session_id"])

    # ── Extend execution_artifacts ───────────────────────────────────────
    op.add_column(
        "execution_artifacts",
        sa.Column("execution_job_id", pg.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "execution_artifacts",
        sa.Column("execution_result_id", pg.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_artifact_execution_job_id",
        "execution_artifacts",
        "execution_jobs",
        ["execution_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_artifact_execution_result_id",
        "execution_artifacts",
        "execution_results",
        ["execution_result_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_artifact_job_id", "execution_artifacts", ["execution_job_id"])
    op.create_index("ix_artifact_result_id", "execution_artifacts", ["execution_result_id"])


def downgrade() -> None:
    """Remove Phase 4 tables and columns."""

    # ── Revert execution_artifacts extensions ────────────────────────────
    op.drop_index("ix_artifact_result_id", "execution_artifacts")
    op.drop_index("ix_artifact_job_id", "execution_artifacts")
    op.drop_constraint("fk_artifact_execution_result_id", "execution_artifacts", type_="foreignkey")
    op.drop_constraint("fk_artifact_execution_job_id", "execution_artifacts", type_="foreignkey")
    op.drop_column("execution_artifacts", "execution_result_id")
    op.drop_column("execution_artifacts", "execution_job_id")

    # ── Drop recorded_actions ────────────────────────────────────────────
    op.drop_index("ix_ra_session_id", "recorded_actions")
    op.drop_index("ix_ra_script_id", "recorded_actions")
    op.drop_table("recorded_actions")

    # ── Drop execution_step_results ──────────────────────────────────────
    op.drop_index("ix_esr_result_id", "execution_step_results")
    op.drop_table("execution_step_results")

    # ── Drop execution_results ───────────────────────────────────────────
    op.drop_index("ix_er_test_case_id", "execution_results")
    op.drop_index("ix_er_job_id", "execution_results")
    op.drop_table("execution_results")

    # ── Drop execution_jobs ──────────────────────────────────────────────
    op.drop_index("ix_ej_workspace", "execution_jobs")
    op.drop_index("ix_ej_status", "execution_jobs")
    op.drop_index("ix_ej_script_id", "execution_jobs")
    op.drop_table("execution_jobs")

    # ── Drop script_versions ─────────────────────────────────────────────
    op.drop_index("ix_sv_script_id", "script_versions")
    op.drop_table("script_versions")

    # ── Revert automation_scripts extensions ─────────────────────────────
    op.drop_index("ix_ascript_test_case_id", "automation_scripts")
    op.drop_constraint("fk_ascript_test_case_id", "automation_scripts", type_="foreignkey")
    op.drop_constraint("fk_ascript_approved_version_id", "automation_scripts", type_="foreignkey")
    op.drop_column("automation_scripts", "test_case_id")
    op.drop_column("automation_scripts", "approved_version_id")
