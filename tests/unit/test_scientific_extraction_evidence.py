"""Unit Tests for Evidence Grounding and Provenance Validation Engine."""

from __future__ import annotations

import pytest

from dataset.schemas.document_processing import ChunkStrategy, ProcessedChunk
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
from pipelines.extraction.validator import EvidenceGroundingValidator


@pytest.fixture
def sample_chunk() -> ProcessedChunk:
    text = (
        "This paper examines how deep learning models improve intrusion detection "
        "in modern cyber networks. The proposed convolutional neural network achieved "
        "an accuracy of 98.4% on the NSL-KDD benchmark."
    )
    return ProcessedChunk(
        chunk_id="chk_test_001",
        canonical_id="rg_doi_test123",
        document_id="doc_test123",
        file_hash="abc123hash",
        section_id="sec_01",
        section_title="1. Introduction",
        section_level=1,
        page_start=1,
        page_end=1,
        paragraph_start_order=1,
        paragraph_end_order=1,
        paragraph_ids=["p_001"],
        text=text,
        char_count=len(text),
        word_count=len(text.split()),
        token_count_est=len(text.split()),
        strategy=ChunkStrategy.STRATEGY_A_PARAGRAPH,
    )


def test_validator_exact_match(sample_chunk):
    validator = EvidenceGroundingValidator()
    # "deep learning" is at start_char=25, end_char=38
    target = "deep learning"
    start = sample_chunk.text.find(target)
    end = start + len(target)

    record = ScientificEntityRecord(
        record_id="ent_01",
        category=ScientificEntityType.METHOD,
        surface_text=target,
        normalized_name=target,
        evidence=EvidenceSpan(text=target, start_char=start, end_char=end),
        provenance=ExtractionProvenance(
            canonical_id=sample_chunk.canonical_id,
            chunk_id=sample_chunk.chunk_id,
        ),
    )

    validated = validator.validate_entity(record, sample_chunk)
    assert validated.validation_status == ValidationStatus.VALIDATED
    assert validated.evidence.is_exact_match is True


def test_validator_realigns_misaligned_offsets(sample_chunk):
    validator = EvidenceGroundingValidator()
    target = "intrusion detection"
    # Provide intentionally incorrect offsets
    record = ScientificEntityRecord(
        record_id="ent_02",
        category=ScientificEntityType.PROBLEM,
        surface_text=target,
        normalized_name=target,
        evidence=EvidenceSpan(text=target, start_char=0, end_char=len(target)),
        provenance=ExtractionProvenance(
            canonical_id=sample_chunk.canonical_id,
            chunk_id=sample_chunk.chunk_id,
        ),
    )

    validated = validator.validate_entity(record, sample_chunk)
    assert validated.validation_status == ValidationStatus.VALIDATED
    assert sample_chunk.text[validated.evidence.start_char : validated.evidence.end_char] == target
    assert "OFFSETS_REALIGNED_TO_EXACT_SUBSTRING" in validated.validation_notes


def test_validator_rejects_hallucinated_evidence(sample_chunk):
    validator = EvidenceGroundingValidator()
    # Text that does not exist in the source chunk
    hallucination = "quantum entanglement teleportation algorithm"
    record = ScientificEntityRecord(
        record_id="ent_03",
        category=ScientificEntityType.METHOD,
        surface_text=hallucination,
        normalized_name=hallucination,
        evidence=EvidenceSpan(text=hallucination, start_char=0, end_char=len(hallucination)),
        provenance=ExtractionProvenance(
            canonical_id=sample_chunk.canonical_id,
            chunk_id=sample_chunk.chunk_id,
        ),
    )

    validated = validator.validate_entity(record, sample_chunk)
    assert validated.validation_status == ValidationStatus.REJECTED
    assert "EVIDENCE_TEXT_ABSENT_FROM_SOURCE_CHUNK" in validated.validation_notes


