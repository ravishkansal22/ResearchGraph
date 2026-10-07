"""Full-text acquisition, candidate retrieval, and document validation package."""

from pipelines.ingestion.fulltext.acquirer import OnDemandFullTextAcquirer
from pipelines.ingestion.fulltext.collector import FullTextCollector
from pipelines.ingestion.fulltext.retrieval import MetadataCandidateRetriever
from pipelines.ingestion.fulltext.validator import PDFValidator

__all__ = [
    "FullTextCollector",
    "MetadataCandidateRetriever",
    "PDFValidator",
    "OnDemandFullTextAcquirer",
]
