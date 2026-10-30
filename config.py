import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    BOT_TOKEN: str = "DUMMY_TOKEN"
    DB_PATH: str = str(BASE_DIR / "skinparser.db")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
