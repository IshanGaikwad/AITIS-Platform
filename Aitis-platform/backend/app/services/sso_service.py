"""Organization SSO service — OIDC-based browser sign-in initiation & callback.

Implements the *initiation* half of enterprise SSO: a user enters their work
email, we discover which organization SSO provider serves that email domain, and
redirect them to the provider's OIDC authorization endpoint. The callback half
exchanges the code, reads userinfo, enforces the domain allow-list / provisioning
policy, and links or creates the user.

Only OIDC-family providers (``oidc``, ``azure_ad``, ``google_workspace``) support
browser redirect sign-in. SAML and LDAP are configured but not initiated here.
"""

import uuid
from typing import Optional
from urllib.parse import urlencode

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.system import SSOProvider
from app.models.user import User
from app.services.auth_service import (
    get_or_create_user_from_oauth,
    get_user_by_email,
    get_user_by_provider_id,
)

# Provider types that can drive an OIDC browser redirect flow.
OIDC_FAMILY = {"oidc", "azure_ad", "google_workspace"}

STATE_PREFIX = "provider:sso"


def _domain_from_email(email: str) -> str:
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid work email is required.")
    return email.rsplit("@", 1)[-1].strip().lower()


def _provider_login_id(provider: SSOProvider) -> str:
    """Stable provider key stored on the User row (one identity space per provider)."""
    return f"sso:{provider.id.hex}"


async def find_provider_for_email(db: AsyncSession, email: str) -> Optional[SSOProvider]:
    """Find an enabled SSO provider whose domain allow-list contains the email domain."""
    domain = _domain_from_email(email)
    result = await db.execute(select(SSOProvider).where(SSOProvider.is_enabled.is_(True)))
    providers = list(result.scalars().all())

    matches = [
        p for p in providers
        if domain in {d.strip().lower() for d in (p.domain_whitelist or [])}
    ]
    if not matches:
        return None
    # Prefer a provider explicitly marked default.
    matches.sort(key=lambda p: not p.is_default)
    return matches[0]


def _redirect_uri(provider: SSOProvider) -> str:
    return (provider.config or {}).get("redirect_uri") or settings.oauth2_redirect_uri


async def _resolve_oidc_endpoints(provider: SSOProvider) -> dict:
    """Resolve authorization/token/userinfo endpoints from explicit config or discovery."""
    if provider.provider_type not in OIDC_FAMILY:
        raise HTTPException(
            status_code=400,
            detail=f"'{provider.provider_type}' SSO does not support browser sign-in.",
        )

    config = provider.config or {}
    auth_ep = config.get("authorization_endpoint")
    token_ep = config.get("token_endpoint")
    userinfo_ep = config.get("userinfo_endpoint")

    if not (auth_ep and token_ep and userinfo_ep):
        issuer = config.get("issuer_url")
        if not issuer:
            raise HTTPException(
                status_code=400,
                detail="OIDC provider is missing 'issuer_url' or explicit endpoints.",
            )
        well_known = issuer.rstrip("/") + "/.well-known/openid-configuration"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(well_known)
                resp.raise_for_status()
                doc = resp.json()
        except Exception as exc:  # noqa: BLE001 — surface discovery failure clearly
            raise HTTPException(
                status_code=502,
                detail=f"Failed to load OIDC discovery document: {exc}",
            )
        auth_ep = auth_ep or doc.get("authorization_endpoint")
        token_ep = token_ep or doc.get("token_endpoint")
        userinfo_ep = userinfo_ep or doc.get("userinfo_endpoint")

    if not (auth_ep and token_ep and userinfo_ep):
        raise HTTPException(
            status_code=400,
            detail="OIDC provider configuration is incomplete (missing endpoints).",
        )
    return {
        "authorization_endpoint": auth_ep,
        "token_endpoint": token_ep,
        "userinfo_endpoint": userinfo_ep,
    }


