"""Unit Tests for Knowledge Base Validation and Quarantine Routing.

Tests schema checks, span bounds, complete provenance verification, and
referential integrity routing to QuarantinedRecord.
Schema Version: 0.5.0
"""

import pytest
from dataset.schemas.scientific_knowledge import ScientificEntityType
from dataset.schemas.scientific_knowledge_base import QuarantineReason
from pipelines.knowledge_base.validator import (
    validate_entity_mention_record,
    validate_evidence_span,
    validate_provenance,
    validate_relationship_record,
    validate_statement_record,
)


def test_validate_evidence_span() -> None:
    # Valid
    ok, span, err = validate_evidence_span(
        {"text": "deep learning", "start_char": 10, "end_char": 23, "is_exact_match": True}
    )
    assert ok is True
    assert span is not None
    assert span.text == "deep learning"

    # Missing text
    ok, span, err = validate_evidence_span({"text": "", "start_char": 0, "end_char": 10})
    assert ok is False
    assert "empty" in str(err)

    # Negative start_char
    ok, span, err = validate_evidence_span({"text": "test", "start_char": -1, "end_char": 5})
    assert ok is False

    # Inverted span (end < start)
    ok, span, err = validate_evidence_span({"text": "test", "start_char": 10, "end_char": 5})
    assert ok is False


def test_validate_provenance() -> None:
    # Valid
    ok, prov, err = validate_provenance(
        {"canonical_id": "rg_doi_1", "document_id": "doc_1", "chunk_id": "chk_1"}
    )
    assert ok is True
    assert prov is not None
    assert prov.canonical_id == "rg_doi_1"

    # Missing canonical_id
    ok, prov, err = validate_provenance({"document_id": "doc_1", "chunk_id": "chk_1"})
    assert ok is False
    assert "canonical_id" in str(err)


def test_validate_entity_mention_quarantine() -> None:
    # Missing surface_text
    raw_bad = {
        "record_id": "ent_bad_01",
        "category": "METHOD",
        "surface_text": "",
        "evidence": {"text": "something", "start_char": 0, "end_char": 9},
        "provenance": {"canonical_id": "rg_1", "document_id": "doc_1", "chunk_id": "chk_1"},
    }
    mention, quar = validate_entity_mention_record(raw_bad)
    assert mention is None
    assert quar is not None
    assert quar.quarantine_reason == QuarantineReason.SCHEMA_VALIDATION_ERROR

    # Inverted span bounds
    raw_span_bad = {
        "record_id": "ent_bad_02",
        "category": "METHOD",
        "surface_text": "Transformer",
        "evidence": {"text": "Transformer", "start_char": 20, "end_char": 10},
        "provenance": {"canonical_id": "rg_1", "document_id": "doc_1", "chunk_id": "chk_1"},
    }
    mention, quar = validate_entity_mention_record(raw_span_bad)
    assert mention is None
    assert quar is not None
    assert quar.quarantine_reason == QuarantineReason.INVALID_SPAN_BOUNDS


def test_validate_relationship_dangling_endpoint() -> None:
    # Source ID does not exist in valid entities or statements
    raw_rel = {
        "relation_id": "rel_bad_01",
        "relation_type": "ADDRESSES",
        "source_id": "ent_nonexistent_01",
        "target_id": "ent_valid_02",
        "evidence": {"text": "CNNs address noise", "start_char": 0, "end_char": 18},
        "provenance": {"canonical_id": "rg_1", "document_id": "doc_1", "chunk_id": "chk_1"},
    }
    valid_entities = {"ent_valid_02"}
    valid_statements = set()
    upstream_to_kb = {}

    rel_node, quar = validate_relationship_record(
        raw_rel,
        valid_entity_ids=valid_entities,
        valid_statement_ids=valid_statements,
        upstream_to_kb=upstream_to_kb,
    )
    assert rel_node is None
    assert quar is not None
    assert quar.quarantine_reason == QuarantineReason.DANGLING_RELATION_ENDPOINT
    assert "unresolvable endpoint" in quar.error_message
