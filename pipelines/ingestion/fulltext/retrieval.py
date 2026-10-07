"""Query-Driven Metadata Candidate Retriever.

Performs lexical and metadata-based retrieval over canonical papers to select
candidate papers for on-demand full-text acquisition without downloading the entire corpus.
Handles missing abstracts gracefully by dynamically rebalancing scoring weights.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from dataset.schemas.canonical_paper import CanonicalPaper


class MetadataCandidateRetriever:
    """Retrieves top candidate papers based on metadata relevance to a research problem/query."""

    def __init__(
        self,
        title_weight: float = 0.55,
        abstract_weight: float = 0.30,
        topic_weight: float = 0.15,
    ):
        self.title_weight = title_weight
        self.abstract_weight = abstract_weight
        self.topic_weight = topic_weight

    @staticmethod
    def _tokenize(text: Optional[str]) -> Set[str]:
        """Normalize and tokenize text into lowercase words, stripping punctuation."""
        if not text:
            return set()
        cleaned = re.sub(r"[^\w\s-]", " ", text.lower())
        tokens = [t.strip() for t in cleaned.split() if len(t.strip()) > 2]
        return set(tokens)

    def compute_similarity(
        self,
        query_tokens: Set[str],
        doc_tokens: Set[str],
    ) -> float:
        """Compute Jaccard-based lexical overlap between query and document field tokens."""
        if not query_tokens or not doc_tokens:
            return 0.0
        intersection = query_tokens.intersection(doc_tokens)
        if not intersection:
            return 0.0
        # Overlap coefficient relative to query size
        overlap = len(intersection) / len(query_tokens)
        return round(min(overlap, 1.0), 4)

    def score_paper(
        self,
        paper: CanonicalPaper,
        query: str,
    ) -> Tuple[float, Dict[str, float]]:
        """Score a canonical paper against a query with dynamic missing-field normalization.

        Returns:
            (total_score, component_scores_dict)
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return 0.0, {}

        # 1. Title Score
        title_tokens = self._tokenize(paper.title)
        title_sim = self.compute_similarity(query_tokens, title_tokens)

        # 2. Abstract Score (if present)
        has_abstract = bool(paper.abstract and len(paper.abstract.strip()) > 10)
        abstract_sim = 0.0
        if has_abstract:
            abstract_tokens = self._tokenize(paper.abstract)
            abstract_sim = self.compute_similarity(query_tokens, abstract_tokens)

        # 3. Topic & Keyword Score
        topic_names = [top.name for top in paper.topics] if paper.topics else []
        topic_text = " ".join(topic_names + (paper.keywords or []))
        has_topics = bool(topic_text.strip())
        topic_sim = 0.0
        if has_topics:
            topic_tokens = self._tokenize(topic_text)
            topic_sim = self.compute_similarity(query_tokens, topic_tokens)

        # Dynamic weight re-normalization when fields are missing
        active_weights: Dict[str, float] = {}
        active_weights["title"] = self.title_weight
        if has_abstract:
            active_weights["abstract"] = self.abstract_weight
        if has_topics:
            active_weights["topic"] = self.topic_weight

        total_weight = sum(active_weights.values())
        norm_title_weight = active_weights["title"] / total_weight
        norm_abstract_weight = (active_weights.get("abstract", 0.0)) / total_weight if has_abstract else 0.0
        norm_topic_weight = (active_weights.get("topic", 0.0)) / total_weight if has_topics else 0.0

        total_score = (
            (title_sim * norm_title_weight)
            + (abstract_sim * norm_abstract_weight)
            + (topic_sim * norm_topic_weight)
        )

        component_scores = {
            "title_score": round(title_sim, 4),
            "abstract_score": round(abstract_sim, 4) if has_abstract else 0.0,
            "topic_score": round(topic_sim, 4) if has_topics else 0.0,
            "has_abstract": 1.0 if has_abstract else 0.0,
            "has_topics": 1.0 if has_topics else 0.0,
            "total_score": round(total_score, 4),
        }

        return round(total_score, 4), component_scores

    def retrieve_candidates(
        self,
        papers: List[CanonicalPaper],
        query: str,
        top_k: int = 25,
        min_score: float = 0.05,
    ) -> List[Tuple[CanonicalPaper, float, Dict[str, float]]]:
        """Rank and return top-K candidate papers matching query.

        Returns:
            List of (paper, score, component_scores) sorted by score descending.
        """
        scored_papers = []
        for paper in papers:
            score, components = self.score_paper(paper, query)
            if score >= min_score:
                scored_papers.append((paper, score, components))

        scored_papers.sort(key=lambda item: item[1], reverse=True)
        return scored_papers[:top_k]
