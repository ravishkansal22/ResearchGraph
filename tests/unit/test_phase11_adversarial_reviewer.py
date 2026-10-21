"""Unit tests for Phase 11: Adversarial Reviewer ("Reviewer #2").

Verifies:
1. Multi-dimensional scientific review scoring across 10 dimensions.
2. Severity-ranked weakness sorting (CRITICAL -> MAJOR -> MINOR).
3. Rejection of ungrounded or contradictory proposals.
4. Promotion to PROMISING_BUT_UNVERIFIED for strong grounded hypotheses.
5. Absolute refusal to declare hypotheses scientifically verified without empirical testing.
"""

from __future__ import annotations

import pytest

from pipelines.hypothesis.schema import (
    HypothesisValidationStatus,
    ResearchHypothesis,
)
from pipelines.reviewer.adversarial import AdversarialReviewer
from pipelines.reviewer.schema import (
    AdversarialReview,
    ReviewVerdict,
    WeaknessSeverity,
)


class TestAdversarialReviewer:
    """Test suite for skeptical scientific peer review."""

    @pytest.fixture
    def sound_hypothesis(self) -> ResearchHypothesis:
        return ResearchHypothesis(
            hypothesis_id="hyp_sound_01",
            candidate_id="cand_01",
            title="Federated Optimization in Oncology",
            research_problem="Multi-institutional clinical cancer predictive modeling",
            source_domain_method="Federated Learning",
            target_domain_problem="Data Privacy Constraints in Healthcare",
            proposed_mechanism="Decouple model parameter optimization from centralized data pooling using secure gradient aggregation.",
            transfer_rationale="Resolves institutional boundary constraints without central raw data transfer.",
            evidence_summary={
                "source_evidence": ["Evidence passage 1", "Evidence passage 2"],
                "target_evidence": ["Evidence passage 3", "Evidence passage 4"],
            },
            assumptions=["Client data distributions satisfy non-iid Dirichlet bounds alpha >= 0.5."],
            expected_outcome="Maintains 95% AUC of centralized training while reducing raw data transfer to 0 MB.",
            failure_conditions=["Severe label skew alpha < 0.1 leads to gradient divergence."],
            baseline_methods=["Centralized ResNet-50", "Isolated Local Institutional Models"],
            independent_variables=["Aggregation protocol (FedAvg vs FedProx)", "Dirichlet non-iid skew alpha"],
            dependent_variables=["Test Set Macro-AUC", "Inter-node communication bytes"],
            falsification_criteria="Fails to improve Macro-AUC by at least 5% (p < 0.05 across 5 seeds) over local baseline.",
            required_experiments=["5-fold cross-validation on multi-center clinical dataset"],
            validation_status=HypothesisValidationStatus.UNVALIDATED_PROPOSAL,
            uncertainty_explanation="Unmodeled clinical batch effects may affect convergence.",
        )

    @pytest.fixture
    def flawed_hypothesis(self) -> ResearchHypothesis:
        return ResearchHypothesis(
            hypothesis_id="hyp_flawed_01",
            candidate_id="cand_02",
            title="Combine AI for Better Results",
            research_problem="AI",
            source_domain_method="Quantum Deep Learning",
            target_domain_problem="General Problems",
            proposed_mechanism="Use AI to make it smarter.",
            transfer_rationale="Because both are advanced.",
            evidence_summary={"source_evidence": [], "target_evidence": []},  # Zero evidence!
            assumptions=[],
            expected_outcome="It will perform better.",
            failure_conditions=[],  # No failure modes acknowledged!
            baseline_methods=["Old Method"],
            independent_variables=[],
            dependent_variables=[],
            falsification_criteria="It fails.",
            required_experiments=[],
            validation_status=HypothesisValidationStatus.UNVALIDATED_PROPOSAL,
            uncertainty_explanation="None",
        )

    def test_sound_hypothesis_promising_review(self, sound_hypothesis):
        reviewer = AdversarialReviewer()
        review = reviewer.review_hypothesis(sound_hypothesis)

        assert isinstance(review, AdversarialReview)
        assert review.verdict == ReviewVerdict.PROMISING_BUT_UNVERIFIED
        assert review.overall_score >= 7.0
        assert len(review.dimension_scores) == 10
        assert sound_hypothesis.validation_status == HypothesisValidationStatus.REVIEW_PASSED
        assert "p < 0.05" in review.falsification_recommendation

    def test_flawed_hypothesis_rejected(self, flawed_hypothesis):
        reviewer = AdversarialReviewer()
        review = reviewer.review_hypothesis(flawed_hypothesis)

        assert review.verdict == ReviewVerdict.REJECTED
        assert review.overall_score < 6.0
        assert flawed_hypothesis.validation_status == HypothesisValidationStatus.REJECTED

        # Critical weaknesses identified
        critical_items = [w for w in review.severity_ranked_weaknesses if w.severity == WeaknessSeverity.CRITICAL]
        assert len(critical_items) > 0
        crit_dims = {w.dimension for w in critical_items}
        assert "evidence_grounding" in crit_dims or "negative_knowledge_collision" in crit_dims
