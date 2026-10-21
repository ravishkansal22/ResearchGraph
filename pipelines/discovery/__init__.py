"""ResearchGraph Phase 7: Cross-Domain Discovery Algorithms."""

from pipelines.discovery.ablation import run_discovery_ablation_experiment
from pipelines.discovery.algorithms import CrossDomainDiscoveryEngine, generate_candidate_id
from pipelines.discovery.schema import (
    DiscoveryCandidate,
    DiscoveryScoreExplanation,
    DiscoveryStrategy,
)
from pipelines.discovery.scorer import DiscoveryScorer, ScorerConfig

__all__ = [
    "DiscoveryStrategy",
    "DiscoveryScoreExplanation",
    "DiscoveryCandidate",
    "ScorerConfig",
    "DiscoveryScorer",
    "CrossDomainDiscoveryEngine",
    "generate_candidate_id",
    "run_discovery_ablation_experiment",
]
