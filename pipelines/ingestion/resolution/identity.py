"""Identity Resolution Engine.

Implements multi-signal matching across DOIs, arXiv IDs, normalized titles,
author fingerprints, and publication years with confidence scoring.
"""

from __future__ import annotations

import difflib
import hashlib
import logging
from typing import Dict, List, Optional, Set, Tuple

from dataset.schemas.canonical_paper import CanonicalPaper, ConfidenceLevel
from pipelines.ingestion.normalizers.text import normalize_title_for_matching

logger = logging.getLogger(__name__)


def compute_title_similarity(title1: str, title2: str) -> float:
    """Calculate normalized title similarity ratio using SequenceMatcher.

    Scores range from 0.0 (completely dissimilar) to 1.0 (exact match).
    """
    t1 = normalize_title_for_matching(title1)
    t2 = normalize_title_for_matching(title2)
    if not t1 or not t2:
        return 0.0
    if t1 == t2:
        return 1.0

    # Quick word overlap ratio (Jaccard on token sets)
    words1 = set(t1.split())
    words2 = set(t2.split())
    if not words1 or not words2:
        return 0.0

    jaccard = len(words1 & words2) / len(words1 | words2)
    seq_ratio = difflib.SequenceMatcher(None, t1, t2).ratio()

    # Blended token + sequence similarity
    return 0.4 * jaccard + 0.6 * seq_ratio


def generate_deterministic_canonical_id(paper: CanonicalPaper) -> str:
    """Generate a deterministic canonical ID based on primary identifiers.

    Hierarchy:
    1. DOI (most universal) -> rg_doi_<hash>
    2. arXiv ID -> rg_arx_<hash>
    3. Normalized title + first author last name -> rg_tit_<hash>
    """
    if paper.doi:
        h = hashlib.sha256(paper.doi.strip().lower().encode("utf-8")).hexdigest()[:12]
        return f"rg_doi_{h}"

    if paper.arxiv_id:
        h = hashlib.sha256(paper.arxiv_id.strip().lower().encode("utf-8")).hexdigest()[:12]
        return f"rg_arx_{h}"

    norm_title = normalize_title_for_matching(paper.title)
    first_author_last = ""
    if paper.authors and paper.authors[0].last_name:
        first_author_last = paper.authors[0].last_name.lower().strip()
    elif paper.authors and paper.authors[0].name:
        first_author_last = paper.authors[0].name.split()[-1].lower().strip()

    seed = f"{norm_title}|{first_author_last}|{paper.publication_year or ''}"
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"rg_tit_{h}"


class IdentityResolver:
    """Resolves scientific work identities and matches incoming records against existing clusters."""

    def __init__(
        self,
        fuzzy_title_threshold: float = 0.90,
        high_confidence_title_threshold: float = 0.96,
    ):
        self.fuzzy_title_threshold = fuzzy_title_threshold
        self.high_confidence_title_threshold = high_confidence_title_threshold

    def match_papers(
        self,
        p1: CanonicalPaper,
        p2: CanonicalPaper,
    ) -> Tuple[bool, ConfidenceLevel, str]:
        """Determine whether two paper records represent the same scientific work.

        Returns:
            (is_match, confidence_level, match_reason)
        """
        # 1. Exact DOI match
        if p1.doi and p2.doi and p1.doi.lower() == p2.doi.lower():
            return True, ConfidenceLevel.EXACT, f"Matching DOI: {p1.doi}"

        # 2. Exact arXiv ID match
        if p1.arxiv_id and p2.arxiv_id and p1.arxiv_id.lower() == p2.arxiv_id.lower():
            return True, ConfidenceLevel.EXACT, f"Matching arXiv ID: {p1.arxiv_id}"

        # 3. Normalized Title Matching
        t1_norm = normalize_title_for_matching(p1.title)
        t2_norm = normalize_title_for_matching(p2.title)

        if not t1_norm or not t2_norm:
            return False, ConfidenceLevel.UNRESOLVED, "Missing normalized title"

        # Check exact normalized title match
        if t1_norm == t2_norm:
            # Check author overlap if authors are available
            author_overlap = self._check_author_overlap(p1, p2)
            year_match = self._check_year_compatibility(p1, p2)

            if author_overlap and year_match:
                return True, ConfidenceLevel.EXACT, "Exact normalized title and author/year match"
            elif author_overlap or year_match:
                return True, ConfidenceLevel.HIGH_CONFIDENCE, "Exact title match with consistent metadata"
            else:
                return True, ConfidenceLevel.POSSIBLE, "Exact title match but differing author/year"

        # 4. Fuzzy title comparison
        sim = compute_title_similarity(p1.title, p2.title)
        if sim >= self.high_confidence_title_threshold:
            if self._check_author_overlap(p1, p2) and self._check_year_compatibility(p1, p2):
                return True, ConfidenceLevel.HIGH_CONFIDENCE, f"High title similarity ({sim:.2f}) + author/year match"

        if sim >= self.fuzzy_title_threshold:
            if self._check_author_overlap(p1, p2) and self._check_year_compatibility(p1, p2):
                return True, ConfidenceLevel.POSSIBLE, f"Possible duplicate ({sim:.2f} similarity)"

        return False, ConfidenceLevel.UNRESOLVED, "No matching identity criteria satisfied"

    def _check_author_overlap(self, p1: CanonicalPaper, p2: CanonicalPaper) -> bool:
        """Check if there is at least one overlapping author between two records."""
        if not p1.authors or not p2.authors:
            return True  # If author metadata is missing on either, do not penalize

        lasts1 = {a.last_name.lower().strip() for a in p1.authors if a.last_name}
        lasts2 = {a.last_name.lower().strip() for a in p2.authors if a.last_name}

        if lasts1 and lasts2 and (lasts1 & lasts2):
            return True

        names1 = {normalize_title_for_matching(a.name) for a in p1.authors if a.name}
        names2 = {normalize_title_for_matching(a.name) for a in p2.authors if a.name}

        return bool(names1 & names2)

    def _check_year_compatibility(self, p1: CanonicalPaper, p2: CanonicalPaper) -> bool:
        """Check if publication years are identical or within 1 year (e.g. preprint vs pub)."""
        if p1.publication_year is None or p2.publication_year is None:
            return True
        return abs(p1.publication_year - p2.publication_year) <= 1
