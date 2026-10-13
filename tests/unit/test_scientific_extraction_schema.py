"""Unit Tests for Phase 3 Scientific Extraction Schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from dataset.schemas.scientific_knowledge import (
    AttributionType,
    EvidenceSpan,
    ExtractionProvenance,
    ScientificEntityRecord,
    ScientificEntityType,
    ScientificRelationRecord,
    ScientificRelationType,
    ScientificStatementRecord,
    ScientificStatementType,
    ValidationStatus,
)


def test_valid_evidence_span():
    span = EvidenceSpan(
        text="convolutional neural network",
        start_char=10,
        end_char=38,
        is_exact_match=True,
        confidence=0.95,
    )
    assert span.text == "convolutional neural network"
    assert span.start_char == 10
    assert span.end_char == 38
    assert span.confidence == 0.95


def test_invalid_evidence_span_bounds():
    # end_char <= start_char must raise ValidationError
    with pytest.raises(ValidationError):
        EvidenceSpan(text="test", start_char=10, end_char=10)

    with pytest.raises(ValidationError):
        EvidenceSpan(text="test", start_char=15, end_char=10)


def test_invalid_evidence_confidence_bounds():
    with pytest.raises(ValidationError):
        EvidenceSpan(text="test", start_char=0, end_char=4, confidence=1.5)

    with pytest.raises(ValidationError):
        EvidenceSpan(text="test", start_char=0, end_char=4, confidence=-0.1)


def test_valid_entity_record():
    rec = ScientificEntityRecord(
        record_id="ent_001",
        schema_version="0.4.0",
        category=ScientificEntityType.METHOD,
        surface_text="LSTM",
        normalized_name="LSTM",
        evidence=EvidenceSpan(text="LSTM", start_char=5, end_char=9),
        provenance=ExtractionProvenance(
            canonical_id="rg_doi_123",
            chunk_id="chk_123_A_001",
        ),
        attribution=AttributionType.AUTHOR_STATED,
        confidence_score=0.95,
        extraction_method="rule_based",
        extraction_version="v0.4.0",
        validation_status=ValidationStatus.VALIDATED,
    )
    assert rec.category == ScientificEntityType.METHOD
    assert rec.attribution == AttributionType.AUTHOR_STATED
    assert rec.provenance.canonical_id == "rg_doi_123"


def test_invalid_entity_category():
    with pytest.raises(ValidationError):
        ScientificEntityRecord(
            record_id="ent_001",
            category="NOT_A_VALID_CATEGORY",  # type: ignore
            surface_text="LSTM",
            normalized_name="LSTM",
            evidence=EvidenceSpan(text="LSTM", start_char=5, end_char=9),
            provenance=ExtractionProvenance(
                canonical_id="rg_doi_123",
                chunk_id="chk_123_A_001",
            ),
        )


def test_valid_statement_record():
    rec = ScientificStatementRecord(
        record_id="stmt_001",
        schema_version="0.4.0",
        category=ScientificStatementType.CLAIM,
        surface_text="This paper proposes an intrusion detection framework.",
        normalized_statement="This paper proposes an intrusion detection framework.",
        evidence=EvidenceSpan(
            text="This paper proposes an intrusion detection framework.",
            start_char=0,
            end_char=54,
        ),
        provenance=ExtractionProvenance(
            canonical_id="rg_doi_123",
            chunk_id="chk_123_A_001",
        ),
    )
    assert rec.category == ScientificStatementType.CLAIM
    assert rec.validation_status == ValidationStatus.VALIDATED


def test_valid_relation_record():
    rel = ScientificRelationRecord(
        relation_id="rel_001",
        schema_version="0.4.0",
        relation_type=ScientificRelationType.ADDRESSES,
        source_id="ent_001",
        target_id="ent_002",
        source_category="METHOD",
        target_category="PROBLEM",
        surface_text="LSTM addresses anomaly detection",
        evidence=EvidenceSpan(
            text="LSTM addresses anomaly detection",
            start_char=0,
            end_char=32,
        ),
        provenance=ExtractionProvenance(
            canonical_id="rg_doi_123",
            chunk_id="chk_123_A_001",
        ),
        is_directed=True,
    )
    assert rel.relation_type == ScientificRelationType.ADDRESSES
    assert rel.is_directed is True
    assert rel.source_id == "ent_001"
    assert rel.target_id == "ent_002"


def test_schema_json_serialization():
    rec = ScientificEntityRecord(
        record_id="ent_001",
        category=ScientificEntityType.METRIC,
        surface_text="accuracy",
        normalized_name="accuracy",
        evidence=EvidenceSpan(text="accuracy", start_char=0, end_char=8),
        provenance=ExtractionProvenance(
            canonical_id="rg_doi_123",
            chunk_id="chk_123_A_001",
        ),
    )
    data = rec.model_dump()
    assert data["category"] == "METRIC"
    assert data["schema_version"] == "0.4.0"

    reconstructed = ScientificEntityRecord.model_validate(data)
    assert reconstructed.record_id == rec.record_id
    assert reconstructed.category == rec.category
