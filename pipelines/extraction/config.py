"""Extraction Pipeline Configuration (Phase 3).

Defines default paths, sampling parameters, schema versions, and model configurations
for scientific information extraction.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExtractionConfig(BaseSettings):
    """Configuration settings for scientific knowledge extraction."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment & Logging
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Versions
    EXTRACTION_SCHEMA_VERSION: str = "0.4.0"
    EXTRACTION_PIPELINE_VERSION: str = "v0.4.0"
    UPSTREAM_CHUNK_VERSION: str = "v0.3.0"

    # Sampling / Pilot Defaults
    DEFAULT_SAMPLE_SIZE: int = 75
    DEFAULT_RANDOM_SEED: int = 42
    MIN_CHUNK_CHARS: int = 40

    # Paths (relative to repo root)
    DATASET_STORAGE_ROOT: str = "./dataset"

    # LLM Settings (Optional / Configurable)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_MODEL_NAME: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.0
    LLM_TIMEOUT_SECONDS: float = 30.0
    LLM_MAX_RETRIES: int = 3

    # Evidence Grounding Thresholds
    MIN_EVIDENCE_CHARS: int = 3
    REQUIRE_EXACT_SPANS: bool = True
    ALLOW_SYSTEM_INFERENCES: bool = True

    @property
    def storage_root(self) -> Path:
        return Path(self.DATASET_STORAGE_ROOT).resolve()

    @property
    def v030_chunks_path(self) -> Path:
        return self.storage_root / "processed" / self.UPSTREAM_CHUNK_VERSION / "chunks.jsonl"

    @property
    def v030_documents_path(self) -> Path:
        return self.storage_root / "processed" / self.UPSTREAM_CHUNK_VERSION / "documents.jsonl"

    @property
    def output_dir(self) -> Path:
        return self.storage_root / "processed" / self.EXTRACTION_PIPELINE_VERSION

    @property
    def manifests_dir(self) -> Path:
        return self.storage_root / "manifests"

    @property
    def schemas_dir(self) -> Path:
        return self.storage_root / "schemas"

    def ensure_directories(self) -> None:
        """Ensure destination directories exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        self.schemas_dir.mkdir(parents=True, exist_ok=True)


config = ExtractionConfig()
