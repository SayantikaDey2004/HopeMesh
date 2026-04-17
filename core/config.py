from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    NODE_ENV: str = "dev"
    DB_DEV: Optional[str] = None
    DB_LOCAL: Optional[str] = None
    DB_PROD: Optional[str] = None
    DB_NAME: str
    SECRET_KEY: str
    ALGORITHM: str

    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / ".env"), extra="ignore")

    @property
    def env(self) -> str:
        return (self.NODE_ENV or "dev").strip().lower()

    @property
    def mongo_url(self) -> str:
        db_connection_uri = {
            "local": self.DB_LOCAL or "",
            "dev": self.DB_DEV or "",
            "prod": self.DB_PROD or "",
        }

        if self.env not in db_connection_uri or not db_connection_uri[self.env]:
            raise ValueError(f"Database URI is missing for environment: {self.env}")

        return db_connection_uri[self.env]


settings = Settings()