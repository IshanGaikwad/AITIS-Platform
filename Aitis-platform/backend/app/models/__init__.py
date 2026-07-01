"""AITIS domain models â€” all entities exported here for easy import and Alembic auto-detection."""

# Base & mixins
from app.models.base import Base, UUIDMixin, TimestampMixin, TenantMixin, AIGovernanceMixin  # noqa: F401

# Identity & multi-tenancy
from app.models.user import User  # noqa: F401
from app.models.tenant import (  # noqa: F401
    Role,
    Organization,
    OrganizationMembership,
    Project,
    ProjectMembership,
)
from app.models.invitation import (  # noqa: F401
    InvitationStatus,
    Invitation,
)

# Workspace & requirements
from app.models.workspace import Workspace  # noqa: F401
from app.models.application import ApplicationType, Application  # noqa: F401
from app.models.environment import EnvironmentType, Environment  # noqa: F401
from app.models.requirement import (  # noqa: F401
    RequirementType,
    RequirementPriority,
    RequirementStatus,
    ACCategory,
    Requirement,
    AcceptanceCriterion,
)

# Test definition & execution
from app.models.test import (  # noqa: F401
    TestType,
    TestPriority,
    TestStatus,
    ReviewStatus,
    StepType,
    ExecutionStatus,
    ExecutionType,
    TestSuiteFolder,
    TestSuite,
    TestCase,
    TestCaseVersion,
    TestStep,
    TestExecution,
    TestCaseExecution,
    StepExecution,
)

# Automation
from app.models.automation import (  # noqa: F401
    ScriptLanguage,
    ScriptStatus,
    FrameworkType,
    LocatorStrategy,
    ExecutionJobStatus,
    BrowserType,
    RecordedActionType,
    AutomationScript,
    FrameworkConfiguration,
    PageObject,
    Locator,
    ScriptVersion,
    ExecutionJob,
    ExecutionResult,
    ExecutionStepResult,
    RecordedAction,
)

# Artifacts, defects, healing
from app.models.artifact import (  # noqa: F401
    ArtifactType,
    DefectSeverity,
    DefectStatus,
    HealingStatus,
    ExecutionArtifact,
    Defect,
    HealingProposal,
)

# System & integrations
from app.models.system import (  # noqa: F401
    IntegrationType,
    IntegrationStatus,
    AuditAction,
    NotificationType,
    SSOProviderType,
    Integration,
    SecretReference,
    AuditEvent,
    Notification,
    SSOProvider,
)

# Legacy (deprecated â€” re-exports Requirement as Story)
from app.models.story import Story  # noqa: F401

__all__ = [
    # Base
    "Base", "UUIDMixin", "TimestampMixin", "TenantMixin", "AIGovernanceMixin",
    # Identity
    "User", "Role", "Organization", "OrganizationMembership", "Project", "ProjectMembership",
    # Invitation
    "Invitation", "InvitationStatus",
    # Workspace
    "Workspace", "Application", "ApplicationType", "Environment", "EnvironmentType",
    # Requirements
    "Requirement", "AcceptanceCriterion", "RequirementType", "RequirementPriority", "RequirementStatus", "ACCategory",
    # Test
    "TestSuite", "TestCase", "TestStep", "TestExecution", "TestCaseExecution", "StepExecution",
    "TestType", "TestPriority", "TestStatus", "StepType", "ExecutionStatus",
    # Automation
    "AutomationScript", "FrameworkConfiguration", "PageObject", "Locator",
    "ScriptLanguage", "ScriptStatus", "FrameworkType", "LocatorStrategy",
    "ScriptVersion", "ExecutionJob", "ExecutionResult", "ExecutionStepResult", "RecordedAction",
    "ExecutionJobStatus", "BrowserType", "RecordedActionType",
    # Artifacts
    "ExecutionArtifact", "Defect", "HealingProposal",
    "ArtifactType", "DefectSeverity", "DefectStatus", "HealingStatus",
    # System
    "Integration", "SecretReference", "AuditEvent", "Notification", "SSOProvider",
    "IntegrationType", "IntegrationStatus", "AuditAction", "NotificationType", "SSOProviderType",
    # Legacy
    "Story",
]