async def build_authorization_url(provider: SSOProvider, state: str) -> str:
    """Build the OIDC authorization URL the browser is redirected to."""
    config = provider.config or {}
    client_id = config.get("client_id")
    if not client_id:
        raise HTTPException(status_code=400, detail="SSO provider is missing 'client_id'.")

    endpoints = await _resolve_oidc_endpoints(provider)
    scopes = config.get("scopes") or ["openid", "profile", "email"]
    params = {
        "client_id": client_id,
        "redirect_uri": _redirect_uri(provider),
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
    }
    return endpoints["authorization_endpoint"] + "?" + urlencode(params)


def make_state(provider: SSOProvider, nonce: str) -> str:
    """Encode the provider id into state so the callback can recover it."""
    return f"{STATE_PREFIX}:{provider.id.hex}:{nonce}"


def _provider_id_from_state(state: str) -> uuid.UUID:
    # Format: provider:sso:<provider_hex>:<nonce>
    parts = (state or "").split(":")
    if len(parts) < 3 or parts[0] != "provider" or parts[1] != "sso":
        raise HTTPException(status_code=400, detail="Invalid SSO state.")
    try:
        return uuid.UUID(parts[2])
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid SSO state provider id.")


def _map_userinfo(config: dict, userinfo: dict) -> dict:
    mapping = (config or {}).get("attribute_mapping") or {}
    email = userinfo.get(mapping.get("email", "email")) or userinfo.get("email")
    first = userinfo.get(mapping.get("first_name", "given_name"))
    last = userinfo.get(mapping.get("last_name", "family_name"))
    name = userinfo.get("name") or " ".join(p for p in [first, last] if p) or None
    return {
        "sub": userinfo.get("sub") or userinfo.get("id"),
        "email": email,
        "name": name,
        "picture": userinfo.get("picture"),
    }


async def complete_sso_callback(db: AsyncSession, code: str, state: str) -> User:
    """Exchange the OIDC code, enforce policy, and return the linked/created user."""
    provider_id = _provider_id_from_state(state)
    provider = await db.get(SSOProvider, provider_id)
    if not provider or not provider.is_enabled:
        raise HTTPException(status_code=400, detail="SSO provider not found or disabled.")

    config = provider.config or {}
    client_id = config.get("client_id")
    client_secret = config.get("client_secret")
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="SSO provider credentials are not configured.")

    endpoints = await _resolve_oidc_endpoints(provider)
    redirect_uri = _redirect_uri(provider)

    # Exchange authorization code for tokens.
    async with AsyncOAuth2Client(
        client_id=client_id,
        client_secret=client_secret,
        token_endpoint=endpoints["token_endpoint"],
    ) as client:
        token = await client.fetch_token(
            endpoints["token_endpoint"],
            code=code,
            redirect_uri=redirect_uri,
        )

    access_token = token.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token received from SSO provider.")

    # Fetch userinfo.
    async with httpx.AsyncClient(timeout=10) as http:
        resp = await http.get(
            endpoints["userinfo_endpoint"],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        userinfo = resp.json()

    mapped = _map_userinfo(config, userinfo)
    email = mapped["email"]
    sub = mapped["sub"]
    if not email or not sub:
        raise HTTPException(status_code=400, detail="SSO provider did not return an email/subject.")

    # Enforce the domain allow-list against the *authenticated* email.
    domain = email.rsplit("@", 1)[-1].lower()
    allowed = {d.strip().lower() for d in (provider.domain_whitelist or [])}
    if allowed and domain not in allowed:
        raise HTTPException(
            status_code=403,
            detail="Your email domain is not permitted for this SSO provider.",
        )

    # Enforce provisioning policy: block first-time users when auto-provision is off.
    login_provider = _provider_login_id(provider)
    existing = await get_user_by_provider_id(db, login_provider, str(sub))
    if not existing:
        existing = await get_user_by_email(db, email)
    if not existing and not provider.auto_provision:
        raise HTTPException(
            status_code=403,
            detail="No account exists and auto-provisioning is disabled for this provider.",
        )

    return await get_or_create_user_from_oauth(
        db=db,
        provider=login_provider,
        provider_id=str(sub),
        email=email,
        name=mapped.get("name"),
        picture=mapped.get("picture"),
    )
