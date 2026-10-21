"""ResearchGraph Phase 5: Semantic Representations and Embeddings."""

from pipelines.embeddings.bm25 import BM25Document, BM25Index, RetrievalHit, tokenize
from pipelines.embeddings.models import (
    BaseEmbeddingEncoder,
    DeterministicLSAEncoder,
    EmbeddingModelSpec,
    ModelCategory,
    SentenceTransformerEncoder,
    compute_text_hash,
    get_encoder,
)
from pipelines.embeddings.pipeline import (
    EmbeddingPipeline,
    EmbeddingRecord,
    RepresentationType,
)
from pipelines.embeddings.retrieval import (
    DenseVectorIndex,
    RetrievalComparisonResult,
    ScientificRetrievalEngine,
)

__all__ = [
    "BM25Index",
    "BM25Document",
    "RetrievalHit",
    "tokenize",
    "EmbeddingModelSpec",
    "ModelCategory",
    "BaseEmbeddingEncoder",
    "DeterministicLSAEncoder",
    "SentenceTransformerEncoder",
    "compute_text_hash",
    "get_encoder",
    "RepresentationType",
    "EmbeddingRecord",
    "EmbeddingPipeline",
    "DenseVectorIndex",
    "RetrievalComparisonResult",
    "ScientificRetrievalEngine",
]