def test_validator_rejects_missing_chunk():
    validator = EvidenceGroundingValidator()
    record = ScientificEntityRecord(
        record_id="ent_04",
        category=ScientificEntityType.METHOD,
        surface_text="LSTM",
        normalized_name="LSTM",
        evidence=EvidenceSpan(text="LSTM", start_char=0, end_char=4),
        provenance=ExtractionProvenance(
            canonical_id="rg_doi_missing",
            chunk_id="chk_missing_001",
        ),
    )

    validated = validator.validate_entity(record, chunk=None)
    assert validated.validation_status == ValidationStatus.REJECTED
    assert "CHUNK_NOT_FOUND_IN_CORPUS" in validated.validation_notes


def test_validator_rejects_canonical_id_mismatch(sample_chunk):
    validator = EvidenceGroundingValidator()
    target = "NSL-KDD"
    start = sample_chunk.text.find(target)
    end = start + len(target)

    record = ScientificEntityRecord(
        record_id="ent_05",
        category=ScientificEntityType.DATASET,
        surface_text=target,
        normalized_name=target,
        evidence=EvidenceSpan(text=target, start_char=start, end_char=end),
        provenance=ExtractionProvenance(
            canonical_id="rg_doi_DIFFERENT_PAPER",
            chunk_id=sample_chunk.chunk_id,
        ),
    )

    validated = validator.validate_entity(record, sample_chunk)
    assert validated.validation_status == ValidationStatus.REJECTED
    assert any("CANONICAL_ID_MISMATCH" in note for note in validated.validation_notes)


def test_validator_flags_hedged_claim_in_result_category(sample_chunk):
    validator = EvidenceGroundingValidator()
    hedged_text = "These findings suggest that the approach may potentially improve throughput."
    # Artificial chunk with hedged text
    hedged_chunk = ProcessedChunk(
        chunk_id="chk_test_hedge",
        canonical_id="rg_doi_hedge",
        section_id="sec_01",
        section_title="Discussion",
        page_start=1,
        page_end=1,
        paragraph_start_order=1,
        paragraph_end_order=1,
        text=hedged_text,
        strategy=ChunkStrategy.STRATEGY_A_PARAGRAPH,
    )

    record = ScientificStatementRecord(
        record_id="stmt_hedge",
        category=ScientificStatementType.RESULT,  # Stated as empirical RESULT but text is hedged
        surface_text=hedged_text,
        normalized_statement=hedged_text,
        evidence=EvidenceSpan(text=hedged_text, start_char=0, end_char=len(hedged_text)),
        provenance=ExtractionProvenance(
            canonical_id=hedged_chunk.canonical_id,
            chunk_id=hedged_chunk.chunk_id,
        ),
    )

    validated = validator.validate_statement(record, hedged_chunk)
    assert validated.validation_status == ValidationStatus.NEEDS_REVIEW
    assert "HEDGED_LANGUAGE_DETECTED_IN_RESULT_CATEGORY" in validated.validation_notes


def test_validator_relation_endpoint_check(sample_chunk):
    validator = EvidenceGroundingValidator()
    rel = ScientificRelationRecord(
        relation_id="rel_01",
        relation_type=ScientificRelationType.ADDRESSES,
        source_id="ent_valid_source",
        target_id="ent_NONEXISTENT_TARGET",
        source_category="METHOD",
        target_category="PROBLEM",
        evidence=EvidenceSpan(text=sample_chunk.text[:30], start_char=0, end_char=30),
        provenance=ExtractionProvenance(
            canonical_id=sample_chunk.canonical_id,
            chunk_id=sample_chunk.chunk_id,
        ),
    )

    known_ids = {"ent_valid_source"}
    validated = validator.validate_relation(rel, sample_chunk, known_ids)
    assert validated.validation_status == ValidationStatus.REJECTED
    assert any("TARGET_RECORD_ID_NOT_FOUND" in note for note in validated.validation_notes)
