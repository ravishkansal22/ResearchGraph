"""Hypothesis Formulation, Adversarial Review, and Experiment Design Endpoints."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from researchgraph.schemas.api import (
    AdversarialReviewRequest,
    ExperimentDesignRequest,
    HypothesisGenerateRequest,
)
from pipelines.experiment.designer import ExperimentDesigner
from pipelines.experiment.schema import ExperimentPlan
from pipelines.hypothesis.generator import HypothesisGenerationEngine
from pipelines.hypothesis.schema import ResearchHypothesis
from pipelines.reviewer.adversarial import AdversarialReviewer
from pipelines.reviewer.schema import AdversarialReview

router = APIRouter(tags=["Hypotheses, Review & Experiments"])

_hypo_engine: Optional[HypothesisGenerationEngine] = None
_reviewer: Optional[AdversarialReviewer] = None
_exp_designer: Optional[ExperimentDesigner] = None


def get_hypo_engine() -> HypothesisGenerationEngine:
    global _hypo_engine
    if _hypo_engine is None:
        _hypo_engine = HypothesisGenerationEngine()
    return _hypo_engine


def get_reviewer() -> AdversarialReviewer:
    global _reviewer
    if _reviewer is None:
        _reviewer = AdversarialReviewer()
    return _reviewer


def get_exp_designer() -> ExperimentDesigner:
    global _exp_designer
    if _exp_designer is None:
        _exp_designer = ExperimentDesigner()
    return _exp_designer


@router.post("/hypotheses/generate", response_model=ResearchHypothesis)
def generate_hypothesis(
    request: HypothesisGenerateRequest,
    engine: HypothesisGenerationEngine = Depends(get_hypo_engine),
) -> ResearchHypothesis:
    """Synthesize a structured, falsifiable hypothesis from a discovery candidate."""
    return engine.generate_hypothesis(
        candidate=request.candidate,
        custom_baselines=request.custom_baselines,
    )


@router.get("/hypotheses/{hypothesis_id}", response_model=ResearchHypothesis)
def get_hypothesis(
    hypothesis_id: str,
    engine: HypothesisGenerationEngine = Depends(get_hypo_engine),
) -> ResearchHypothesis:
    """Retrieve a previously generated hypothesis by ID."""
    hyp = engine.get_hypothesis(hypothesis_id)
    if not hyp:
        raise HTTPException(status_code=404, detail=f"Hypothesis {hypothesis_id} not found.")
    return hyp


@router.post("/review/evaluate", response_model=AdversarialReview)
def run_adversarial_review(
    request: AdversarialReviewRequest,
    reviewer: AdversarialReviewer = Depends(get_reviewer),
) -> AdversarialReview:
    """Subject a research hypothesis to Reviewer #2 adversarial critique."""
    return reviewer.review_hypothesis(request.hypothesis)


@router.post("/experiments/design", response_model=ExperimentPlan)
def design_experiment(
    request: ExperimentDesignRequest,
    designer: ExperimentDesigner = Depends(get_exp_designer),
) -> ExperimentPlan:
    """Design an actionable, executable empirical experiment plan for a hypothesis."""
    return designer.design_experiment(
        hypothesis=request.hypothesis,
        review=request.review,
    )
