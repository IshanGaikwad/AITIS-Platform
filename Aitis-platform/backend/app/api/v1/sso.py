"""SSO & Enterprise Auth API — SAML, OIDC, LDAP integration.

Phase 9: Provides endpoints for configuring and managing enterprise
single sign-on providers including SAML 2.0, OpenID Connect, and LDAP.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role
from app.db.database import get_db

router = APIRouter()


# ── Pydantic schemas ─────────────────────────────────────────────────
class SSOProviderBase(BaseModel):
    name: str = Field(..., description="Display name for the SSO provider")
    provider_type: str = Field(..., description="saml | oidc | ldap | azure_ad | google_workspace")
    is_enabled: bool = True
    is_default: bool = False


class SSOProviderCreate(SSOProviderBase):
    config: dict = Field(default_factory=dict, description="Provider-specific configuration")
    domain_whitelist: List[str] = Field(default_factory=list, description="Allowed email domains")
    auto_provision: bool = Field(False, description="Auto-create users on first login")


class SSOProviderUpdate(BaseModel):
    name: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    config: Optional[dict] = None
    domain_whitelist: Optional[List[str]] = None
    auto_provision: Optional[bool] = None


class SSOProviderOut(BaseModel):
    id: str
    name: str
    provider_type: str
    is_enabled: bool
    is_default: bool
    domain_whitelist: List[str]
    auto_provision: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SAMLConfig(BaseModel):
    """SAML 2.0 configuration template."""
    entity_id: str = Field(..., description="SP Entity ID (this application)")
    acs_url: str = Field(..., description="Assertion Consumer Service URL")
    idp_metadata_url: Optional[str] = Field(None, description="IdP metadata URL")
    idp_entity_id: Optional[str] = None
    idp_sso_url: Optional[str] = None
    idp_certificate: Optional[str] = Field(None, description="IdP x509 certificate (PEM)")
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    attribute_mapping: dict = Field(
        default_factory=lambda: {
            "email": "email",
            "first_name": "givenName",
            "last_name": "sn",
            "groups": "memberOf",
        }
    )


class OIDCConfig(BaseModel):
    """OpenID Connect configuration template."""
    client_id: str = Field(..., description="OIDC client ID")
    client_secret: str = Field(..., description="OIDC client secret")
    issuer_url: str = Field(..., description="OIDC issuer/discovery URL")
    authorization_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None
    userinfo_endpoint: Optional[str] = None
    jwks_uri: Optional[str] = None
    scopes: List[str] = Field(default_factory=lambda: ["openid", "profile", "email"])
    attribute_mapping: dict = Field(
        default_factory=lambda: {
            "email": "email",
            "first_name": "given_name",
            "last_name": "family_name",
        }
    )


class LDAPConfig(BaseModel):
    """LDAP configuration template."""
    server_url: str = Field(..., description="ldap:// or ldaps:// server URL")
    bind_dn: str = Field(..., description="Bind DN for authentication")
    bind_password: str = Field(..., description="Bind password")
    base_dn: str = Field(..., description="Base DN for user search")
    user_filter: str = "(uid={username})"
    group_filter: str = "(member={user_dn})"
    attribute_mapping: dict = Field(
        default_factory=lambda: {
            "email": "mail",
            "first_name": "givenName",
            "last_name": "sn",
            "username": "uid",
        }
    )


class SSOTestResult(BaseModel):
    success: bool
    provider_type: str
    message: str
    details: dict = Field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════

@router.get("/providers", response_model=List[SSOProviderOut])
async def list_sso_providers(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator")),
):
    """List all SSO providers for the organization."""
    org_id = current_user.get("organization_id")

    # For now, return in-memory config (can be moved to DB model)
    # In production, this would query an SSOProvider model
    return []


@router.post("/providers", response_model=SSOProviderOut, status_code=status.HTTP_201_CREATED)
async def create_sso_provider(
    payload: SSOProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator")),
):
    """Configure a new SSO provider."""
    org_id = current_user.get("organization_id")

    # Validate provider type
    valid_types = {"saml", "oidc", "ldap", "azure_ad", "google_workspace"}
    if payload.provider_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider type. Must be one of: {', '.join(valid_types)}",
        )

    # Validate config based on provider type
    if payload.provider_type == "saml":
        _validate_saml_config(payload.config)
    elif payload.provider_type == "oidc":
        _validate_oidc_config(payload.config)
    elif payload.provider_type == "ldap":
        _validate_ldap_config(payload.config)

    # In production, store to DB
    provider_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    return SSOProviderOut(
        id=provider_id,
        name=payload.name,
        provider_type=payload.provider_type,
        is_enabled=payload.is_enabled,
        is_default=payload.is_default,
        domain_whitelist=payload.domain_whitelist,
        auto_provision=payload.auto_provision,
        created_at=now,
        updated_at=now,
    )


@router.put("/providers/{provider_id}", response_model=SSOProviderOut)
async def update_sso_provider(
    provider_id: str,
    payload: SSOProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator")),
):
    """Update an SSO provider configuration."""
    # In production, update DB record
    raise HTTPException(status_code=501, detail="Update not yet implemented — coming soon")


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sso_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator")),
):
    """Remove an SSO provider configuration."""
    # In production, soft-delete DB record
    raise HTTPException(status_code=501, detail="Delete not yet implemented — coming soon")


@router.post("/providers/{provider_id}/test", response_model=SSOTestResult)
async def test_sso_connection(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator")),
):
    """Test the connection to an SSO provider."""
    # In production, attempt a test connection
    return SSOTestResult(
        success=True,
        provider_type="saml",
        message="Connection test endpoint ready. Configure provider first.",
        details={"provider_id": provider_id},
    )


@router.get("/config/saml-template")
async def get_saml_config_template(
    base_url: str = Query("https://app.aitis.dev"),
    current_user=Depends(require_role("administrator")),
):
    """Get a SAML configuration template with pre-filled SP metadata."""
    return {
        "service_provider": {
            "entity_id": f"{base_url}/sso/saml/metadata",
            "acs_url": f"{base_url}/api/sso/saml/acs",
            "slo_url": f"{base_url}/api/sso/saml/slo",
            "name_id_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            "certificate": "<!-- SP x509 certificate will be generated on save -->",
        },
        "identity_provider": {
            "idp_metadata_url": "https://your-idp.example.com/metadata",
            "idp_entity_id": "https://your-idp.example.com/entity",
            "idp_sso_url": "https://your-idp.example.com/sso",
            "idp_certificate": "<!-- Paste IdP x509 certificate (PEM) here -->",
        },
        "attribute_mapping": {
            "email": "email",
            "first_name": "givenName",
            "last_name": "sn",
            "groups": "memberOf",
        },
    }


@router.get("/config/oidc-template")
async def get_oidc_config_template(
    base_url: str = Query("https://app.aitis.dev"),
    current_user=Depends(require_role("administrator")),
):
    """Get an OpenID Connect configuration template."""
    return {
        "client_id": "your-client-id",
        "client_secret": "your-client-secret",
        "issuer_url": "https://accounts.google.com",
        "redirect_uri": f"{base_url}/api/sso/oidc/callback",
        "scopes": ["openid", "profile", "email"],
        "attribute_mapping": {
            "email": "email",
            "first_name": "given_name",
            "last_name": "family_name",
        },
        "providers": {
            "google": {
                "issuer_url": "https://accounts.google.com",
                "description": "Google Workspace / G Suite",
            },
            "azure_ad": {
                "issuer_url": "https://login.microsoftonline.com/{tenant_id}/v2.0",
                "description": "Microsoft Azure AD / Entra ID",
            },
            "okta": {
                "issuer_url": "https://{your-domain}.okta.com",
                "description": "Okta",
            },
            "auth0": {
                "issuer_url": "https://{your-domain}.auth0.com",
                "description": "Auth0",
            },
        },
    }


@router.get("/config/ldap-template")
async def get_ldap_config_template(
    current_user=Depends(require_role("administrator")),
):
    """Get an LDAP configuration template."""
    return {
        "server_url": "ldaps://ldap.example.com:636",
        "bind_dn": "cn=admin,dc=example,dc=com",
        "bind_password": "your-bind-password",
        "base_dn": "dc=example,dc=com",
        "user_filter": "(uid={username})",
        "group_filter": "(member={user_dn})",
        "tls_enabled": True,
        "tls_ca_cert": "<!-- Optional: CA certificate for TLS -->",
        "attribute_mapping": {
            "email": "mail",
            "first_name": "givenName",
            "last_name": "sn",
            "username": "uid",
            "phone": "telephoneNumber",
        },
    }


# ── Validation helpers ──────────────────────────────────────────────

def _validate_saml_config(config: dict):
    """Validate SAML configuration."""
    required = ["entity_id", "acs_url"]
    missing = [k for k in required if k not in config]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"SAML config missing required fields: {', '.join(missing)}",
        )
    if not config.get("idp_metadata_url") and not config.get("idp_sso_url"):
        raise HTTPException(
            status_code=400,
            detail="SAML config requires either idp_metadata_url or idp_sso_url",
        )


def _validate_oidc_config(config: dict):
    """Validate OIDC configuration."""
    required = ["client_id", "client_secret", "issuer_url"]
    missing = [k for k in required if k not in config]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"OIDC config missing required fields: {', '.join(missing)}",
        )


def _validate_ldap_config(config: dict):
    """Validate LDAP configuration."""
    required = ["server_url", "bind_dn", "bind_password", "base_dn"]
    missing = [k for k in required if k not in config]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"LDAP config missing required fields: {', '.join(missing)}",
        )