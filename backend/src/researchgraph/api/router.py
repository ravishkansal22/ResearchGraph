"""Aggregated API Router for ResearchGraph Backend."""

from __future__ import annotations

from fastapi import APIRouter

from researchgraph.api.routes import (
    discovery,
    evaluation,
    gap,
    graph,
    health,
    hypotheses,
    literature,
    negative_knowledge,
    orchestration,
    retrieval,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(literature.router)
api_router.include_router(retrieval.router)
api_router.include_router(graph.router)
api_router.include_router(discovery.router)
api_router.include_router(gap.router)
api_router.include_router(negative_knowledge.router)
api_router.include_router(hypotheses.router)
api_router.include_router(orchestration.router)
api_router.include_router(evaluation.router)
