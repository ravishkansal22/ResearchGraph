"""Configuration for the ResearchGraph Scientific Knowledge Base Pipeline.

Defines input artifact sources, target output directories, and execution parameters.
Schema Version: 0.5.0
"""

from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, Field


class KnowledgeBaseConfig(BaseModel):
    """Runtime configuration for knowledge base ingestion and building."""

    kb_version: str = Field(default="v0.5.1", description="Target knowledge base release version")
    schema_version: str = Field(default="0.5.1", description="Schema definition version")

    # Upstream data sources
    papers_path: Path = Field(
        default=Path("dataset/processed/v0.1.0/canonical_papers.jsonl"),
        description="Path to Phase 1 canonical papers",
    )
    chunks_path: Path = Field(
        default=Path("dataset/processed/v0.3.0/chunks.jsonl"),
        description="Path to Phase 2 processed chunks",
    )
    extractions_v040_records_path: Path = Field(
        default=Path("dataset/processed/v0.4.0/extracted_records.jsonl"),
        description="Path to Phase 3 v0.4.0 extracted records",
    )
    extractions_v040_relationships_path: Path = Field(
        default=Path("dataset/processed/v0.4.0/extracted_relationships.jsonl"),
        description="Path to Phase 3 v0.4.0 extracted relationships",
    )
    extractions_v041_records_path: Path = Field(
        default=Path("dataset/processed/v0.4.1/extracted_records.jsonl"),
        description="Path to Phase 3 v0.4.1 extracted records",
    )

    # Target persistence directory
    output_dir: Path = Field(
        default=Path("dataset/processed/v0.5.1"),
        description="Target directory for versioned knowledge base artifacts",
    )
    manifest_dir: Path = Field(
        default=Path("dataset/manifests"),
        description="Directory for build manifests and quality reports",
    )

    # Ingestion controls
    ingest_v040_records: bool = Field(default=True, description="Whether to ingest v0.4.0 baseline extractions")
    ingest_v041_records: bool = Field(default=True, description="Whether to ingest v0.4.1 experimental extractions")
    ingest_v040_relationships: bool = Field(default=True, description="Whether to ingest v0.4.0 relationships")
    save_parquet: bool = Field(default=True, description="Whether to export Parquet analytical snapshots")
    save_sqlite: bool = Field(default=True, description="Whether to populate SQLite relational database")
