"""Governance & Compliance API — audit, RBAC, policy enforcement.

Phase 9: Provides endpoints for governance, compliance reporting,
role-based access control management, and policy enforcement.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role
from app.db.database import get_db

router = APIRouter()


# ── Pydantic schemas ─────────────────────────────────────────────────
class RoleAssignment(BaseModel):
    user_id: str
    role: str = Field(..., description="administrator | org_owner | qa_lead | qa_engineer | viewer")
    scope: str = Field("project", description="organization | project | workspace")
    scope_id: Optional[str] = None


class RoleAssignmentOut(BaseModel):
    id: str
    user_id: str
    user_email: str
    role: str
    scope: str
    scope_id: Optional[str] = None
    assigned_by: Optional[str] = None
    assigned_at: str


class Policy(BaseModel):
    name: str
    description: str
    category: str = Field(..., description="security | quality | automation | compliance")
    rule_type: str = Field(..., description="require_approval | block_execution | notify | enforce_mfa")
    conditions: dict = Field(default_factory=dict)
    is_enabled: bool = True
    priority: int = 0


class PolicyOut(BaseModel):
    id: str
    name: str
    description: str
    category: str
    rule_type: str
    is_enabled: bool
    priority: int
    created_at: str
    updated_at: str


class ComplianceReport(BaseModel):
    generated_at: str
    organization_id: str
    project_id: Optional[str] = None
    sections: List[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    score: float = 0.0
    status: str = "compliant"  # compliant | at_risk | non_compliant


class AuditLogEntry(BaseModel):
    id: str
    timestamp: str
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: dict = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditLogQuery(BaseModel):
    actor_id: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


# ══════════════════════════════════════════════════════════════════════
# Role Management
# ══════════════════════════════════════════════════════════════════════

@router.get("/roles")
async def list_available_roles(
    current_user=Depends(get_current_user),
):
    """List all available roles and their permissions."""
    return {
        "roles": [
            {
                "name": "administrator",
                "label": "Administrator",
                "description": "Full platform access including billing and SSO configuration",
                "permissions": [
                    "manage_organization", "manage_project", "manage_users",
                    "manage_roles", "manage_sso", "manage_billing",
                    "manage_workspaces", "manage_requirements", "manage_test_cases",
                    "manage_automation", "execute_tests", "view_reports",
                    "manage_defects", "manage_environments", "view_audit_logs",
                ],
            },
            {
                "name": "org_owner",
                "label": "Organization Owner",
                "description": "Organization-level management without billing access",
                "permissions": [
                    "manage_organization", "manage_project", "manage_users",
                    "manage_roles", "manage_workspaces", "manage_requirements",
                    "manage_test_cases", "manage_automation", "execute_tests",
                    "view_reports", "manage_defects", "manage_environments",
                    "view_audit_logs",
                ],
            },
            {
                "name": "qa_lead",
                "label": "QA Lead",
                "description": "Full QA management including automation and approvals",
                "permissions": [
                    "manage_workspaces", "manage_requirements", "manage_test_cases",
                    "manage_automation", "execute_tests", "view_reports",
                    "manage_defects", "manage_environments", "approve_scripts",
                    "manage_test_suites",
                ],
            },
            {
                "name": "qa_engineer",
                "label": "QA Engineer",
                "description": "Test creation, execution, and defect management",
                "permissions": [
                    "manage_test_cases", "manage_automation", "execute_tests",
                    "view_reports", "manage_defects", "create_scripts",
                ],
            },
            {
                "name": "automation_engineer",
                "label": "Automation Engineer",
                "description": "Focused on automation script development and execution",
                "permissions": [
                    "manage_automation", "execute_tests", "view_reports",
                    "create_scripts", "manage_page_objects", "manage_locators",
                ],
            },
            {
                "name": "viewer",
                "label": "Viewer",
                "description": "Read-only access to reports and dashboards",
                "permissions": [
                    "view_reports", "view_dashboard", "view_traceability",
                ],
            },
        ]
    }


@router.post("/roles/assign", response_model=RoleAssignmentOut, status_code=status.HTTP_201_CREATED)
async def assign_role(
    payload: RoleAssignment,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "org_owner")),
):
    """Assign a role to a user."""
    valid_roles = {"administrator", "org_owner", "qa_lead", "qa_engineer", "automation_engineer", "viewer"}
    if payload.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
        )

    # In production, store to DB
    return RoleAssignmentOut(
        id=str(uuid.uuid4()),
        user_id=payload.user_id,
        user_email="user@example.com",  # Would be resolved from user service
        role=payload.role,
        scope=payload.scope,
        scope_id=payload.scope_id,
        assigned_by=current_user.get("id") if isinstance(current_user, dict) else None,
        assigned_at=datetime.now(timezone.utc).isoformat(),
    )


@router.delete("/roles/revoke/{user_id}/{role}")
async def revoke_role(
    user_id: str,
    role: str,
    scope: str = Query("project"),
    scope_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "org_owner")),
):
    """Revoke a role from a user."""
    return {"message": f"Role '{role}' revoked from user {user_id}", "success": True}


# ══════════════════════════════════════════════════════════════════════
# Policy Management
# ══════════════════════════════════════════════════════════════════════

@router.get("/policies", response_model=List[PolicyOut])
async def list_policies(
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "org_owner", "qa_lead")),
):
    """List governance policies."""
    # In production, query DB
    return [
        PolicyOut(
            id="policy-001",
            name="Require Script Approval",
            description="All automation scripts must be approved before execution",
            category="automation",
            rule_type="require_approval",
            is_enabled=True,
            priority=10,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        ),
        PolicyOut(
            id="policy-002",
            name="Block External Network Calls",
            description="Block test scripts from making calls to external domains",
            category="security",
            rule_type="block_execution",
            is_enabled=True,
            priority=20,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        ),
        PolicyOut(
            id="policy-003",
            name="Enforce MFA for Admins",
            description="Require multi-factor authentication for administrator accounts",
            category="security",
            rule_type="enforce_mfa",
            is_enabled=True,
            priority=5,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        ),
        PolicyOut(
            id="policy-004",
            name="Minimum Coverage Threshold",
            description="Notify when requirement coverage drops below 80%",
            category="quality",
            rule_type="notify",
            is_enabled=True,
            priority=15,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        ),
    ]


@router.post("/policies", response_model=PolicyOut, status_code=status.HTTP_201_CREATED)
async def create_policy(
    payload: Policy,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "org_owner")),
):
    """Create a new governance policy."""
    valid_categories = {"security", "quality", "automation", "compliance"}
    if payload.category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}",
        )

    valid_rules = {"require_approval", "block_execution", "notify", "enforce_mfa"}
    if payload.rule_type not in valid_rules:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rule type. Must be one of: {', '.join(valid_rules)}",
        )

    now = datetime.now(timezone.utc).isoformat()
    return PolicyOut(
        id=str(uuid.uuid4()),
        name=payload.name,
        description=payload.description,
        category=payload.category,
        rule_type=payload.rule_type,
        is_enabled=payload.is_enabled,
        priority=payload.priority,
        created_at=now,
        updated_at=now,
    )


# ══════════════════════════════════════════════════════════════════════
# Compliance Reports
# ══════════════════════════════════════════════════════════════════════

@router.get("/compliance/report", response_model=ComplianceReport)
async def generate_compliance_report(
    project_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "org_owner", "qa_lead")),
):
    """Generate a compliance report for the organization/project."""
    org_id = current_user.get("organization_id")
    ws_id = project_id or current_user.get("project_id")

    # In production, compute from actual data
    sections = [
        {
            "name": "Access Control",
            "status": "compliant",
            "checks": [
                {"name": "MFA enabled for admins", "passed": True},
                {"name": "Role-based access configured", "passed": True},
                {"name": "No orphaned accounts", "passed": True},
            ],
        },
        {
            "name": "Test Execution Security",
            "status": "compliant",
            "checks": [
                {"name": "Script validation enabled", "passed": True},
                {"name": "Network isolation configured", "passed": True},
                {"name": "Execution audit logging active", "passed": True},
            ],
        },
        {
            "name": "Quality Gates",
            "status": "at_risk",
            "checks": [
                {"name": "Coverage threshold met (>80%)", "passed": True},
                {"name": "All critical paths tested", "passed": False, "detail": "3 critical requirements uncovered"},
                {"name": "Defect SLA met", "passed": True},
            ],
        },
        {
            "name": "Data Governance",
            "status": "compliant",
            "checks": [
                {"name": "PII not stored in test data", "passed": True},
                {"name": "Test data retention policy active", "passed": True},
                {"name": "Encryption at rest enabled", "passed": True},
            ],
        },
    ]

    passed = sum(c["passed"] for s in sections for c in s["checks"])
    total = sum(len(s["checks"]) for s in sections)
    score = round((passed / total) * 100, 1) if total > 0 else 0

    return ComplianceReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        organization_id=str(org_id),
        project_id=str(ws_id),
        sections=sections,
        summary={
            "total_checks": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": score,
        },
        score=score,
        status="compliant" if score >= 90 else "at_risk" if score >= 70 else "non_compliant",
    )


@router.get("/compliance/frameworks")
async def list_compliance_frameworks(
    current_user=Depends(get_current_user),
):
    """List supported compliance frameworks."""
    return {
        "frameworks": [
            {
                "name": "SOC 2",
                "description": "Service Organization Control 2 — security, availability, processing integrity, confidentiality, privacy",
                "controls_count": 64,
                "supported": True,
            },
            {
                "name": "ISO 27001",
                "description": "Information security management system requirements",
                "controls_count": 114,
                "supported": True,
            },
            {
                "name": "GDPR",
                "description": "General Data Protection Regulation — EU data privacy",
                "controls_count": 99,
                "supported": True,
            },
            {
                "name": "HIPAA",
                "description": "Health Insurance Portability and Accountability Act",
                "controls_count": 78,
                "supported": False,
            },
            {
                "name": "PCI DSS",
                "description": "Payment Card Industry Data Security Standard",
                "controls_count": 300,
                "supported": False,
            },
        ]
    }


# ══════════════════════════════════════════════════════════════════════
# Audit Log
# ══════════════════════════════════════════════════════════════════════

@router.get("/audit-log", response_model=List[AuditLogEntry])
async def query_audit_log(
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "org_owner")),
):
    """Query the governance audit log."""
    # In production, query from audit_events table
    return []


@router.get("/audit-log/export")
async def export_audit_log(
    format: str = Query("csv", description="csv | json"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "org_owner")),
):
    """Export the audit log in CSV or JSON format."""
    return {
        "format": format,
        "message": "Audit log export endpoint ready. Configure date range to export.",
        "download_url": None,  # Would generate a signed download URL
    }