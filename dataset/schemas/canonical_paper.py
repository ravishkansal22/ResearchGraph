"""ResearchGraph Canonical Dataset Models and Schema Definitions.

Phase 1: Literature Dataset Collection (Schema Version 0.2.0 / v0.1.1)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ConfidenceLevel(str, Enum):
    """Confidence levels for identity resolution and duplicate detection."""
    EXACT = "EXACT"                      # Exact identifier match (DOI, arXiv ID, canonical source ID)
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"  # Normalized title + primary author + exact/adjacent year
    POSSIBLE = "POSSIBLE"                # High fuzzy title similarity + partial author overlap
    UNRESOLVED = "UNRESOLVED"            # Conflicting signals or insufficient overlap to merge


class FulltextStatus(str, Enum):
    """Status of full-text discovery and artifact acquisition."""
    DISCOVERABLE = "DISCOVERABLE"        # Legitimate OA URL / PDF link verified in metadata
    DOWNLOADED = "DOWNLOADED"            # Artifact physically acquired and stored locally
    UNAVAILABLE = "UNAVAILABLE"          # Confirmed closed access / paywalled / no OA link
    NOT_CHECKED = "NOT_CHECKED"          # OA discovery has not been evaluated
    FAILED = "FAILED"                    # Acquisition attempted but failed (e.g. 403, 404, timeout)

    # Backward-compatibility aliases for v0.1.0 pipelines
    FULLTEXT_AVAILABLE = "DISCOVERABLE"
    FULLTEXT_UNAVAILABLE = "UNAVAILABLE"
    FULLTEXT_NOT_CHECKED = "NOT_CHECKED"
    FULLTEXT_FAILED = "FAILED"


class DocumentType(str, Enum):
    """Classification of the scientific document."""
    RESEARCH_ARTICLE = "RESEARCH_ARTICLE"
    CONFERENCE_PAPER = "CONFERENCE_PAPER"
    REVIEW = "REVIEW"
    SURVEY = "SURVEY"
    BOOK_CHAPTER = "BOOK_CHAPTER"
    EDITORIAL = "EDITORIAL"
    FRONT_MATTER = "FRONT_MATTER"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class Author(BaseModel):
    """Normalized author representation."""
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    orcid: Optional[str] = None
    affiliations: List[str] = Field(default_factory=list)


class Institution(BaseModel):
    """Normalized institution representation."""
    name: str
    ror_id: Optional[str] = None
    country_code: Optional[str] = None


class Venue(BaseModel):
    """Normalized publication venue (journal, conference, preprint server, book series)."""
    name: Optional[str] = None
    type: Optional[str] = None  # e.g., journal, conference, repository, book, book series
    issn: Optional[str] = None
    isbn: Optional[str] = None
    raw_venue: Optional[str] = None


class Topic(BaseModel):
    """Normalized topic, concept, or domain tag."""
    name: str
    score: Optional[float] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class ProvenanceRecord(BaseModel):
    """Provenance tracking for data lineage."""
    source: str                          # e.g. "openalex", "semantic_scholar", "arxiv", "crossref"
    source_record_id: str               # ID in that specific source
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_url: Optional[str] = None
    source_version: Optional[str] = None
    raw_payload_checksum: Optional[str] = None


class SourceRecords(BaseModel):
    """Mapping of source names to their respective native identifiers."""
    openalex: Optional[str] = None
    semantic_scholar: Optional[str] = None
    arxiv: Optional[str] = None
    crossref: Optional[str] = None
    other: Dict[str, str] = Field(default_factory=dict)


class OpenAccessInfo(BaseModel):
    """Open access status and license information."""
    is_oa: bool = False
    oa_status: Optional[str] = None     # gold, green, bronze, hybrid, closed
    oa_url: Optional[str] = None
    license: Optional[str] = None


class CanonicalPaper(BaseModel):
    """Canonical ResearchGraph Paper Representation.

    Source-independent representation of a scientific publication,
    consolidated from one or multiple scholarly sources with full provenance.
    """
    canonical_id: str = Field(..., description="Unique ResearchGraph canonical paper identifier (e.g. rg_xxxxx)")
    title: str = Field(..., description="Normalized paper title")
    abstract: Optional[str] = Field(default=None, description="Full abstract text if available")
    document_type: DocumentType = Field(default=DocumentType.UNKNOWN, description="Classified document type")
    authors: List[Author] = Field(default_factory=list, description="Ordered list of authors with affiliations")
    institutions: List[Institution] = Field(default_factory=list, description="Extracted institutions/affiliations")
    venue: Optional[Venue] = Field(default=None, description="Publication venue details")
    
    # Granular publication dates
    published_date: Optional[str] = Field(default=None, description="Primary resolved publication date (YYYY-MM-DD or YYYY)")
    online_publication_date: Optional[str] = Field(default=None, description="Date first published or made available online")
    print_publication_date: Optional[str] = Field(default=None, description="Date of print/volume publication")
    issued_date: Optional[str] = Field(default=None, description="Formal issue or copyright registration date")
    publication_date: Optional[str] = Field(default=None, description="Backward-compatible alias for primary publication date")
    publication_year: Optional[int] = Field(default=None, description="Year of publication")

    # Identifiers
    doi: Optional[str] = Field(default=None, description="Normalized DOI string (e.g. 10.1145/1234567)")
    arxiv_id: Optional[str] = Field(default=None, description="Normalized arXiv identifier (e.g. 2401.12345)")
    other_source_ids: SourceRecords = Field(default_factory=SourceRecords, description="Source-specific IDs")

    # Thematic and semantic metadata
    topics: List[Topic] = Field(default_factory=list, description="Associated topics and field classifications")
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")

    # Citation network
    references: List[str] = Field(default_factory=list, description="Referenced DOIs, arXiv IDs, or source IDs")
    citation_count: Optional[int] = Field(default=None, description="Total recorded citation count")
    influential_citation_count: Optional[int] = Field(default=None, description="Influential citations count (if provided)")

    # Full text & access
    open_access: OpenAccessInfo = Field(default_factory=OpenAccessInfo, description="Open access status and URL")
    fulltext_status: FulltextStatus = Field(default=FulltextStatus.NOT_CHECKED, description="Explicit full-text status")
    fulltext_available: FulltextStatus = Field(default=FulltextStatus.NOT_CHECKED, description="Backward-compatible status flag")
    fulltext_url: Optional[str] = Field(default=None, description="Direct URL to accessible full-text PDF/HTML")
    fulltext_path: Optional[str] = Field(default=None, description="Local relative path to downloaded full-text artifact")

    # Lineage and confidence
    source_records: SourceRecords = Field(default_factory=SourceRecords, description="Active source records linked")
    provenance: List[ProvenanceRecord] = Field(default_factory=list, description="Full lineage of source ingestions")
    identity_confidence: ConfidenceLevel = Field(default=ConfidenceLevel.EXACT, description="Confidence of consolidation")

    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @field_validator("fulltext_status", "fulltext_available", mode="before")
    @classmethod
    def _coerce_fulltext_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            clean = v.strip().upper()
            legacy_map = {
                "AVAILABLE": FulltextStatus.DISCOVERABLE,
                "FULLTEXT_AVAILABLE": FulltextStatus.DISCOVERABLE,
                "DISCOVERABLE": FulltextStatus.DISCOVERABLE,
                "DOWNLOADED": FulltextStatus.DOWNLOADED,
                "FULLTEXT_DOWNLOADED": FulltextStatus.DOWNLOADED,
                "UNAVAILABLE": FulltextStatus.UNAVAILABLE,
                "FULLTEXT_UNAVAILABLE": FulltextStatus.UNAVAILABLE,
                "NOT_CHECKED": FulltextStatus.NOT_CHECKED,
                "FULLTEXT_NOT_CHECKED": FulltextStatus.NOT_CHECKED,
                "FAILED": FulltextStatus.FAILED,
                "FULLTEXT_FAILED": FulltextStatus.FAILED,
            }
            if clean in legacy_map:
                return legacy_map[clean]
        return v


class RawRecord(BaseModel):
    """Raw unmodified source response container."""
    source: str
    source_record_id: str
    fetched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    query: Optional[str] = None
    raw_data: Dict[str, Any]
