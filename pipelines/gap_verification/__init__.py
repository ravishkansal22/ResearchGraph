"""ResearchGraph Phase 8: Research-Gap and Novelty Verification."""

from pipelines.gap_verification.schema import (
    GapStatus,
    RelatedWorkFinding,
    RelatedWorkRelation,
    ResearchGapDossier,
    SearchAuditRecord,
)
from pipelines.gap_verification.verifier import ResearchGapVerifier

__all__ = [
    "GapStatus",
    "RelatedWorkRelation",
    "RelatedWorkFinding",
    "SearchAuditRecord",
    "ResearchGapDossier",
    "ResearchGapVerifier",
]
