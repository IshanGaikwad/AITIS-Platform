
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Test Intelligence API"
    app_env: str = "development"
    api_v1_prefix: str = "/api"

    # Database
    database_url: str = "sqlite:///./app.db"

    # Jira Configuration
    jira_base_url: str | None = None
    jira_email: str | None = None
    jira_api_token: str | None = None

    # Authentication
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # OAuth2 SSO Configuration
    oauth2_provider: str = "auth0"  # auth0, google, microsoft, github, atlassian
    oauth2_client_id: str | None = None
    oauth2_client_secret: str | None = None
    oauth2_domain: str | None = None  # For Auth0
    oauth2_tenant_id: str | None = None  # For Microsoft
    oauth2_audience: str | None = None  # For Atlassian
    oauth2_scopes: str | None = None  # For Atlassian
    oauth2_redirect_uri: str = "http://localhost:3000/auth/callback"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
