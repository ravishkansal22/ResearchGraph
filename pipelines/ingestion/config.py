"""Ingestion Pipeline Configuration.

Manages environment settings, rate limits, timeouts, and storage directory paths.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IngestionConfig(BaseSettings):
    """Configuration for scholarly data ingestion pipelines."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Dataset & Storage Paths
    DATASET_STORAGE_ROOT: str = "./dataset"
    SCHEMA_VERSION: str = "0.1.0"
    PIPELINE_VERSION: str = "0.1.0"
    DEFAULT_DATASET_VERSION: str = "v0.1.0"

    # API Settings & Polite Pool Email
    OPENALEX_MAILTO: Optional[str] = "researchgraph-dev@users.noreply.github.com"
    OPENALEX_API_KEY: Optional[str] = None
    SEMANTIC_SCHOLAR_API_KEY: Optional[str] = None
    ARXIV_USER_AGENT: str = "ResearchGraph/0.1.0 (mailto:researchgraph-dev@users.noreply.github.com)"
    CROSSREF_MAILTO: Optional[str] = "researchgraph-dev@users.noreply.github.com"

    # Request & Rate Limit Settings
    HTTP_TIMEOUT_SECONDS: float = 30.0
    MAX_RETRIES: int = 4
    BACKOFF_FACTOR: float = 1.5
    
    # Rate limits (seconds between requests for politeness)
    OPENALEX_RATE_LIMIT_DELAY: float = 0.1      # OpenAlex allows up to 10 req/sec with polite email
    SEMANTIC_SCHOLAR_RATE_LIMIT_DELAY: float = 1.0  # S2 unauthenticated: 1 req/sec
    ARXIV_RATE_LIMIT_DELAY: float = 3.0         # arXiv polite policy: 1 req per 3 sec
    CROSSREF_RATE_LIMIT_DELAY: float = 0.2      # Crossref polite pool: 5 req/sec

    # Full-text acquisition settings
    MAX_FULLTEXT_DOWNLOAD_BYTES: int = 50 * 1024 * 1024  # 50 MB max per PDF
    FULLTEXT_DOWNLOAD_TIMEOUT: float = 45.0

    @property
    def storage_root(self) -> Path:
        return Path(self.DATASET_STORAGE_ROOT).resolve()

    @property
    def raw_dir(self) -> Path:
        return self.storage_root / "raw"

    @property
    def interim_dir(self) -> Path:
        return self.storage_root / "interim"

    @property
    def processed_dir(self) -> Path:
        return self.storage_root / "processed"

    @property
    def fulltext_dir(self) -> Path:
        return self.storage_root / "fulltext"

    @property
    def manifests_dir(self) -> Path:
        return self.storage_root / "manifests"

    @property
    def schemas_dir(self) -> Path:
        return self.storage_root / "schemas"

    def ensure_directories(self) -> None:
        """Create standard dataset storage directories if they do not exist."""
        for d in [
            self.raw_dir / "openalex",
            self.raw_dir / "semantic_scholar",
            self.raw_dir / "arxiv",
            self.raw_dir / "crossref",
            self.interim_dir,
            self.processed_dir,
            self.fulltext_dir,
            self.manifests_dir,
            self.schemas_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)


config = IngestionConfig()
