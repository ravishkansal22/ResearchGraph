"""ResearchGraph Phase 5: Unified Scientific Retrieval Engine.

Provides unified lexical (BM25), dense semantic vector, and hybrid (Reciprocal Rank Fusion)
retrieval over the scientific literature corpus, entities, and statements.
Enables direct empirical comparisons between lexical and semantic retrieval strategies.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np

from pipelines.embeddings.bm25 import BM25Index, RetrievalHit
from pipelines.embeddings.models import BaseEmbeddingEncoder, get_encoder
from pipelines.embeddings.pipeline import EmbeddingRecord, RepresentationType

logger = logging.getLogger(__name__)


@dataclass
class RetrievalComparisonResult:
    """Diagnostic comparison between lexical, dense semantic, and hybrid retrieval."""
    query: str
    top_k: int
    lexical_hits: List[RetrievalHit]
    dense_hits: List[RetrievalHit]
    hybrid_hits: List[RetrievalHit]
    lexical_latency_ms: float
    dense_latency_ms: float
    hybrid_latency_ms: float
    overlap_at_k: float  # Jaccard overlap between top-k lexical and dense hits
    rank_correlation: float  # Spearman/Rank consistency estimate


class DenseVectorIndex:
    """In-memory dense vector index utilizing normalized inner product (cosine similarity)."""

    def __init__(self, encoder: BaseEmbeddingEncoder):
        self.encoder = encoder
        self.record_ids: List[str] = []
        self.texts: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.matrix: Optional[np.ndarray] = None  # (N, D) normalized vectors
        self.rep_types: List[str] = []

    def build_from_records(self, records: List[EmbeddingRecord]) -> None:
        """Populate the vector index from pre-computed EmbeddingRecord objects."""
        if not records:
            return

        self.record_ids = [r.record_id for r in records]
        self.texts = [r.source_text for r in records]
        self.metadatas = [r.metadata for r in records]
        self.rep_types = [r.representation_type.value for r in records]

        vectors = np.array([r.embedding for r in records], dtype=np.float32)
        # Ensure L2 normalization
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        self.matrix = (vectors / norms).astype(np.float32)

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_rep_type: Optional[str] = None,
    ) -> List[RetrievalHit]:
        """Search the dense vector index using cosine similarity."""
        if self.matrix is None or len(self.record_ids) == 0:
            return []

        query_vec = self.encoder.encode([query], is_query=True)  # (1, D)
        scores = np.dot(self.matrix, query_vec.T).squeeze()  # (N,)

        if filter_rep_type:
            # Mask out records not matching rep_type
            for idx, r_type in enumerate(self.rep_types):
                if r_type != filter_rep_type:
                    scores[idx] = -1e9

        top_indices = np.argsort(scores)[::-1][:top_k]
        hits: List[RetrievalHit] = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= -1e8:
                continue
            hits.append(
                RetrievalHit(
                    record_id=self.record_ids[idx],
                    score=round(score, 4),
                    text=self.texts[idx],
                    metadata={
                        **self.metadatas[idx],
                        "representation_type": self.rep_types[idx],
                    },
                    retrieval_method="dense_vector",
                )
            )
        return hits


class ScientificRetrievalEngine:
    """Unified scientific retrieval engine orchestrating lexical, dense, and hybrid strategies."""

    def __init__(
        self,
        bm25_index: Optional[BM25Index] = None,
        dense_index: Optional[DenseVectorIndex] = None,
        encoder: Optional[BaseEmbeddingEncoder] = None,
    ):
        self.bm25_index = bm25_index or BM25Index()
        self.encoder = encoder or get_encoder()
        self.dense_index = dense_index or DenseVectorIndex(self.encoder)

    def retrieve_lexical(self, query: str, top_k: int = 10) -> List[RetrievalHit]:
        """Run pure BM25 lexical retrieval."""
        return self.bm25_index.search(query=query, top_k=top_k)

    def retrieve_dense(
        self,
        query: str,
        top_k: int = 10,
        filter_rep_type: Optional[str] = None,
    ) -> List[RetrievalHit]:
        """Run pure dense semantic vector retrieval."""
        return self.dense_index.search(query=query, top_k=top_k, filter_rep_type=filter_rep_type)

    def retrieve_hybrid(
        self,
        query: str,
        top_k: int = 10,
        rrf_k: int = 60,
        filter_rep_type: Optional[str] = None,
    ) -> List[RetrievalHit]:
        """Run hybrid retrieval fusing BM25 and dense results via Reciprocal Rank Fusion (RRF)."""
        lexical_hits = self.retrieve_lexical(query=query, top_k=top_k * 2)
        dense_hits = self.retrieve_dense(query=query, top_k=top_k * 2, filter_rep_type=filter_rep_type)

        rrf_scores: Dict[str, float] = {}
        hit_records: Dict[str, RetrievalHit] = {}

        # 1. Lexical ranks
        for rank, hit in enumerate(lexical_hits):
            rrf_scores[hit.record_id] = rrf_scores.get(hit.record_id, 0.0) + (1.0 / (rrf_k + rank + 1))
            hit_records[hit.record_id] = hit

        # 2. Dense ranks
        for rank, hit in enumerate(dense_hits):
            rrf_scores[hit.record_id] = rrf_scores.get(hit.record_id, 0.0) + (1.0 / (rrf_k + rank + 1))
            hit_records[hit.record_id] = hit

        # Sort by composite RRF score
        sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        hybrid_hits: List[RetrievalHit] = []

        for record_id, score in sorted_items:
            orig = hit_records[record_id]
            hybrid_hits.append(
                RetrievalHit(
                    record_id=record_id,
                    score=round(score, 5),
                    text=orig.text,
                    metadata=orig.metadata,
                    retrieval_method="hybrid_rrf",
                )
            )

        return hybrid_hits

    def compare_retrieval(
        self,
        query: str,
        top_k: int = 10,
    ) -> RetrievalComparisonResult:
        """Execute and benchmark lexical, dense, and hybrid strategies side-by-side."""
        t0 = time.perf_counter()
        lex_hits = self.retrieve_lexical(query, top_k=top_k)
        t_lex = (time.perf_counter() - t0) * 1000.0

        t0 = time.perf_counter()
        dense_hits = self.retrieve_dense(query, top_k=top_k)
        t_dense = (time.perf_counter() - t0) * 1000.0

        t0 = time.perf_counter()
        hybrid_hits = self.retrieve_hybrid(query, top_k=top_k)
        t_hybrid = (time.perf_counter() - t0) * 1000.0

        # Calculate Jaccard overlap between lexical and dense hits
        lex_ids = {h.record_id for h in lex_hits}
        dense_ids = {h.record_id for h in dense_hits}
        union_ids = lex_ids.union(dense_ids)
        overlap = len(lex_ids.intersection(dense_ids)) / len(union_ids) if union_ids else 0.0

        return RetrievalComparisonResult(
            query=query,
            top_k=top_k,
            lexical_hits=lex_hits,
            dense_hits=dense_hits,
            hybrid_hits=hybrid_hits,
            lexical_latency_ms=round(t_lex, 2),
            dense_latency_ms=round(t_dense, 2),
            hybrid_latency_ms=round(t_hybrid, 2),
            overlap_at_k=round(overlap, 4),
            rank_correlation=0.0,
        )
