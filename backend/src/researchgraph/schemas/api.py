"""Pydantic v2 Request and Response Schemas for ResearchGraph API."""

from __future__ import annotations

from typing import Any

from pipelines.discovery.schema import DiscoveryCandidate
from pipelines.experiment.schema import ExperimentPlan
from pipelines.gap_verification.schema import ResearchGapDossier
from pipelines.hypothesis.schema import ResearchHypothesis
from pipelines.reviewer.schema import AdversarialReview
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """System health and readiness status."""

    status: str = "healthy"
    app_name: str
    app_version: str
    environment: str
    sqlite_available: bool
    chunks_available: bool
    embeddings_available: bool


class VersionsResponse(BaseModel):
    """Corpus, schema, and pipeline release versions."""

    backend_version: str
    canonical_paper_schema: str = "0.2.0"
    document_processing_version: str = "v0.3.0"
    scientific_extraction_version: str = "v0.4.1"
    knowledge_base_version: str = "v0.5.1"
    embedding_pipeline_version: str = "v0.6.0"
    discovery_pipeline_version: str = "v0.7.0"


class RetrievalRequest(BaseModel):
    """Request payload for lexical, dense, or hybrid retrieval."""

    query: str = Field(..., min_length=2, description="Search query string")
    top_k: int = Field(default=10, ge=1, le=100, description="Maximum results to return")
    filter_rep_type: str | None = Field(
        default=None, description="Optional representation type filter"
    )


class RetrievalHitModel(BaseModel):
    """Individual retrieval search hit."""

    record_id: str
    score: float
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    retrieval_method: str


class RetrievalResponse(BaseModel):
    """Search results response."""

    query: str
    retrieval_method: str
    hits_count: int
    hits: list[RetrievalHitModel]
    latency_ms: float


class DiscoverySearchRequest(BaseModel):
    """Search request for discovering cross-domain candidate connections."""

    research_problem: str = Field(
        ..., min_length=3, description="Problem or bottleneck description"
    )
    target_domains: list[str] | None = Field(default=None, description="Target scientific domains")
    min_score: float = Field(default=0.35, ge=0.0, le=1.0)
    limit: int = Field(default=5, ge=1, le=20)


class DiscoverySearchResponse(BaseModel):
    """Discovered cross-domain candidates response."""

    research_problem: str
    total_found: int
    candidates: list[DiscoveryCandidate]


class GapVerificationRequest(BaseModel):
    """Request payload to verify candidate research gap."""

    proposed_gap: str = Field(..., min_length=5, description="Exact formulation of proposed gap")
    target_domains: list[str] | None = Field(default=None)


class NegativeSearchRequest(BaseModel):
    """Search for documented limitations, failures, and bottlenecks."""

    method_or_concept: str = Field(..., min_length=2)
    failure_category: str | None = Field(default=None)


class HypothesisGenerateRequest(BaseModel):
    """Request to generate falsifiable hypothesis from discovery candidate."""

    candidate: DiscoveryCandidate
    custom_baselines: list[str] | None = Field(default=None)


class AdversarialReviewRequest(BaseModel):
    """Request to review a research hypothesis."""

    hypothesis: ResearchHypothesis


class ExperimentDesignRequest(BaseModel):
    """Request to design an experiment protocol for a hypothesis."""

    hypothesis: ResearchHypothesis
    review: AdversarialReview | None = Field(default=None)


class OrchestrationStageResult(BaseModel):
    """Execution status and output summary of an individual workflow stage."""

    stage_name: str
    status: str  # "COMPLETED", "SKIPPED", "FAILED", "INSUFFICIENT_EVIDENCE"
    execution_time_ms: float
    output_summary: str
    error: str | None = None


class OrchestrationRequest(BaseModel):
    """End-to-end scientific discovery orchestration query."""

    research_question: str = Field(
        ..., min_length=5, description="Scientific bottleneck or question"
    )
    target_domain: str | None = Field(default=None)
    execute_review: bool = Field(default=True, description="Run Reviewer #2 adversarial critique")
    execute_experiment_design: bool = Field(
        default=True, description="Generate operational experiment plan"
    )


class OrchestrationResponse(BaseModel):
    """Complete end-to-end scientific research synthesis dossier."""

    workflow_id: str
    research_question: str
    stages: list[OrchestrationStageResult]
    discovery_candidates: list[DiscoveryCandidate]
    gap_dossier: ResearchGapDossier | None = None
    selected_hypothesis: ResearchHypothesis | None = None
    review: AdversarialReview | None = None
    experiment_plan: ExperimentPlan | None = None
    final_status: str  # "HYPOTHESIS_FORMULATED", "INSUFFICIENT_EVIDENCE", "GAP_REJECTED"
    total_duration_ms: float
