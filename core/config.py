from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    APP_NAME: str = "AI Powered Need Detection and Volunteer Matching"
    NODE_ENV: str = "dev"
    GENAI_API_KEY: str
    DB_URL: Optional[str] = None
    DB_DEV: Optional[str] = None
    DB_LOCAL: Optional[str] = None
    DB_PROD: Optional[str] = None
    DB_NAME: str
    SECRET_KEY: str
    ALGORITHM: str
    BREVO_API_KEY: Optional[str] = None
    EMAIL_BREVO_API_KEY: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    BREVO_SENDER_EMAIL: Optional[str] = None
    BREVO_SENDER_NAME: str = "Support Team"
    FRONTEND_URL: Optional[str] = None
    RESET_PASSWORD_URL: Optional[str] = None

    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / ".env"), extra="ignore")

    @property
    def env(self) -> str:
        return (self.NODE_ENV or "dev").strip().lower()

    @staticmethod
    def _clean(value: Optional[str]) -> str:
        return str(value or "").strip()

    @property
    def mongo_url(self) -> str:
        explicit_url = self._clean(self.DB_URL)
        if explicit_url:
            return explicit_url

        db_connection_uri = {
            "local": self._clean(self.DB_LOCAL),
            "dev": self._clean(self.DB_DEV),
            "prod": self._clean(self.DB_PROD),
        }

        if self.env not in db_connection_uri or not db_connection_uri[self.env]:
            raise ValueError(f"Database URI is missing for environment: {self.env}")

        return db_connection_uri[self.env]

    @property
    def brevo_api_key(self) -> Optional[str]:
        return self.EMAIL_BREVO_API_KEY or self.BREVO_API_KEY

    @property
    def reset_password_url(self) -> str:
        if self.RESET_PASSWORD_URL:
            return self.RESET_PASSWORD_URL

        if self.FRONTEND_URL:
            return f"{self.FRONTEND_URL.rstrip('/')}/reset-password"

        raise ValueError("Set RESET_PASSWORD_URL or FRONTEND_URL in environment")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()