"""Health, Readiness, and Version Information Endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pipelines.embeddings.models import MODEL_REGISTRY

from researchgraph.core.config import settings
from researchgraph.schemas.api import HealthResponse, VersionsResponse

router = APIRouter(tags=["System & Health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """System health status and storage artifact availability."""
    sqlite_ok = Path(settings.sqlite_db_path).exists()
    chunks_ok = Path(settings.chunks_parquet_path).exists()
    embeddings_ok = Path(settings.embeddings_dir / "scientific_embeddings.parquet").exists()

    return HealthResponse(
        status="healthy" if (sqlite_ok and chunks_ok) else "degraded",
        app_name=settings.app_name,
        app_version=settings.app_version,
        environment=settings.environment,
        sqlite_available=sqlite_ok,
        chunks_available=chunks_ok,
        embeddings_available=embeddings_ok,
    )


@router.get("/ready")
def get_ready() -> dict[str, str]:
    """Readiness probe for container orchestration."""
    return {"status": "ready"}


@router.get("/versions", response_model=VersionsResponse)
def get_versions() -> VersionsResponse:
    """Corpus, knowledge base, and pipeline release versions."""
    return VersionsResponse(
        backend_version=settings.app_version,
    )


@router.get("/models")
def get_models() -> dict[str, Any]:
    """List registered embedding and representation models."""
    return {
        "active_model": settings.embedding_model_key,
        "device": settings.torch_device,
        "registered_models": {
            k: {
                "model_name": spec.model_name,
                "category": spec.category.value,
                "dimension": spec.dimension,
                "revision": spec.revision,
                "license": spec.license,
                "description": spec.description,
            }
            for k, spec in MODEL_REGISTRY.items()
        },
    }
