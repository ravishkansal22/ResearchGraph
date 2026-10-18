"""ResearchGraph Phase 4: Canonical Scientific Knowledge Base Schemas.

Defines the normalized, persistent, and queryable scientific knowledge models
representing canonical papers, entities, mentions, statements, and relationships.
Schema Version: 0.5.0
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field, field_validator

from dataset.schemas.canonical_paper import Author, Topic, Venue
from dataset.schemas.scientific_knowledge import (
    AttributionType,
    EvidenceSpan,
    ExtractionProvenance,
    ScientificEntityType,
    ScientificRelationType,
    ScientificStatementType,
    ValidationStatus,
)


class AliasResolutionStatus(str, Enum):
    """Resolution status of concept aliases and lexical variants."""
    CONFIRMED = "CONFIRMED"            # Formally verified synonymous term or acronym
    CANDIDATE = "CANDIDATE"            # High-similarity candidate awaiting domain review
    UNRESOLVED = "UNRESOLVED"          # Ambiguous or domain-dependent variation
    SEPARATE = "SEPARATE"              # Confirmed distinct concept (must not merge)


class QuarantineReason(str, Enum):
    """Diagnostic categorization for quarantined extraction records."""
    DANGLING_RELATION_ENDPOINT = "DANGLING_RELATION_ENDPOINT"
    MISSING_PROVENANCE_FIELD = "MISSING_PROVENANCE_FIELD"
    INVALID_SPAN_BOUNDS = "INVALID_SPAN_BOUNDS"
    SCHEMA_VALIDATION_ERROR = "SCHEMA_VALIDATION_ERROR"
    UNGROUNDED_EVIDENCE = "UNGROUNDED_EVIDENCE"
    DUPLICATE_IMPORT_COLLISION = "DUPLICATE_IMPORT_COLLISION"
    UNKNOWN = "UNKNOWN"


class CanonicalPaperNode(BaseModel):
    """Canonical representation of a scientific paper within the knowledge base."""
    paper_id: str = Field(..., description="Stable canonical paper identifier (e.g. rg_doi_xxx)")
    schema_version: str = Field(default="0.5.0", description="Schema definition version")
    doi: Optional[str] = Field(default=None, description="Normalized DOI string")
    arxiv_id: Optional[str] = Field(default=None, description="Normalized arXiv identifier")
    title: str = Field(..., description="Normalized paper title")
    abstract: Optional[str] = Field(default=None, description="Full abstract text")
    publication_year: Optional[int] = Field(default=None, description="Year of publication")
    venue: Optional[Venue] = Field(default=None, description="Publication venue details")
    authors: List[Author] = Field(default_factory=list, description="Ordered list of authors")
    topics: List[Topic] = Field(default_factory=list, description="Domain and concept topics")
    open_access_url: Optional[str] = Field(default=None, description="Direct URL to open-access paper")
    file_hash: Optional[str] = Field(default=None, description="SHA-256 hash of source PDF artifact")
    total_entities_count: int = Field(default=0, description="Count of extracted entities linked to paper")
    total_statements_count: int = Field(default=0, description="Count of statements linked to paper")
    total_relationships_count: int = Field(default=0, description="Count of relations linked to paper")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EntityMention(BaseModel):
    """Individual textual occurrence of a scientific entity grounded in a specific chunk."""
    mention_id: str = Field(..., description="Stable unique mention ID (e.g. ent_men_xxx)")
    entity_id: str = Field(..., description="Foreign key to CanonicalEntityNode")
    paper_id: str = Field(..., description="Foreign key to CanonicalPaperNode")
    chunk_id: str = Field(..., description="Source chunk identifier")
    category: ScientificEntityType = Field(..., description="Scientific entity category")
    surface_text: str = Field(..., description="Exact original surface text as appeared in chunk")
    normalized_name: str = Field(..., description="Conservative normalized form of mention")
    evidence: EvidenceSpan = Field(..., description="Character-level supporting evidence span")
    provenance: ExtractionProvenance = Field(..., description="Complete extraction provenance")
    attribution: AttributionType = Field(default=AttributionType.AUTHOR_STATED, description="Attribution origin")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")
    extraction_version: str = Field(default="v0.4.1", description="Originating pipeline version")
    validation_status: ValidationStatus = Field(default=ValidationStatus.VALIDATED, description="Grounding status")
    upstream_record_id: str = Field(..., description="Record ID from upstream extraction stage")


class CanonicalEntityNode(BaseModel):
    """Consolidated, canonical scientific concept or entity in the knowledge base."""
    entity_id: str = Field(..., description="Stable deterministic entity ID (e.g. kb_ent_method_xxx)")
    schema_version: str = Field(default="0.5.0", description="Schema definition version")
    category: ScientificEntityType = Field(..., description="Scientific entity category")
    canonical_name: str = Field(..., description="Normalized canonical concept label")
    aliases: List[str] = Field(default_factory=list, description="Confirmed synonym and surface variants")
    mentions_count: int = Field(default=1, description="Total occurrences across the corpus")
    paper_ids: List[str] = Field(default_factory=list, description="List of papers where entity is mentioned")
    chunk_ids: List[str] = Field(default_factory=list, description="List of chunks containing mentions")
    mention_ids: List[str] = Field(default_factory=list, description="Foreign keys to individual EntityMentions")
    description: Optional[str] = Field(default=None, description="Grounded concept definition or description")
    validation_status: ValidationStatus = Field(default=ValidationStatus.VALIDATED, description="Validation status")
    alias_resolution_status: AliasResolutionStatus = Field(
        default=AliasResolutionStatus.CONFIRMED,
        description="Confidence of alias consolidation",
    )
    first_seen_version: str = Field(default="v0.4.0", description="Earliest pipeline version where entity appeared")
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CanonicalStatementNode(BaseModel):
    """Grounded scientific proposition, claim, result, limitation, or future direction."""
    statement_id: str = Field(..., description="Stable unique statement ID (e.g. kb_stmt_xxx)")
    schema_version: str = Field(default="0.5.0", description="Schema definition version")
    category: ScientificStatementType = Field(..., description="Statement category")
    surface_text: str = Field(..., description="Verbatim original sentence or clause")
    normalized_statement: str = Field(..., description="Normalized statement representation")
    paper_id: str = Field(..., description="Foreign key to CanonicalPaperNode")
    chunk_id: str = Field(..., description="Source chunk identifier")
    evidence: EvidenceSpan = Field(..., description="Character-level supporting evidence span")
    provenance: ExtractionProvenance = Field(..., description="Full source provenance")
    attribution: AttributionType = Field(default=AttributionType.AUTHOR_STATED, description="Attribution origin")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")
    extraction_version: str = Field(default="v0.4.1", description="Originating pipeline version")
    validation_status: ValidationStatus = Field(default=ValidationStatus.VALIDATED, description="Grounding status")
    validation_notes: List[str] = Field(default_factory=list, description="Validation notes or warnings")
    related_entity_ids: List[str] = Field(default_factory=list, description="Linked CanonicalEntityNode IDs")
    upstream_record_id: str = Field(..., description="Record ID from upstream extraction stage")


class CanonicalRelationshipNode(BaseModel):
    """Verified semantic relationship between canonical entities or statements."""
    relationship_id: str = Field(..., description="Stable unique relationship ID (e.g. kb_rel_xxx)")
    schema_version: str = Field(default="0.5.0", description="Schema definition version")
    relation_type: ScientificRelationType = Field(..., description="Semantic relation predicate")
    source_id: str = Field(..., description="Foreign key to subject node (entity or statement)")
    target_id: str = Field(..., description="Foreign key to object node (entity or statement)")
    source_type: str = Field(default="ENTITY", description="'ENTITY' or 'STATEMENT'")
    target_type: str = Field(default="ENTITY", description="'ENTITY' or 'STATEMENT'")
    paper_id: str = Field(..., description="Foreign key to CanonicalPaperNode")
    chunk_id: str = Field(..., description="Source chunk identifier")
    surface_text: Optional[str] = Field(default=None, description="Connecting phrase or trigger span in text")
    evidence: EvidenceSpan = Field(..., description="Supporting evidence span for relation")
    provenance: ExtractionProvenance = Field(..., description="Full source provenance")
    attribution: AttributionType = Field(default=AttributionType.AUTHOR_STATED, description="Attribution origin")
    is_directed: bool = Field(default=True, description="True if relationship is directed")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score")
    extraction_version: str = Field(default="v0.4.1", description="Originating pipeline version")
    validation_status: ValidationStatus = Field(default=ValidationStatus.VALIDATED, description="Grounding status")
    upstream_relation_id: str = Field(..., description="Relation ID from upstream extraction stage")


class QuarantinedRecord(BaseModel):
    """Quarantine container for extraction records failing validation or referential integrity."""
    quarantine_id: str = Field(..., description="Stable quarantine record ID (e.g. kb_quar_xxx)")
    record_type: str = Field(..., description="'ENTITY', 'STATEMENT', or 'RELATIONSHIP'")
    quarantine_reason: QuarantineReason = Field(..., description="Diagnostic failure reason")
    error_message: str = Field(..., description="Detailed diagnostic error message")
    source_version: str = Field(default="unknown", description="Upstream extractor version")
    upstream_id: Optional[str] = Field(default=None, description="Original record/relation ID if present")
    raw_payload: Dict[str, Any] = Field(..., description="Complete original raw record payload")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AliasMapping(BaseModel):
    """Explicit mapping between a surface variation and its canonical entity name."""
    surface_form: str = Field(..., description="Normalized surface variant (e.g. 'cnn')")
    canonical_name: str = Field(..., description="Canonical representative name (e.g. 'convolutional neural network')")
    category: ScientificEntityType = Field(..., description="Associated scientific entity category")
    status: AliasResolutionStatus = Field(default=AliasResolutionStatus.CONFIRMED, description="Resolution status")
    rationale: str = Field(default="Acronym / Full name expansion", description="Scholarly or linguistic rationale")


class KnowledgeBaseManifest(BaseModel):
    """Comprehensive, reproducible build manifest for the Scientific Knowledge Base."""
    kb_version: str = Field(default="v0.5.0", description="Knowledge base release version")
    schema_version: str = Field(default="0.5.0", description="Schema version")
    build_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    upstream_sources: Dict[str, str] = Field(default_factory=dict, description="Paths and versions of upstream inputs")
    total_papers_count: int = Field(default=0, description="Total canonical papers ingested")
    total_canonical_entities_count: int = Field(default=0, description="Total unique canonical entities")
    total_entity_mentions_count: int = Field(default=0, description="Total individual entity mentions grounded")
    total_statements_count: int = Field(default=0, description="Total scientific statements")
    total_relationships_count: int = Field(default=0, description="Total verified relationships")
    total_quarantined_records_count: int = Field(default=0, description="Total records quarantined")
    confirmed_aliases_count: int = Field(default=0, description="Count of confirmed aliases applied")
    entities_by_category: Dict[str, int] = Field(default_factory=dict, description="Canonical entity counts by category")
    statements_by_category: Dict[str, int] = Field(default_factory=dict, description="Statement counts by category")
    relationships_by_type: Dict[str, int] = Field(default_factory=dict, description="Relationship counts by relation type")
    quarantine_reasons_breakdown: Dict[str, int] = Field(default_factory=dict, description="Breakdown of quarantine reasons")
    referential_integrity_pass_rate: float = Field(default=1.0, description="Fraction of valid relationships")
    provenance_completeness_rate: float = Field(default=1.0, description="Fraction of records with full provenance")
