from dataclasses import dataclass
from typing import Dict, Any, Optional
from urllib.parse import urlencode
from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import HTTPException

from app.core.config import settings


SUPPORTED_PROVIDERS = {"auth0", "google", "microsoft", "github", "atlassian"}


@dataclass(frozen=True)
class ProviderConfig:
    """Resolved credentials/config for a single OAuth2 provider request."""
    provider: str
    client_id: str
    client_secret: str
    redirect_uri: str
    domain: Optional[str] = None
    tenant_id: Optional[str] = None
    audience: Optional[str] = None
    scopes: Optional[str] = None


class OAuth2Provider:
    def __init__(self):
        self.provider = settings.oauth2_provider
        self.client_id = settings.oauth2_client_id
        self.client_secret = settings.oauth2_client_secret
        self.redirect_uri = settings.oauth2_redirect_uri
        self.audience = settings.oauth2_audience or "api.atlassian.com"
        self.scopes = settings.oauth2_scopes or "read:jira-work read:confluence-content.all"

    # ── Provider resolution ─────────────────────────────────────────────
    def resolve(self, provider: Optional[str] = None) -> ProviderConfig:
        """Resolve credentials for the requested provider.

        Provider-specific OAUTH (e.g. GITHUB_CLIENT_ID) takes precedence. When the
        requested provider is the globally-configured default, the generic OAUTH2_*
        values are used as a fallback so single-provider deployments keep working.
        """
        provider = (provider or self.provider or "").lower()
        if provider not in SUPPORTED_PROVIDERS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported login provider: '{provider}'.",
            )

        overrides = {
            "github": (settings.github_client_id, settings.github_client_secret),
            "atlassian": (settings.atlassian_client_id, settings.atlassian_client_secret),
            "google": (settings.google_client_id, settings.google_client_secret),
            "microsoft": (settings.microsoft_client_id, settings.microsoft_client_secret),
        }
        client_id, client_secret = overrides.get(provider, (None, None))

        # Fall back to the generic creds only for the configured default provider.
        if provider == self.provider:
            client_id = client_id or settings.oauth2_client_id
            client_secret = client_secret or settings.oauth2_client_secret

        if not client_id or not client_secret:
            raise HTTPException(
                status_code=400,
                detail=f"{provider.capitalize()} login is not configured on this server.",
            )

        return ProviderConfig(
            provider=provider,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=self.redirect_uri,
            domain=settings.oauth2_domain,
            tenant_id=settings.oauth2_tenant_id,
            audience=self.audience,
            scopes=self.scopes,
        )

    # ── Authorization URL ───────────────────────────────────────────────
    def get_authorization_url(self, state: str, provider: Optional[str] = None) -> str:
        """Generate OAuth2 authorization URL for the given provider."""
        cfg = self.resolve(provider)
        if cfg.provider == "auth0":
            return self._get_auth0_auth_url(state, cfg)
        elif cfg.provider == "google":
            return self._get_google_auth_url(state, cfg)
        elif cfg.provider == "microsoft":
            return self._get_microsoft_auth_url(state, cfg)
        elif cfg.provider == "github":
            return self._get_github_auth_url(state, cfg)
        elif cfg.provider == "atlassian":
            return self._get_atlassian_auth_url(state, cfg)
        raise HTTPException(status_code=400, detail=f"Unsupported OAuth2 provider: {cfg.provider}")

    def _get_auth0_auth_url(self, state: str, cfg: ProviderConfig) -> str:
        if not cfg.domain:
            raise HTTPException(status_code=500, detail="Auth0 domain not configured")
        params = {
            "client_id": cfg.client_id,
            "redirect_uri": cfg.redirect_uri,
            "response_type": "code",
            "scope": "openid profile email",
            "state": state,
        }
        return f"https://{cfg.domain}/authorize?" + urlencode(params)

    def _get_google_auth_url(self, state: str, cfg: ProviderConfig) -> str:
        params = {
            "client_id": cfg.client_id,
            "redirect_uri": cfg.redirect_uri,
            "response_type": "code",
            "scope": "openid profile email",
            "state": state,
            "access_type": "offline",
        }
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)

    def _get_microsoft_auth_url(self, state: str, cfg: ProviderConfig) -> str:
        tenant_id = cfg.tenant_id or "common"
        params = {
            "client_id": cfg.client_id,
            "redirect_uri": cfg.redirect_uri,
            "response_type": "code",
            "scope": "openid profile email",
            "state": state,
        }
        return f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?" + urlencode(params)

    def _get_github_auth_url(self, state: str, cfg: ProviderConfig) -> str:
        params = {
            "client_id": cfg.client_id,
            "redirect_uri": cfg.redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
        return "https://github.com/login/oauth/authorize?" + urlencode(params)

    def _get_atlassian_auth_url(self, state: str, cfg: ProviderConfig) -> str:
        params = {
            "audience": cfg.audience,
            "client_id": cfg.client_id,
            "redirect_uri": cfg.redirect_uri,
            "response_type": "code",
            "scope": cfg.scopes,
            "prompt": "consent",
            "state": state,
        }
        return "https://auth.atlassian.com/authorize?" + urlencode(params)

    # ── Token exchange ──────────────────────────────────────────────────
    async def exchange_code_for_token(self, code: str, provider: Optional[str] = None) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        cfg = self.resolve(provider)
        token_urls = {
            "auth0": f"https://{cfg.domain}/oauth/token" if cfg.domain else None,
            "google": "https://oauth2.googleapis.com/token",
            "microsoft": f"https://login.microsoftonline.com/{cfg.tenant_id or 'common'}/oauth2/v2.0/token",
            "github": "https://github.com/login/oauth/access_token",
            "atlassian": "https://auth.atlassian.com/oauth/token",
        }
        token_url = token_urls.get(cfg.provider)
        if not token_url:
            raise HTTPException(status_code=400, detail=f"Unsupported OAuth2 provider: {cfg.provider}")

        async with AsyncOAuth2Client(
            client_id=cfg.client_id,
            client_secret=cfg.client_secret,
            token_endpoint=token_url,
        ) as client:
            return await client.fetch_token(
                token_url,
                code=code,
                redirect_uri=cfg.redirect_uri,
            )

    # ── User info ───────────────────────────────────────────────────────
    async def get_user_info(self, access_token: str, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get user information from OAuth2 provider."""
        cfg = self.resolve(provider)
        if cfg.provider == "auth0":
            return await self._get_auth0_user_info(access_token, cfg)
        elif cfg.provider == "google":
            return await self._get_google_user_info(access_token)
        elif cfg.provider == "microsoft":
            return await self._get_microsoft_user_info(access_token)
        elif cfg.provider == "github":
            return await self._get_github_user_info(access_token)
        elif cfg.provider == "atlassian":
            return await self._get_atlassian_user_info(access_token)
        raise HTTPException(status_code=400, detail=f"Unsupported OAuth2 provider: {cfg.provider}")

    async def _get_auth0_user_info(self, access_token: str, cfg: ProviderConfig) -> Dict[str, Any]:
        userinfo_url = f"https://{cfg.domain}/userinfo"
        async with AsyncOAuth2Client(token=access_token) as client:
            resp = await client.get(userinfo_url)
            return resp.json()

    async def _get_google_user_info(self, access_token: str) -> Dict[str, Any]:
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        async with AsyncOAuth2Client(token=access_token) as client:
            resp = await client.get(userinfo_url)
            return resp.json()

    async def _get_microsoft_user_info(self, access_token: str) -> Dict[str, Any]:
        userinfo_url = "https://graph.microsoft.com/v1.0/me"
        async with AsyncOAuth2Client(token=access_token) as client:
            resp = await client.get(userinfo_url)
            return resp.json()

    async def _get_github_user_info(self, access_token: str) -> Dict[str, Any]:
        user_url = "https://api.github.com/user"
        emails_url = "https://api.github.com/user/emails"

        async with AsyncOAuth2Client(token=access_token) as client:
            # Get user profile
            user_resp = await client.get(user_url)
            user_data = user_resp.json()

            # Get primary email
            emails_resp = await client.get(emails_url)
            emails_data = emails_resp.json()

            primary_email = None
            if isinstance(emails_data, list):
                primary_email = next(
                    (e["email"] for e in emails_data if e.get("primary")),
                    None,
                )
            primary_email = primary_email or user_data.get("email")

            return {
                "sub": str(user_data["id"]),
                "name": user_data.get("name"),
                "email": primary_email,
                "picture": user_data.get("avatar_url"),
                "login": user_data.get("login"),
            }

    async def _get_atlassian_user_info(self, access_token: str) -> Dict[str, Any]:
        userinfo_url = "https://api.atlassian.com/me"
        async with AsyncOAuth2Client(token=access_token) as client:
            resp = await client.get(userinfo_url)
            data = resp.json()
            # Normalize to the common shape used by get_or_create_user_from_oauth
            return {
                "sub": data.get("account_id") or data.get("sub"),
                "name": data.get("name"),
                "email": data.get("email"),
                "picture": data.get("picture"),
            }


# Global OAuth2 provider instance
oauth2_provider = OAuth2Provider()
