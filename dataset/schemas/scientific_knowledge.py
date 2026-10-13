"""ResearchGraph Phase 3: Scientific Knowledge Extraction Schemas.

Defines the structured, evidence-grounded, provenance-preserving representation
for scientific entities, statements, and relationships extracted from processed literature.
Schema Version: 0.4.0
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ScientificEntityType(str, Enum):
    """Scientific entity and concept categories."""
    METHOD = "METHOD"                 # Algorithm, architecture, model, technique, or intervention
    PROBLEM = "PROBLEM"               # Scientific or technical problem being addressed
    BOTTLENECK = "BOTTLENECK"         # Mechanism or constraint that limits a method or system
    METRIC = "METRIC"                 # Evaluation metric or measured quantity
    DATASET = "DATASET"               # Dataset or benchmark
    TASK = "TASK"                     # Task or experimental objective
    ASSUMPTION = "ASSUMPTION"         # Condition assumed by the authors
    DOMAIN = "DOMAIN"                 # Scientific application area


class ScientificStatementType(str, Enum):
    """Scientific statement and proposition categories."""
    CLAIM = "CLAIM"                   # Proposition or core hypothesis made by the authors
    RESULT = "RESULT"                 # Reported experimental or analytical finding
    LIMITATION = "LIMITATION"         # Stated limitation or weakness
    FUTURE_DIRECTION = "FUTURE_DIRECTION"  # Research direction proposed by the authors
    FAILURE_MODE = "FAILURE_MODE"     # Reported failure condition or reason for underperformance


class ScientificRelationType(str, Enum):
    """Grounded semantic relationships between scientific records."""
    ADDRESSES = "ADDRESSES"           # Method addresses problem
    USES = "USES"                     # Method uses dataset, metric, or component
    IMPROVES = "IMPROVES"             # Method improves a stated outcome relative to a baseline
    OUTPERFORMS = "OUTPERFORMS"       # Method outperforms a named baseline under specified conditions
    LIMITED_BY = "LIMITED_BY"         # Method or system is limited by a bottleneck
    EVALUATED_ON = "EVALUATED_ON"     # Method is evaluated on a dataset or task
    ASSUMES = "ASSUMES"               # Method or claim relies on an assumption
    REPORTS = "REPORTS"               # Paper reports a result or claim
    SUGGESTS = "SUGGESTS"             # Authors suggest a future direction
    CONTRADICTS = "CONTRADICTS"       # One statement conflicts with another


class AttributionType(str, Enum):
    """Epistemological attribution of the extracted knowledge."""
    AUTHOR_STATED = "AUTHOR_STATED"   # Explicitly stated by the authors in the primary text
    SYSTEM_INFERRED = "SYSTEM_INFERRED"  # Synthesized, normalized, or deduced by the system


class ValidationStatus(str, Enum):
    """Quality and evidence grounding verification status."""
    VALIDATED = "VALIDATED"           # Grounding verified against source text and provenance
    NEEDS_REVIEW = "NEEDS_REVIEW"     # Borderline confidence, complex phrasing, or partial alignment
    REJECTED = "REJECTED"             # Failed grounding (hallucination, missing evidence, or schema invalid)


class EvidenceSpan(BaseModel):
    """Cryptographic and character-level evidence span linking extraction to source text."""
    text: str = Field(..., description="Exact textual evidence quotation extracted from chunk")
    start_char: int = Field(..., ge=0, description="0-indexed start character offset in chunk text")
    end_char: int = Field(..., gt=0, description="0-indexed end character offset in chunk text")
    is_exact_match: bool = Field(default=True, description="True if text matches chunk[start_char:end_char] exactly")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in evidence boundary alignment")

    @field_validator("end_char")
    @classmethod
    def validate_span_bounds(cls, v: int, info: Any) -> int:
        start = info.data.get("start_char", 0)
        if v <= start:
            raise ValueError(f"end_char ({v}) must be strictly greater than start_char ({start})")
        return v


class ExtractionProvenance(BaseModel):
    """Complete document, section, and chunk provenance for reproducibility."""
    canonical_id: str = Field(..., description="Canonical paper identifier (e.g. rg_doi_xxx)")
    document_id: Optional[str] = Field(default=None, description="Document processing identifier")
    chunk_id: str = Field(..., description="Source chunk identifier (e.g. chk_rg_xxx_A_001)")
    section_id: Optional[str] = Field(default=None, description="Containing section identifier")
    section_title: Optional[str] = Field(default=None, description="Containing section heading")
    section_level: Optional[int] = Field(default=1, description="Section hierarchy level")
    page_start: Optional[int] = Field(default=None, description="Starting physical page number")
    page_end: Optional[int] = Field(default=None, description="Ending physical page number")
    file_hash: Optional[str] = Field(default=None, description="SHA-256 hash of source PDF")


class ScientificEntityRecord(BaseModel):
    """Typed scientific entity or concept record."""
    record_id: str = Field(..., description="Stable unique record ID (e.g. ent_rg_xxx_001)")
    schema_version: str = Field(default="0.4.0", description="Schema definition version")
    category: ScientificEntityType = Field(..., description="Scientific entity category")
    surface_text: str = Field(..., description="Original surface text as it appeared in source chunk")
    normalized_name: str = Field(..., description="Conservative normalized entity name")
    evidence: EvidenceSpan = Field(..., description="Character-level supporting evidence span")
    provenance: ExtractionProvenance = Field(..., description="Full source provenance")
    attribution: AttributionType = Field(default=AttributionType.AUTHOR_STATED, description="Attribution origin")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score")
    extraction_method: str = Field(default="rule_based_v1", description="Identifier of extractor algorithm/model")
    extraction_version: str = Field(default="v0.4.0", description="Pipeline execution version")
    validation_status: ValidationStatus = Field(default=ValidationStatus.VALIDATED, description="Grounding status")
    validation_notes: List[str] = Field(default_factory=list, description="Diagnostic notes or validation warnings")
    related_record_ids: List[str] = Field(default_factory=list, description="Linked record IDs in knowledge graph")


class ScientificStatementRecord(BaseModel):
    """Typed scientific statement, claim, finding, limitation, or future direction."""
    record_id: str = Field(..., description="Stable unique record ID (e.g. stmt_rg_xxx_001)")
    schema_version: str = Field(default="0.4.0", description="Schema definition version")
    category: ScientificStatementType = Field(..., description="Scientific statement category")
    surface_text: str = Field(..., description="Exact original statement sentence or clause")
    normalized_statement: Optional[str] = Field(default=None, description="Conservative normalized statement")
    evidence: EvidenceSpan = Field(..., description="Character-level supporting evidence span")
    provenance: ExtractionProvenance = Field(..., description="Full source provenance")
    attribution: AttributionType = Field(default=AttributionType.AUTHOR_STATED, description="Attribution origin")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score")
    extraction_method: str = Field(default="rule_based_v1", description="Identifier of extractor algorithm/model")
    extraction_version: str = Field(default="v0.4.0", description="Pipeline execution version")
    validation_status: ValidationStatus = Field(default=ValidationStatus.VALIDATED, description="Grounding status")
    validation_notes: List[str] = Field(default_factory=list, description="Diagnostic notes or validation warnings")
    related_entity_ids: List[str] = Field(default_factory=list, description="Extracted entities mentioned in statement")
    related_record_ids: List[str] = Field(default_factory=list, description="Linked statement or relation records")


class ScientificRelationRecord(BaseModel):
    """Typed directional scientific relationship between extracted entities or statements."""
    relation_id: str = Field(..., description="Stable unique relation ID (e.g. rel_rg_xxx_001)")
    schema_version: str = Field(default="0.4.0", description="Schema definition version")
    relation_type: ScientificRelationType = Field(..., description="Typed relationship edge")
    source_id: str = Field(..., description="Record ID of source node (entity or statement)")
    target_id: str = Field(..., description="Record ID of target node (entity or statement)")
    source_category: str = Field(..., description="Category label of source record")
    target_category: str = Field(..., description="Category label of target record")
    surface_text: Optional[str] = Field(default=None, description="Connecting phrase or trigger span in text")
    evidence: EvidenceSpan = Field(..., description="Character-level supporting evidence span for relationship")
    provenance: ExtractionProvenance = Field(..., description="Full source provenance")
    attribution: AttributionType = Field(default=AttributionType.AUTHOR_STATED, description="Attribution origin")
    is_directed: bool = Field(default=True, description="Whether relation edge is strictly directed")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score")
    extraction_method: str = Field(default="rule_based_v1", description="Identifier of extractor algorithm/model")
    extraction_version: str = Field(default="v0.4.0", description="Pipeline execution version")
    validation_status: ValidationStatus = Field(default=ValidationStatus.VALIDATED, description="Grounding status")
    validation_notes: List[str] = Field(default_factory=list, description="Diagnostic notes or validation warnings")


class ExtractionBatchResult(BaseModel):
    """Container for batch extraction results and execution statistics."""
    batch_id: str = Field(..., description="Execution batch identifier")
    pipeline_version: str = Field(default="v0.4.0", description="Extraction pipeline version")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC execution timestamp",
    )
    total_chunks_processed: int = Field(default=0, description="Number of source chunks analyzed")
    entities: List[ScientificEntityRecord] = Field(default_factory=list, description="Extracted entity records")
    statements: List[ScientificStatementRecord] = Field(default_factory=list, description="Extracted statement records")
    relations: List[ScientificRelationRecord] = Field(default_factory=list, description="Extracted relationship records")
    rejected_count: int = Field(default=0, description="Number of rejected candidate extractions")
    validation_summary: Dict[str, int] = Field(default_factory=dict, description="Counts by validation status")
