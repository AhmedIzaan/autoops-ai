from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUTOOPS_", env_file=".env", case_sensitive=False)

    env: str = Field(default="local", description="Deployment environment label")
    db_url: str = Field(
        default="sqlite+aiosqlite:///./autoops.db",
        description="Database URL (async driver)",
    )
    storage_dir: str = Field(
        default="./storage/uploads",
        description="Directory for storing uploaded files and generated artifacts",
    )
    gemini_api_key: str | None = Field(default=None, description="API key for Gemini")
    allowed_origins: str = Field(default="*", description="CORS allowlist (comma-separated)")

    @property
    def cors_origins(self) -> list[str]:
        """Parse allowed_origins string into a list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # ── SMTP / Email settings ──────────────────────────────────────────────
    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP server hostname")
    smtp_port: int = Field(default=587, description="SMTP port (587=STARTTLS, 465=SSL)")
    smtp_username: str | None = Field(default=None, description="SMTP login username / sender address")
    smtp_password: str | None = Field(default=None, description="SMTP password or app-password")
    smtp_sender: str | None = Field(default=None, description="From: address (falls back to smtp_username)")
    send_emails: bool = Field(default=False, description="Set to true to actually send emails via SMTP")


settings = Settings()
