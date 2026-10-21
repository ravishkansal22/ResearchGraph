"""ResearchGraph Phase 7: Cross-Domain Discovery Schemas.

Defines discovery strategies, candidates, mechanistic explanations, and
interpretable scoring breakdowns.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DiscoveryStrategy(str, Enum):
    """Mechanistic cross-domain discovery strategies."""
    PROBLEM_TO_METHOD = "PROBLEM_TO_METHOD"
    METHOD_TO_BOTTLENECK = "METHOD_TO_BOTTLENECK"
    LIMITATION_TO_METHOD_TRANSFER = "LIMITATION_TO_METHOD_TRANSFER"
    SWANSON_LBD_TRAVERSAL = "SWANSON_LBD_TRAVERSAL"
    SEMANTIC_ANALOGICAL_NEIGHBOR = "SEMANTIC_ANALOGICAL_NEIGHBOR"
    GRAPH_PATH_DISCOVERY = "GRAPH_PATH_DISCOVERY"
    ASSUMPTION_MISMATCH = "ASSUMPTION_MISMATCH"
    DIRECTION_CONVERGENCE = "DIRECTION_CONVERGENCE"


class DiscoveryScoreExplanation(BaseModel):
    """Interpretable breakdown of discovery candidate score components."""
    semantic_relevance: float = Field(..., ge=0.0, le=1.0, description="Semantic affinity score")
    evidence_support: float = Field(..., ge=0.0, le=1.0, description="Strength of supporting evidence spans")
    cross_domain_distance: float = Field(..., ge=0.0, le=1.0, description="Disciplinary divergence proxy")
    mechanistic_compatibility: float = Field(..., ge=0.0, le=1.0, description="Topological compatibility")
    contradiction_risk_penalty: float = Field(default=0.0, ge=0.0, le=1.0, description="Contradiction or failure risk")
    evidence_diversity: float = Field(default=1.0, ge=0.0, le=1.0, description="Multi-paper source diversity")
    redundancy_penalty: float = Field(default=0.0, ge=0.0, le=1.0, description="Direct co-occurrence penalty")
    composite_score: float = Field(..., ge=0.0, le=1.0, description="Final ranked discovery score")
    score_rationale: str = Field(..., description="Plain-language justification for scoring")


class DiscoveryCandidate(BaseModel):
    """Structured, evidence-grounded candidate cross-domain connection."""
    candidate_id: str = Field(..., description="Unique candidate identifier (e.g. disc_cand_xxx)")
    strategy: DiscoveryStrategy = Field(..., description="Algorithm strategy generating this candidate")
    source_concept_id: str = Field(..., description="Source domain method, technique, or mechanism ID")
    source_concept_name: str = Field(..., description="Source concept canonical name")
    source_domain: str = Field(..., description="Originating scientific domain")
    target_problem_id: str = Field(..., description="Target domain problem, bottleneck, or task ID")
    target_problem_name: str = Field(..., description="Target problem canonical name")
    target_domain: str = Field(..., description="Target scientific domain")
    proposed_mechanism: str = Field(..., description="Causal/functional mechanism bridging source and target")
    utility_rationale: str = Field(..., description="Explanation of why this connection is practically valuable")
    source_evidence: List[str] = Field(default_factory=list, description="Direct textual evidence from source domain")
    target_evidence: List[str] = Field(default_factory=list, description="Direct textual evidence from target domain")
    source_paper_ids: List[str] = Field(default_factory=list, description="Papers substantiating source side")
    target_paper_ids: List[str] = Field(default_factory=list, description="Papers substantiating target side")
    assumptions_required: List[str] = Field(default_factory=list, description="Explicit conditions required for transfer")
    known_limitations: List[str] = Field(default_factory=list, description="Documented failure modes or boundary conditions")
    disconfirmation_criteria: str = Field(..., description="What empirical observation would falsify this connection")
    score: DiscoveryScoreExplanation = Field(..., description="Interpretable multi-dimensional score breakdown")
    pipeline_version: str = Field(default="v0.7.0")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
