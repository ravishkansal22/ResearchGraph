"""ResearchGraph Phase 8: Research-Gap and Novelty Verification Schemas.

Defines the structured Research-Gap Dossier, verification audit trail,
evidence records, and epistemic status categories.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GapStatus(str, Enum):
    """Rigorous epistemic evaluation of a proposed research gap."""
    POSSIBLE_GAP = "POSSIBLE_GAP"                    # Problem appears open in indexed corpus; no direct precedent located
    EVIDENCE_AGAINST_GAP = "EVIDENCE_AGAINST_GAP"    # Contradicting prior art or direct solution already documented
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # Corpus coverage is too sparse to evaluate proposition
    REQUIRES_REVIEW = "REQUIRES_REVIEW"              # Conflicting or ambiguous evidence requiring domain expert adjudication


class RelatedWorkRelation(str, Enum):
    """Categorical relationship of retrieved related work to candidate gap."""
    DIRECT_PRECEDENT = "DIRECT_PRECEDENT"            # Already implemented or explored previously
    CONTRADICTORY_FINDING = "CONTRADICTORY_FINDING"  # Documents an empirical contradiction or negative result
    SUPPORTING_EVIDENCE = "SUPPORTING_EVIDENCE"      # Substantiates that the bottleneck exists
    ANALOGOUS_WORK = "ANALOGOUS_WORK"                # Similar methodology applied in adjacent field


class RelatedWorkFinding(BaseModel):
    """Retrieved scientific record bearing on candidate gap."""
    paper_id: str
    paper_title: str
    chunk_id: Optional[str] = None
    relationship: RelatedWorkRelation
    excerpt: str
    relevance_score: float
    analysis: str


class SearchAuditRecord(BaseModel):
    """Immutable audit trail of a search operation conducted during verification."""
    search_strategy: str  # "bm25", "dense_vector", "graph_relationships", "kb_statements"
    query_string: str
    hits_count: int
    top_score: float
    execution_time_ms: float


class ResearchGapDossier(BaseModel):
    """Complete, evidence-grounded research-gap verification dossier."""
    dossier_id: str = Field(..., description="Unique dossier ID (e.g. gap_dos_xxx)")
    proposed_gap_statement: str = Field(..., description="Precise formulation of candidate research gap")
    key_concepts: List[str] = Field(default_factory=list, description="Extracted core concepts and methods")
    domains_involved: List[str] = Field(default_factory=list, description="Target scientific domains")
    search_audit_trail: List[SearchAuditRecord] = Field(default_factory=list, description="Log of all searches executed")
    supporting_evidence: List[RelatedWorkFinding] = Field(default_factory=list, description="Findings confirming gap existence")
    opposing_or_prior_work: List[RelatedWorkFinding] = Field(default_factory=list, description="Prior art or contradictions")
    corpus_coverage_limitations: str = Field(..., description="Explicit statement of indexing boundaries and blind spots")
    confidence_rationale: str = Field(..., description="Epistemic rationale explaining the assigned status")
    additional_searches_required: List[str] = Field(default_factory=list, description="External queries needed outside current corpus")
    final_status: GapStatus = Field(..., description="Assigned verification status (Never 'VERIFIED_NOVEL')")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
