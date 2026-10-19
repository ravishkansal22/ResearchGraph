"""Relationship Integrity and Evidence Support Validator.

Evaluates scientific relationships across structural, evidence-support, and human-verification
dimensions. Detects and flags table-wide Cartesian product artifacts and unsupported associations.
Schema Version: 0.5.1
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Tuple

from dataset.schemas.scientific_knowledge_base import (
    EvidenceSupportStatus,
    HumanVerificationStatus,
    StructuralValidityStatus,
)

logger = logging.getLogger(__name__)

# Regex pattern for numbered table rows (e.g., "1 Adversarial ... 2 Prompt Injection ...")
RE_NUMBERED_TABLE_ROW = re.compile(r"(?:^|\s)(\d{1,2})\s+([A-Z][a-zA-Z0-9\s\-_/]+?)(?=(?:\s\d{1,2}\s+[A-Z])|$)")


def extract_table_row_associations(text: str) -> Dict[int, str]:
    """Parse numbered table rows from structured summary text into row-number -> row-content mapping."""
    rows: Dict[int, str] = {}
    matches = list(re.finditer(r"(?:^|\s)(\d{1,2})\s+", text))
    if len(matches) < 2:
        return rows

    for i in range(len(matches)):
        row_num = int(matches[i].group(1))
        start_idx = matches[i].end()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        row_content = text[start_idx:end_idx].strip()
        rows[row_num] = row_content
    return rows


def find_row_for_term(rows: Dict[int, str], term: str) -> Optional[int]:
    """Identify which numbered row contains the given surface or canonical term."""
    norm_term = term.lower().strip()
    for row_num, content in rows.items():
        if norm_term in content.lower():
            return row_num
    return None


def evaluate_relationship_evidence_support(
    source_name: str,
    target_name: str,
    relation_type: str,
    evidence_text: str,
    chunk_id: str = "",
    surface_text: Optional[str] = None,
) -> Tuple[EvidenceSupportStatus, Optional[str]]:
    """Assess whether the cited evidence text genuinely entails the subject-predicate-object relationship.
    
    Returns:
        (EvidenceSupportStatus, correction_notes)
    """
    if not evidence_text or not evidence_text.strip():
        return EvidenceSupportStatus.UNSUPPORTED, "Missing evidence text"

    # 1. Check for tabular summary structure with numbered items
    table_rows = extract_table_row_associations(evidence_text)
    if len(table_rows) >= 3:
        source_row = find_row_for_term(table_rows, source_name)
        target_row = find_row_for_term(table_rows, target_name)

        if source_row is not None and target_row is not None:
            if source_row != target_row:
                notes = (
                    f"Cartesian product table artifact: Subject '{source_name}' belongs to table item {source_row} "
                    f"whereas Object '{target_name}' belongs to table item {target_row} in chunk {chunk_id}. "
                    f"Cited evidence contains a multi-row summary table; cross-row pairing is unsupported by evidence."
                )
                return EvidenceSupportStatus.UNSUPPORTED, notes
            else:
                # Same row in table - check if relation semantics match table schema
                notes = f"Grounded within table item {source_row} in chunk {chunk_id}."
                return EvidenceSupportStatus.SUPPORTED, notes

    # 2. Check for sentence-level co-occurrence and explicit relation trigger
    norm_ev = evidence_text.lower()
    norm_src = source_name.lower()
    norm_tgt = target_name.lower()

    if norm_src not in norm_ev or norm_tgt not in norm_ev:
        return EvidenceSupportStatus.UNSUPPORTED, f"Subject '{source_name}' or object '{target_name}' missing from evidence span"

    # Default for non-table text: if not verified by explicit linguistic pattern or human review, mark NOT_ASSESSED
    return EvidenceSupportStatus.NOT_ASSESSED, "Evidence span contains co-occurring terms; semantic entailment not assessed"
