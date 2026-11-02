"""Server-only configuration; environment variables override backend/.env."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    deepseek_api_key: SecretStr = SecretStr("")
    deepseek_model: str = "deepseek-flash"
    deepseek_timeout: float = Field(default=45, ge=1, le=120)
