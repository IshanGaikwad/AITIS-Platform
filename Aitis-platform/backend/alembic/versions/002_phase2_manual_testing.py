"""Phase 2 — Manual Test Management & Execution schema additions

Revision ID: 002_phase2_manual_testing
Revises: 001_initial
Create Date: 2025-06-24 00:00:00.000000

Adds:
  - test_suite_folders (hierarchical folder organisation)
  - test_case_versions (immutable version snapshots)
  - Phase 2 columns on test_cases (description, review_status, owner_id, tags, version, requirement_ids)
  - Phase 2 columns on test_steps (description, tenant columns)
  - Phase 2 columns on test_executions (execution_type, executed_by, notes)
  - Phase 2 columns on step_executions (comment, tenant columns)
  - Phase 2 columns on test_case_executions (tenant columns)
  - folder_id FK on test_suites
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg


# revision identifiers, used by Alembic.
revision: str = "002_phase2_manual_testing"
down_revision: Union[str, None] = "002_application_environment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. test_suite_folders (new table) ───────────────────────────────
    op.create_table(
        "test_suite_folders",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                  index=True, nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
                  index=True, nullable=True),
        sa.Column("project_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", ondelete="CASCADE"),
                  index=True, nullable=False),
        sa.Column("parent_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("test_suite_folders.id", ondelete="CASCADE"),
                  index=True, nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── 2. test_suites — add folder_id FK ──────────────────────────────
    op.add_column("test_suites",
                   sa.Column("folder_id", pg.UUID(as_uuid=True),
                             sa.ForeignKey("test_suite_folders.id", ondelete="SET NULL"),
                             nullable=True))
    op.create_index("ix_suite_folder_id", "test_suites", ["folder_id"])

    # ── 3. test_cases — add Phase 2 columns ────────────────────────────
    op.add_column("test_cases",
                   sa.Column("description", sa.Text, nullable=True))
    op.add_column("test_cases",
                   sa.Column("review_status", sa.String(20),
                             server_default="pending", nullable=False))
    op.add_column("test_cases",
                   sa.Column("owner_id", pg.UUID(as_uuid=True),
                             sa.ForeignKey("users.id", ondelete="SET NULL"),
                             nullable=True))
    op.create_index("ix_tc_owner_id", "test_cases", ["owner_id"])
    op.add_column("test_cases",
                   sa.Column("tags", pg.JSONB, nullable=True))
    op.add_column("test_cases",
                   sa.Column("version", sa.Integer, server_default="1", nullable=False))
    op.add_column("test_cases",
                   sa.Column("requirement_ids", pg.JSONB, nullable=True))

    # ── 4. test_case_versions (new table) ──────────────────────────────
    op.create_table(
        "test_case_versions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                  index=True, nullable=False),
        sa.Column("workspace_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
                  index=True, nullable=True),
        sa.Column("test_case_id", pg.UUID(as_uuid=True),
                  sa.ForeignKey("test_cases.id", ondelete="CASCADE"),
                  index=True, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("preconditions", sa.Text, nullable=True),
        sa.Column("gherkin", sa.Text, nullable=True),
        sa.Column("tags", pg.JSONB, nullable=True),
        sa.Column("requirement_ids", pg.JSONB, nullable=True),
        sa.Column("steps_snapshot", pg.JSONB, nullable=True),
        sa.Column("changed_by", pg.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("change_summary", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tcv_tc_id", "test_case_versions", ["test_case_id"])

    # ── 5. test_steps — add Phase 2 columns + tenant columns ───────────
    op.add_column("test_steps",
                   sa.Column("description", sa.Text, nullable=True))
    op.add_column("test_steps",
                   sa.Column("organization_id", pg.UUID(as_uuid=True),
                             sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                             nullable=True))
    op.add_column("test_steps",
                   sa.Column("workspace_id", pg.UUID(as_uuid=True),
                             sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
                             nullable=True))
    op.create_index("ix_step_org_id", "test_steps", ["organization_id"])
    op.create_index("ix_step_ws_id", "test_steps", ["workspace_id"])

    # ── 6. test_executions — add Phase 2 columns ───────────────────────
    op.add_column("test_executions",
                   sa.Column("execution_type", sa.String(20),
                             server_default="automated", nullable=False))
    op.add_column("test_executions",
                   sa.Column("executed_by", pg.UUID(as_uuid=True),
                             sa.ForeignKey("users.id", ondelete="SET NULL"),
                             nullable=True))
    op.create_index("ix_exec_executed_by", "test_executions", ["executed_by"])
    op.add_column("test_executions",
                   sa.Column("notes", sa.Text, nullable=True))

    # ── 7. test_case_executions — add tenant columns ───────────────────
    op.add_column("test_case_executions",
                   sa.Column("organization_id", pg.UUID(as_uuid=True),
                             sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                             nullable=True))
    op.add_column("test_case_executions",
                   sa.Column("workspace_id", pg.UUID(as_uuid=True),
                             sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
                             nullable=True))
    op.create_index("ix_tce_org_id", "test_case_executions", ["organization_id"])
    op.create_index("ix_tce_ws_id", "test_case_executions", ["workspace_id"])

    # ── 8. step_executions — add Phase 2 columns + tenant columns ──────
    op.add_column("step_executions",
                   sa.Column("comment", sa.Text, nullable=True))
    op.add_column("step_executions",
                   sa.Column("organization_id", pg.UUID(as_uuid=True),
                             sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                             nullable=True))
    op.add_column("step_executions",
                   sa.Column("workspace_id", pg.UUID(as_uuid=True),
                             sa.ForeignKey("workspaces.id", ondelete="SET NULL"),
                             nullable=True))
    op.create_index("ix_se_org_id", "step_executions", ["organization_id"])
    op.create_index("ix_se_ws_id", "step_executions", ["workspace_id"])


def downgrade() -> None:
    # ── 8. step_executions — drop Phase 2 + tenant columns ─────────────
    op.drop_index("ix_se_ws_id", table_name="step_executions")
    op.drop_index("ix_se_org_id", table_name="step_executions")
    op.drop_column("step_executions", "workspace_id")
    op.drop_column("step_executions", "organization_id")
    op.drop_column("step_executions", "comment")

    # ── 7. test_case_executions — drop tenant columns ──────────────────
    op.drop_index("ix_tce_ws_id", table_name="test_case_executions")
    op.drop_index("ix_tce_org_id", table_name="test_case_executions")
    op.drop_column("test_case_executions", "workspace_id")
    op.drop_column("test_case_executions", "organization_id")

    # ── 6. test_executions — drop Phase 2 columns ──────────────────────
    op.drop_index("ix_exec_executed_by", table_name="test_executions")
    op.drop_column("test_executions", "notes")
    op.drop_column("test_executions", "executed_by")
    op.drop_column("test_executions", "execution_type")

    # ── 5. test_steps — drop Phase 2 + tenant columns ──────────────────
    op.drop_index("ix_step_ws_id", table_name="test_steps")
    op.drop_index("ix_step_org_id", table_name="test_steps")
    op.drop_column("test_steps", "workspace_id")
    op.drop_column("test_steps", "organization_id")
    op.drop_column("test_steps", "description")

    # ── 4. test_case_versions — drop table ─────────────────────────────
    op.drop_index("ix_tcv_tc_id", table_name="test_case_versions")
    op.drop_table("test_case_versions")

    # ── 3. test_cases — drop Phase 2 columns ───────────────────────────
    op.drop_column("test_cases", "requirement_ids")
    op.drop_column("test_cases", "version")
    op.drop_column("test_cases", "tags")
    op.drop_index("ix_tc_owner_id", table_name="test_cases")
    op.drop_column("test_cases", "owner_id")
    op.drop_column("test_cases", "review_status")
    op.drop_column("test_cases", "description")

    # ── 2. test_suites — drop folder_id ────────────────────────────────
    op.drop_index("ix_suite_folder_id", table_name="test_suites")
    op.drop_column("test_suites", "folder_id")

    # ── 1. test_suite_folders — drop table ─────────────────────────────
    op.drop_table("test_suite_folders")