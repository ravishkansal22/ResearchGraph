"""Unit Tests for Scientific Extraction Evaluator with Ground-Truth Metrics."""

from __future__ import annotations

import pytest

from dataset.schemas.document_processing import ChunkStrategy, ProcessedChunk
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
from pipelines.extraction.evaluator import ExtractionEvaluator


@pytest.fixture
def evaluator() -> ExtractionEvaluator:
    return ExtractionEvaluator()


def test_evaluator_strict_and_category_metrics(evaluator):
    # Predictions
    pred_entities = [
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
            category=ScientificEntityType.PROBLEM,
            surface_text="Intrusion Detection",
            normalized_name="intrusion detection",
            evidence=EvidenceSpan(text="Intrusion Detection", start_char=5, end_char=24),
            provenance=ExtractionProvenance(canonical_id="paper_1", chunk_id="chk_01"),
        ),
        # False positive prediction
        ScientificEntityRecord(
            record_id="ent_03",
            category=ScientificEntityType.METRIC,
            surface_text="Latency",
            normalized_name="latency",
            evidence=EvidenceSpan(text="Latency", start_char=25, end_char=32),
            provenance=ExtractionProvenance(canonical_id="paper_1", chunk_id="chk_01"),
        ),
    ]

    # Ground truth: 2 entities (LSTM, Intrusion Detection), plus 1 missed entity (NSL-KDD)
    ground_truth = [
        {"chunk_id": "chk_01", "category": "METHOD", "normalized_text": "lstm", "evidence_span": "lstm"},
        {"chunk_id": "chk_01", "category": "PROBLEM", "normalized_text": "intrusion detection", "evidence_span": "intrusion detection"},
        {"chunk_id": "chk_01", "category": "DATASET", "normalized_text": "nsl-kdd", "evidence_span": "nsl-kdd"},
    ]

    report = evaluator.evaluate_batch(
        chunks_count=1,
        entities=pred_entities,
        statements=[],
        relations=[],
        rejected_records=[],
        duration_ms=10.0,
        ground_truth=ground_truth,
    )

    # 2 TP, 1 FP, 1 FN
    # Precision = 2 / 3 = 0.6667
    # Recall = 2 / 3 = 0.6667
    # F1 = 0.6667
    assert report.ground_truth_status == "EVALUATED_AGAINST_GROUND_TRUTH"
    assert report.scientific_precision == 0.6667
    assert report.scientific_recall == 0.6667
    assert report.scientific_f1 == 0.6667

    # Category-wise metrics
    assert "METHOD" in report.category_scientific_metrics
    assert report.category_scientific_metrics["METHOD"]["precision"] == 1.0
    assert report.category_scientific_metrics["METHOD"]["recall"] == 1.0
    assert report.category_scientific_metrics["METHOD"]["f1_score"] == 1.0

    assert "PROBLEM" in report.category_scientific_metrics
    assert report.category_scientific_metrics["PROBLEM"]["f1_score"] == 1.0

    assert "DATASET" in report.category_scientific_metrics
    assert report.category_scientific_metrics["DATASET"]["recall"] == 0.0  # Missed (FN)

    assert "METRIC" in report.category_scientific_metrics
    assert report.category_scientific_metrics["METRIC"]["precision"] == 0.0  # Spurious (FP)


