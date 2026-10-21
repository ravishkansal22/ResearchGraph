"""Unit tests for Phase 10: Hypothesis Generation Engine.

Verifies:
1. Hypothesis synthesis from discovery candidate.
2. Operationalization of independent and dependent variables.
3. Retention of baselines, failure conditions, and falsification criteria.
4. Epistemic status initialization as UNVALIDATED_PROPOSAL.
"""

from __future__ import annotations

import pytest

from pipelines.discovery.schema import (
    DiscoveryCandidate,
    DiscoveryScoreExplanation,
    DiscoveryStrategy,
)
from pipelines.hypothesis.generator import HypothesisGenerationEngine
from pipelines.hypothesis.schema import (
    HypothesisValidationStatus,
    ResearchHypothesis,
)


class TestHypothesisGenerationEngine:
    """Test suite for hypothesis formulation."""

    @pytest.fixture
    def sample_candidate(self) -> DiscoveryCandidate:
        return DiscoveryCandidate(
            candidate_id="disc_cand_test_01",
            strategy=DiscoveryStrategy.PROBLEM_TO_METHOD,
            source_concept_id="kb_ent_fl",
            source_concept_name="Federated Learning",
            source_domain="Security & Privacy",
            target_problem_id="kb_ent_oncol",
            target_problem_name="Multi-Center Clinical Oncology Records",
            target_domain="Healthcare & Oncology",
            proposed_mechanism="Decouple model parameter optimization from local clinical data storage via secure aggregation.",
            utility_rationale="Resolves institutional privacy bottlenecks in collaborative cancer modeling.",
            source_evidence=["Federated learning minimizes raw data transmission across institutions."],
            target_evidence=["Oncology modeling across hospitals is limited by strict data privacy regulations."],
            source_paper_ids=["paper_01"],
            target_paper_ids=["paper_02"],
            assumptions_required=["Local client updates converge under convex loss approximations."],
            known_limitations=["Performance drops under high non-iid partition skew."],
            disconfirmation_criteria="Fails to outperform local centralized baseline by 5% with p < 0.05.",
            score=DiscoveryScoreExplanation(
                semantic_relevance=0.8,
                evidence_support=0.75,
                cross_domain_distance=0.9,
                mechanistic_compatibility=0.85,
                composite_score=0.72,
                score_rationale="High cross-domain distance and grounded evidence.",
            ),
        )

    def test_generate_hypothesis(self, sample_candidate):
        engine = HypothesisGenerationEngine()
        hypothesis = engine.generate_hypothesis(sample_candidate)

        assert isinstance(hypothesis, ResearchHypothesis)
        assert hypothesis.candidate_id == "disc_cand_test_01"
        assert "Federated Learning" in hypothesis.title
        assert "Clinical Oncology" in hypothesis.title
        assert len(hypothesis.independent_variables) >= 2
        assert len(hypothesis.dependent_variables) >= 2
        assert len(hypothesis.baseline_methods) >= 2
        assert len(hypothesis.failure_conditions) >= 1
        assert "p < 0.05" in hypothesis.falsification_criteria
        assert hypothesis.validation_status == HypothesisValidationStatus.UNVALIDATED_PROPOSAL

        # Check retrieval from engine pool
        retrieved = engine.get_hypothesis(hypothesis.hypothesis_id)
        assert retrieved is not None
        assert retrieved.hypothesis_id == hypothesis.hypothesis_id
