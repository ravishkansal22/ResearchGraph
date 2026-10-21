"""Research-Gap and Novelty Verification Endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pipelines.gap_verification.schema import ResearchGapDossier
from pipelines.gap_verification.verifier import ResearchGapVerifier

from researchgraph.schemas.api import GapVerificationRequest

router = APIRouter(prefix="/gap-verification", tags=["Research-Gap Verification"])

_verifier: ResearchGapVerifier | None = None


def get_gap_verifier() -> ResearchGapVerifier:
    global _verifier
    if _verifier is None:
        _verifier = ResearchGapVerifier()
    return _verifier


@router.post("/verify", response_model=ResearchGapDossier)
def verify_research_gap(
    request: GapVerificationRequest,
    verifier: ResearchGapVerifier = Depends(get_gap_verifier),
) -> ResearchGapDossier:
    """Evaluate whether a proposed gap is genuine or has contradictory prior art."""
    return verifier.verify_gap(
        proposed_gap=request.proposed_gap,
        target_domains=request.target_domains,
    )
