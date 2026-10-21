"""Scientific Retrieval Endpoints (BM25, Dense Vector, Hybrid RRF)."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
import pyarrow.parquet as pq

from researchgraph.core.config import settings
from researchgraph.schemas.api import (
    RetrievalHitModel,
    RetrievalRequest,
    RetrievalResponse,
)
from pipelines.embeddings.bm25 import BM25Index
from pipelines.embeddings.models import get_encoder
from pipelines.embeddings.pipeline import EmbeddingPipeline, RepresentationType
from pipelines.embeddings.retrieval import DenseVectorIndex, ScientificRetrievalEngine

router = APIRouter(prefix="/retrieval", tags=["Semantic Retrieval"])

_retrieval_engine: Optional[ScientificRetrievalEngine] = None


def get_retrieval_engine() -> ScientificRetrievalEngine:
    global _retrieval_engine
    if _retrieval_engine is None:
        # Load sample chunks into index
        bm25 = BM25Index()
        chunks_path = settings.chunks_parquet_path
        encoder = get_encoder(model_name_or_key=settings.embedding_model_key)

        records = []
        if chunks_path.exists():
            table = pq.read_table(str(chunks_path))
            n = min(300, table.num_rows)
            cids = table["chunk_id"].to_pylist()[:n]
            texts = table["text"].to_pylist()[:n]
            pids = table["canonical_id"].to_pylist()[:n]

            for cid, txt, pid in zip(cids, texts, pids):
                bm25.add_document(cid, txt, metadata={"paper_id": pid})

            bm25.build()
            encoder.fit(texts)
            vecs = encoder.encode(texts)

            for cid, txt, pid, vec in zip(cids, texts, pids, vecs):
                records.append(
                    EmbeddingPipeline().encoder.spec and
                    EmbeddingPipeline().generate_statement_embeddings  # just ensure module loaded
                )

            dense_records = []
            from pipelines.embeddings.pipeline import EmbeddingRecord
            for cid, txt, pid, vec in zip(cids, texts, pids, vecs):
                dense_records.append(
                    EmbeddingRecord(
                        record_id=cid,
                        representation_type=RepresentationType.CHUNK,
                        source_text=txt,
                        source_text_hash="hash",
                        model_name=encoder.spec.model_name,
                        model_revision=encoder.spec.revision,
                        dimension=encoder.spec.dimension,
                        embedding=vec.tolist(),
                        metadata={"paper_id": pid},
                    )
                )

            dense_index = DenseVectorIndex(encoder=encoder)
            dense_index.build_from_records(dense_records)
            _retrieval_engine = ScientificRetrievalEngine(bm25_index=bm25, dense_index=dense_index, encoder=encoder)
        else:
            _retrieval_engine = ScientificRetrievalEngine()
    return _retrieval_engine


@router.post("/lexical", response_model=RetrievalResponse)
def search_lexical(
    request: RetrievalRequest,
    engine: ScientificRetrievalEngine = Depends(get_retrieval_engine),
) -> RetrievalResponse:
    """Execute pure Okapi BM25 lexical search."""
    t0 = time.perf_counter()
    hits = engine.retrieve_lexical(query=request.query, top_k=request.top_k)
    lat = (time.perf_counter() - t0) * 1000.0

    hit_models = [
        RetrievalHitModel(
            record_id=h.record_id,
            score=h.score,
            text=h.text,
            metadata=h.metadata,
            retrieval_method=h.retrieval_method,
        )
        for h in hits
    ]
    return RetrievalResponse(
        query=request.query,
        retrieval_method="bm25",
        hits_count=len(hit_models),
        hits=hit_models,
        latency_ms=round(lat, 2),
    )


@router.post("/dense", response_model=RetrievalResponse)
def search_dense(
    request: RetrievalRequest,
    engine: ScientificRetrievalEngine = Depends(get_retrieval_engine),
) -> RetrievalResponse:
    """Execute pure dense semantic vector retrieval."""
    t0 = time.perf_counter()
    hits = engine.retrieve_dense(
        query=request.query,
        top_k=request.top_k,
        filter_rep_type=request.filter_rep_type,
    )
    lat = (time.perf_counter() - t0) * 1000.0

    hit_models = [
        RetrievalHitModel(
            record_id=h.record_id,
            score=h.score,
            text=h.text,
            metadata=h.metadata,
            retrieval_method=h.retrieval_method,
        )
        for h in hits
    ]
    return RetrievalResponse(
        query=request.query,
        retrieval_method="dense_vector",
        hits_count=len(hit_models),
        hits=hit_models,
        latency_ms=round(lat, 2),
    )


@router.post("/hybrid", response_model=RetrievalResponse)
def search_hybrid(
    request: RetrievalRequest,
    engine: ScientificRetrievalEngine = Depends(get_retrieval_engine),
) -> RetrievalResponse:
    """Execute hybrid retrieval using Reciprocal Rank Fusion (RRF)."""
    t0 = time.perf_counter()
    hits = engine.retrieve_hybrid(
        query=request.query,
        top_k=request.top_k,
        filter_rep_type=request.filter_rep_type,
    )
    lat = (time.perf_counter() - t0) * 1000.0

    hit_models = [
        RetrievalHitModel(
            record_id=h.record_id,
            score=h.score,
            text=h.text,
            metadata=h.metadata,
            retrieval_method=h.retrieval_method,
        )
        for h in hits
    ]
    return RetrievalResponse(
        query=request.query,
        retrieval_method="hybrid_rrf",
        hits_count=len(hit_models),
        hits=hit_models,
        latency_ms=round(lat, 2),
    )


@router.post("/compare")
def compare_retrieval_strategies(
    request: RetrievalRequest,
    engine: ScientificRetrievalEngine = Depends(get_retrieval_engine),
) -> Dict[str, Any]:
    """Execute side-by-side comparison of lexical, dense, and hybrid retrieval."""
    result = engine.compare_retrieval(query=request.query, top_k=request.top_k)
    return {
        "query": result.query,
        "top_k": result.top_k,
        "lexical_latency_ms": result.lexical_latency_ms,
        "dense_latency_ms": result.dense_latency_ms,
        "hybrid_latency_ms": result.hybrid_latency_ms,
        "overlap_at_k": result.overlap_at_k,
        "lexical_hits": [{"id": h.record_id, "score": h.score} for h in result.lexical_hits],
        "dense_hits": [{"id": h.record_id, "score": h.score} for h in result.dense_hits],
        "hybrid_hits": [{"id": h.record_id, "score": h.score} for h in result.hybrid_hits],
    }
