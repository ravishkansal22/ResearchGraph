"""Scientific Information Extraction Quality and Evaluation Engine.

Calculates reproducible engineering metrics (provenance validity, exact evidence grounding,
schema conformance, rejection rate) and provides ground-truth comparison metrics
(precision, recall, F1) when human annotations are available.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from dataset.schemas.scientific_knowledge import (
    ScientificEntityRecord,
    ScientificRelationRecord,
    ScientificStatementRecord,
    ValidationStatus,
)

logger = logging.getLogger(__name__)

# Valid taxonomy of categories supported by ResearchGraph schemas
VALID_CATEGORIES = {
    # Entities
    "METHOD", "TASK", "DATASET", "METRIC", "DOMAIN", "PROBLEM", "BOTTLENECK", "ASSUMPTION",
    # Statements
    "CLAIM", "RESULT", "LIMITATION", "FUTURE_DIRECTION", "FAILURE_MODE",
    # Relations
    "ADDRESSES", "USES", "IMPROVES", "OUTPERFORMS", "LIMITED_BY", "EVALUATED_ON", "ASSUMES", "REPORTS", "SUGGESTS", "CONTRADICTS",
}

# Common spelling / plural aliases mapped cleanly to canonical schema categories
CATEGORY_ALIASES: Dict[str, str] = {
    "METHODS": "METHOD",
    "ALGORITHM": "METHOD",
    "TECHNIQUE": "METHOD",
    "TASKS": "TASK",
    "DATASETS": "DATASET",
    "CORPUS": "DATASET",
    "BENCHMARK": "DATASET",
    "METRICS": "METRIC",
    "DOMAINS": "DOMAIN",
    "PROBLEMS": "PROBLEM",
    "BOTTLENECKS": "BOTTLENECK",
    "CHALLENGE": "BOTTLENECK",
    "CHALLENGES": "BOTTLENECK",
    "LIMITATIONS": "LIMITATION",
    "RESULTS": "RESULT",
    "FINDING": "RESULT",
    "FINDINGS": "RESULT",
    "CLAIMS": "CLAIM",
    "CONTRIBUTION": "CLAIM",
    "CONTRIBUTIONS": "CLAIM",
    "FUTURE_DIRECTIONS": "FUTURE_DIRECTION",
}


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
    relaxed_scientific_precision: Optional[float] = None
    relaxed_scientific_recall: Optional[float] = None
    relaxed_scientific_f1: Optional[float] = None
    evidence_correctness_accuracy: Optional[float] = None
    relation_extraction_metrics: Dict[str, Any] = field(default_factory=dict)
    category_scientific_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    false_positive_records: List[Dict[str, Any]] = field(default_factory=list)
    false_negative_records: List[Dict[str, Any]] = field(default_factory=list)
    common_error_categories: Dict[str, int] = field(default_factory=dict)
    human_verdict_summary: Dict[str, int] = field(default_factory=dict)


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
        """Compute strict & relaxed precision/recall/F1, category-wise metrics, and evidence correctness."""
        report.ground_truth_status = "EVALUATED_AGAINST_GROUND_TRUTH"
        report.human_annotations_count = len(ground_truth)

        # 1. Prepare structured records
        # Ground truth format: Dict with {chunk_id, category, normalized_text, evidence_span, source, target}
        gt_items = []
        for gt in ground_truth:
            raw_cat = str(gt.get("category", "")).strip().upper()
            cat = CATEGORY_ALIASES.get(raw_cat, raw_cat)
            norm = str(gt.get("normalized_text", "")).lower().strip()
            cid = str(gt.get("chunk_id", "")).strip()
            ev = str(gt.get("evidence_span", "")).lower().strip()
            src = str(gt.get("source", "")).lower().strip()
            tgt = str(gt.get("target", "")).lower().strip()
            is_rel = bool(src and tgt) or cat in {
                "ADDRESSES", "USES", "IMPROVES", "OUTPERFORMS", "LIMITED_BY", "EVALUATED_ON", "ASSUMES", "REPORTS", "SUGGESTS", "CONTRADICTS"
            }
            if cat and (norm or (src and tgt)):
                gt_items.append({
                    "chunk_id": cid,
                    "category": cat,
                    "normalized_text": norm,
                    "evidence_span": ev,
                    "source": src,
                    "target": tgt,
                    "is_relation": is_rel,
                })

        pred_items = []
        for p in predicted_records:
            cat = getattr(p, "category", None) or getattr(p, "relation_type", None)
            raw_cat = (cat.value if hasattr(cat, "value") else str(cat)).strip().upper()
            cat_str = CATEGORY_ALIASES.get(raw_cat, raw_cat)
            norm = (getattr(p, "normalized_name", None) or getattr(p, "normalized_statement", None) or p.surface_text or "").lower().strip()
            cid = p.provenance.chunk_id
            ev = (p.evidence.text if getattr(p, "evidence", None) else "").lower().strip()
            src = (getattr(p, "source_id", "") or "").lower().strip()
            tgt = (getattr(p, "target_id", "") or "").lower().strip()
            is_rel = hasattr(p, "relation_type") or hasattr(p, "source_id") or cat_str in {
                "ADDRESSES", "USES", "IMPROVES", "OUTPERFORMS", "LIMITED_BY", "EVALUATED_ON", "ASSUMES", "REPORTS", "SUGGESTS", "CONTRADICTS"
            }
            pred_items.append({
                "chunk_id": cid,
                "category": cat_str,
                "normalized_text": norm,
                "evidence_span": ev,
                "source": src,
                "target": tgt,
                "is_relation": is_rel,
                "original": p,
            })

        # 2. Strict Matching: exact (chunk_id, category, normalized_text)
        gt_strict_set = {(g["chunk_id"], g["category"], g["normalized_text"]) for g in gt_items if not g["is_relation"]}
        pred_strict_set = {(p["chunk_id"], p["category"], p["normalized_text"]) for p in pred_items if not p["is_relation"]}

        tp_strict = len(gt_strict_set.intersection(pred_strict_set))
        fp_strict = len(pred_strict_set - gt_strict_set)
        fn_strict = len(gt_strict_set - pred_strict_set)

        prec_strict = tp_strict / (tp_strict + fp_strict) if (tp_strict + fp_strict) > 0 else 0.0
        rec_strict = tp_strict / (tp_strict + fn_strict) if (tp_strict + fn_strict) > 0 else 0.0
        f1_strict = (2 * prec_strict * rec_strict / (prec_strict + rec_strict)) if (prec_strict + rec_strict) > 0 else 0.0

        report.scientific_precision = round(prec_strict, 4)
        report.scientific_recall = round(rec_strict, 4)
        report.scientific_f1 = round(f1_strict, 4)

        # Collect explicit False Positive & False Negative records
        fp_strict_items = sorted(list(pred_strict_set - gt_strict_set))
        fn_strict_items = sorted(list(gt_strict_set - pred_strict_set))

        report.false_positive_records = [
            {
                "chunk_id": item[0],
                "category": item[1],
                "normalized_text": item[2],
                "error_type": "SPURIOUS_OR_UNMATCHED_PREDICTION",
            }
            for item in fp_strict_items
        ]
        report.false_negative_records = [
            {
                "chunk_id": item[0],
                "category": item[1],
                "normalized_text": item[2],
                "error_type": "MISSED_GROUND_TRUTH_RECORD",
            }
            for item in fn_strict_items
        ]

        error_counts: Dict[str, int] = {}
        for fp in report.false_positive_records:
            k = f"SPURIOUS_{fp['category']}"
            error_counts[k] = error_counts.get(k, 0) + 1
        for fn in report.false_negative_records:
            k = f"MISSED_{fn['category']}"
            error_counts[k] = error_counts.get(k, 0) + 1
        report.common_error_categories = error_counts

        # 3. Category-Wise Metrics (Strict)
        all_categories = sorted(list({g["category"] for g in gt_items}.union({p["category"] for p in pred_items})))
        cat_metrics: Dict[str, Dict[str, Any]] = {}

        for cat in all_categories:
            gt_cat = {(g["chunk_id"], g["normalized_text"]) for g in gt_items if g["category"] == cat}
            pred_cat = {(p["chunk_id"], p["normalized_text"]) for p in pred_items if p["category"] == cat}

            tp_c = len(gt_cat.intersection(pred_cat))
            fp_c = len(pred_cat - gt_cat)
            fn_c = len(gt_cat - pred_cat)

            p_c = tp_c / (tp_c + fp_c) if (tp_c + fp_c) > 0 else 0.0
            r_c = tp_c / (tp_c + fn_c) if (tp_c + fn_c) > 0 else 0.0
            f_c = (2 * p_c * r_c / (p_c + r_c)) if (p_c + r_c) > 0 else 0.0

            cat_metrics[cat] = {
                "category": cat,
                "true_positives": tp_c,
                "false_positives": fp_c,
                "false_negatives": fn_c,
                "precision": round(p_c, 4),
                "recall": round(r_c, 4),
                "f1_score": round(f_c, 4),
            }

        report.category_scientific_metrics = cat_metrics

        # 4. Relaxed Matching (handles partial matches and token overlap)
        matched_gt_indices = set()
        tp_relaxed = 0

        # Deduplicate predictions and ground truth for clean relaxed evaluation
        unique_preds = []
        seen_preds = set()
        for p in pred_items:
            k = (p["chunk_id"], p["category"], p["normalized_text"])
            if k not in seen_preds:
                seen_preds.add(k)
                unique_preds.append(p)

        unique_gts = []
        seen_gts = set()
        for g in gt_items:
            k = (g["chunk_id"], g["category"], g["normalized_text"])
            if k not in seen_gts:
                seen_gts.add(k)
                unique_gts.append(g)

        for p in unique_preds:
            for g_idx, g in enumerate(unique_gts):
                if g_idx in matched_gt_indices:
                    continue
                if p["chunk_id"] == g["chunk_id"] and p["category"] == g["category"]:
                    # Check token overlap or substring match
                    p_tokens = set(p["normalized_text"].split())
                    g_tokens = set(g["normalized_text"].split())
                    is_sub = (p["normalized_text"] in g["normalized_text"]) or (g["normalized_text"] in p["normalized_text"])
                    token_overlap = len(p_tokens & g_tokens) / max(1, len(p_tokens | g_tokens))

                    if is_sub or token_overlap >= 0.5:
                        tp_relaxed += 1
                        matched_gt_indices.add(g_idx)
                        break

        fp_relaxed = max(0, len(unique_preds) - tp_relaxed)
        fn_relaxed = max(0, len(unique_gts) - tp_relaxed)

        prec_relaxed = tp_relaxed / (tp_relaxed + fp_relaxed) if (tp_relaxed + fp_relaxed) > 0 else 0.0
        rec_relaxed = tp_relaxed / (tp_relaxed + fn_relaxed) if (tp_relaxed + fn_relaxed) > 0 else 0.0
        f1_relaxed = (2 * prec_relaxed * rec_relaxed / (prec_relaxed + rec_relaxed)) if (prec_relaxed + rec_relaxed) > 0 else 0.0

        report.relaxed_scientific_precision = round(prec_relaxed, 4)
        report.relaxed_scientific_recall = round(rec_relaxed, 4)
        report.relaxed_scientific_f1 = round(f1_relaxed, 4)

        # 5. Evidence Correctness Evaluation
        # For matched entities, check if predicted evidence overlaps with ground truth evidence span
        correct_evidence_count = 0
        ev_evaluable_count = 0

        for p in pred_items:
            for g in gt_items:
                if p["chunk_id"] == g["chunk_id"] and p["category"] == g["category"] and p["normalized_text"] == g["normalized_text"]:
                    if g["evidence_span"]:
                        ev_evaluable_count += 1
                        if g["evidence_span"] in p["evidence_span"] or p["evidence_span"] in g["evidence_span"]:
                            correct_evidence_count += 1
                    break

        ev_acc = (correct_evidence_count / ev_evaluable_count) if ev_evaluable_count > 0 else 1.0
        report.evidence_correctness_accuracy = round(ev_acc, 4)

        # 6. Relationship Extraction Specific Metrics
        gt_rels = [g for g in gt_items if g["is_relation"]]
        pred_rels = [p for p in pred_items if p["is_relation"]]

        if gt_rels or pred_rels:
            gt_rel_set = {(g["chunk_id"], g["category"]) for g in gt_rels}
            pred_rel_set = {(p["chunk_id"], p["category"]) for p in pred_rels}

            tp_rel = len(gt_rel_set.intersection(pred_rel_set))
            fp_rel = len(pred_rel_set - gt_rel_set)
            fn_rel = len(gt_rel_set - pred_rel_set)

            p_rel = tp_rel / (tp_rel + fp_rel) if (tp_rel + fp_rel) > 0 else 0.0
            r_rel = tp_rel / (tp_rel + fn_rel) if (tp_rel + fn_rel) > 0 else 0.0
            f_rel = (2 * p_rel * r_rel / (p_rel + r_rel)) if (p_rel + r_rel) > 0 else 0.0

            report.relation_extraction_metrics = {
                "ground_truth_relations_count": len(gt_rels),
                "predicted_relations_count": len(pred_rels),
                "true_positives": tp_rel,
                "false_positives": fp_rel,
                "false_negatives": fn_rel,
                "precision": round(p_rel, 4),
                "recall": round(r_rel, 4),
                "f1_score": round(f_rel, 4),
            }
        else:
            report.relation_extraction_metrics = {
                "ground_truth_relations_count": 0,
                "predicted_relations_count": 0,
                "precision": None,
                "recall": None,
                "f1_score": None,
            }

    @staticmethod
    def parse_human_annotations_csv(csv_path: Union[str, Path]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Parse human review CSV into evaluator-ready ground-truth items and status summary.

        Reads standard ResearchGraph audit packet / annotation template CSV with human verdict
        columns (CORRECT, PARTIALLY_CORRECT, UNSUPPORTED, MISSING).
        """
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Annotation file not found: {path}")

        gt_records: List[Dict[str, Any]] = []
        seen_gt_keys = set()
        verdict_counts: Dict[str, int] = {
            "CORRECT": 0,
            "PARTIALLY_CORRECT": 0,
            "UNSUPPORTED": 0,
            "MISSING": 0,
            "UNREVIEWED": 0,
        }

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                verdict = (row.get("human_verdict") or "").strip().upper()
                if not verdict or verdict in ("UNREVIEWED", "BLANK", "PENDING"):
                    verdict_counts["UNREVIEWED"] += 1
                    continue

                if verdict in verdict_counts:
                    verdict_counts[verdict] += 1
                else:
                    verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

                cid = (row.get("chunk_id") or "").strip()
                raw_cat = (row.get("human_ground_truth_category") or "").strip().upper()
                cat = CATEGORY_ALIASES.get(raw_cat, raw_cat)
                norm = (row.get("human_ground_truth_normalized_text") or "").strip()
                ev = (row.get("human_ground_truth_evidence_span") or "").strip()
                src = (row.get("human_relation_source") or row.get("system_relation_source") or row.get("source") or "").strip()
                tgt = (row.get("human_relation_target") or row.get("system_relation_target") or row.get("target") or "").strip()
                attr = (row.get("human_attribution") or "AUTHOR_STATED").strip().upper()

                if verdict in ("CORRECT", "PARTIALLY_CORRECT"):
                    # If human fields omitted on CORRECT, inherit system predictions
                    if not cat:
                        sys_cat = (row.get("system_predicted_category") or "").strip().upper()
                        cat = CATEGORY_ALIASES.get(sys_cat, sys_cat)
                    if not norm:
                        norm = (row.get("system_predicted_surface_text") or "").strip()
                    if not ev:
                        ev = (row.get("system_evidence_span") or "").strip()

                    if cat and (norm or ev or (src and tgt)):
                        key = (cid, cat, (norm or ev).lower(), src.lower(), tgt.lower())
                        if key not in seen_gt_keys:
                            seen_gt_keys.add(key)
                            gt_records.append({
                                "chunk_id": cid,
                                "category": cat,
                                "normalized_text": norm or ev,
                                "evidence_span": ev or norm,
                                "source": src,
                                "target": tgt,
                                "attribution": attr,
                            })

                elif verdict == "MISSING":
                    if cat and (norm or ev or (src and tgt)):
                        key = (cid, cat, (norm or ev).lower(), src.lower(), tgt.lower())
                        if key not in seen_gt_keys:
                            seen_gt_keys.add(key)
                            gt_records.append({
                                "chunk_id": cid,
                                "category": cat,
                                "normalized_text": norm or ev,
                                "evidence_span": ev or norm,
                                "source": src,
                                "target": tgt,
                                "attribution": attr,
                            })

                # UNSUPPORTED records are not added to ground truth (they serve as false positive check)

        return gt_records, verdict_counts

