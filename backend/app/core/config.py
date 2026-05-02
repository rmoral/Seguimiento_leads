from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://leads:changeme@db:5432/seguimiento_leads"
    JWT_SECRET: str = "change-this-to-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173"
    ENVIRONMENT: str = "development"
    REDIS_URL: str = "redis://redis:6379/0"

    # Gmail OAuth (Phase 2)
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    GMAIL_REDIRECT_URI: str = "http://localhost:8000/email-accounts/gmail/callback"
    OAUTH_FRONTEND_REDIRECT: str = "http://localhost:5173/settings"

    # Symmetric key for encrypting OAuth tokens at rest.
    # If empty, a deterministic dev key is derived from JWT_SECRET (NOT for prod).
    ENCRYPTION_KEY: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
