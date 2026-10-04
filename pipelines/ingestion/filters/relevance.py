"""Configurable AI Relevance and Domain Filter.

Provides flexible classification across core AI, AI-adjacent, and interdisciplinary fields
without rigid taxonomic pigeonholing.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from dataset.schemas.canonical_paper import CanonicalPaper

logger = logging.getLogger(__name__)

# Core AI Patterns (accommodating plural and singular variations)
CORE_AI_PATTERNS = [
    r"\bartificial intelligence\b",
    r"\bmachine learning\b",
    r"\bdeep learning\b",
    r"\bneural networks?\b",
    r"\breinforcement learning\b",
    r"\bnatural language processing\b",
    r"\blarge language models?\b",
    r"\bllms?\b",
    r"\btransformers?\b",
    r"\battention mechanisms?\b",
    r"\bcomputer vision\b",
    r"\bdiffusion models?\b",
    r"\bgenerative adversarial networks?\b",
    r"\bgans?\b",
    r"\bagentic\b",
    r"\bautonomous agents?\b",
    r"\bretrieval augmented generation\b",
    r"\brag\b",
    r"\brepresentation learning\b",
    r"\bself[- ]supervised learning\b",
    r"\bgraph neural networks?\b",
    r"\bcontrastive learning\b",
    r"\bspeech recognition\b",
    r"\balignment\b",
    r"\bmechanistic interpretability\b",
]

# arXiv Categories for AI
ARXIV_AI_CATEGORIES = {
    "cs.ai", "cs.lg", "cs.cl", "cs.cv", "cs.ne", "cs.ro", "stat.ml", "cs.ma"
}

# Interdisciplinary / Adjacent Bridge Terms
ADJACENT_PATTERNS = [
    r"\bcomputational biology\b",
    r"\bbioinformatics\b",
    r"\bcomputational neuroscience\b",
    r"\bquantum computing\b",
    r"\bdrug discovery\b",
    r"\brobotics\b",
    r"\bcontrol systems?\b",
    r"\boptimizations?\b",
    r"\bcausal inference\b",
    r"\bstatistical physics\b",
    r"\binformation theory\b",
    r"\bcomplex systems\b",
    r"\bknowledge graphs?\b",
    r"\bsymbolic reasoning\b",
]


class AIRelevanceFilter:
    """Filter that classifies papers by AI domain relevance while accommodating interdisciplinary work."""

    def __init__(
        self,
        mode: str = "broad_ai",  # 'strict_ai', 'broad_ai', 'all'
        custom_include_keywords: Optional[List[str]] = None,
    ):
        self.mode = mode
        self.custom_keywords = {k.lower().strip() for k in (custom_include_keywords or [])}

    def evaluate(self, paper: CanonicalPaper) -> Tuple[bool, str, float]:
        """Evaluate whether a canonical paper satisfies the relevance filter.

        Returns:
            (is_relevant, domain_tag, score)
        """
        if self.mode == "all":
            return True, "unfiltered", 1.0

        score = 0.0
        matched_tags: List[str] = []

        # Check arXiv categories & explicit topics
        for top in paper.topics:
            norm_top = top.name.lower().strip()
            if norm_top in ARXIV_AI_CATEGORIES:
                score = max(score, 0.85)
                matched_tags.append(f"arxiv:{norm_top}")
            elif any(re.search(pat, norm_top) for pat in CORE_AI_PATTERNS):
                score = max(score, 0.75)
                matched_tags.append(f"topic:{norm_top}")
            elif norm_top in self.custom_keywords:
                score = max(score, 0.70)
                matched_tags.append(f"custom:{norm_top}")

        # Search in title & abstract
        search_blob = f"{paper.title} {paper.abstract or ''}".lower()

        # Core AI terms matched
        matched_core = [pat for pat in CORE_AI_PATTERNS if re.search(pat, search_blob)]
        if matched_core:
            core_score = 0.65 if len(matched_core) == 1 else 0.85
            score = max(score, core_score)
            for m in matched_core[:3]:
                matched_tags.append(f"core:{m.strip(chr(92) + 'b')}")

        # Adjacent terms matched
        matched_adj = [adj for adj in ADJACENT_PATTERNS if re.search(adj, search_blob)]
        if matched_adj and not matched_core:
            adj_score = 0.35
            score = max(score, adj_score)
            for m in matched_adj[:3]:
                matched_tags.append(f"adjacent:{m.strip(chr(92) + 'b')}")

        for custom in self.custom_keywords:
            if re.search(r"\b" + re.escape(custom) + r"\b", search_blob):
                score = max(score, 0.65)
                matched_tags.append(f"custom:{custom}")

        score = min(round(score, 3), 1.0)

        if self.mode == "strict_ai":
            is_relevant = score >= 0.60
        elif self.mode == "broad_ai":
            is_relevant = score >= 0.30
        else:
            is_relevant = True

        tag = matched_tags[0] if matched_tags else "general_science"
        return is_relevant, tag, score

    def filter_papers(
        self, papers: List[CanonicalPaper]
    ) -> Tuple[List[CanonicalPaper], Dict[str, Any]]:
        """Filter list of canonical papers and return summary statistics."""
        passed: List[CanonicalPaper] = []
        rejected: List[CanonicalPaper] = []

        for p in papers:
            is_rel, _, _ = self.evaluate(p)
            if is_rel:
                passed.append(p)
            else:
                rejected.append(p)

        stats = {
            "total_evaluated": len(papers),
            "passed_count": len(passed),
            "rejected_count": len(rejected),
            "pass_rate": round(len(passed) / len(papers), 4) if papers else 0.0,
            "filter_mode": self.mode,
        }
        return passed, stats
