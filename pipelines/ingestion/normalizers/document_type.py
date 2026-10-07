"""Document Type Classification Utilities.

Maps heterogeneous source publication types into standardized ResearchGraph DocumentType enums.
"""

from __future__ import annotations

import re
from typing import Optional
from dataset.schemas.canonical_paper import DocumentType

# Regular expressions for title heuristic disambiguation
SURVEY_RE = re.compile(r"\b(?:survey|a comprehensive survey|a systematic survey)\b", re.IGNORECASE)
REVIEW_RE = re.compile(r"\b(?:a review of|systematic (?:literature )?review|overview and perspective|state[- ]of[- ]the[- ]art review|literature review)\b", re.IGNORECASE)


def classify_document_type(
    source_type: Optional[str],
    source: str,
    title: Optional[str] = None,
) -> DocumentType:
    """Classify the document type from source-specific metadata and title cues.

    Args:
        source_type: Raw publication type string reported by the scholarly source.
        source: Scholarly source adapter name ('openalex', 'crossref', 'arxiv', 'semantic_scholar').
        title: Normalized or raw paper title for disambiguating surveys and reviews.

    Returns:
        DocumentType enum member.
    """
    clean_type = (source_type or "").strip().lower()
    title_str = title or ""

    # Check survey/review title cues first
    if SURVEY_RE.search(title_str):
        return DocumentType.SURVEY
    if REVIEW_RE.search(title_str):
        return DocumentType.REVIEW

    if source == "openalex":
        if clean_type in ("article", "journal-article"):
            return DocumentType.RESEARCH_ARTICLE
        elif clean_type in ("conference-paper", "conference-abstract", "proceedings"):
            return DocumentType.CONFERENCE_PAPER
        elif clean_type in ("book-chapter", "book-section"):
            return DocumentType.BOOK_CHAPTER
        elif clean_type in ("book", "monograph", "edited-book"):
            return DocumentType.BOOK_CHAPTER
        elif clean_type in ("review", "systematic-review"):
            return DocumentType.REVIEW
        elif clean_type in ("editorial", "letter", "note"):
            return DocumentType.EDITORIAL
        elif clean_type in ("reference-entry", "erratum", "paratext"):
            return DocumentType.FRONT_MATTER
        elif clean_type in ("preprint", "posted-content"):
            return DocumentType.RESEARCH_ARTICLE
        elif clean_type in ("peer-review", "software", "dataset", "other"):
            return DocumentType.OTHER
        return DocumentType.UNKNOWN

    elif source == "crossref":
        if clean_type in ("journal-article", "posted-content"):
            return DocumentType.RESEARCH_ARTICLE
        elif clean_type in ("proceedings-article", "proceedings"):
            return DocumentType.CONFERENCE_PAPER
        elif clean_type in ("book-chapter", "book-section"):
            return DocumentType.BOOK_CHAPTER
        elif clean_type in ("monograph", "edited-book", "book", "reference-book"):
            return DocumentType.BOOK_CHAPTER
        elif clean_type in ("editorial", "letter"):
            return DocumentType.EDITORIAL
        elif clean_type in ("journal", "journal-issue", "component"):
            return DocumentType.FRONT_MATTER
        elif clean_type in ("peer-review", "dataset"):
            return DocumentType.OTHER
        elif clean_type in ("other", ""):
            return DocumentType.UNKNOWN
        return DocumentType.UNKNOWN

    elif source == "arxiv":
        return DocumentType.RESEARCH_ARTICLE

    elif source == "semantic_scholar":
        if "journal" in clean_type or "article" in clean_type:
            return DocumentType.RESEARCH_ARTICLE
        elif "conference" in clean_type or "proceedings" in clean_type:
            return DocumentType.CONFERENCE_PAPER
        elif "review" in clean_type:
            return DocumentType.REVIEW
        elif "book" in clean_type:
            return DocumentType.BOOK_CHAPTER
        elif "editorial" in clean_type:
            return DocumentType.EDITORIAL
        return DocumentType.RESEARCH_ARTICLE

    return DocumentType.UNKNOWN
