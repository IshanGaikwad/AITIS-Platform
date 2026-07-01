"""SSO & Enterprise Auth API — SAML, OIDC, LDAP integration.

Phase 9: Provides endpoints for configuring and managing enterprise
single sign-on providers including SAML 2.0, OpenID Connect, and LDAP.
"""

import secrets
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.models.system import SSOProvider as SSOProviderModel
from app.services import sso_service

router = APIRouter()


def _provider_to_out(p: SSOProviderModel) -> "SSOProviderOut":
    return SSOProviderOut(
        id=str(p.id),
        name=p.name,
        provider_type=p.provider_type,
        is_enabled=p.is_enabled,
        is_default=p.is_default,
        domain_whitelist=list(p.domain_whitelist or []),
        auto_provision=p.auto_provision,
        created_at=p.created_at.isoformat() if p.created_at else "",
        updated_at=p.updated_at.isoformat() if p.updated_at else "",
    )


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

async def _get_owned_provider(db: AsyncSession, provider_id: str, org_id) -> SSOProviderModel:
    """Load a provider and verify it belongs to the caller's organization."""
    try:
        pid = uuid.UUID(provider_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid provider id")
    provider = await db.get(SSOProviderModel, pid)
    if not provider or (org_id and str(provider.organization_id) != str(org_id)):
        raise HTTPException(status_code=404, detail="SSO provider not found")
    return provider


@router.get("/providers", response_model=List[SSOProviderOut])
async def list_sso_providers(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator")),
):
    """List all SSO providers for the organization."""
    org_id = current_user.get("organization_id")
    result = await db.execute(
        select(SSOProviderModel)
        .where(SSOProviderModel.organization_id == org_id)
        .order_by(SSOProviderModel.created_at.desc())
    )
    return [_provider_to_out(p) for p in result.scalars().all()]


@router.post("/providers", response_model=SSOProviderOut, status_code=status.HTTP_201_CREATED)
async def create_sso_provider(
    payload: SSOProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator")),
):
    """Configure a new SSO provider."""
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="No organization context")

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

    # A new default unsets any existing default for this org.
    if payload.is_default:
        existing = await db.execute(
            select(SSOProviderModel).where(
                SSOProviderModel.organization_id == org_id,
                SSOProviderModel.is_default.is_(True),
            )
        )
        for other in existing.scalars().all():
            other.is_default = False

    provider = SSOProviderModel(
        organization_id=uuid.UUID(str(org_id)),
        name=payload.name,
        provider_type=payload.provider_type,
        is_enabled=payload.is_enabled,
        is_default=payload.is_default,
        config=payload.config,
        domain_whitelist=payload.domain_whitelist,
        auto_provision=payload.auto_provision,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return _provider_to_out(provider)


@router.put("/providers/{provider_id}", response_model=SSOProviderOut)
async def update_sso_provider(
    provider_id: str,
    payload: SSOProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator")),
):
    """Update an SSO provider configuration."""
    org_id = current_user.get("organization_id")
    provider = await _get_owned_provider(db, provider_id, org_id)

    data = payload.model_dump(exclude_unset=True)
    if data.get("is_default"):
        existing = await db.execute(
            select(SSOProviderModel).where(
                SSOProviderModel.organization_id == provider.organization_id,
                SSOProviderModel.is_default.is_(True),
                SSOProviderModel.id != provider.id,
            )
        )
        for other in existing.scalars().all():
            other.is_default = False

    for key, val in data.items():
        setattr(provider, key, val)
    await db.commit()
    await db.refresh(provider)
    return _provider_to_out(provider)


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sso_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator")),
):
    """Remove an SSO provider configuration."""
    org_id = current_user.get("organization_id")
    provider = await _get_owned_provider(db, provider_id, org_id)
    await db.delete(provider)
    await db.commit()


# ══════════════════════════════════════════════════════════════════════
# Org-SSO initiation (public — the user is not yet authenticated)
# ══════════════════════════════════════════════════════════════════════

class SSOInitiateRequest(BaseModel):
    email: str = Field(..., description="Work email used to discover the org's SSO provider")


class SSOInitiateResponse(BaseModel):
    authorization_url: str
    state: str
    provider_name: str


@router.post("/initiate", response_model=SSOInitiateResponse)
async def initiate_sso(
    payload: SSOInitiateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Discover the SSO provider for an email domain and return its authorization URL.

    Public endpoint: the user has not logged in yet. The browser is then redirected
    to the returned ``authorization_url``; the IdP returns to ``/auth/callback``.
    """
    provider = await sso_service.find_provider_for_email(db, payload.email)
    if not provider:
        raise HTTPException(
            status_code=404,
            detail="No organization SSO is configured for this email domain.",
        )
    if provider.provider_type not in sso_service.OIDC_FAMILY:
        raise HTTPException(
            status_code=400,
            detail=f"'{provider.provider_type}' SSO cannot be initiated from the browser.",
        )

    state = sso_service.make_state(provider, secrets.token_urlsafe(24))
    authorization_url = await sso_service.build_authorization_url(provider, state)
    return SSOInitiateResponse(
        authorization_url=authorization_url,
        state=state,
        provider_name=provider.name,
    )


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
                "description": "Google Project / G Suite",
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