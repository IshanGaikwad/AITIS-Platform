"""Add Application and Environment models for Phase 1 project management

Revision ID: 002_application_environment
Revises: 001_initial
Create Date: 2025-06-24 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg


# revision identifiers, used by Alembic.
revision: str = "002_application_environment"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Application and Environment tables, extend Project with owner_id and tags."""
    
    # ── Add new columns to projects table ────────────────────────────────
    # Add owner_id foreign key to users
    op.add_column(
        'projects',
        sa.Column('owner_id', pg.UUID(as_uuid=True), nullable=True)
    )
    
    # Add tags JSONB array field
    op.add_column(
        'projects',
        sa.Column('tags', pg.JSONB, server_default='[]', nullable=True)
    )
    
    # Add foreign key constraint for owner_id
    op.create_foreign_key(
        'fk_projects_owner_id',
        'projects',
        'users',
        ['owner_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # ── Create applications table ────────────────────────────────────────
    op.create_table(
        'applications',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', pg.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', pg.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', pg.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('application_type', sa.String(50), nullable=False),  # WEB, MOBILE_WEB, ANDROID, IOS, HYBRID
        sa.Column('repository_url', sa.Text, nullable=True),
        sa.Column('metadata_', pg.JSONB, server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.Index('ix_applications_project_id', 'project_id'),
        sa.Index('ix_applications_organization_id', 'organization_id'),
        sa.Index('ix_applications_workspace_id', 'workspace_id'),
    )
    
    # ── Create environments table ────────────────────────────────────────
    op.create_table(
        'environments',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', pg.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', pg.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', pg.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', pg.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('environment_type', sa.String(50), nullable=False),  # dev, qa, uat, staging, prod, custom
        sa.Column('base_url', sa.Text, nullable=False),
        sa.Column('environment_variables', pg.JSONB, server_default='[]', nullable=False),  # List of {name, isSecret} refs only
        sa.Column('health_check_enabled', sa.Boolean, server_default=sa.text('false'), nullable=False),
        sa.Column('health_check_url', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.Index('ix_environments_project_id', 'project_id'),
        sa.Index('ix_environments_application_id', 'application_id'),
        sa.Index('ix_environments_organization_id', 'organization_id'),
        sa.Index('ix_environments_workspace_id', 'workspace_id'),
    )


def downgrade() -> None:
    """Revert Application and Environment tables and Project extensions."""
    
    # Drop environments table
    op.drop_table('environments')
    
    # Drop applications table
    op.drop_table('applications')
    
    # Remove columns from projects table
    op.drop_constraint('fk_projects_owner_id', 'projects', type_='foreignkey')
    op.drop_column('projects', 'owner_id')
    op.drop_column('projects', 'tags')
