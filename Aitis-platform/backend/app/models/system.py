"""Integration and system models â€” Integration, SecretReference, AuditEvent, Notification."""

import uuid
from typing import Optional
from enum import Enum

from sqlalchemy import String, Text, ForeignKey, Integer, Boolean, Index
from sqlalchemy import Uuid
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, TenantMixin


class IntegrationType(str, Enum):
    jira = "jira"
    confluence = "confluence"
    github = "github"
    gitlab = "gitlab"
    slack = "slack"
    teams = "teams"
    jenkins = "jenkins"
    github_actions = "github_actions"
    circleci = "circleci"
    s3 = "s3"
    custom = "custom"


class IntegrationStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    error = "error"


class AuditAction(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"
    login = "login"
    logout = "logout"
    execute = "execute"
    approve = "approve"
    reject = "reject"
    export = "export"
    import_ = "import"


class NotificationType(str, Enum):
    info = "info"
    warning = "warning"
    error = "error"
    success = "success"


# â”€â”€ Integration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class Integration(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "integrations"
    __table_args__ = (
        Index("ix_integ_project", "project_id"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(30), default=IntegrationType.jira.value)
    status: Mapped[str] = mapped_column(String(20), default=IntegrationStatus.active.value)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    base_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    last_sync_at: Mapped[Optional[str]] = mapped_column(nullable=True)
    sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    secrets = relationship("SecretReference", back_populates="integration", lazy="selectin", cascade="all, delete-orphan")


# â”€â”€ Secret Reference â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class SecretReference(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "secret_references"
    __table_args__ = (
        Index("ix_secret_integration_id", "integration_id"),
    )

    integration_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "api_token", "client_secret"
    vault_path: Mapped[str] = mapped_column(String(1024), nullable=False)  # path in vault/env
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    integration = relationship("Integration", back_populates="secrets")


# â”€â”€ Audit Event â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class AuditEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_org_id", "organization_id"),
        Index("ix_audit_project_id", "project_id"),
        Index("ix_audit_user_id", "user_id"),
        Index("ix_audit_action", "action"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=False, index=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "requirement", "test_case"
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), nullable=True)
    changes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {field: {old, new}}
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)


# â”€â”€ Notification â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class Notification(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notif_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(20), default=NotificationType.info.value)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    action_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)


class SSOProviderType(str, Enum):
    saml = "saml"
    oidc = "oidc"
    ldap = "ldap"
    azure_ad = "azure_ad"
    google_workspace = "google_workspace"


# ── SSO Provider ─────────────────────────────────────────────────────────────
class SSOProvider(Base, UUIDMixin, TimestampMixin):
    """Organization-scoped enterprise SSO provider (SAML / OIDC / LDAP).

    Org-scoped only (not project-scoped), so it deliberately does not use
    TenantMixin. ``domain_whitelist`` drives email-domain → provider discovery
    during the org-SSO initiation flow.
    """
    __tablename__ = "sso_providers"
    __table_args__ = (
        Index("ix_sso_org_id", "organization_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(30), default=SSOProviderType.oidc.value)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    # Provider-specific config (OIDC: client_id/secret, issuer_url, endpoints, scopes,
    # attribute_mapping). Secrets live here for now; move to SecretReference later.
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    domain_whitelist: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    auto_provision: Mapped[bool] = mapped_column(Boolean, default=False)

