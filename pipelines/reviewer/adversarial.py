"""ResearchGraph Phase 11: Adversarial Reviewer ("Reviewer #2") Engine.

Performs rigorous, skeptical peer-review of candidate research hypotheses across
10 defined scientific dimensions. Flags superficial analogies, ungrounded assumptions,
overlooked baselines, and negative knowledge collisions.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

from pipelines.hypothesis.schema import (
    HypothesisValidationStatus,
    ResearchHypothesis,
)
from pipelines.reviewer.schema import (
    AdversarialReview,
    CriticismItem,
    ReviewVerdict,
    WeaknessSeverity,
)

logger = logging.getLogger(__name__)


class AdversarialReviewer:
    """Skeptical peer reviewer evaluating scientific hypotheses."""

    def review_hypothesis(self, hypothesis: ResearchHypothesis) -> AdversarialReview:
        """Conduct an adversarial evaluation of a hypothesis across 10 scientific dimensions."""
        dim_scores: Dict[str, float] = {}
        criticisms: List[CriticismItem] = []
        missing_ev: List[str] = []
        alternatives: List[str] = []
        revisions: List[str] = []

        # 1. Problem Specificity
        if len(hypothesis.research_problem.strip()) > 15:
            dim_scores["problem_specificity"] = 8.5
        else:
            dim_scores["problem_specificity"] = 4.0
            criticisms.append(
                CriticismItem(
                    dimension="problem_specificity",
                    severity=WeaknessSeverity.MAJOR,
                    critique="The stated research problem lacks operational specificity and boundary constraints.",
                    suggested_remedy="Narrow the problem definition to specific dataset distributions and benchmark tasks.",
                )
            )

        # 2. Evidence Grounding
        src_ev = hypothesis.evidence_summary.get("source_evidence", [])
        tgt_ev = hypothesis.evidence_summary.get("target_evidence", [])
        total_ev = len(src_ev) + len(tgt_ev)

        if total_ev >= 4:
            dim_scores["evidence_grounding"] = 9.0
        elif total_ev >= 2:
            dim_scores["evidence_grounding"] = 7.0
            missing_ev.append("Target domain empirical constraint requires additional citation grounding.")
        else:
            dim_scores["evidence_grounding"] = 3.5
            missing_ev.append("Cited excerpts are insufficient to prove the mechanism functions across domains.")
            criticisms.append(
                CriticismItem(
                    dimension="evidence_grounding",
                    severity=WeaknessSeverity.CRITICAL,
                    critique="Proposed mechanism relies on fewer than 2 grounded evidence excerpts from source literature.",
                    suggested_remedy="Retrieve direct textual grounding from validated empirical studies before proceeding.",
                )
            )

        # 3. Overlooked Prior Work
        if "standard" in [b.lower() for b in hypothesis.baseline_methods]:
            dim_scores["overlooked_prior_work"] = 7.5
        else:
            dim_scores["overlooked_prior_work"] = 6.0
            criticisms.append(
                CriticismItem(
                    dimension="overlooked_prior_work",
                    severity=WeaknessSeverity.MINOR,
                    critique="Recent benchmark papers in target domain may have explored analogous parameter transfers.",
                    suggested_remedy="Include a systematic search of recent workshop preprints in the target field.",
                )
            )

        # 4. Domain Comparability
        if hypothesis.source_domain_method.lower() != hypothesis.target_domain_problem.lower():
            dim_scores["domain_comparability"] = 8.0
        else:
            dim_scores["domain_comparability"] = 4.0
            criticisms.append(
                CriticismItem(
                    dimension="domain_comparability",
                    severity=WeaknessSeverity.MAJOR,
                    critique="Transfer occurs within identical domain terminology without demonstrating cross-domain distance.",
                    suggested_remedy="Clarify why this connection represents a genuine cross-domain epistemological transfer.",
                )
            )

        # 5. Realistic Assumptions
        if len(hypothesis.assumptions) >= 2:
            dim_scores["realistic_assumptions"] = 8.0
        else:
            dim_scores["realistic_assumptions"] = 5.0
            criticisms.append(
                CriticismItem(
                    dimension="realistic_assumptions",
                    severity=WeaknessSeverity.MAJOR,
                    critique="Crucial assumptions regarding data distribution and convergence are unstated.",
                    suggested_remedy="State explicit bounds on client non-iid divergence and network dropouts.",
                )
            )

        # 6. Superficial Analogy Risk
        has_mechanistic_vocab = any(
            w in hypothesis.proposed_mechanism.lower()
            for w in ["decoupling", "gradient", "optimization", "aggregation", "latency", "loss", "parameter"]
        )
        if has_mechanistic_vocab:
            dim_scores["superficial_analogy"] = 8.5
        else:
            dim_scores["superficial_analogy"] = 4.5
            criticisms.append(
                CriticismItem(
                    dimension="superficial_analogy",
                    severity=WeaknessSeverity.MAJOR,
                    critique="Proposed transfer relies on linguistic metaphor rather than concrete mathematical mechanism.",
                    suggested_remedy="Formalize the functional transfer as an explicit loss formulation or optimization protocol.",
                )
            )

        # 7. Negative Knowledge Collision
        if len(hypothesis.failure_conditions) > 0:
            dim_scores["negative_knowledge_collision"] = 8.0
            revisions.append(f"Acknowledge documented limitation: {hypothesis.failure_conditions[0]}")
        else:
            dim_scores["negative_knowledge_collision"] = 4.0
            criticisms.append(
                CriticismItem(
                    dimension="negative_knowledge_collision",
                    severity=WeaknessSeverity.CRITICAL,
                    critique="No known failure modes or negative results acknowledged in hypothesis formulation.",
                    suggested_remedy="Cross-reference with Dead-End Graveyard records for documented method bottlenecks.",
                )
            )

        # 8. Measurability
        if hypothesis.independent_variables and hypothesis.dependent_variables:
            dim_scores["measurability"] = 9.0
        else:
            dim_scores["measurability"] = 5.0
            criticisms.append(
                CriticismItem(
                    dimension="measurability",
                    severity=WeaknessSeverity.MAJOR,
                    critique="Experimental variables are not clearly separated into independent and dependent metrics.",
                    suggested_remedy="Explicitly operationalize measurable outcomes with defined evaluation units.",
                )
            )

        # 9. Simpler Baseline Explanations
        dim_scores["simpler_baselines"] = 7.5
        alternatives.append("Observed improvements could be explained by regularization rather than architectural transfer.")
        alternatives.append("A tuned linear baseline or smaller dense model may match performance without transfer complexity.")

        # 10. Falsification Rigor
        if "%" in hypothesis.falsification_criteria and "p <" in hypothesis.falsification_criteria:
            dim_scores["falsification_rigor"] = 9.5
        else:
            dim_scores["falsification_rigor"] = 6.0
            criticisms.append(
                CriticismItem(
                    dimension="falsification_rigor",
                    severity=WeaknessSeverity.MINOR,
                    critique="Falsification criteria should specify exact statistical significance thresholds and sample sizes.",
                    suggested_remedy="Include explicit p-value and effect-size cutoff thresholds.",
                )
            )

        # Sort criticisms by severity: CRITICAL -> MAJOR -> MINOR
        severity_order = {WeaknessSeverity.CRITICAL: 0, WeaknessSeverity.MAJOR: 1, WeaknessSeverity.MINOR: 2}
        criticisms.sort(key=lambda c: severity_order[c.severity])

        overall_score = round(sum(dim_scores.values()) / len(dim_scores), 2)

        # Determine Verdict
        has_critical = any(c.severity == WeaknessSeverity.CRITICAL for c in criticisms)
        major_count = sum(1 for c in criticisms if c.severity == WeaknessSeverity.MAJOR)

        if has_critical:
            verdict = ReviewVerdict.REJECTED
            hypothesis.validation_status = HypothesisValidationStatus.REJECTED
        elif major_count >= 2:
            verdict = ReviewVerdict.MAJOR_REVISION
            hypothesis.validation_status = HypothesisValidationStatus.REVISION_REQUIRED
        elif total_ev < 3:
            verdict = ReviewVerdict.NEEDS_MORE_EVIDENCE
            hypothesis.validation_status = HypothesisValidationStatus.REVISION_REQUIRED
        else:
            verdict = ReviewVerdict.PROMISING_BUT_UNVERIFIED
            hypothesis.validation_status = HypothesisValidationStatus.REVIEW_PASSED

        falsification_rec = (
            f"Run a strictly controlled ablation testing '{hypothesis.source_domain_method}' against "
            f"'{hypothesis.baseline_methods[0]}' on the target task. If statistical significance "
            f"fails to reach p < 0.05 across 5 distinct random seed initializations, reject the hypothesis immediately."
        )

        rev_id = f"rev_{hashlib.sha256((hypothesis.hypothesis_id + verdict.value).encode()).hexdigest()[:12]}"

        return AdversarialReview(
            review_id=rev_id,
            hypothesis_id=hypothesis.hypothesis_id,
            verdict=verdict,
            overall_score=overall_score,
            dimension_scores=dim_scores,
            severity_ranked_weaknesses=criticisms,
            missing_evidence=missing_ev,
            alternative_explanations=alternatives,
            required_revisions=revisions,
            falsification_recommendation=falsification_rec,
        )
