from typing import Dict, Any, Optional
from urllib.parse import urlencode
from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import HTTPException

from app.core.config import settings


class OAuth2Provider:
    def __init__(self):
        self.provider = settings.oauth2_provider
        self.client_id = settings.oauth2_client_id
        self.client_secret = settings.oauth2_client_secret
        self.redirect_uri = settings.oauth2_redirect_uri
        self.audience = settings.oauth2_audience or "api.atlassian.com"
        self.scopes = settings.oauth2_scopes or "read:jira-work read:confluence-content.all"

    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth2 authorization URL"""
        if self.provider == "auth0":
            return self._get_auth0_auth_url(state)
        elif self.provider == "google":
            return self._get_google_auth_url(state)
        elif self.provider == "microsoft":
            return self._get_microsoft_auth_url(state)
        elif self.provider == "github":
            return self._get_github_auth_url(state)
        elif self.provider == "atlassian":
            return self._get_atlassian_auth_url(state)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported OAuth2 provider: {self.provider}")

    def _get_auth0_auth_url(self, state: str) -> str:
        domain = settings.oauth2_domain
        if not domain:
            raise HTTPException(status_code=500, detail="Auth0 domain not configured")

        return f"https://{domain}/authorize?" + "&".join([
            f"client_id={self.client_id}",
            f"redirect_uri={self.redirect_uri}",
            "response_type=code",
            "scope=openid profile email",
            f"state={state}",
        ])

    def _get_google_auth_url(self, state: str) -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth?" + "&".join([
            f"client_id={self.client_id}",
            f"redirect_uri={self.redirect_uri}",
            "response_type=code",
            "scope=openid profile email",
            f"state={state}",
            "access_type=offline",
        ])

    def _get_microsoft_auth_url(self, state: str) -> str:
        tenant_id = settings.oauth2_tenant_id or "common"
        return f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?" + "&".join([
            f"client_id={self.client_id}",
            f"redirect_uri={self.redirect_uri}",
            "response_type=code",
            "scope=openid profile email",
            f"state={state}",
        ])

    def _get_github_auth_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "user:email",
            "state": state,
        }
        return "https://github.com/login/oauth/authorize?" + urlencode(params)

    def _get_atlassian_auth_url(self, state: str) -> str:
        params = {
            "audience": self.audience,
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.scopes,
            "prompt": "consent",
            "state": state,
        }
        return "https://auth.atlassian.com/authorize?" + urlencode(params)

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        if self.provider == "auth0":
            return await self._exchange_auth0_code(code)
        elif self.provider == "google":
            return await self._exchange_google_code(code)
        elif self.provider == "microsoft":
            return await self._exchange_microsoft_code(code)
        elif self.provider == "github":
            return await self._exchange_github_code(code)
        elif self.provider == "atlassian":
            return await self._exchange_atlassian_code(code)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported OAuth2 provider: {self.provider}")

    async def _exchange_auth0_code(self, code: str) -> Dict[str, Any]:
        domain = settings.oauth2_domain
        token_url = f"https://{domain}/oauth/token"

        async with AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_endpoint=token_url,
        ) as client:
            token = await client.fetch_token(
                token_url,
                code=code,
                redirect_uri=self.redirect_uri,
            )
            return token

    async def _exchange_google_code(self, code: str) -> Dict[str, Any]:
        token_url = "https://oauth2.googleapis.com/token"

        async with AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_endpoint=token_url,
        ) as client:
            token = await client.fetch_token(
                token_url,
                code=code,
                redirect_uri=self.redirect_uri,
            )
            return token

    async def _exchange_microsoft_code(self, code: str) -> Dict[str, Any]:
        tenant_id = settings.oauth2_tenant_id or "common"
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

        async with AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_endpoint=token_url,
        ) as client:
            token = await client.fetch_token(
                token_url,
                code=code,
                redirect_uri=self.redirect_uri,
            )
            return token

    async def _exchange_github_code(self, code: str) -> Dict[str, Any]:
        token_url = "https://github.com/login/oauth/access_token"

        async with AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_endpoint=token_url,
        ) as client:
            token = await client.fetch_token(
                token_url,
                code=code,
                redirect_uri=self.redirect_uri,
            )
            return token

    async def _exchange_atlassian_code(self, code: str) -> Dict[str, Any]:
        token_url = "https://auth.atlassian.com/oauth/token"

        async with AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_endpoint=token_url,
        ) as client:
            token = await client.fetch_token(
                token_url,
                code=code,
                redirect_uri=self.redirect_uri,
            )
            return token

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from OAuth2 provider"""
        if self.provider == "auth0":
            return await self._get_auth0_user_info(access_token)
        elif self.provider == "google":
            return await self._get_google_user_info(access_token)
        elif self.provider == "microsoft":
            return await self._get_microsoft_user_info(access_token)
        elif self.provider == "github":
            return await self._get_github_user_info(access_token)
        elif self.provider == "atlassian":
            return await self._get_atlassian_user_info(access_token)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported OAuth2 provider: {self.provider}")

    async def _get_auth0_user_info(self, access_token: str) -> Dict[str, Any]:
        domain = settings.oauth2_domain
        userinfo_url = f"https://{domain}/userinfo"

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

            primary_email = next(
                (email["email"] for email in emails_data if email["primary"]),
                user_data.get("email")
            )

            return {
                "sub": str(user_data["id"]),
                "name": user_data.get("name"),
                "email": primary_email,
                "picture": user_data.get("avatar_url"),
                "login": user_data.get("login"),
            }


# Global OAuth2 provider instance
oauth2_provider = OAuth2Provider()