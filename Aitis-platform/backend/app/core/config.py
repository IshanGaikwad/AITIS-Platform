
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Test Intelligence API"
    app_env: str = "development"
    api_v1_prefix: str = "/api"

    jira_base_url: str | None = None
    jira_email: str | None = None
    jira_api_token: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
