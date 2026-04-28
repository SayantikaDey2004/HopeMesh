from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    DB_DEV: Optional[str] = None
    DB_LOCAL: Optional[str] = None
    DB_NAME: str
    SECRET_KEY: str
    ALGORITHM: str

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    @property
    def mongo_url(self) -> str:
        if self.DB_DEV:
            return self.DB_DEV
        if self.DB_LOCAL:
            return self.DB_LOCAL
        raise ValueError("Set DB_DEV or DB_LOCAL in .env")


settings = Settings()
