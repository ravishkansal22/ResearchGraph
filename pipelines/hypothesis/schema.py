"""ResearchGraph Phase 10: Hypothesis Generation Engine Schemas.

Defines evidence-grounded, falsifiable scientific research hypotheses,
operational variables, failure conditions, and uncertainty models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HypothesisValidationStatus(str, Enum):
    """Validation lifecycle status for generated hypotheses."""
    UNVALIDATED_PROPOSAL = "UNVALIDATED_PROPOSAL"    # Initial synthesized candidate awaiting review
    REVIEW_PASSED = "REVIEW_PASSED"                  # Survived Reviewer #2 adversarial critique
    REVISION_REQUIRED = "REVISION_REQUIRED"          # Requires assumption or baseline adjustment
    REJECTED = "REJECTED"                            # Definitively falsified or invalid mechanism


class ResearchHypothesis(BaseModel):
    """Structured, evidence-grounded, and falsifiable scientific hypothesis."""
    hypothesis_id: str = Field(..., description="Unique hypothesis identifier (e.g. hyp_xxx)")
    version: str = Field(default="1.0.0", description="Hypothesis version")
    candidate_id: str = Field(..., description="Foreign key to originating DiscoveryCandidate")
    title: str = Field(..., description="Concise scientific hypothesis title")
    research_problem: str = Field(..., description="Target domain problem being resolved")
    source_domain_method: str = Field(..., description="Technique transferred from source domain")
    target_domain_problem: str = Field(..., description="Target bottleneck or empirical limitation")
    proposed_mechanism: str = Field(..., description="Detailed causal/functional mechanism of action")
    transfer_rationale: str = Field(..., description="Theoretical or empirical justification for transfer")
    evidence_summary: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Grounded evidence excerpts categorized by source and target domains",
    )
    assumptions: List[str] = Field(default_factory=list, description="Explicit necessary conditions for mechanism")
    expected_outcome: str = Field(..., description="Precise expected quantitative empirical behavior")
    failure_conditions: List[str] = Field(default_factory=list, description="Documented conditions where hypothesis fails")
    baseline_methods: List[str] = Field(default_factory=list, description="Competitive state-of-the-art baselines")
    independent_variables: List[str] = Field(default_factory=list, description="Manipulated experimental variables (IV)")
    dependent_variables: List[str] = Field(default_factory=list, description="Measured outcome variables (DV)")
    falsification_criteria: str = Field(..., description="Exact empirical threshold disproving hypothesis")
    required_experiments: List[str] = Field(default_factory=list, description="Essential experimental protocols")
    validation_status: HypothesisValidationStatus = Field(default=HypothesisValidationStatus.UNVALIDATED_PROPOSAL)
    uncertainty_explanation: str = Field(..., description="Identified confounding factors and epistemic limits")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
