"""Validation and Referential Integrity Module for Scientific Knowledge Base.

Validates entity mentions, scientific statements, relationships, and source provenance,
routing ungrounded, invalid, or dangling records to quarantine containers.
Schema Version: 0.5.0
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import ValidationError

from dataset.schemas.scientific_knowledge import (
    AttributionType,
    EvidenceSpan,
    ExtractionProvenance,
    ScientificEntityType,
    ScientificRelationType,
    ScientificStatementType,
    ValidationStatus,
)
from dataset.schemas.scientific_knowledge_base import (
    CanonicalEntityNode,
    CanonicalPaperNode,
    CanonicalRelationshipNode,
    CanonicalStatementNode,
    EntityMention,
    QuarantineReason,
    QuarantinedRecord,
)
from pipelines.knowledge_base.normalizer import (
    generate_canonical_relationship_id,
    generate_canonical_statement_id,
    generate_mention_id,
    generate_quarantine_id,
    normalize_text,
    resolve_canonical_entity,
)

logger = logging.getLogger(__name__)

# Valid entity types set
VALID_ENTITY_TYPES: Set[str] = {e.value for e in ScientificEntityType}
# Valid statement types set
VALID_STATEMENT_TYPES: Set[str] = {s.value for s in ScientificStatementType}
# Valid relationship types set
VALID_RELATION_TYPES: Set[str] = {r.value for r in ScientificRelationType}


def create_quarantine_record(
    record_type: str,
    reason: QuarantineReason,
    error_message: str,
    raw_payload: Dict[str, Any],
    source_version: str = "unknown",
    upstream_id: Optional[str] = None,
) -> QuarantinedRecord:
    """Helper to build a deterministic QuarantinedRecord."""
    uid = upstream_id or raw_payload.get("record_id") or raw_payload.get("relation_id") or "unknown"
    quar_id = generate_quarantine_id(str(uid), reason.value)
    return QuarantinedRecord(
        quarantine_id=quar_id,
        record_type=record_type,
        quarantine_reason=reason,
        error_message=error_message,
        source_version=source_version,
        upstream_id=str(uid) if uid else None,
        raw_payload=raw_payload,
    )


def validate_evidence_span(evidence_raw: Any) -> Tuple[bool, Optional[EvidenceSpan], Optional[str]]:
    """Validate character-level evidence span bounds and text."""
    if not isinstance(evidence_raw, dict):
        return False, None, "Evidence must be a dictionary"
    
    text = evidence_raw.get("text")
    if not text or not isinstance(text, str) or not text.strip():
        return False, None, "Evidence text is missing or empty"
        
    start_char = evidence_raw.get("start_char")
    end_char = evidence_raw.get("end_char")
    
    if start_char is None or not isinstance(start_char, int) or start_char < 0:
        return False, None, f"Invalid start_char: {start_char}"
        
    if end_char is None or not isinstance(end_char, int) or end_char < start_char:
        return False, None, f"Invalid end_char: {end_char} (start_char={start_char})"
        
    try:
        span = EvidenceSpan(
            text=text,
            start_char=start_char,
            end_char=end_char,
            is_exact_match=evidence_raw.get("is_exact_match", True),
            confidence=float(evidence_raw.get("confidence", 1.0)),
        )
        return True, span, None
    except Exception as e:
        return False, None, f"EvidenceSpan initialization failed: {e}"


def validate_provenance(prov_raw: Any) -> Tuple[bool, Optional[ExtractionProvenance], Optional[str]]:
    """Validate completeness of extraction provenance."""
    if not isinstance(prov_raw, dict):
        return False, None, "Provenance must be a dictionary"
        
    canonical_id = prov_raw.get("canonical_id")
    chunk_id = prov_raw.get("chunk_id")
    document_id = prov_raw.get("document_id")
    
    if not canonical_id or not isinstance(canonical_id, str):
        return False, None, "Missing or invalid canonical_id in provenance"
    if not chunk_id or not isinstance(chunk_id, str):
        return False, None, "Missing or invalid chunk_id in provenance"
    if not document_id or not isinstance(document_id, str):
        return False, None, "Missing or invalid document_id in provenance"
        
    try:
        prov = ExtractionProvenance(
            canonical_id=canonical_id,
            document_id=document_id,
            chunk_id=chunk_id,
            section_id=prov_raw.get("section_id"),
            section_title=prov_raw.get("section_title"),
            section_level=prov_raw.get("section_level", 1),
            page_start=prov_raw.get("page_start", 1),
            page_end=prov_raw.get("page_end", 1),
            file_hash=prov_raw.get("file_hash"),
        )
        return True, prov, None
    except Exception as e:
        return False, None, f"ExtractionProvenance initialization failed: {e}"


def validate_entity_mention_record(
    raw: Dict[str, Any],
    source_version: str = "v0.4.1",
) -> Tuple[Optional[EntityMention], Optional[QuarantinedRecord]]:
    """Validate a raw entity extraction record and construct an EntityMention, or quarantine if invalid."""
    upstream_id = raw.get("record_id")
    if not upstream_id:
        return None, create_quarantine_record(
            "ENTITY",
            QuarantineReason.SCHEMA_VALIDATION_ERROR,
            "Missing record_id field",
            raw,
            source_version,
        )

    category_str = raw.get("category")
    if not category_str or category_str not in VALID_ENTITY_TYPES:
        return None, create_quarantine_record(
            "ENTITY",
            QuarantineReason.SCHEMA_VALIDATION_ERROR,
            f"Invalid or missing entity category: {category_str}",
            raw,
            source_version,
            upstream_id,
        )

    surface_text = raw.get("surface_text")
    if not surface_text or not isinstance(surface_text, str) or not surface_text.strip():
        return None, create_quarantine_record(
            "ENTITY",
            QuarantineReason.SCHEMA_VALIDATION_ERROR,
            "Missing or empty surface_text",
            raw,
            source_version,
            upstream_id,
        )

    # Validate evidence
    ev_ok, ev_span, ev_err = validate_evidence_span(raw.get("evidence"))
    if not ev_ok or ev_span is None:
        reason = QuarantineReason.INVALID_SPAN_BOUNDS if "char" in str(ev_err) else QuarantineReason.UNGROUNDED_EVIDENCE
        return None, create_quarantine_record(
            "ENTITY",
            reason,
            f"Evidence validation failed: {ev_err}",
            raw,
            source_version,
            upstream_id,
        )

    # Validate provenance
    prov_ok, prov, prov_err = validate_provenance(raw.get("provenance"))
    if not prov_ok or prov is None:
        return None, create_quarantine_record(
            "ENTITY",
            QuarantineReason.MISSING_PROVENANCE_FIELD,
            f"Provenance validation failed: {prov_err}",
            raw,
            source_version,
            upstream_id,
        )

    category = ScientificEntityType(category_str)
    canonical_name, _, _ = resolve_canonical_entity(surface_text, category)
    norm_name = normalize_text(surface_text)

    # Temporary placeholder for entity_id; will be linked to CanonicalEntityNode in stage 5
    mention_id = generate_mention_id(prov.chunk_id, category, ev_span.start_char, ev_span.end_char)

    attribution = raw.get("attribution", AttributionType.AUTHOR_STATED)
    if isinstance(attribution, str):
        try:
            attribution = AttributionType(attribution)
        except ValueError:
            attribution = AttributionType.AUTHOR_STATED

    val_status = raw.get("validation_status", ValidationStatus.VALIDATED)
    if isinstance(val_status, str):
        try:
            val_status = ValidationStatus(val_status)
        except ValueError:
            val_status = ValidationStatus.VALIDATED

    mention = EntityMention(
        mention_id=mention_id,
        entity_id="",  # Linked during entity consolidation
        paper_id=prov.canonical_id,
        chunk_id=prov.chunk_id,
        category=category,
        surface_text=surface_text,
        normalized_name=norm_name,
        evidence=ev_span,
        provenance=prov,
        attribution=attribution,
        confidence_score=float(raw.get("confidence_score", 1.0)),
        extraction_version=str(raw.get("extraction_version", source_version)),
        validation_status=val_status,
        upstream_record_id=upstream_id,
    )
    return mention, None


def validate_statement_record(
    raw: Dict[str, Any],
    source_version: str = "v0.4.1",
) -> Tuple[Optional[CanonicalStatementNode], Optional[QuarantinedRecord]]:
    """Validate a raw statement extraction record and construct a CanonicalStatementNode, or quarantine if invalid."""
    upstream_id = raw.get("record_id")
    if not upstream_id:
        return None, create_quarantine_record(
            "STATEMENT",
            QuarantineReason.SCHEMA_VALIDATION_ERROR,
            "Missing record_id field",
            raw,
            source_version,
        )

    category_str = raw.get("category")
    if not category_str or category_str not in VALID_STATEMENT_TYPES:
        return None, create_quarantine_record(
            "STATEMENT",
            QuarantineReason.SCHEMA_VALIDATION_ERROR,
            f"Invalid or missing statement category: {category_str}",
            raw,
            source_version,
            upstream_id,
        )

    surface_text = raw.get("surface_text")
    if not surface_text or not isinstance(surface_text, str) or not surface_text.strip():
        return None, create_quarantine_record(
            "STATEMENT",
            QuarantineReason.SCHEMA_VALIDATION_ERROR,
            "Missing or empty surface_text",
            raw,
            source_version,
            upstream_id,
        )

    # Validate evidence
    ev_ok, ev_span, ev_err = validate_evidence_span(raw.get("evidence"))
    if not ev_ok or ev_span is None:
        reason = QuarantineReason.INVALID_SPAN_BOUNDS if "char" in str(ev_err) else QuarantineReason.UNGROUNDED_EVIDENCE
        return None, create_quarantine_record(
            "STATEMENT",
            reason,
            f"Evidence validation failed: {ev_err}",
            raw,
            source_version,
            upstream_id,
        )

    # Validate provenance
    prov_ok, prov, prov_err = validate_provenance(raw.get("provenance"))
    if not prov_ok or prov is None:
        return None, create_quarantine_record(
            "STATEMENT",
            QuarantineReason.MISSING_PROVENANCE_FIELD,
            f"Provenance validation failed: {prov_err}",
            raw,
            source_version,
            upstream_id,
        )

    category = ScientificStatementType(category_str)
    norm_statement = normalize_text(surface_text)
    stmt_id = generate_canonical_statement_id(prov.canonical_id, prov.chunk_id, category.value, norm_statement)

    attribution = raw.get("attribution", AttributionType.AUTHOR_STATED)
    if isinstance(attribution, str):
        try:
            attribution = AttributionType(attribution)
        except ValueError:
            attribution = AttributionType.AUTHOR_STATED

    val_status = raw.get("validation_status", ValidationStatus.VALIDATED)
    if isinstance(val_status, str):
        try:
            val_status = ValidationStatus(val_status)
        except ValueError:
            val_status = ValidationStatus.VALIDATED

    stmt = CanonicalStatementNode(
        statement_id=stmt_id,
        category=category,
        surface_text=surface_text,
        normalized_statement=norm_statement,
        paper_id=prov.canonical_id,
        chunk_id=prov.chunk_id,
        evidence=ev_span,
        provenance=prov,
        attribution=attribution,
        confidence_score=float(raw.get("confidence_score", 1.0)),
        extraction_version=str(raw.get("extraction_version", source_version)),
        validation_status=val_status,
        validation_notes=list(raw.get("validation_notes", [])),
        related_entity_ids=[],
        upstream_record_id=upstream_id,
    )
    return stmt, None


def validate_relationship_record(
    raw: Dict[str, Any],
    valid_entity_ids: Set[str],
    valid_statement_ids: Set[str],
    upstream_to_kb: Dict[str, str],
    source_version: str = "v0.4.0",
) -> Tuple[Optional[CanonicalRelationshipNode], Optional[QuarantinedRecord]]:
    """Validate a raw relationship record and resolve its endpoints to canonical node IDs.
    
    If either endpoint cannot be resolved, quarantines the record with DANGLING_RELATION_ENDPOINT.
    """
    upstream_id = raw.get("relation_id") or raw.get("record_id")
    if not upstream_id:
        return None, create_quarantine_record(
            "RELATIONSHIP",
            QuarantineReason.SCHEMA_VALIDATION_ERROR,
            "Missing relation_id field",
            raw,
            source_version,
        )

    relation_type_str = raw.get("relation_type")
    if not relation_type_str or relation_type_str not in VALID_RELATION_TYPES:
        return None, create_quarantine_record(
            "RELATIONSHIP",
            QuarantineReason.SCHEMA_VALIDATION_ERROR,
            f"Invalid or missing relation_type: {relation_type_str}",
            raw,
            source_version,
            upstream_id,
        )

    raw_source = raw.get("source_id")
    raw_target = raw.get("target_id")

    if not raw_source or not raw_target:
        return None, create_quarantine_record(
            "RELATIONSHIP",
            QuarantineReason.SCHEMA_VALIDATION_ERROR,
            f"Missing source_id ({raw_source}) or target_id ({raw_target})",
            raw,
            source_version,
            upstream_id,
        )

    # Resolve source endpoint
    source_kb_id: Optional[str] = None
    source_type = "ENTITY"
    if raw_source in valid_entity_ids:
        source_kb_id = raw_source
    elif raw_source in valid_statement_ids:
        source_kb_id = raw_source
        source_type = "STATEMENT"
    elif raw_source in upstream_to_kb:
        source_kb_id = upstream_to_kb[raw_source]
        source_type = "STATEMENT" if source_kb_id in valid_statement_ids else "ENTITY"

    # Resolve target endpoint
    target_kb_id: Optional[str] = None
    target_type = "ENTITY"
    if raw_target in valid_entity_ids:
        target_kb_id = raw_target
    elif raw_target in valid_statement_ids:
        target_kb_id = raw_target
        target_type = "STATEMENT"
    elif raw_target in upstream_to_kb:
        target_kb_id = upstream_to_kb[raw_target]
        target_type = "STATEMENT" if target_kb_id in valid_statement_ids else "ENTITY"

    # Check for dangling endpoints
    if not source_kb_id or not target_kb_id:
        missing = []
        if not source_kb_id:
            missing.append(f"source: {raw_source}")
        if not target_kb_id:
            missing.append(f"target: {raw_target}")
        return None, create_quarantine_record(
            "RELATIONSHIP",
            QuarantineReason.DANGLING_RELATION_ENDPOINT,
            f"Referential integrity failure: unresolvable endpoint(s) [{', '.join(missing)}]",
            raw,
            source_version,
            upstream_id,
        )

    # Validate evidence
    ev_ok, ev_span, ev_err = validate_evidence_span(raw.get("evidence"))
    if not ev_ok or ev_span is None:
        reason = QuarantineReason.INVALID_SPAN_BOUNDS if "char" in str(ev_err) else QuarantineReason.UNGROUNDED_EVIDENCE
        return None, create_quarantine_record(
            "RELATIONSHIP",
            reason,
            f"Evidence validation failed: {ev_err}",
            raw,
            source_version,
            upstream_id,
        )

    # Validate provenance
    prov_ok, prov, prov_err = validate_provenance(raw.get("provenance"))
    if not prov_ok or prov is None:
        return None, create_quarantine_record(
            "RELATIONSHIP",
            QuarantineReason.MISSING_PROVENANCE_FIELD,
            f"Provenance validation failed: {prov_err}",
            raw,
            source_version,
            upstream_id,
        )

    rel_type = ScientificRelationType(relation_type_str)
    rel_id = generate_canonical_relationship_id(source_kb_id, rel_type.value, target_kb_id, prov.chunk_id)

    attribution = raw.get("attribution", AttributionType.AUTHOR_STATED)
    if isinstance(attribution, str):
        try:
            attribution = AttributionType(attribution)
        except ValueError:
            attribution = AttributionType.AUTHOR_STATED

    val_status = raw.get("validation_status", ValidationStatus.VALIDATED)
    if isinstance(val_status, str):
        try:
            val_status = ValidationStatus(val_status)
        except ValueError:
            val_status = ValidationStatus.VALIDATED

    rel_node = CanonicalRelationshipNode(
        relationship_id=rel_id,
        relation_type=rel_type,
        source_id=source_kb_id,
        target_id=target_kb_id,
        source_type=source_type,
        target_type=target_type,
        paper_id=prov.canonical_id,
        chunk_id=prov.chunk_id,
        surface_text=raw.get("surface_text"),
        evidence=ev_span,
        provenance=prov,
        attribution=attribution,
        is_directed=bool(raw.get("is_directed", True)),
        confidence_score=float(raw.get("confidence_score", 1.0)),
        extraction_version=str(raw.get("extraction_version", source_version)),
        validation_status=val_status,
        upstream_relation_id=upstream_id,
    )
    return rel_node, None
