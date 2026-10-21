"""ResearchGraph Backend Application Configuration.

Defines runtime settings, paths, model registry options, CORS policies,
and database connection parameters using Pydantic Settings v2.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Project Information
    app_name: str = "ResearchGraph Backend"
    app_version: str = "0.7.0"
    environment: str = "development"
    debug: bool = False

    # Server Bindings
    host: str = "0.0.0.0"
    port: int = 8000
    api_prefix: str = "/api/v1"

    # CORS Origins
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # Database & Storage Paths
    database_url: Optional[str] = None  # Fallback to sqlite if postgres is not configured
    sqlite_db_path: Path = Path("dataset/processed/v0.5.1/knowledge_base.db")
    chunks_parquet_path: Path = Path("dataset/processed/v0.3.0/chunks.parquet")
    embeddings_dir: Path = Path("dataset/processed/v0.6.0")
    reports_dir: Path = Path("research")

    # Embedding & Model Settings
    embedding_model_key: str = "tfidf-lsa-384"  # Default deterministic baseline
    torch_device: str = "cpu"
    enable_external_downloads: bool = False

    # External LLM / Service Settings (Offline / Fallback by default)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None


settings = Settings()
