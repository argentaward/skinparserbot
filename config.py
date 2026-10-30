import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = "/data/skinparser.db" if Path("/data").is_dir() else str(BASE_DIR / "skinparser.db")

class Settings(BaseSettings):
    BOT_TOKEN: str = "DUMMY_TOKEN"
    DB_PATH: str = DEFAULT_DB
    PROXY_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
