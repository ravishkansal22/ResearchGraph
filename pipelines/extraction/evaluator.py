"""Scientific Information Extraction Quality and Evaluation Engine.

Calculates reproducible engineering metrics (provenance validity, exact evidence grounding,
schema conformance, rejection rate) and provides ground-truth comparison metrics
(precision, recall, F1) when human annotations are available.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from dataset.schemas.scientific_knowledge import (
    ScientificEntityRecord,
    ScientificRelationRecord,
    ScientificStatementRecord,
    ValidationStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class CategoryMetrics:
    """Precision, recall, and F1 metrics for a single scientific category."""
    category: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None


@dataclass
class ExtractionEvaluationReport:
    """Comprehensive evaluation report separating engineering from scientific metrics."""
    # Run Metadata
    pipeline_version: str
    schema_version: str
    timestamp: str
    total_chunks: int

    # Engineering Integrity Metrics (Measured)
    total_entities_extracted: int
    total_statements_extracted: int
    total_relations_extracted: int
    total_candidate_records: int
    total_validated_records: int
    total_needs_review_records: int
    total_rejected_records: int

    # Rates & Conformance
    validation_pass_rate: float
    rejection_rate: float
    needs_review_rate: float
    evidence_grounding_accuracy: float
    provenance_validity_rate: float
    unsupported_claim_rate: float
    empty_output_chunk_count: int
    empty_output_chunk_rate: float

    # Category Counts
    entity_counts_by_category: Dict[str, int]
    statement_counts_by_category: Dict[str, int]
    relation_counts_by_category: Dict[str, int]
    rejection_reasons_breakdown: Dict[str, int]

    # Performance
    total_duration_ms: float
    avg_latency_per_chunk_ms: float

    # Ground-Truth Quality Status (Explicitly Separated)
    ground_truth_status: str = "PENDING_HUMAN_ANNOTATION"
    human_annotations_count: int = 0
    scientific_precision: Optional[float] = None
    scientific_recall: Optional[float] = None
    scientific_f1: Optional[float] = None
    category_scientific_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class ExtractionEvaluator:
    """Evaluates extraction batch results against grounding criteria and optional ground truth."""

    def evaluate_batch(
        self,
        chunks_count: int,
        entities: List[ScientificEntityRecord],
        statements: List[ScientificStatementRecord],
        relations: List[ScientificRelationRecord],
        rejected_records: List[Dict[str, Any]],
        duration_ms: float,
        pipeline_version: str = "v0.4.0",
        schema_version: str = "0.4.0",
        timestamp: str = "",
        ground_truth: Optional[List[Dict[str, Any]]] = None,
    ) -> ExtractionEvaluationReport:
        """Compute engineering and evaluation metrics for extraction run."""
        all_records = list(entities) + list(statements) + list(relations)
        total_candidates = len(all_records) + len(rejected_records)

        val_count = sum(1 for r in all_records if r.validation_status == ValidationStatus.VALIDATED)
        rev_count = sum(1 for r in all_records if r.validation_status == ValidationStatus.NEEDS_REVIEW)
        rej_count = len(rejected_records) + sum(1 for r in all_records if r.validation_status == ValidationStatus.REJECTED)

        # Evidence grounding: exact slice match and valid offsets
        grounded_count = sum(
            1 for r in all_records
            if getattr(r, "evidence", None) and r.evidence.is_exact_match
        )
        evidence_acc = (grounded_count / len(all_records)) if all_records else 1.0

        # Provenance validity
        provenance_valid_count = sum(
            1 for r in all_records
            if getattr(r, "provenance", None) and r.provenance.canonical_id and r.provenance.chunk_id
        )
        provenance_rate = (provenance_valid_count / len(all_records)) if all_records else 1.0

        # Unsupported claims rate (statements rejected or flagged for missing evidence)
        candidate_stmts_count = len(statements) + sum(
            1 for r in rejected_records if r.get("record_type") == "STATEMENT"
        )
        unsupported_stmts = sum(
            1 for s in statements if s.validation_status in [ValidationStatus.REJECTED, ValidationStatus.NEEDS_REVIEW]
        ) + sum(1 for r in rejected_records if r.get("record_type") == "STATEMENT")
        unsupported_claim_rate = (unsupported_stmts / candidate_stmts_count) if candidate_stmts_count else 0.0

        # Category distribution
        ent_counts: Dict[str, int] = {}
        for e in entities:
            ent_counts[e.category.value] = ent_counts.get(e.category.value, 0) + 1

        stmt_counts: Dict[str, int] = {}
        for s in statements:
            stmt_counts[s.category.value] = stmt_counts.get(s.category.value, 0) + 1

        rel_counts: Dict[str, int] = {}
        for rel in relations:
            rel_counts[rel.relation_type.value] = rel_counts.get(rel.relation_type.value, 0) + 1

        # Rejection reasons breakdown
        rejection_reasons: Dict[str, int] = {}
        for r in rejected_records:
            for note in r.get("validation_notes", ["UNKNOWN_REJECTION_REASON"]):
                rejection_reasons[note] = rejection_reasons.get(note, 0) + 1

        # Chunks yielding 0 records
        chunks_with_output = {
            r.provenance.chunk_id for r in all_records if getattr(r, "provenance", None)
        }
        empty_chunks = max(0, chunks_count - len(chunks_with_output))
        empty_chunk_rate = (empty_chunks / chunks_count) if chunks_count else 0.0

        val_pass_rate = (val_count / total_candidates) if total_candidates else 1.0
        rejection_rate = (rej_count / total_candidates) if total_candidates else 0.0
        needs_review_rate = (rev_count / total_candidates) if total_candidates else 0.0
        avg_latency = (duration_ms / chunks_count) if chunks_count else 0.0

        report = ExtractionEvaluationReport(
            pipeline_version=pipeline_version,
            schema_version=schema_version,
            timestamp=timestamp,
            total_chunks=chunks_count,
            total_entities_extracted=len(entities),
            total_statements_extracted=len(statements),
            total_relations_extracted=len(relations),
            total_candidate_records=total_candidates,
            total_validated_records=val_count,
            total_needs_review_records=rev_count,
            total_rejected_records=rej_count,
            validation_pass_rate=round(val_pass_rate, 4),
            rejection_rate=round(rejection_rate, 4),
            needs_review_rate=round(needs_review_rate, 4),
            evidence_grounding_accuracy=round(evidence_acc, 4),
            provenance_validity_rate=round(provenance_rate, 4),
            unsupported_claim_rate=round(unsupported_claim_rate, 4),
            empty_output_chunk_count=empty_chunks,
            empty_output_chunk_rate=round(empty_chunk_rate, 4),
            entity_counts_by_category=ent_counts,
            statement_counts_by_category=stmt_counts,
            relation_counts_by_category=rel_counts,
            rejection_reasons_breakdown=rejection_reasons,
            total_duration_ms=round(duration_ms, 2),
            avg_latency_per_chunk_ms=round(avg_latency, 2),
        )

        if ground_truth and len(ground_truth) > 0:
            # When ground-truth labels exist, compute precision, recall, F1
            self._compute_ground_truth_metrics(report, all_records, ground_truth)
        else:
            report.ground_truth_status = "PENDING_HUMAN_ANNOTATION"
            report.human_annotations_count = 0
            report.scientific_precision = None
            report.scientific_recall = None
            report.scientific_f1 = None

        return report

    def _compute_ground_truth_metrics(
        self,
        report: ExtractionEvaluationReport,
        predicted_records: List[Any],
        ground_truth: List[Dict[str, Any]],
    ) -> None:
        """Compute precision, recall, and F1 when actual ground-truth labels are present."""
        report.ground_truth_status = "EVALUATED_AGAINST_GROUND_TRUTH"
        report.human_annotations_count = len(ground_truth)

        # Exact matching on (chunk_id, category, normalized_text)
        gt_set = {
            (gt["chunk_id"], gt["category"], gt["normalized_text"].lower().strip())
            for gt in ground_truth if gt.get("category") and gt.get("normalized_text")
        }

        pred_set = set()
        for p in predicted_records:
            cat = getattr(p, "category", None) or getattr(p, "relation_type", None)
            cat_str = cat.value if hasattr(cat, "value") else str(cat)
            norm = getattr(p, "normalized_name", None) or getattr(p, "normalized_statement", None) or p.surface_text
            pred_set.add((p.provenance.chunk_id, cat_str, norm.lower().strip()))

        tp = len(gt_set.intersection(pred_set))
        fp = len(pred_set - gt_set)
        fn = len(gt_set - pred_set)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        report.scientific_precision = round(precision, 4)
        report.scientific_recall = round(recall, 4)
        report.scientific_f1 = round(f1, 4)