def test_evaluator_relaxed_matching_partial_credit(evaluator):
    # Pred: "convolutional neural network"
    # GT: "convolutional neural networks (CNN)"
    pred_entities = [
        ScientificEntityRecord(
            record_id="ent_01",
            category=ScientificEntityType.METHOD,
            surface_text="convolutional neural network",
            normalized_name="convolutional neural network",
            evidence=EvidenceSpan(text="convolutional neural network", start_char=0, end_char=28),
            provenance=ExtractionProvenance(canonical_id="paper_1", chunk_id="chk_01"),
        )
    ]

    ground_truth = [
        {
            "chunk_id": "chk_01",
            "category": "METHOD",
            "normalized_text": "convolutional neural networks (cnn)",
            "evidence_span": "convolutional neural networks (cnn)",
        }
    ]

    report = evaluator.evaluate_batch(
        chunks_count=1,
        entities=pred_entities,
        statements=[],
        relations=[],
        rejected_records=[],
        duration_ms=10.0,
        ground_truth=ground_truth,
    )

    # In strict mode: 0 TP because string does not match exactly
    assert report.scientific_precision == 0.0
    assert report.scientific_recall == 0.0

    # In relaxed mode: 1 TP because token overlap is >= 0.5
    assert report.relaxed_scientific_precision == 1.0
    assert report.relaxed_scientific_recall == 1.0
    assert report.relaxed_scientific_f1 == 1.0


def test_evaluator_evidence_correctness(evaluator):
    pred_entities = [
        ScientificEntityRecord(
            record_id="ent_01",
            category=ScientificEntityType.METHOD,
            surface_text="LSTM",
            normalized_name="lstm",
            evidence=EvidenceSpan(text="LSTM model", start_char=0, end_char=10),
            provenance=ExtractionProvenance(canonical_id="paper_1", chunk_id="chk_01"),
        )
    ]

    ground_truth = [
        {"chunk_id": "chk_01", "category": "METHOD", "normalized_text": "lstm", "evidence_span": "lstm"}
    ]

    report = evaluator.evaluate_batch(
        chunks_count=1,
        entities=pred_entities,
        statements=[],
        relations=[],
        rejected_records=[],
        duration_ms=5.0,
        ground_truth=ground_truth,
    )

    # Evidence overlap matches ("lstm" is in "lstm model")
    assert report.evidence_correctness_accuracy == 1.0


def test_evaluator_relationship_metrics(evaluator):
    pred_relations = [
        ScientificRelationRecord(
            relation_id="rel_01",
            relation_type=ScientificRelationType.ADDRESSES,
            source_id="ent_01",
            target_id="ent_02",
            source_category="METHOD",
            target_category="PROBLEM",
            evidence=EvidenceSpan(text="LSTM addresses anomaly detection", start_char=0, end_char=32),
            provenance=ExtractionProvenance(canonical_id="paper_1", chunk_id="chk_01"),
        )
    ]

    ground_truth = [
        {
            "chunk_id": "chk_01",
            "category": "ADDRESSES",
            "normalized_text": "addresses",
            "source": "ent_01",
            "target": "ent_02",
        }
    ]

    report = evaluator.evaluate_batch(
        chunks_count=1,
        entities=[],
        statements=[],
        relations=pred_relations,
        rejected_records=[],
        duration_ms=5.0,
        ground_truth=ground_truth,
    )

    rel_metrics = report.relation_extraction_metrics
    assert rel_metrics["true_positives"] == 1
    assert rel_metrics["precision"] == 1.0
    assert rel_metrics["recall"] == 1.0
    assert rel_metrics["f1_score"] == 1.0


def test_evaluator_unreviewed_annotations_pending(evaluator, tmp_path):
    """Verify unpopulated human review CSV returns PENDING_HUMAN_ANNOTATION."""
    csv_file = tmp_path / "blank_review.csv"
    csv_file.write_text(
        "packet_index,chunk_id,canonical_id,section_title,section_bucket,has_system_output,audit_investigation_goal,chunk_text,system_record_type,system_predicted_category,system_predicted_surface_text,system_evidence_span,human_ground_truth_category,human_ground_truth_normalized_text,human_ground_truth_evidence_span,human_attribution,human_verdict,human_reviewer_comments\n"
        "1,chk_01,paper_1,Abstract,ABSTRACT,True,Goal,Text,ENTITY,METHOD,LSTM,LSTM,,,,,\n"
        "2,chk_02,paper_2,Methods,METHODS,False,Goal,Text,ADD_MISSING,,,,,,\n",
        encoding="utf-8",
    )

    gt_records, verdict_counts = evaluator.parse_human_annotations_csv(csv_file)
    assert len(gt_records) == 0
    assert verdict_counts["UNREVIEWED"] == 2

    # Evaluator report remains PENDING_HUMAN_ANNOTATION
    report = evaluator.evaluate_batch(
        chunks_count=2,
        entities=[],
        statements=[],
        relations=[],
        rejected_records=[],
        duration_ms=5.0,
        ground_truth=gt_records,
    )
    assert report.ground_truth_status == "PENDING_HUMAN_ANNOTATION"
    assert report.scientific_precision is None
    assert report.scientific_recall is None


