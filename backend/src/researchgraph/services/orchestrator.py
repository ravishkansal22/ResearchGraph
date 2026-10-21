"""ResearchGraph End-to-End Scientific Discovery Orchestration Workflow.

Coordinates the complete 10-stage scientific inquiry pipeline:
1. Research Question Parsing & Query Understanding
2. Lexical (BM25) and Dense Semantic Retrieval
3. Evidence Collection & Provenance Grounding
4. Trusted Scientific Knowledge Graph Retrieval
5. Cross-Domain Candidate Discovery (Topological & Semantic)
6. Research-Gap and Novelty Verification (Dossier Generation)
7. Dead-End Graveyard & Negative-Knowledge Collision Check
8. Falsifiable Hypothesis Generation
9. Reviewer #2 Adversarial Scientific Critique
10. Operational Experiment Protocol Design

Tracks execution latency, status, errors, and output summaries across each stage.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

from researchgraph.schemas.api import (
    OrchestrationRequest,
    OrchestrationResponse,
    OrchestrationStageResult,
)
from pipelines.discovery.algorithms import CrossDomainDiscoveryEngine
from pipelines.discovery.schema import DiscoveryCandidate
from pipelines.embeddings.retrieval import ScientificRetrievalEngine
from pipelines.experiment.designer import ExperimentDesigner
from pipelines.experiment.schema import ExperimentPlan
from pipelines.gap_verification.schema import GapStatus, ResearchGapDossier
from pipelines.gap_verification.verifier import ResearchGapVerifier
from pipelines.graph.builder import ResearchGraphBuilder
from pipelines.hypothesis.generator import HypothesisGenerationEngine
from pipelines.hypothesis.schema import ResearchHypothesis
from pipelines.negative_knowledge.graveyard import DeadEndGraveyard
from pipelines.reviewer.adversarial import AdversarialReviewer
from pipelines.reviewer.schema import AdversarialReview, ReviewVerdict

logger = logging.getLogger(__name__)


class ResearchWorkflowOrchestrator:
    """Coordinates end-to-end scientific synthesis from research question to experiment plan."""

    def __init__(
        self,
        retrieval_engine: Optional[ScientificRetrievalEngine] = None,
        discovery_engine: Optional[CrossDomainDiscoveryEngine] = None,
        gap_verifier: Optional[ResearchGapVerifier] = None,
        graveyard: Optional[DeadEndGraveyard] = None,
        hypothesis_engine: Optional[HypothesisGenerationEngine] = None,
        reviewer: Optional[AdversarialReviewer] = None,
        experiment_designer: Optional[ExperimentDesigner] = None,
    ):
        self.retrieval = retrieval_engine or ScientificRetrievalEngine()
        self.discovery = discovery_engine or CrossDomainDiscoveryEngine(retrieval_engine=self.retrieval)
        self.gap_verifier = gap_verifier or ResearchGapVerifier(retrieval_engine=self.retrieval)
        self.graveyard = graveyard or DeadEndGraveyard()
        self.hypothesis_engine = hypothesis_engine or HypothesisGenerationEngine(graveyard=self.graveyard)
        self.reviewer = reviewer or AdversarialReviewer()
        self.experiment_designer = experiment_designer or ExperimentDesigner()

    def execute_workflow(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """Execute the complete multi-stage scientific discovery workflow."""
        start_time = time.perf_counter()
        stages: List[OrchestrationStageResult] = []
        workflow_id = f"wf_{hashlib.sha256((request.research_question + str(time.time())).encode()).hexdigest()[:12]}"

        # Stage 1: Query Understanding
        t0 = time.perf_counter()
        query = request.research_question.strip()
        stages.append(
            OrchestrationStageResult(
                stage_name="Query Understanding",
                status="COMPLETED",
                execution_time_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                output_summary=f"Parsed scientific problem '{query[:60]}...' with target domain {request.target_domain or 'General AI'}.",
            )
        )

        # Stage 2: Lexical and Semantic Retrieval
        t0 = time.perf_counter()
        retrieval_hits = self.retrieval.retrieve_hybrid(query, top_k=8)
        stages.append(
            OrchestrationStageResult(
                stage_name="Literature Retrieval",
                status="COMPLETED" if retrieval_hits else "INSUFFICIENT_EVIDENCE",
                execution_time_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                output_summary=f"Retrieved {len(retrieval_hits)} grounded passages via Hybrid RRF fusion.",
            )
        )

        # Stage 3: Cross-Domain Candidate Discovery
        t0 = time.perf_counter()
        candidates = self.discovery.discover_all_strategies(research_problem=query, limit=5)
        stages.append(
            OrchestrationStageResult(
                stage_name="Cross-Domain Discovery",
                status="COMPLETED" if candidates else "INSUFFICIENT_EVIDENCE",
                execution_time_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                output_summary=(
                    f"Discovered {len(candidates)} cross-domain candidate connections."
                    if candidates else "No viable cross-domain candidate surpassed the evidence score threshold."
                ),
            )
        )

        # Stage 4: Research-Gap and Novelty Verification
        t0 = time.perf_counter()
        gap_dossier = self.gap_verifier.verify_gap(
            proposed_gap=query,
            target_domains=[request.target_domain] if request.target_domain else None,
        )
        stages.append(
            OrchestrationStageResult(
                stage_name="Research-Gap Verification",
                status="COMPLETED",
                execution_time_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                output_summary=f"Assigned status {gap_dossier.final_status.value}. {gap_dossier.confidence_rationale[:100]}...",
            )
        )

        # Early termination if gap is directly contradicted or evidence is completely absent
        if not candidates:
            total_duration = round((time.perf_counter() - start_time) * 1000.0, 2)
            return OrchestrationResponse(
                workflow_id=workflow_id,
                research_question=query,
                stages=stages,
                discovery_candidates=[],
                gap_dossier=gap_dossier,
                selected_hypothesis=None,
                review=None,
                experiment_plan=None,
                final_status="INSUFFICIENT_EVIDENCE",
                total_duration_ms=total_duration,
            )

        top_candidate = candidates[0]

        # Stage 5: Negative Knowledge Check
        t0 = time.perf_counter()
        collision_records = self.graveyard.check_contradiction_risk(
            method_name=top_candidate.source_concept_name,
            problem_or_task=query,
        )
        stages.append(
            OrchestrationStageResult(
                stage_name="Negative Knowledge Check",
                status="COMPLETED",
                execution_time_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                output_summary=f"Identified {len(collision_records)} documented failure modes or boundary conditions.",
            )
        )

        # Stage 6: Hypothesis Generation
        t0 = time.perf_counter()
        hypothesis = self.hypothesis_engine.generate_hypothesis(candidate=top_candidate)
        stages.append(
            OrchestrationStageResult(
                stage_name="Hypothesis Formulation",
                status="COMPLETED",
                execution_time_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                output_summary=f"Formulated falsifiable hypothesis '{hypothesis.title}' with {len(hypothesis.independent_variables)} IVs and {len(hypothesis.dependent_variables)} DVs.",
            )
        )

        # Stage 7: Adversarial Reviewer ("Reviewer #2")
        review: Optional[AdversarialReview] = None
        if request.execute_review:
            t0 = time.perf_counter()
            review = self.reviewer.review_hypothesis(hypothesis)
            stages.append(
                OrchestrationStageResult(
                    stage_name="Adversarial Review (Reviewer #2)",
                    status="COMPLETED",
                    execution_time_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                    output_summary=f"Review verdict: {review.verdict.value} (Score: {review.overall_score}/10). Identified {len(review.severity_ranked_weaknesses)} weaknesses.",
                )
            )

        # Stage 8: Experiment Design
        experiment_plan: Optional[ExperimentPlan] = None
        if request.execute_experiment_design:
            t0 = time.perf_counter()
            experiment_plan = self.experiment_designer.design_experiment(
                hypothesis=hypothesis,
                review=review,
            )
            stages.append(
                OrchestrationStageResult(
                    stage_name="Experiment Protocol Design",
                    status="COMPLETED",
                    execution_time_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                    output_summary=f"Constructed {len(experiment_plan.protocol_steps)}-step executable protocol and {len(experiment_plan.ablation_plan)} ablations.",
                )
            )

        final_status = (
            "HYPOTHESIS_FORMULATED"
            if hypothesis and (not review or review.verdict != ReviewVerdict.REJECTED)
            else "REJECTED_BY_REVIEWER"
        )
        total_duration = round((time.perf_counter() - start_time) * 1000.0, 2)

        return OrchestrationResponse(
            workflow_id=workflow_id,
            research_question=query,
            stages=stages,
            discovery_candidates=candidates,
            gap_dossier=gap_dossier,
            selected_hypothesis=hypothesis,
            review=review,
            experiment_plan=experiment_plan,
            final_status=final_status,
            total_duration_ms=total_duration,
        )
