"""Continuous Evaluation and Benchmark Endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/evaluation", tags=["Continuous Evaluation"])


@router.get("/reports/retrieval")
def get_retrieval_report() -> dict[str, Any]:
    """Retrieve the latest Phase 5 empirical retrieval benchmark results."""
    repo_root = Path(__file__).resolve().parents[4]
    candidates = [
        Path("research/embeddings/retrieval_evaluation_report.json"),
        repo_root / "research/embeddings/retrieval_evaluation_report.json",
    ]
    report_file = next((p for p in candidates if p.exists()), candidates[0])
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Retrieval benchmark report not yet generated.")
    with open(report_file, encoding="utf-8") as f:
        res: dict[str, Any] = dict(json.load(f))
        return res


@router.get("/reports/discovery")
def get_discovery_ablation_report() -> dict[str, Any]:
    """Retrieve the latest Phase 7 discovery scoring ablation report."""
    repo_root = Path(__file__).resolve().parents[4]
    candidates = [
        Path("research/discovery/discovery_ablation_report.json"),
        repo_root / "research/discovery/discovery_ablation_report.json",
    ]
    report_file = next((p for p in candidates if p.exists()), candidates[0])
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Discovery ablation report not yet generated.")
    with open(report_file, encoding="utf-8") as f:
        res: dict[str, Any] = dict(json.load(f))
        return res
