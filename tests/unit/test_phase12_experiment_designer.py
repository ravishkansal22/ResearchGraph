"""Unit tests for Phase 12: Experiment Designer.

Verifies:
1. Operational experiment plan generation from research hypothesis.
2. Dataset requirements, sample sizes, and split protocols.
3. Step-by-step protocol procedures and component ablations.
4. Statistical significance controls and power testing specifications.
5. Resource and compute budget estimation.
6. Execution status remains PLANNED_READY_FOR_EXECUTION without fabricating execution.
"""

from __future__ import annotations

import pytest

from pipelines.experiment.designer import ExperimentDesigner
from pipelines.experiment.schema import ExperimentPlan
from pipelines.hypothesis.schema import (
    HypothesisValidationStatus,
    ResearchHypothesis,
)


class TestExperimentDesigner:
    """Test suite for empirical experiment protocol design."""

    @pytest.fixture
    def sample_hypothesis(self) -> ResearchHypothesis:
        return ResearchHypothesis(
            hypothesis_id="hyp_fl_exp_01",
            candidate_id="cand_fl_01",
            title="Transfer of Federated Learning to Mitigate Oncology Privacy Bottlenecks",
            research_problem="Multi-center clinical oncology predictive modeling",
            source_domain_method="Federated Learning",
            target_domain_problem="Data Privacy Constraints in Healthcare",
            proposed_mechanism="Decouple model parameter optimization from centralized data pooling using secure gradient aggregation.",
            transfer_rationale="Resolves institutional boundary constraints without central raw data transfer.",
            evidence_summary={
                "source_evidence": ["Evidence passage 1"],
                "target_evidence": ["Evidence passage 2"],
            },
            assumptions=["Client distributions satisfy non-iid Dirichlet bounds alpha >= 0.5."],
            expected_outcome="Maintains 95% AUC of centralized training with 0 MB raw data exchange.",
            failure_conditions=["Severe label skew alpha < 0.1 leads to gradient divergence."],
            baseline_methods=["Centralized ResNet-50", "Isolated Local Institutional Models"],
            independent_variables=["Aggregation protocol (FedAvg vs FedProx)", "Dirichlet non-iid skew alpha"],
            dependent_variables=["Test Set Macro-AUC", "Inter-node communication bytes"],
            falsification_criteria="Fails to improve Macro-AUC by at least 5% (p < 0.05 across 5 seeds) over local baseline.",
            required_experiments=["5-fold cross-validation on multi-center clinical dataset"],
            validation_status=HypothesisValidationStatus.REVIEW_PASSED,
            uncertainty_explanation="Clinical batch effects may affect convergence.",
        )

    def test_design_experiment_plan(self, sample_hypothesis):
        designer = ExperimentDesigner()
        plan = designer.design_experiment(sample_hypothesis)

        assert isinstance(plan, ExperimentPlan)
        assert plan.hypothesis_id == "hyp_fl_exp_01"
        assert len(plan.baseline_methods) >= 2
        assert len(plan.protocol_steps) >= 6
        assert len(plan.ablation_plan) >= 2
        assert len(plan.reproducibility_checklist) >= 4
        assert plan.dataset_requirements.sample_size_min >= 1000
        assert plan.statistical_protocol.alpha_significance_level == 0.05
        assert plan.statistical_protocol.random_seeds_count == 5
        assert plan.resource_estimate.estimated_gpu_hours > 0.0
        # Rigorous boundary: explicitly marked as planned, not fabricated as executed!
        assert plan.execution_status == "PLANNED_READY_FOR_EXECUTION"
        assert plan.explicit_rejection_criteria == sample_hypothesis.falsification_criteria
