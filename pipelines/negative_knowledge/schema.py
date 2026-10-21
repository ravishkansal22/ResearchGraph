"""ResearchGraph Phase 9: Negative Knowledge and Dead-End Detection Schemas.

Defines negative empirical results, method limitations, failed assumptions,
computational bottlenecks, and boundary conditions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from dataset.schemas.scientific_knowledge import AttributionType


class FailureCategory(str, Enum):
    """Categorization of documented failure modes and limitations."""
    EMPIRICAL_REGRESSION = "EMPIRICAL_REGRESSION"        # Method performed worse than baseline or failed ablation
    METHOD_LIMITATION = "METHOD_LIMITATION"              # Author-stated architectural or conceptual constraint
    COMPUTATIONAL_BOTTLENECK = "COMPUTATIONAL_BOTTLENECK"# Memory, latency, or sample-complexity limit
    ASSUMPTION_FAILURE = "ASSUMPTION_FAILURE"            # Theoretical assumption that does not hold empirically
    CONTRADICTION = "CONTRADICTION"                      # Conflicting findings across evaluation regimes
    BOUNDARY_CONDITION = "BOUNDARY_CONDITION"            # Specific environment/dataset where approach ceases to work


class NegativeEvidenceType(str, Enum):
    """Epistemic strength of negative finding."""
    EXPLICIT_FAILURE = "EXPLICIT_FAILURE"                # Author explicitly documents failure in experiment
    AUTHOR_STATED_LIMITATION = "AUTHOR_STATED_LIMITATION"# Stated in limitations / future work section
    SYSTEM_INFERRED_RISK = "SYSTEM_INFERRED_RISK"        # Inferred from statistical divergence or boundary conditions
    UNVERIFIED_NEGATIVE_CLAIM = "UNVERIFIED_NEGATIVE_CLAIM" # Anecdotal or unverified negative assertion


class NegativeKnowledgeRecord(BaseModel):
    """Single cataloged negative result, limitation, or dead-end pathway."""
    record_id: str = Field(..., description="Unique record identifier (e.g. neg_rec_xxx)")
    method_or_concept: str = Field(..., description="Method, technique, or architecture facing limitation")
    failure_category: FailureCategory = Field(..., description="Category of failure or bottleneck")
    evidence_type: NegativeEvidenceType = Field(..., description="Epistemic tier of evidence")
    description: str = Field(..., description="Summary explanation of the negative finding")
    conditions_or_task: str = Field(default="General", description="Task, dataset, or conditions where limitation occurs")
    evidence_text: str = Field(..., description="Exact quoted excerpt from publication")
    paper_id: str = Field(..., description="Source paper canonical ID")
    chunk_id: Optional[str] = Field(default=None, description="Source chunk ID")
    attribution: AttributionType = Field(default=AttributionType.AUTHOR_STATED)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
