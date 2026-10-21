"""Unit tests for Phase 8: Research-Gap and Novelty Verification.

Verifies:
1. ResearchGapVerifier pipeline and audit trail logging.
2. Direct precedent detection assigning EVIDENCE_AGAINST_GAP.
3. Supporting evidence identification without prior art assigning POSSIBLE_GAP.
4. Insufficient literature density assigning INSUFFICIENT_EVIDENCE.
5. Absolute refusal to declare VERIFIED_NOVEL.
6. Explicit corpus boundary limits retention in dossier.
"""

from __future__ import annotations

import pytest

from pipelines.embeddings.bm25 import BM25Index
from pipelines.embeddings.retrieval import ScientificRetrievalEngine
from pipelines.gap_verification.schema import (
    GapStatus,
    RelatedWorkRelation,
    ResearchGapDossier,
)
from pipelines.gap_verification.verifier import ResearchGapVerifier


class TestResearchGapVerifier:
    """Test suite for research gap verification and dossier generation."""

    @pytest.fixture
    def mock_retrieval_verifier(self) -> ResearchGapVerifier:
        bm25 = BM25Index()
        # Document 1: Solved precedent
        bm25.add_document(
            "doc_solved",
            "We propose federated learning with differential privacy for multi-hospital oncology clinical records",
            metadata={"paper_id": "rg_doi_solved"},
        )
        # Document 2: Open limitation
        bm25.add_document(
            "doc_open",
            "A critical open limitation in prompt injection defenses remains scalable runtime verification without latency overhead",
            metadata={"paper_id": "rg_doi_open"},
        )
        bm25.build()

        retrieval = ScientificRetrievalEngine(bm25_index=bm25)
        return ResearchGapVerifier(retrieval_engine=retrieval)

    def test_precedent_detected_evidence_against_gap(self, mock_retrieval_verifier):
        verifier = mock_retrieval_verifier
        dossier = verifier.verify_gap("federated learning differential privacy oncology records")

        assert dossier.final_status == GapStatus.EVIDENCE_AGAINST_GAP
        assert len(dossier.opposing_or_prior_work) > 0
        assert dossier.opposing_or_prior_work[0].relationship == RelatedWorkRelation.DIRECT_PRECEDENT
        assert "direct prior precedents" in dossier.confidence_rationale.lower()
        # Epistemic invariant: Never output VERIFIED_NOVEL
        assert dossier.final_status != "VERIFIED_NOVEL"

    def test_open_problem_detected_possible_gap(self, mock_retrieval_verifier):
        verifier = mock_retrieval_verifier
        dossier = verifier.verify_gap("prompt injection defenses scalable runtime verification latency")

        assert dossier.final_status == GapStatus.POSSIBLE_GAP
        assert len(dossier.supporting_evidence) > 0
        assert dossier.supporting_evidence[0].relationship == RelatedWorkRelation.SUPPORTING_EVIDENCE
        assert "possible research gap" in dossier.confidence_rationale.lower()
        assert "50 canonical papers" in dossier.corpus_coverage_limitations

    def test_sparse_query_insufficient_evidence(self, mock_retrieval_verifier):
        verifier = mock_retrieval_verifier
        dossier = verifier.verify_gap("exotic superconducting metamaterial quantum cryogenic phase")

        assert dossier.final_status == GapStatus.INSUFFICIENT_EVIDENCE
        assert "insufficient evidence" in dossier.confidence_rationale.lower()
        assert len(dossier.search_audit_trail) >= 2

    def test_audit_trail_completeness(self, mock_retrieval_verifier):
        verifier = mock_retrieval_verifier
        dossier = verifier.verify_gap("prompt injection defenses")

        strategies = {a.search_strategy for a in dossier.search_audit_trail}
        assert "bm25" in strategies
        assert "dense_vector" in strategies
        assert "kb_statements" in strategies
        for audit in dossier.search_audit_trail:
            assert audit.execution_time_ms >= 0.0
            assert audit.query_string == "prompt injection defenses"
