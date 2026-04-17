from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    MONGO_URL: str | None = None
    DB_LOCAL: str | None = None
    DB_NAME: str
    SECRET_KEY: str
    ALGORITHM: str

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    @property
    def mongo_url(self) -> str:
        return self.MONGO_URL or self.DB_LOCAL or "mongodb://localhost:27017"


settings = Settings()