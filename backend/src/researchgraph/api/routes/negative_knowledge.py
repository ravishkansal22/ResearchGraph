"""Negative Knowledge and Dead-End Graveyard Endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query

from researchgraph.schemas.api import NegativeSearchRequest
from pipelines.negative_knowledge.graveyard import DeadEndGraveyard
from pipelines.negative_knowledge.schema import NegativeKnowledgeRecord

router = APIRouter(prefix="/negative-knowledge", tags=["Negative Knowledge"])

_graveyard: Optional[DeadEndGraveyard] = None


def get_graveyard() -> DeadEndGraveyard:
    global _graveyard
    if _graveyard is None:
        _graveyard = DeadEndGraveyard()
        _graveyard.build_index()
    return _graveyard


@router.get("/search", response_model=List[NegativeKnowledgeRecord])
def search_negative_knowledge(
    method: str = Query(..., min_length=2, description="Target method or concept name"),
    graveyard: DeadEndGraveyard = Depends(get_graveyard),
) -> List[NegativeKnowledgeRecord]:
    """Retrieve cataloged limitations, empirical failures, and boundary conditions."""
    return graveyard.find_method_limitations(method_name=method)


@router.get("/bottlenecks")
def list_recurring_bottlenecks(
    limit: int = Query(default=10, ge=1, le=50),
    graveyard: DeadEndGraveyard = Depends(get_graveyard),
) -> List[Dict[str, Any]]:
    """List most frequently occurring empirical bottlenecks across the corpus."""
    return graveyard.list_recurring_bottlenecks(limit=limit)
