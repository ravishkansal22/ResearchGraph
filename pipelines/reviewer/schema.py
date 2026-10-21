"""ResearchGraph Phase 11: Adversarial Reviewer ("Reviewer #2") Schemas.

Defines skeptical scientific critique, 10 review dimensions, severity-ranked weaknesses,
alternative explanations, and explicit review verdicts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReviewVerdict(str, Enum):
    """Categorical evaluation verdict issued by the adversarial reviewer."""
    PROMISING_BUT_UNVERIFIED = "PROMISING_BUT_UNVERIFIED"  # Strong grounding, sound mechanism, needs empirical testing
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"            # Plausible mechanism, but evidence grounding is insufficient
    MAJOR_REVISION = "MAJOR_REVISION"                      # Confounders, flawed assumptions, or simpler baseline threats
    REJECTED = "REJECTED"                                  # Falsified by existing literature, superficial analogy, or unviable


class WeaknessSeverity(str, Enum):
    """Severity classification of identified scientific weaknesses."""
    CRITICAL = "CRITICAL"  # Fatal flaw disproving or rendering the proposal invalid
    MAJOR = "MAJOR"        # Significant threat to validity requiring major experimental revision
    MINOR = "MINOR"        # Clarification or measurement refinement needed


class CriticismItem(BaseModel):
    """Specific scientific critique on a defined review dimension."""
    dimension: str = Field(..., description="Targeted review dimension")
    severity: WeaknessSeverity = Field(..., description="Severity of the critique")
    critique: str = Field(..., description="Detailed skeptical scientific criticism")
    suggested_remedy: str = Field(..., description="Experimental or methodological remedy")


class AdversarialReview(BaseModel):
    """Comprehensive, adversarial peer-review dossier challenging a proposed hypothesis."""
    review_id: str = Field(..., description="Unique review identifier (e.g. rev_xxx)")
    hypothesis_id: str = Field(..., description="Foreign key to evaluated ResearchHypothesis")
    verdict: ReviewVerdict = Field(..., description="Formal peer-review verdict")
    overall_score: float = Field(..., ge=0.0, le=10.0, description="Overall quality score (0 to 10)")
    dimension_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Scores out of 10 across the 10 scientific review dimensions",
    )
    severity_ranked_weaknesses: List[CriticismItem] = Field(
        default_factory=list,
        description="Ordered list of scientific criticisms sorted by severity",
    )
    missing_evidence: List[str] = Field(default_factory=list, description="Uncited or ungrounded claims")
    alternative_explanations: List[str] = Field(
        default_factory=list,
        description="Simpler or alternative phenomena that could explain the expected outcome",
    )
    required_revisions: List[str] = Field(default_factory=list, description="Mandatory adjustments before testing")
    falsification_recommendation: str = Field(
        ...,
        description="The single most efficient experiment that could decisively falsify this hypothesis",
    )
    reviewer_persona: str = Field(
        default="Reviewer #2 (Skeptical Scientific Reviewer)",
        description="Adversarial evaluation persona",
    )
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
