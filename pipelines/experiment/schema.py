"""ResearchGraph Phase 12: Experiment Designer Schemas.

Defines operational experiment plans, baseline suites, variable controls,
ablation steps, statistical significance protocols, and falsification checklists.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DatasetRequirement(BaseModel):
    """Specification of required benchmark datasets and evaluation splits."""
    dataset_name: str = Field(..., description="Target benchmark dataset name")
    sample_size_min: int = Field(default=1000, description="Minimum instances required for statistical power")
    split_protocol: str = Field(default="Stratified 70/15/15 train/val/test across 5 folds")
    distribution_characteristics: str = Field(
        default="Representative class balance with controlled label-skew variations",
        description="Data distribution constraints",
    )


class ResourceEstimate(BaseModel):
    """Estimated hardware, memory, and runtime budget required for reproducibility."""
    target_hardware: str = Field(default="1x NVIDIA RTX 3090 / A10G or CPU fallback")
    estimated_gpu_hours: float = Field(default=8.5, description="Estimated total GPU runtime")
    peak_vram_gb: float = Field(default=12.0, description="Peak VRAM consumption")
    estimated_cost_usd: float = Field(default=15.0, description="Cloud compute cost estimate")


class StatisticalProtocol(BaseModel):
    """Formal hypothesis testing and statistical power protocol."""
    test_type: str = Field(default="Wilcoxon signed-rank test (non-parametric)")
    alpha_significance_level: float = Field(default=0.05)
    random_seeds_count: int = Field(default=5)
    confidence_interval: float = Field(default=0.95)
    multiple_testing_correction: str = Field(default="Benjamini-Hochberg FDR")


class ExperimentPlan(BaseModel):
    """Executable experimental protocol designed to test or falsify a research hypothesis."""
    experiment_id: str = Field(..., description="Unique experiment plan ID (e.g. exp_plan_xxx)")
    hypothesis_id: str = Field(..., description="Foreign key to evaluated ResearchHypothesis")
    research_question: str = Field(..., description="Precise empirical question to be resolved")
    target_domain: str = Field(..., description="Scientific application domain")
    baseline_methods: List[str] = Field(..., description="Competitive baseline algorithms")
    independent_variables: List[str] = Field(..., description="Controlled independent variables")
    dependent_variables: List[str] = Field(..., description="Measured quantitative dependent metrics")
    dataset_requirements: DatasetRequirement = Field(..., description="Required data specifications")
    evaluation_metrics: List[str] = Field(..., description="Quantitative benchmark metrics (AUC, F1, latency)")
    protocol_steps: List[str] = Field(..., description="Sequential steps for experiment execution")
    ablation_plan: List[str] = Field(..., description="Controlled component ablation procedures")
    resource_estimate: ResourceEstimate = Field(..., description="Compute budget and hardware needs")
    statistical_protocol: StatisticalProtocol = Field(..., description="Statistical significance criteria")
    threats_to_validity: List[str] = Field(..., description="Identified confounders and external validity risks")
    expected_result_patterns: str = Field(..., description="Expected quantitative behavioral profile")
    explicit_rejection_criteria: str = Field(..., description="Exact threshold requiring hypothesis rejection")
    reproducibility_checklist: List[str] = Field(..., description="Artifact, seed, and data provenance checklist")
    execution_status: str = Field(default="PLANNED_READY_FOR_EXECUTION")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
