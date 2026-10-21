"""ResearchGraph Phase 7: Interpretable Discovery Candidate Scorer.

Computes multi-dimensional candidate rankings from mathematically defined,
empirically ablatable components:
- Semantic relevance (S_sem)
- Evidence support (S_ev)
- Cross-domain distance (S_dist)
- Mechanistic compatibility (S_mech)
- Contradiction risk (R_contra)
- Evidence diversity (S_div)
- Redundancy / co-citation penalty (P_red)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from pipelines.discovery.schema import DiscoveryScoreExplanation


@dataclass
class ScorerConfig:
    """Configurable weights and ablation toggles for candidate discovery ranking."""
    weight_semantic: float = 0.25
    weight_evidence: float = 0.25
    weight_distance: float = 0.20
    weight_mechanistic: float = 0.20
    weight_diversity: float = 0.10
    weight_contradiction_penalty: float = 0.30
    weight_redundancy_penalty: float = 0.40

    # Ablation Toggles
    enable_semantic: bool = True
    enable_evidence: bool = True
    enable_distance: bool = True
    enable_mechanistic: bool = True
    enable_diversity: bool = True
    enable_contradiction: bool = True
    enable_redundancy_penalty: bool = True


class DiscoveryScorer:
    """Interpretable scoring engine for cross-domain discovery candidates."""

    def __init__(self, config: Optional[ScorerConfig] = None):
        self.config = config or ScorerConfig()

    def score_candidate(
        self,
        semantic_sim: float,
        source_evidence: List[str],
        target_evidence: List[str],
        source_domain: str,
        target_domain: str,
        source_paper_ids: List[str],
        target_paper_ids: List[str],
        known_contradictions_count: int = 0,
        mechanistic_match: bool = True,
    ) -> DiscoveryScoreExplanation:
        """Compute interpretable composite discovery score with justification."""
        cfg = self.config

        # 1. Semantic Relevance S_sem in [0, 1]
        s_sem = max(0.0, min(1.0, float(semantic_sim))) if cfg.enable_semantic else 0.5

        # 2. Evidence Support S_ev in [0, 1]
        ev_count = len(source_evidence) + len(target_evidence)
        s_ev = min(1.0, ev_count / 4.0) if cfg.enable_evidence else 0.5

        # 3. Cross-Domain Distance S_dist in [0, 1]
        if not cfg.enable_distance:
            s_dist = 0.5
        else:
            if source_domain.strip().lower() != target_domain.strip().lower():
                s_dist = 0.90  # Substantial disciplinary divergence (cross-domain)
            else:
                s_dist = 0.30  # Same-domain connection (less novel)

        # 4. Mechanistic Compatibility S_mech in [0, 1]
        s_mech = 0.85 if (mechanistic_match and cfg.enable_mechanistic) else 0.40

        # 5. Evidence Diversity S_div in [0, 1]
        unique_papers = len(set(source_paper_ids).union(set(target_paper_ids)))
        s_div = min(1.0, unique_papers / 3.0) if cfg.enable_diversity else 0.5

        # 6. Contradiction Risk Penalty R_contra in [0, 1]
        r_contra = (
            min(1.0, known_contradictions_count * 0.35)
            if cfg.enable_contradiction
            else 0.0
        )

        # 7. Redundancy Penalty P_red in [0, 1]
        # Direct co-occurrence in the same paper means the link is already known
        shared_papers = set(source_paper_ids).intersection(set(target_paper_ids))
        p_red = (
            0.80 if (shared_papers and cfg.enable_redundancy_penalty)
            else 0.0
        )

        # Weighted Composite Score
        raw_positive = (
            cfg.weight_semantic * s_sem
            + cfg.weight_evidence * s_ev
            + cfg.weight_distance * s_dist
            + cfg.weight_mechanistic * s_mech
            + cfg.weight_diversity * s_div
        )
        total_weight = (
            cfg.weight_semantic + cfg.weight_evidence + cfg.weight_distance
            + cfg.weight_mechanistic + cfg.weight_diversity
        )
        normalized_pos = raw_positive / total_weight if total_weight > 0 else 0.5

        # Apply penalties
        penalty = (cfg.weight_contradiction_penalty * r_contra) + (cfg.weight_redundancy_penalty * p_red)
        composite = max(0.0, min(1.0, normalized_pos - penalty))

        rationale_parts = []
        if s_dist > 0.7:
            rationale_parts.append(f"High cross-domain distance between '{source_domain}' and '{target_domain}'.")
        else:
            rationale_parts.append("Intra-domain transfer.")

        if p_red > 0.5:
            rationale_parts.append("Penalized for direct co-occurrence in existing paper.")
        else:
            rationale_parts.append("Zero prior co-occurrence detected (undiscovered public knowledge proxy).")

        if r_contra > 0.0:
            rationale_parts.append(f"Contradiction/limitation penalty applied ({r_contra:.2f}).")

        rationale_parts.append(f"Grounding supported by {ev_count} evidence excerpts across {unique_papers} papers.")

        return DiscoveryScoreExplanation(
            semantic_relevance=round(s_sem, 4),
            evidence_support=round(s_ev, 4),
            cross_domain_distance=round(s_dist, 4),
            mechanistic_compatibility=round(s_mech, 4),
            contradiction_risk_penalty=round(r_contra, 4),
            evidence_diversity=round(s_div, 4),
            redundancy_penalty=round(p_red, 4),
            composite_score=round(composite, 4),
            score_rationale=" ".join(rationale_parts),
        )
