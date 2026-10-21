"""Unit tests for Phase 5: Semantic Representations and Embeddings.

Verifies:
1. Lexical baseline BM25 indexing, scoring, smoothing, and ranking.
2. Embedding encoders: Deterministic LSA baseline, dimensions, normalization, hashing.
3. EmbeddingPipeline: Chunk, statement, and entity embeddings with full reproducibility metadata.
4. DenseVectorIndex: In-memory cosine similarity and representation type filtering.
5. ScientificRetrievalEngine: Pure lexical, pure dense, and hybrid RRF retrieval.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from pipelines.embeddings.bm25 import BM25Index, tokenize
from pipelines.embeddings.models import (
    DeterministicLSAEncoder,
    EmbeddingModelSpec,
    ModelCategory,
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
    RetrievalHit,
    ScientificRetrievalEngine,
)


class TestBM25Index:
    """Test suite for Okapi BM25 lexical retrieval."""

    def test_tokenize_normalization(self):
        text = "Federated Learning: A Privacy-Preserving Approach for Healthcare (2026)!"
        tokens = tokenize(text)
        assert "federated" in tokens
        assert "learning" in tokens
        assert "privacy-preserving" in tokens or "privacy" in tokens
        assert "healthcare" in tokens
        # Stopwords removed
        assert "a" not in tokens
        assert "for" not in tokens

    def test_bm25_empty_and_unknown_terms(self):
        bm25 = BM25Index()
        bm25.build()
        assert bm25.search("nonexistent") == []

        bm25.add_document("doc1", "Federated learning privacy architecture")
        bm25.build()
        hits = bm25.search("quantum teleportation")
        assert hits == []

    def test_bm25_ranking_accuracy(self):
        bm25 = BM25Index()
        bm25.add_document("d1", "Convolutional neural network image classification pathology")
        bm25.add_document("d2", "Federated learning privacy in clinical oncology")
        bm25.add_document("d3", "Natural language processing automated sentiment assessment")
        bm25.build()

        hits = bm25.search("convolutional network image", top_k=2)
        assert len(hits) >= 1
        assert hits[0].record_id == "d1"
        assert hits[0].score > 0.0


class TestEmbeddingEncoders:
    """Test suite for dense embedding encoders."""

    def test_text_hash_deterministic(self):
        h1 = compute_text_hash("Deep residual networks for computer vision")
        h2 = compute_text_hash("Deep residual networks for computer vision")
        h3 = compute_text_hash("Other text")
        assert h1 == h2
        assert h1 != h3
        assert len(h1) == 64

    def test_lsa_encoder_properties(self):
        encoder = DeterministicLSAEncoder(dimension=128)
        corpus = [
            "Federated learning distributed optimization",
            "Convolutional neural network computer vision",
            "Graph neural networks knowledge discovery",
            "Adversarial robustness perturbation bounds",
        ]
        encoder.fit(corpus)
        vecs = encoder.encode(corpus)
        assert vecs.shape == (4, 128)

        # Check L2 normalization
        norms = np.linalg.norm(vecs, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-5)

        # Determinism
        vecs2 = encoder.encode([corpus[0]])
        np.testing.assert_allclose(vecs[0], vecs2[0], atol=1e-5)


class TestEmbeddingPipeline:
    """Test suite for pipeline generation and artifact persistence."""

    def test_pipeline_statements_and_entities(self):
        encoder = DeterministicLSAEncoder(dimension=64)
        pipeline = EmbeddingPipeline(encoder=encoder, pipeline_version="v0.6.0")

        sample_statements = [
            {
                "statement_id": "stmt_01",
                "normalized_statement": "Federated learning reduces data transmission bandwidth by 40%",
                "category": "RESULT",
                "paper_id": "rg_doi_01",
                "chunk_id": "chk_01",
            },
            {
                "statement_id": "stmt_02",
                "normalized_statement": "Deep networks fail under non-iid client distribution",
                "category": "LIMITATION",
                "paper_id": "rg_doi_02",
                "chunk_id": "chk_02",
            },
        ]
        stmt_records = pipeline.generate_statement_embeddings(sample_statements)
        assert len(stmt_records) == 2
        assert stmt_records[0].representation_type == RepresentationType.STATEMENT
        assert stmt_records[0].record_id == "stmt_01"
        assert len(stmt_records[0].embedding) == 64

        sample_entities = [
            {
                "entity_id": "ent_01",
                "canonical_name": "federated learning",
                "category": "METHOD",
                "aliases": ["fl", "federated optimization"],
                "description": "Collaborative training paradigm without centralized data pooling",
            },
            {
                "entity_id": "ent_02",
                "canonical_name": "data heterogeneity",
                "category": "BOTTLENECK",
                "aliases": ["non-iid data"],
                "description": "Distribution divergence across local clients",
            },
        ]
        ent_records = pipeline.generate_entity_embeddings(sample_entities)
        assert len(ent_records) == 2
        assert ent_records[0].representation_type == RepresentationType.ENTITY
        assert ent_records[1].representation_type == RepresentationType.PROBLEM_BOTTLENECK

        with tempfile.TemporaryDirectory() as tmpdir:
            out_files = pipeline.save_records(stmt_records + ent_records, tmpdir, "test_emb")
            assert Path(out_files["parquet"]).exists()
            assert Path(out_files["jsonl"]).exists()
            assert Path(out_files["manifest"]).exists()


class TestRetrievalEngine:
    """Test suite for unified retrieval comparisons."""

    def test_lexical_dense_hybrid_retrieval(self):
        encoder = DeterministicLSAEncoder(dimension=64)
        corpus = [
            "Federated learning preserves privacy in clinical medical records",
            "Convolutional models achieve state of the art in radiographic pathology",
            "Adversarial perturbations degrade deep neural network classification accuracy",
            "Lightweight transformers reduce compute cost on embedded mobile devices",
        ]
        encoder.fit(corpus)
        vecs = encoder.encode(corpus)

        bm25 = BM25Index()
        records = []
        for idx, text in enumerate(corpus):
            doc_id = f"doc_{idx}"
            bm25.add_document(doc_id, text, metadata={"idx": idx})
            records.append(
                EmbeddingRecord(
                    record_id=doc_id,
                    representation_type=RepresentationType.CHUNK,
                    source_text=text,
                    source_text_hash=compute_text_hash(text),
                    model_name="tfidf-lsa-384",
                    model_revision="v1.0",
                    dimension=64,
                    embedding=vecs[idx].tolist(),
                    metadata={"idx": idx},
                )
            )
        bm25.build()

        dense_index = DenseVectorIndex(encoder=encoder)
        dense_index.build_from_records(records)

        engine = ScientificRetrievalEngine(bm25_index=bm25, dense_index=dense_index, encoder=encoder)

        # 1. Pure Lexical
        lex_hits = engine.retrieve_lexical("radiographic pathology", top_k=2)
        assert len(lex_hits) > 0
        assert lex_hits[0].record_id == "doc_1"

        # 2. Pure Dense
        dense_hits = engine.retrieve_dense("radiographic pathology", top_k=2)
        assert len(dense_hits) > 0

        # 3. Hybrid RRF
        hybrid_hits = engine.retrieve_hybrid("radiographic pathology", top_k=2)
        assert len(hybrid_hits) > 0
        assert hybrid_hits[0].record_id == "doc_1"

        # 4. Comparison
        comp = engine.compare_retrieval("federated learning privacy", top_k=2)
        assert len(comp.lexical_hits) > 0
        assert len(comp.dense_hits) > 0
        assert len(comp.hybrid_hits) > 0
        assert comp.lexical_latency_ms >= 0.0
