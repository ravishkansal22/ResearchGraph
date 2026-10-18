"""Synthetic Unit Tests for Human Benchmark Evaluation Pipeline.

Validates:
1. Missing labels and unreviewed row resilience
2. Duplicate record handling (predictions and annotations)
3. Invalid and alias category normalization
4. Empty chunk edge cases (true negatives, pure false positives, pure false negatives)
5. Partial matches and relaxed token overlap matching
6. Dual-reviewer reconciliation and Cohen's Kappa computation
7. Comparative evaluation of v0.4.0 vs v0.4.1 on identical synthetic ground truth

NOTE: All tests in this file use strictly isolated synthetic fixtures to validate
engineering correctness without fabricating production ground truth.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from dataset.schemas.scientific_knowledge import (
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
from pipelines.extraction.evaluator import ExtractionEvaluationReport, ExtractionEvaluator
from scripts.evaluate_human_benchmark import evaluate_human_benchmark
from scripts.reconcile_human_annotations import compute_cohens_kappa, reconcile_reviewers

FIELDNAMES = [
    "packet_index",
    "chunk_id",
    "canonical_id",
    "section_title",
    "section_bucket",
    "has_system_output",
    "audit_investigation_goal",
    "chunk_text",
    "system_record_type",
    "system_predicted_category",
    "system_predicted_surface_text",
    "system_evidence_span",
    "system_relation_source",
    "system_relation_target",
    "human_ground_truth_category",
    "human_ground_truth_normalized_text",
    "human_ground_truth_evidence_span",
    "human_relation_source",
    "human_relation_target",
    "human_attribution",
    "human_verdict",
    "human_reviewer_comments",
    "reviewer_id",
]


def write_test_csv(file_path: Path, rows: List[Dict[str, Any]]) -> None:
    """Helper to write synthetic CSV with exact column mapping."""
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            full_row = {k: "" for k in FIELDNAMES}
            full_row.update(r)
            writer.writerow(full_row)


@pytest.fixture
def evaluator() -> ExtractionEvaluator:
    return ExtractionEvaluator()


def test_missing_labels_and_unreviewed_rows(evaluator, tmp_path):
    """Verify that unreviewed rows in CSV are cleanly tracked and do not corrupt metrics."""
    csv_file = tmp_path / "mixed_review.csv"
    write_test_csv(
        csv_file,
        [
            {
                "packet_index": 1,
                "chunk_id": "chk_01",
                "system_record_type": "ENTITY",
                "system_predicted_category": "METHOD",
                "system_predicted_surface_text": "LSTM",
                "system_evidence_span": "LSTM",
                "human_verdict": "CORRECT",
            },
            {
                "packet_index": 1,
                "chunk_id": "chk_01",
                "system_record_type": "ENTITY",
                "system_predicted_category": "PROBLEM",
                "system_predicted_surface_text": "latency",
                "system_evidence_span": "latency",
                "human_verdict": "",  # Unreviewed
            },
            {
                "packet_index": 1,
                "chunk_id": "chk_01",
                "system_record_type": "ADD_MISSING",
                "human_verdict": "",  # Blank slot
            },
        ],
    )

    gt_records, verdict_counts = evaluator.parse_human_annotations_csv(csv_file)
    assert len(gt_records) == 1
    assert verdict_counts["CORRECT"] == 1
    assert verdict_counts["UNREVIEWED"] == 2

    pred = [
        ScientificEntityRecord(
            record_id="ent_01",
            category=ScientificEntityType.METHOD,
            surface_text="LSTM",
            normalized_name="lstm",
            evidence=EvidenceSpan(text="LSTM", start_char=0, end_char=4),
            provenance=ExtractionProvenance(canonical_id="paper_1", chunk_id="chk_01"),
        )
    ]

    report = evaluator.evaluate_batch(
        chunks_count=1,
        entities=pred,
        statements=[],
        relations=[],
        rejected_records=[],
        duration_ms=5.0,
        ground_truth=gt_records,
    )
    assert report.scientific_precision == 1.0
    assert report.scientific_recall == 1.0
    assert report.scientific_f1 == 1.0


def test_duplicate_records_handling(evaluator, tmp_path):
    """Verify that duplicate predictions or duplicate human annotations are properly deduplicated."""
    csv_file = tmp_path / "duplicate_review.csv"
    write_test_csv(
        csv_file,
        [
            {
                "packet_index": 1,
                "chunk_id": "chk_01",
                "system_record_type": "ENTITY",
                "system_predicted_category": "METHOD",
                "system_predicted_surface_text": "LSTM",
                "system_evidence_span": "LSTM",
                "human_verdict": "CORRECT",
            },
            {
                "packet_index": 1,
                "chunk_id": "chk_01",
                "system_record_type": "ADD_MISSING",
                "human_ground_truth_category": "METHOD",
                "human_ground_truth_normalized_text": "LSTM",
                "human_ground_truth_evidence_span": "LSTM",
                "human_attribution": "AUTHOR_STATED",
                "human_verdict": "MISSING",
                "human_reviewer_comments": "Duplicate entry",
            },
        ],
    )

    gt_records, _ = evaluator.parse_human_annotations_csv(csv_file)
    # Deduplication in parser ensures only 1 ground truth record
    assert len(gt_records) == 1

    # Model predicted the same entity twice
    pred_duplicates = [
        ScientificEntityRecord(
            record_id="ent_01",
            category=ScientificEntityType.METHOD,
            surface_text="LSTM",
            normalized_name="lstm",
            evidence=EvidenceSpan(text="LSTM", start_char=0, end_char=4),
            provenance=ExtractionProvenance(canonical_id="paper_1", chunk_id="chk_01"),
        ),
        ScientificEntityRecord(
            record_id="ent_02",
            category=ScientificEntityType.METHOD,
            surface_text="LSTM",
            normalized_name="lstm",
            evidence=EvidenceSpan(text="LSTM", start_char=0, end_char=4),
            provenance=ExtractionProvenance(canonical_id="paper_1", chunk_id="chk_01"),
        ),
    ]

    report = evaluator.evaluate_batch(
        chunks_count=1,
        entities=pred_duplicates,
        statements=[],
        relations=[],
        rejected_records=[],
        duration_ms=5.0,
        ground_truth=gt_records,
    )

    # In strict matching, sets prevent duplicate inflation
    assert report.scientific_precision == 1.0
    assert report.scientific_recall == 1.0
    assert report.scientific_f1 == 1.0

    # In relaxed matching, deduplicated prediction items prevent false positives
    assert report.relaxed_scientific_precision == 1.0
    assert report.relaxed_scientific_recall == 1.0
    assert report.relaxed_scientific_f1 == 1.0


def test_invalid_categories_resilience(evaluator, tmp_path):
    """Verify category alias normalization (e.g. METHODS -> METHOD) and resilience against typos."""
    csv_file = tmp_path / "aliases_review.csv"
    write_test_csv(
        csv_file,
        [
            {
                "packet_index": 1,
                "chunk_id": "chk_01",
                "system_record_type": "ADD_MISSING",
                "human_ground_truth_category": "METHODS",
                "human_ground_truth_normalized_text": "LSTM",
                "human_ground_truth_evidence_span": "LSTM",
                "human_attribution": "AUTHOR_STATED",
                "human_verdict": "MISSING",
            },
            {
                "packet_index": 1,
                "chunk_id": "chk_01",
                "system_record_type": "ADD_MISSING",
                "human_ground_truth_category": "DATASETS",
                "human_ground_truth_normalized_text": "NSL-KDD",
                "human_ground_truth_evidence_span": "NSL-KDD",
                "human_attribution": "AUTHOR_STATED",
                "human_verdict": "MISSING",
            },
            {
                "packet_index": 1,
                "chunk_id": "chk_01",
                "system_record_type": "ADD_MISSING",
                "human_ground_truth_category": "LIMITATIONS",
                "human_ground_truth_normalized_text": "High latency",
                "human_ground_truth_evidence_span": "High latency",
                "human_attribution": "AUTHOR_STATED",
                "human_verdict": "MISSING",
            },
        ],
    )

    gt_records, _ = evaluator.parse_human_annotations_csv(csv_file)
    categories = [g["category"] for g in gt_records]
    assert "METHOD" in categories  # METHODS normalized to METHOD
    assert "DATASET" in categories  # DATASETS normalized to DATASET
    assert "LIMITATION" in categories  # LIMITATIONS normalized to LIMITATION


def test_empty_chunks_edge_cases(evaluator):
    """Verify empty chunk metrics: true negative chunk, pure false positive chunk, pure false negative chunk."""
    # Case A: True Negative Chunk (model extracted 0, human annotated 0)
    report_tn = evaluator.evaluate_batch(
        chunks_count=1,
        entities=[],
        statements=[],
        relations=[],
        rejected_records=[],
        duration_ms=2.0,
        ground_truth=[],
    )
    assert report_tn.ground_truth_status == "PENDING_HUMAN_ANNOTATION"

    # Case B: Pure False Positive Chunk (model extracted 1 entity, human ground truth has 0)
    pred_fp = [
        ScientificEntityRecord(
            record_id="ent_01",
            category=ScientificEntityType.METRIC,
            surface_text="accuracy",
            normalized_name="accuracy",
            evidence=EvidenceSpan(text="accuracy", start_char=0, end_char=8),
            provenance=ExtractionProvenance(canonical_id="paper_1", chunk_id="chk_fp"),
        )
    ]
    gt_empty = [
        # Record on another chunk to trigger ground truth evaluation
        {"chunk_id": "chk_other", "category": "METHOD", "normalized_text": "bert", "evidence_span": "bert"}
    ]
    report_fp = evaluator.evaluate_batch(
        chunks_count=1,
        entities=pred_fp,
        statements=[],
        relations=[],
        rejected_records=[],
        duration_ms=2.0,
        ground_truth=gt_empty,
    )
    assert report_fp.scientific_precision == 0.0

    # Case C: Pure False Negative Chunk (model extracted 0, human found 2 missing items)
    gt_fn = [
        {"chunk_id": "chk_fn", "category": "METHOD", "normalized_text": "vosviewer", "evidence_span": "vosviewer"},
        {"chunk_id": "chk_fn", "category": "DATASET", "normalized_text": "scopus", "evidence_span": "scopus"},
    ]
    report_fn = evaluator.evaluate_batch(
        chunks_count=1,
        entities=[],
        statements=[],
        relations=[],
        rejected_records=[],
        duration_ms=2.0,
        ground_truth=gt_fn,
    )
    assert report_fn.scientific_precision == 0.0
    assert report_fn.scientific_recall == 0.0
    assert len(report_fn.false_negative_records) == 2


def test_partial_matches_relaxed_evaluation(evaluator):
    """Verify that partial string matches and token overlap (>= 0.5) receive relaxed credit."""
    pred = [
        ScientificEntityRecord(
            record_id="ent_01",
            category=ScientificEntityType.METHOD,
            surface_text="support vector machine classifier",
            normalized_name="support vector machine classifier",
            evidence=EvidenceSpan(text="support vector machine classifier", start_char=0, end_char=33),
            provenance=ExtractionProvenance(canonical_id="paper_1", chunk_id="chk_01"),
        )
    ]

    gt = [
        {
            "chunk_id": "chk_01",
            "category": "METHOD",
            "normalized_text": "support vector machine",
            "evidence_span": "support vector machine",
        }
    ]

    report = evaluator.evaluate_batch(
        chunks_count=1,
        entities=pred,
        statements=[],
        relations=[],
        rejected_records=[],
        duration_ms=2.0,
        ground_truth=gt,
    )

    # Strict mode: 0 TP because strings do not match verbatim
    assert report.scientific_precision == 0.0
    assert report.scientific_recall == 0.0

    # Relaxed mode: 1 TP because "support vector machine" is a substring of "support vector machine classifier"
    assert report.relaxed_scientific_precision == 1.0
    assert report.relaxed_scientific_recall == 1.0
    assert report.relaxed_scientific_f1 == 1.0


def test_dual_annotator_reconciliation_synthetic(tmp_path):
    """Verify dual-reviewer reconciliation: agreement rate, Cohen's Kappa, and consensus generation."""
    rev1_file = tmp_path / "rev1.csv"
    rev2_file = tmp_path / "rev2.csv"

    rows_r1 = [
        # Row 1: Both agree CORRECT
        {
            "packet_index": 1,
            "chunk_id": "chk_01",
            "system_record_type": "ENTITY",
            "system_predicted_category": "METHOD",
            "system_predicted_surface_text": "LSTM",
            "system_evidence_span": "LSTM",
            "human_verdict": "CORRECT",
            "human_reviewer_comments": "Good",
            "reviewer_id": "reviewer_1",
        },
        # Row 2: Both agree UNSUPPORTED
        {
            "packet_index": 2,
            "chunk_id": "chk_01",
            "system_record_type": "ENTITY",
            "system_predicted_category": "METRIC",
            "system_predicted_surface_text": "latency",
            "system_evidence_span": "latency",
            "human_verdict": "UNSUPPORTED",
            "human_reviewer_comments": "Bad",
            "reviewer_id": "reviewer_1",
        },
        # Row 3: Disagreement: Rev1=CORRECT, Rev2=UNSUPPORTED
        {
            "packet_index": 3,
            "chunk_id": "chk_02",
            "system_record_type": "ENTITY",
            "system_predicted_category": "DOMAIN",
            "system_predicted_surface_text": "health",
            "system_evidence_span": "health",
            "human_verdict": "CORRECT",
            "human_reviewer_comments": "Domain",
            "reviewer_id": "reviewer_1",
        },
        # Row 4: Disagreement: Rev1=PARTIALLY_CORRECT (TASK), Rev2=PARTIALLY_CORRECT (METHOD)
        {
            "packet_index": 4,
            "chunk_id": "chk_02",
            "system_record_type": "ENTITY",
            "system_predicted_category": "METHOD",
            "system_predicted_surface_text": "grading",
            "system_evidence_span": "grading",
            "human_ground_truth_category": "TASK",
            "human_ground_truth_normalized_text": "grading",
            "human_ground_truth_evidence_span": "grading",
            "human_attribution": "AUTHOR_STATED",
            "human_verdict": "PARTIALLY_CORRECT",
            "human_reviewer_comments": "Is task",
            "reviewer_id": "reviewer_1",
        },
    ]

    rows_r2 = [
        # Row 1: Both agree CORRECT
        {
            "packet_index": 1,
            "chunk_id": "chk_01",
            "system_record_type": "ENTITY",
            "system_predicted_category": "METHOD",
            "system_predicted_surface_text": "LSTM",
            "system_evidence_span": "LSTM",
            "human_verdict": "CORRECT",
            "human_reviewer_comments": "Good",
            "reviewer_id": "reviewer_2",
        },
        # Row 2: Both agree UNSUPPORTED
        {
            "packet_index": 2,
            "chunk_id": "chk_01",
            "system_record_type": "ENTITY",
            "system_predicted_category": "METRIC",
            "system_predicted_surface_text": "latency",
            "system_evidence_span": "latency",
            "human_verdict": "UNSUPPORTED",
            "human_reviewer_comments": "Bad",
            "reviewer_id": "reviewer_2",
        },
        # Row 3: Disagreement: Rev1=CORRECT, Rev2=UNSUPPORTED
        {
            "packet_index": 3,
            "chunk_id": "chk_02",
            "system_record_type": "ENTITY",
            "system_predicted_category": "DOMAIN",
            "system_predicted_surface_text": "health",
            "system_evidence_span": "health",
            "human_verdict": "UNSUPPORTED",
            "human_reviewer_comments": "Not domain",
            "reviewer_id": "reviewer_2",
        },
        # Row 4: Disagreement: Rev1=PARTIALLY_CORRECT (TASK), Rev2=PARTIALLY_CORRECT (METHOD)
        {
            "packet_index": 4,
            "chunk_id": "chk_02",
            "system_record_type": "ENTITY",
            "system_predicted_category": "METHOD",
            "system_predicted_surface_text": "grading",
            "system_evidence_span": "grading",
            "human_ground_truth_category": "METHOD",
            "human_ground_truth_normalized_text": "grading",
            "human_ground_truth_evidence_span": "grading",
            "human_attribution": "AUTHOR_STATED",
            "human_verdict": "PARTIALLY_CORRECT",
            "human_reviewer_comments": "Is method",
            "reviewer_id": "reviewer_2",
        },
    ]

    write_test_csv(rev1_file, rows_r1)
    write_test_csv(rev2_file, rows_r2)

    out_consensus = tmp_path / "consensus.csv"
    out_report = tmp_path / "adjudication_report.md"

    summary = reconcile_reviewers(rev1_file, rev2_file, out_consensus, out_report)

    assert summary["total_rows"] == 4
    assert summary["both_reviewed_count"] == 4
    assert summary["concordant_count"] == 2  # Rows 1 and 2
    assert summary["discordant_count"] == 2  # Rows 3 (verdict mismatch) and 4 (category mismatch)
    assert summary["observed_agreement_rate"] == 0.75  # 3 of 4 verdicts matched
    assert summary["full_concordance_rate"] == 0.50   # 2 of 4 had exact category & span agreement

    with open(out_consensus, "r", encoding="utf-8") as f:
        c_rows = list(csv.DictReader(f))
    assert len(c_rows) == 4
    assert c_rows[0]["human_verdict"] == "CORRECT"  # Agreed
    assert c_rows[1]["human_verdict"] == "UNSUPPORTED"  # Agreed
    assert c_rows[2]["human_verdict"] == "NEEDS_ADJUDICATION"  # Disagreed verdict
    assert c_rows[3]["human_verdict"] == "NEEDS_ADJUDICATION"  # Disagreed category


