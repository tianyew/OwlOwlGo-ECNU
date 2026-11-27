"""Server-only configuration; environment variables override backend/.env."""

from pathlib import Path
from typing import Literal
from uuid import UUID

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
    database_url: SecretStr = SecretStr("")
    rag_enabled: bool = False
    rag_ingest_user_ids: list[UUID] = Field(default_factory=list)
    rag_embedding_base_url: str = ""
    rag_embedding_api_key: SecretStr = SecretStr("")
    rag_embedding_model: str = "text-embedding-v4"
    rag_embedding_revision: str = "1"
    rag_embedding_dimensions: int = Field(default=1024, ge=1, le=16000)
    rag_embedding_batch_size: int = Field(default=10, ge=1, le=10)
    rag_embedding_timeout: float = Field(default=15, ge=1, le=60)
    owl_log_file: Path = BACKEND_ROOT / "logs" / "app.log"
    owl_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    owl_log_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    owl_log_backup_count: int = Field(default=5, ge=1)
    owl_account_file: Path = BACKEND_ROOT / "local-data" / "accounts.json"
    owl_learning_file: Path | None = None
    owl_secure_cookies: bool = False
    owl_seed_demo_account: bool = False
    owl_session_seconds: int = Field(default=7 * 24 * 60 * 60, ge=60, le=30 * 24 * 60 * 60)
    owl_auth_window_seconds: int = Field(default=300, ge=1, le=3600)
    owl_login_account_limit: int = Field(default=10, ge=1)
    owl_login_ip_limit: int = Field(default=60, ge=1)
    owl_register_ip_limit: int = Field(default=20, ge=1)
