"""Continuous Evaluation and Benchmark Endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from researchgraph.core.config import settings

router = APIRouter(prefix="/evaluation", tags=["Continuous Evaluation"])


@router.get("/reports/retrieval")
def get_retrieval_report() -> Dict[str, Any]:
    """Retrieve the latest Phase 5 empirical retrieval benchmark results."""
    report_file = Path("research/embeddings/retrieval_evaluation_report.json")
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Retrieval benchmark report not yet generated.")
    with open(report_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/reports/discovery")
def get_discovery_ablation_report() -> Dict[str, Any]:
    """Retrieve the latest Phase 7 discovery scoring ablation report."""
    report_file = Path("research/discovery/discovery_ablation_report.json")
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Discovery ablation report not yet generated.")
    with open(report_file, "r", encoding="utf-8") as f:
        return json.load(f)
