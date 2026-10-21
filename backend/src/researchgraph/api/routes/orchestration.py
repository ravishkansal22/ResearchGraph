"""End-to-End Scientific Inquiry Orchestration Endpoint."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends

from researchgraph.schemas.api import (
    OrchestrationRequest,
    OrchestrationResponse,
)
from researchgraph.services.orchestrator import (
    ResearchWorkflowOrchestrator,
)

router = APIRouter(prefix="/orchestration", tags=["End-to-End Orchestration"])

_orchestrator: Optional[ResearchWorkflowOrchestrator] = None


def get_orchestrator() -> ResearchWorkflowOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ResearchWorkflowOrchestrator()
    return _orchestrator


@router.post("/synthesize", response_model=OrchestrationResponse)
def execute_scientific_synthesis(
    request: OrchestrationRequest,
    orchestrator: ResearchWorkflowOrchestrator = Depends(get_orchestrator),
) -> OrchestrationResponse:
    """Execute complete scientific discovery workflow from research question to experiment plan."""
    return orchestrator.execute_workflow(request)
