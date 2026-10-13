"""Evidence Grounding and Provenance Validation Engine.

Strictly enforces traceability of every extracted scientific entity, statement,
and relationship back to original chunk character spans and cryptographic provenance.
Rejects ungrounded or hallucinated records and flags ambiguous cases for manual review.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from dataset.schemas.document_processing import ProcessedChunk
from dataset.schemas.scientific_knowledge import (
    AttributionType,
    EvidenceSpan,
    ScientificEntityRecord,
    ScientificRelationRecord,
    ScientificStatementRecord,
    ValidationStatus,
)

logger = logging.getLogger(__name__)


class EvidenceGroundingValidator:
    """Strict validator for scientific information evidence grounding."""

    def __init__(
        self,
        min_evidence_chars: int = 3,
        strict_offset_matching: bool = True,
    ):
        self.min_evidence_chars = min_evidence_chars
        self.strict_offset_matching = strict_offset_matching

    def validate_entity(
        self,
        record: ScientificEntityRecord,
        chunk: Optional[ProcessedChunk],
    ) -> ScientificEntityRecord:
        """Validate evidence grounding and provenance for a scientific entity record."""
        notes: List[str] = list(record.validation_notes)

        # 1. Chunk existence & provenance validation
        if chunk is None:
            record.validation_status = ValidationStatus.REJECTED
            notes.append("CHUNK_NOT_FOUND_IN_CORPUS")
            record.validation_notes = notes
            return record

        if record.provenance.canonical_id != chunk.canonical_id:
            record.validation_status = ValidationStatus.REJECTED
            notes.append(f"CANONICAL_ID_MISMATCH: {record.provenance.canonical_id} != {chunk.canonical_id}")
            record.validation_notes = notes
            return record

        # 2. Evidence presence and length check
        evidence_text = record.evidence.text.strip()
        if not evidence_text or len(evidence_text) < self.min_evidence_chars:
            record.validation_status = ValidationStatus.REJECTED
            notes.append("EVIDENCE_TOO_SHORT_OR_EMPTY")
            record.validation_notes = notes
            return record

        # 3. Exact character offset grounding verification
        chunk_text = chunk.text
        start_char = record.evidence.start_char
        end_char = record.evidence.end_char

        # Check bounds
        if start_char < 0 or end_char > len(chunk_text) or start_char >= end_char:
            # Attempt to realign offsets if evidence text is in chunk
            realigned = self._realign_offsets(chunk_text, evidence_text)
            if realigned:
                record.evidence.start_char, record.evidence.end_char = realigned
                record.evidence.is_exact_match = True
                notes.append("OFFSETS_REALIGNED_FROM_OUT_OF_BOUNDS")
            else:
                record.validation_status = ValidationStatus.REJECTED
                notes.append("OFFSETS_OUT_OF_BOUNDS_AND_TEXT_NOT_FOUND")
                record.validation_notes = notes
                return record

        # Verify current offset slice matches evidence text
        current_slice = chunk_text[record.evidence.start_char : record.evidence.end_char]
        if current_slice != evidence_text:
            # Check case-insensitive or trimmed match
            if current_slice.strip().lower() == evidence_text.lower():
                notes.append("CASE_OR_WHITESPACE_OFFSET_ALIGNMENT_DIFFERENCE")
            else:
                # Substring search recovery
                realigned = self._realign_offsets(chunk_text, evidence_text)
                if realigned:
                    record.evidence.start_char, record.evidence.end_char = realigned
                    record.evidence.is_exact_match = True
                    notes.append("OFFSETS_REALIGNED_TO_EXACT_SUBSTRING")
                else:
                    record.validation_status = ValidationStatus.REJECTED
                    notes.append("EVIDENCE_TEXT_ABSENT_FROM_SOURCE_CHUNK")
                    record.validation_notes = notes
                    return record

        # 4. Surface text containment check
        surface = record.surface_text.strip()
        if surface and surface.lower() not in evidence_text.lower() and surface.lower() not in chunk_text.lower():
            record.validation_status = ValidationStatus.NEEDS_REVIEW
            notes.append("SURFACE_TEXT_NOT_CONTAINED_IN_EVIDENCE_OR_CHUNK")

        # 5. Confidence score thresholding
        if record.confidence_score < 0.5:
            record.validation_status = ValidationStatus.NEEDS_REVIEW
            notes.append("LOW_CONFIDENCE_SCORE")

        if record.validation_status != ValidationStatus.REJECTED and record.validation_status != ValidationStatus.NEEDS_REVIEW:
            record.validation_status = ValidationStatus.VALIDATED

        record.validation_notes = notes
        return record

    def validate_statement(
        self,
        record: ScientificStatementRecord,
        chunk: Optional[ProcessedChunk],
    ) -> ScientificStatementRecord:
        """Validate evidence grounding and epistemological attribution for a statement."""
        notes: List[str] = list(record.validation_notes)

        # 1. Chunk existence & provenance validation
        if chunk is None:
            record.validation_status = ValidationStatus.REJECTED
            notes.append("CHUNK_NOT_FOUND_IN_CORPUS")
            record.validation_notes = notes
            return record

        if record.provenance.canonical_id != chunk.canonical_id:
            record.validation_status = ValidationStatus.REJECTED
            notes.append(f"CANONICAL_ID_MISMATCH: {record.provenance.canonical_id} != {chunk.canonical_id}")
            record.validation_notes = notes
            return record

        # 2. Evidence presence and length check
        evidence_text = record.evidence.text.strip()
        if not evidence_text or len(evidence_text) < self.min_evidence_chars:
            record.validation_status = ValidationStatus.REJECTED
            notes.append("EVIDENCE_TOO_SHORT_OR_EMPTY")
            record.validation_notes = notes
            return record

        # 3. Exact character offset grounding verification
        chunk_text = chunk.text
        start_char = record.evidence.start_char
        end_char = record.evidence.end_char

        if start_char < 0 or end_char > len(chunk_text) or start_char >= end_char:
            realigned = self._realign_offsets(chunk_text, evidence_text)
            if realigned:
                record.evidence.start_char, record.evidence.end_char = realigned
                record.evidence.is_exact_match = True
                notes.append("OFFSETS_REALIGNED_FROM_OUT_OF_BOUNDS")
            else:
                record.validation_status = ValidationStatus.REJECTED
                notes.append("OFFSETS_OUT_OF_BOUNDS_AND_TEXT_NOT_FOUND")
                record.validation_notes = notes
                return record

        current_slice = chunk_text[record.evidence.start_char : record.evidence.end_char]
        if current_slice != evidence_text:
            realigned = self._realign_offsets(chunk_text, evidence_text)
            if realigned:
                record.evidence.start_char, record.evidence.end_char = realigned
                record.evidence.is_exact_match = True
                notes.append("OFFSETS_REALIGNED_TO_EXACT_SUBSTRING")
            else:
                record.validation_status = ValidationStatus.REJECTED
                notes.append("EVIDENCE_TEXT_ABSENT_FROM_SOURCE_CHUNK")
                record.validation_notes = notes
                return record

        # 4. Epistemological claim vs fact check
        # Check for epistemic hedges in text:
        hedges = ["may", "could", "might", "potentially", "hypothesize", "preliminary", "suggests"]
        has_hedge = any(f" {h} " in f" {evidence_text.lower()} " for h in hedges)
        if has_hedge and record.category.value == "RESULT":
            record.validation_status = ValidationStatus.NEEDS_REVIEW
            notes.append("HEDGED_LANGUAGE_DETECTED_IN_RESULT_CATEGORY")

        if record.confidence_score < 0.5:
            record.validation_status = ValidationStatus.NEEDS_REVIEW
            notes.append("LOW_CONFIDENCE_SCORE")

        if record.validation_status != ValidationStatus.REJECTED and record.validation_status != ValidationStatus.NEEDS_REVIEW:
            record.validation_status = ValidationStatus.VALIDATED

        record.validation_notes = notes
        return record

    def validate_relation(
        self,
        record: ScientificRelationRecord,
        chunk: Optional[ProcessedChunk],
        known_record_ids: set[str],
    ) -> ScientificRelationRecord:
        """Validate directional link integrity and evidence grounding."""
        notes: List[str] = list(record.validation_notes)

        # 1. Endpoint integrity
        if record.source_id not in known_record_ids:
            record.validation_status = ValidationStatus.REJECTED
            notes.append(f"SOURCE_RECORD_ID_NOT_FOUND: {record.source_id}")
            record.validation_notes = notes
            return record

        if record.target_id not in known_record_ids:
            record.validation_status = ValidationStatus.REJECTED
            notes.append(f"TARGET_RECORD_ID_NOT_FOUND: {record.target_id}")
            record.validation_notes = notes
            return record

        # 2. Chunk provenance
        if chunk is None:
            record.validation_status = ValidationStatus.REJECTED
            notes.append("CHUNK_NOT_FOUND_IN_CORPUS")
            record.validation_notes = notes
            return record

        # 3. Evidence grounding in chunk text
        evidence_text = record.evidence.text.strip()
        if not evidence_text or len(evidence_text) < self.min_evidence_chars:
            record.validation_status = ValidationStatus.REJECTED
            notes.append("EVIDENCE_TOO_SHORT_OR_EMPTY")
            record.validation_notes = notes
            return record

        chunk_text = chunk.text
        if evidence_text not in chunk_text:
            realigned = self._realign_offsets(chunk_text, evidence_text)
            if not realigned:
                record.validation_status = ValidationStatus.REJECTED
                notes.append("RELATION_EVIDENCE_ABSENT_FROM_CHUNK")
                record.validation_notes = notes
                return record
            record.evidence.start_char, record.evidence.end_char = realigned
        else:
            realigned = self._realign_offsets(chunk_text, evidence_text)
            if realigned:
                record.evidence.start_char, record.evidence.end_char = realigned

        # 4. Inferred vs stated attribution check
        if record.attribution == AttributionType.SYSTEM_INFERRED:
            notes.append("SYSTEM_INFERRED_RELATION_FLAGGED_FOR_AUDIT")

        if record.validation_status != ValidationStatus.REJECTED and record.validation_status != ValidationStatus.NEEDS_REVIEW:
            record.validation_status = ValidationStatus.VALIDATED

        record.validation_notes = notes
        return record

    @staticmethod
    def _realign_offsets(chunk_text: str, target: str) -> Optional[Tuple[int, int]]:
        """Find substring offsets in chunk text if misaligned."""
        idx = chunk_text.find(target)
        if idx != -1:
            return idx, idx + len(target)

        # Case-insensitive search fallback
        idx = chunk_text.lower().find(target.lower())
        if idx != -1:
            return idx, idx + len(target)

        return None