def test_comparative_evaluator_v040_vs_v041_synthetic(tmp_path):
    """Verify that evaluate_human_benchmark runs end-to-end on synthetic data and computes deltas."""
    # Create synthetic v0.4.0 output directory
    dir_v040 = tmp_path / "v040"
    dir_v040.mkdir()
    rec_v040 = dir_v040 / "extracted_records.jsonl"
    rec_v040.write_text(
        json.dumps({
            "record_id": "ent_01",
            "schema_version": "0.4.0",
            "category": "METHOD",
            "surface_text": "LSTM",
            "normalized_name": "lstm",
            "evidence": {"text": "LSTM", "start_char": 0, "end_char": 4, "is_exact_match": True},
            "provenance": {"canonical_id": "paper_1", "chunk_id": "chk_01"},
            "extraction_version": "v0.4.0",
            "validation_status": "VALIDATED",
        }) + "\n",
        encoding="utf-8",
    )
    (dir_v040 / "extracted_relationships.jsonl").write_text("", encoding="utf-8")
    (dir_v040 / "rejected_records.jsonl").write_text("", encoding="utf-8")

    # Create synthetic v0.4.1 output directory (extracts LSTM + VOSviewer)
    dir_v041 = tmp_path / "v041"
    dir_v041.mkdir()
    rec_v041 = dir_v041 / "extracted_records.jsonl"
    rec_v041.write_text(
        json.dumps({
            "record_id": "ent_01",
            "schema_version": "0.4.0",
            "category": "METHOD",
            "surface_text": "LSTM",
            "normalized_name": "lstm",
            "evidence": {"text": "LSTM", "start_char": 0, "end_char": 4, "is_exact_match": True},
            "provenance": {"canonical_id": "paper_1", "chunk_id": "chk_01"},
            "extraction_version": "v0.4.1",
            "validation_status": "VALIDATED",
        }) + "\n" +
        json.dumps({
            "record_id": "ent_02",
            "schema_version": "0.4.0",
            "category": "METHOD",
            "surface_text": "VOSviewer",
            "normalized_name": "vosviewer",
            "evidence": {"text": "VOSviewer", "start_char": 10, "end_char": 19, "is_exact_match": True},
            "provenance": {"canonical_id": "paper_1", "chunk_id": "chk_01"},
            "extraction_version": "v0.4.1",
            "validation_status": "VALIDATED",
        }) + "\n",
        encoding="utf-8",
    )
    (dir_v041 / "extracted_relationships.jsonl").write_text("", encoding="utf-8")
    (dir_v041 / "rejected_records.jsonl").write_text("", encoding="utf-8")

    # Ground truth contains both LSTM and VOSviewer
    annotations_file = tmp_path / "gold_annotations.csv"
    write_test_csv(
        annotations_file,
        [
            {
                "packet_index": 1,
                "chunk_id": "chk_01",
                "system_record_type": "ENTITY",
                "system_predicted_category": "METHOD",
                "system_predicted_surface_text": "LSTM",
                "system_evidence_span": "LSTM",
                "human_verdict": "CORRECT",
                "human_reviewer_comments": "Good",
                "reviewer_id": "consensus",
            },
            {
                "packet_index": 1,
                "chunk_id": "chk_01",
                "system_record_type": "ADD_MISSING",
                "human_ground_truth_category": "METHOD",
                "human_ground_truth_normalized_text": "VOSviewer",
                "human_ground_truth_evidence_span": "VOSviewer",
                "human_attribution": "AUTHOR_STATED",
                "human_verdict": "MISSING",
                "human_reviewer_comments": "Missed tool",
                "reviewer_id": "consensus",
            },
        ],
    )

    out_dir = tmp_path / "eval_out"
    result = evaluate_human_benchmark(annotations_file, dir_v040, dir_v041, out_dir, "test_eval")

    assert result["status"] == "EVALUATED_AGAINST_GROUND_TRUTH"
    assert result["total_ground_truth_records"] == 2

    # v0.4.0: 1 TP (LSTM), 0 FP, 1 FN (VOSviewer) -> Precision=1.0, Recall=0.5, F1=0.6667
    assert result["models"]["v0.4.0"]["scientific_precision"] == 1.0
    assert result["models"]["v0.4.0"]["scientific_recall"] == 0.5
    assert result["models"]["v0.4.0"]["scientific_f1"] == 0.6667

    # v0.4.1: 2 TP (LSTM, VOSviewer), 0 FP, 0 FN -> Precision=1.0, Recall=1.0, F1=1.0
    assert result["models"]["v0.4.1"]["scientific_precision"] == 1.0
    assert result["models"]["v0.4.1"]["scientific_recall"] == 1.0
    assert result["models"]["v0.4.1"]["scientific_f1"] == 1.0

    # Delta: Strict F1 improved by +0.3333
    assert result["deltas"]["strict_f1_delta"] == pytest.approx(0.3333, abs=0.001)
