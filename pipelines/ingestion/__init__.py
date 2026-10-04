"""ResearchGraph Ingestion Pipeline Package."""

from pipelines.ingestion.config import config
from pipelines.ingestion.pipeline import LiteratureIngestionPipeline

__all__ = ["config", "LiteratureIngestionPipeline"]
