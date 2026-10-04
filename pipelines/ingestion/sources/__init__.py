"""Source Adapters package for ResearchGraph literature collection."""

from pipelines.ingestion.sources.arxiv import ArxivAdapter
from pipelines.ingestion.sources.base import BaseSourceAdapter
from pipelines.ingestion.sources.crossref import CrossrefAdapter
from pipelines.ingestion.sources.openalex import OpenAlexAdapter
from pipelines.ingestion.sources.semantic_scholar import SemanticScholarAdapter

__all__ = [
    "BaseSourceAdapter",
    "OpenAlexAdapter",
    "SemanticScholarAdapter",
    "ArxivAdapter",
    "CrossrefAdapter",
]