def test_evaluator_parse_synthetic_human_annotations(evaluator, tmp_path):
    """Verify synthetic completed human annotations produce verified metrics and error categorization."""
    csv_file = tmp_path / "synthetic_reviewed_audit_packet.csv"
    # Create synthetic completed review packet
    # Row 1: Prediction CORRECT (METHOD: LSTM)
    # Row 2: Prediction UNSUPPORTED (METRIC: latency) -> counts as FP
    # Row 3: Missed extraction added by reviewer (DATASET: NSL-KDD) -> counts as FN
    csv_file.write_text(
        "packet_index,chunk_id,canonical_id,section_title,section_bucket,has_system_output,audit_investigation_goal,chunk_text,system_record_type,system_predicted_category,system_predicted_surface_text,system_evidence_span,human_ground_truth_category,human_ground_truth_normalized_text,human_ground_truth_evidence_span,human_attribution,human_verdict,human_reviewer_comments\n"
        "1,chk_01,paper_1,Abstract,ABSTRACT,True,Goal,Text,ENTITY,METHOD,LSTM,LSTM,,,,,CORRECT,Verified\n"
        "1,chk_01,paper_1,Abstract,ABSTRACT,True,Goal,Text,ENTITY,METRIC,latency,latency,,,,,UNSUPPORTED,Not a metric\n"
        "1,chk_01,paper_1,Abstract,ABSTRACT,True,Goal,Text,ADD_MISSING,,,,DATASET,NSL-KDD,NSL-KDD,AUTHOR_STATED,MISSING,Missed dataset\n",
        encoding="utf-8",
    )

    gt_records, verdict_counts = evaluator.parse_human_annotations_csv(csv_file)
    assert len(gt_records) == 2  # 1 from CORRECT, 1 from MISSING
    assert verdict_counts["CORRECT"] == 1
    assert verdict_counts["UNSUPPORTED"] == 1
    assert verdict_counts["MISSING"] == 1

    # Now evaluate predictions against parsed ground truth
    pred_entities = [
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
            category=ScientificEntityType.METRIC,
            surface_text="latency",
            normalized_name="latency",
            evidence=EvidenceSpan(text="latency", start_char=10, end_char=17),
            provenance=ExtractionProvenance(canonical_id="paper_1", chunk_id="chk_01"),
        ),
    ]

    report = evaluator.evaluate_batch(
        chunks_count=1,
        entities=pred_entities,
        statements=[],
        relations=[],
        rejected_records=[],
        duration_ms=5.0,
        ground_truth=gt_records,
    )

    # 1 TP (LSTM), 1 FP (latency), 1 FN (NSL-KDD)
    assert report.ground_truth_status == "EVALUATED_AGAINST_GROUND_TRUTH"
    assert report.scientific_precision == 0.5
    assert report.scientific_recall == 0.5
    assert report.scientific_f1 == 0.5

    # Verify False Positive & False Negative Itemization
    assert len(report.false_positive_records) == 1
    assert report.false_positive_records[0]["normalized_text"] == "latency"
    assert report.false_positive_records[0]["category"] == "METRIC"

    assert len(report.false_negative_records) == 1
    assert report.false_negative_records[0]["normalized_text"] == "nsl-kdd"
    assert report.false_negative_records[0]["category"] == "DATASET"

    # Verify Common Error Breakdown
    assert report.common_error_categories["SPURIOUS_METRIC"] == 1
    assert report.common_error_categories["MISSED_DATASET"] == 1

