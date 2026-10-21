"""Cross-Domain Discovery Endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query

from researchgraph.schemas.api import (
    DiscoverySearchRequest,
    DiscoverySearchResponse,
)
from pipelines.discovery.algorithms import CrossDomainDiscoveryEngine
from pipelines.discovery.schema import DiscoveryCandidate

router = APIRouter(prefix="/discovery", tags=["Cross-Domain Discovery"])

_discovery_engine: Optional[CrossDomainDiscoveryEngine] = None


def get_discovery_engine() -> CrossDomainDiscoveryEngine:
    global _discovery_engine
    if _discovery_engine is None:
        _discovery_engine = CrossDomainDiscoveryEngine()
    return _discovery_engine


@router.post("/search", response_model=DiscoverySearchResponse)
def search_cross_domain_candidates(
    request: DiscoverySearchRequest,
    engine: CrossDomainDiscoveryEngine = Depends(get_discovery_engine),
) -> DiscoverySearchResponse:
    """Discover valuable cross-domain candidate connections for a research problem."""
    candidates = engine.discover_problem_to_method(
        target_problem_query=request.research_problem,
        min_score=request.min_score,
        limit=request.limit,
    )
    return DiscoverySearchResponse(
        research_problem=request.research_problem,
        total_found=len(candidates),
        candidates=candidates,
    )


@router.get("/swanson", response_model=List[DiscoveryCandidate])
def run_swanson_lbd(
    source_concept_id: str = Query(...),
    target_concept_id: str = Query(...),
    engine: CrossDomainDiscoveryEngine = Depends(get_discovery_engine),
) -> List[DiscoveryCandidate]:
    """Execute Swanson Literature-Based Discovery (A -> B -> C) between two concepts."""
    return engine.discover_swanson_lbd(
        source_concept_id=source_concept_id,
        target_concept_id=target_concept_id,
    )
