
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Test Intelligence API"
    app_env: str = "development"
    api_v1_prefix: str = "/api"

    # Database — SQLite (dev default) or PostgreSQL with asyncpg
    database_url: str = "sqlite+aiosqlite:///./aitis.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Jira Configuration
    jira_base_url: str | None = None
    jira_email: str | None = None
    jira_api_token: str | None = None

    # Authentication — secret_key MUST be set via environment
    secret_key: str = ""  # No default — must be provided
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # OAuth2 SSO Configuration
    oauth2_provider: str = "auth0"  # auth0, google, microsoft, github, atlassian
    oauth2_client_id: str | None = None
    oauth2_client_secret: str | None = None
    oauth2_domain: str | None = None  # For Auth0
    oauth2_tenant_id: str | None = None  # For Microsoft
    oauth2_audience: str | None = None  # For Atlassian
    oauth2_scopes: str | None = None  # For Atlassian
    oauth2_redirect_uri: str = "http://localhost:3000/auth/callback"

    # S3-compatible storage (for execution artifacts)
    s3_endpoint_url: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket_name: str = "aitis-artifacts"

    # ── Execution Worker (Phase 4) ────────────────────────────────
    # Docker settings for isolated Playwright execution
    docker_socket: str = "unix:///var/run/docker.sock"
    execution_container_image: str = "aitis-playwright-runner:latest"
    execution_cpu_limit: str = "1.0"          # CPU cores
    execution_memory_limit: str = "1g"        # Memory limit
    execution_timeout_default: int = 300       # Default timeout in seconds
    execution_max_concurrent: int = 4          # Max parallel containers
    execution_worker_concurrency: int = 2      # Worker concurrency (prefetch)
    execution_artifacts_dir: str = "/tmp/aitis-artifacts"
    execution_network_mode: str = "bridge"     # Docker network: bridge|none|host
    execution_allowed_networks: list[str] = []  # Networks containers can access

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def validate_startup(self) -> list[str]:
        """Validate critical settings at startup. Raises on fatal misconfig, returns warnings."""
        if not self.secret_key:
            raise RuntimeError(
                "SECRET_KEY is not set. "
                "Set the SECRET_KEY environment variable before starting the server."
            )

        warnings: list[str] = []

        if self.secret_key == "change-me-in-production" and self.app_env == "production":
            warnings.append("SECRET_KEY is still the default value — change it in production!")

        if self.app_env == "production":
            if not self.oauth2_client_id:
                warnings.append("OAUTH2_CLIENT_ID is not set — SSO login will not work")
            if not self.oauth2_client_secret:
                warnings.append("OAUTH2_CLIENT_SECRET is not set — SSO login will not work")

        # Provider-specific validation
        if self.oauth2_provider == "auth0" and not self.oauth2_domain:
            warnings.append("OAUTH2_DOMAIN is required when provider=auth0")
        if self.oauth2_provider == "microsoft" and not self.oauth2_tenant_id:
            warnings.append("OAUTH2_TENANT_ID is required when provider=microsoft")
        if self.oauth2_provider == "atlassian" and not self.oauth2_audience:
            warnings.append("OAUTH2_AUDIENCE is required when provider=atlassian")

        return warnings


settings = Settings()
