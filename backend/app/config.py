from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUTOOPS_", env_file=".env", case_sensitive=False)

    env: str = Field(default="local", description="Deployment environment label")
    db_url: str = Field(
        default="sqlite+aiosqlite:///./autoops.db",
        alias="DATABASE_URL",
        description="Database URL (async driver)",
    )
    gemini_api_key: str | None = Field(default=None, description="API key for Gemini")
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"], description="CORS allowlist")


settings = Settings()
