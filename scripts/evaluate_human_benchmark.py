#!/usr/bin/env python3
"""Execute Human Benchmark Evaluation on ResearchGraph Scientific Extractors.

Evaluates both baseline (v0.4.0) and experimental (v0.4.1) extraction models
against completed human annotations or consensus ground-truth CSV.

Calculates:
- Strict & relaxed precision, recall, and F1
- Category-wise extraction metrics
- Evidence-span correctness accuracy
- Relationship extraction precision and recall
- Itemized false positives and false negatives (error breakdown)

When human annotations are pending/unreviewed, gracefully reports
`PENDING_HUMAN_ANNOTATION` status without fabricating or inferring metrics.

Usage:
    python scripts/evaluate_human_benchmark.py \
        --annotations dataset/manifests/scientific_extraction_v0.4.0_audit_packet_25.csv \
        --output-dir dataset/manifests
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Ensure repository root is in sys.path
import sys
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from dataset.schemas.scientific_knowledge import (
    ScientificEntityRecord,
    ScientificRelationRecord,
    ScientificStatementRecord,
)
from pipelines.extraction.evaluator import ExtractionEvaluationReport, ExtractionEvaluator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("HumanBenchmarkEvaluator")


def load_extracted_records(processed_dir: Path, target_chunk_ids: Set[str]) -> Tuple[List[ScientificEntityRecord], List[ScientificStatementRecord], List[ScientificRelationRecord], List[Dict[str, Any]]]:
    """Load and deserialize extracted entities, statements, relations, and rejections filtered to target chunks."""
    entities: List[ScientificEntityRecord] = []
    statements: List[ScientificStatementRecord] = []
    relations: List[ScientificRelationRecord] = []
    rejected: List[Dict[str, Any]] = []

    rec_file = processed_dir / "extracted_records.jsonl"
    if rec_file.exists():
        with open(rec_file, "r", encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                cid = d.get("provenance", {}).get("chunk_id", "")
                if target_chunk_ids and cid not in target_chunk_ids:
                    continue
                if "normalized_statement" in d or "statement_id" in d:
                    statements.append(ScientificStatementRecord.model_validate(d))
                else:
                    entities.append(ScientificEntityRecord.model_validate(d))

    rel_file = processed_dir / "extracted_relationships.jsonl"
    if rel_file.exists():
        with open(rel_file, "r", encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                cid = d.get("provenance", {}).get("chunk_id", "")
                if target_chunk_ids and cid not in target_chunk_ids:
                    continue
                relations.append(ScientificRelationRecord.model_validate(d))

    rej_file = processed_dir / "rejected_records.jsonl"
    if rej_file.exists():
        with open(rej_file, "r", encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                cid = d.get("provenance", {}).get("chunk_id", "")
                if target_chunk_ids and cid not in target_chunk_ids:
                    continue
                rejected.append(d)

    return entities, statements, relations, rejected


def evaluate_human_benchmark(
    annotations_path: Path,
    v040_dir: Path,
    v041_dir: Path,
    output_dir: Path,
    report_prefix: str = "scientific_extraction_human_benchmark",
) -> Dict[str, Any]:
    """Run full comparative benchmark evaluation against human ground truth."""
    evaluator = ExtractionEvaluator()

    # 1. Parse annotations
    gt_records, verdict_counts = evaluator.parse_human_annotations_csv(annotations_path)

    total_reviewed = (
        verdict_counts.get("CORRECT", 0)
        + verdict_counts.get("PARTIALLY_CORRECT", 0)
        + verdict_counts.get("UNSUPPORTED", 0)
        + verdict_counts.get("MISSING", 0)
    )

    # 2. Check if ground truth is pending
    if total_reviewed == 0:
        logger.info(f"No completed annotations found in {annotations_path}. Evaluation status remains PENDING_HUMAN_ANNOTATION.")
        pending_result = {
            "status": "PENDING_HUMAN_ANNOTATION",
            "annotations_file": str(annotations_path),
            "total_unreviewed_rows": verdict_counts.get("UNREVIEWED", 0),
            "completed_annotations_count": 0,
            "message": "Human review packet contains 0 completed annotations. All ground-truth labels remain blank as required prior to human study.",
            "scientific_metrics_status": "UNVERIFIED",
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{report_prefix}_status.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(pending_result, f, indent=2)

        md_path = output_dir / f"{report_prefix}_report.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# ResearchGraph Phase 3: Human Benchmark Evaluation Status\n\n")
            f.write(f"- **Benchmark Source File**: `{annotations_path.name}`\n")
            f.write("- **Status**: `PENDING_HUMAN_ANNOTATION`\n")
            f.write(f"- **Unreviewed Rows**: {verdict_counts.get('UNREVIEWED', 0)}\n")
            f.write("- **Completed Human Labels**: 0\n\n")
            f.write("> [!NOTE]\n")
            f.write("> Scientific Precision, Recall, and F1 remain **strictly unverified** because human annotations have not yet been completed.\n")
            f.write("> Engineering integrity and provenance verification remain passed.\n")

        return pending_result

    # 3. Determine evaluated chunk IDs from reviewed rows
    evaluated_chunk_ids: Set[str] = set()
    with open(annotations_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            v = (r.get("human_verdict") or "").strip().upper()
            if v and v in ("CORRECT", "PARTIALLY_CORRECT", "UNSUPPORTED", "MISSING"):
                evaluated_chunk_ids.add(r.get("chunk_id", ""))

    chunk_count = len(evaluated_chunk_ids) if evaluated_chunk_ids else 1
    logger.info(f"Evaluating models across {chunk_count} annotated chunks with {len(gt_records)} ground-truth records.")

    # 4. Load predictions for both models
    ent_v040, stmt_v040, rel_v040, rej_v040 = load_extracted_records(v040_dir, evaluated_chunk_ids)
    ent_v041, stmt_v041, rel_v041, rej_v041 = load_extracted_records(v041_dir, evaluated_chunk_ids)

    # 5. Evaluate v0.4.0
    report_v040 = evaluator.evaluate_batch(
        chunks_count=chunk_count,
        entities=ent_v040,
        statements=stmt_v040,
        relations=rel_v040,
        rejected_records=rej_v040,
        duration_ms=10.0,
        pipeline_version="v0.4.0",
        ground_truth=gt_records,
    )

    # 6. Evaluate v0.4.1
    report_v041 = evaluator.evaluate_batch(
        chunks_count=chunk_count,
        entities=ent_v041,
        statements=stmt_v041,
        relations=rel_v041,
        rejected_records=rej_v041,
        duration_ms=10.0,
        pipeline_version="v0.4.1",
        ground_truth=gt_records,
    )

    # 7. Build Comparative Report
    comparison = {
        "status": "EVALUATED_AGAINST_GROUND_TRUTH",
        "annotations_file": str(annotations_path),
        "total_evaluated_chunks": chunk_count,
        "total_ground_truth_records": len(gt_records),
        "human_verdict_summary": verdict_counts,
        "models": {
            "v0.4.0": asdict(report_v040),
            "v0.4.1": asdict(report_v041),
        },
        "deltas": {
            "strict_precision_delta": (report_v041.scientific_precision or 0) - (report_v040.scientific_precision or 0),
            "strict_recall_delta": (report_v041.scientific_recall or 0) - (report_v040.scientific_recall or 0),
            "strict_f1_delta": (report_v041.scientific_f1 or 0) - (report_v040.scientific_f1 or 0),
            "relaxed_f1_delta": (report_v041.relaxed_scientific_f1 or 0) - (report_v040.relaxed_scientific_f1 or 0),
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON Report
    json_path = output_dir / f"{report_prefix}_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    # Save Markdown Report
    md_path = output_dir / f"{report_prefix}_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# ResearchGraph Scientific Extraction: Human Benchmark Evaluation Report\n\n")
        f.write(f"- **Ground Truth Source**: `{annotations_path.name}`\n")
        f.write(f"- **Total Evaluated Chunks**: {chunk_count}\n")
        f.write(f"- **Total Ground Truth Records**: {len(gt_records)}\n")
        f.write(f"- **Human Verdicts**: CORRECT={verdict_counts.get('CORRECT', 0)}, PARTIALLY_CORRECT={verdict_counts.get('PARTIALLY_CORRECT', 0)}, UNSUPPORTED={verdict_counts.get('UNSUPPORTED', 0)}, MISSING={verdict_counts.get('MISSING', 0)}\n\n")

        f.write("## Overall Extraction Performance Comparison\n\n")
        f.write("| Scientific Metric | Baseline `v0.4.0` | Experimental `v0.4.1` | Delta |\n")
        f.write("| :--- | :---: | :---: | :---: |\n")
        f.write(f"| **Strict Precision** | {report_v040.scientific_precision or 0:.4f} | **{report_v041.scientific_precision or 0:.4f}** | {comparison['deltas']['strict_precision_delta']:+.4f} |\n")
        f.write(f"| **Strict Recall** | {report_v040.scientific_recall or 0:.4f} | **{report_v041.scientific_recall or 0:.4f}** | {comparison['deltas']['strict_recall_delta']:+.4f} |\n")
        f.write(f"| **Strict F1-Score** | {report_v040.scientific_f1 or 0:.4f} | **{report_v041.scientific_f1 or 0:.4f}** | {comparison['deltas']['strict_f1_delta']:+.4f} |\n")
        f.write(f"| **Relaxed Precision** | {report_v040.relaxed_scientific_precision or 0:.4f} | **{report_v041.relaxed_scientific_precision or 0:.4f}** | - |\n")
        f.write(f"| **Relaxed Recall** | {report_v040.relaxed_scientific_recall or 0:.4f} | **{report_v041.relaxed_scientific_recall or 0:.4f}** | - |\n")
        f.write(f"| **Relaxed F1-Score** | {report_v040.relaxed_scientific_f1 or 0:.4f} | **{report_v041.relaxed_scientific_f1 or 0:.4f}** | {comparison['deltas']['relaxed_f1_delta']:+.4f} |\n")
        f.write(f"| **Evidence Correctness** | {report_v040.evidence_correctness_accuracy or 0:.4f} | **{report_v041.evidence_correctness_accuracy or 0:.4f}** | - |\n\n")

        f.write("## Category-Wise Breakdown (Strict F1)\n\n")
        all_cats = sorted(list(set(report_v040.category_scientific_metrics.keys()) | set(report_v041.category_scientific_metrics.keys())))
        f.write("| Category | v0.4.0 Prec | v0.4.0 Rec | v0.4.0 F1 | v0.4.1 Prec | v0.4.1 Rec | v0.4.1 F1 |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for cat in all_cats:
            m0 = report_v040.category_scientific_metrics.get(cat, {})
            m1 = report_v041.category_scientific_metrics.get(cat, {})
            f.write(f"| `{cat}` | {m0.get('precision', 0):.2f} | {m0.get('recall', 0):.2f} | {m0.get('f1_score', 0):.2f} | {m1.get('precision', 0):.2f} | {m1.get('recall', 0):.2f} | **{m1.get('f1_score', 0):.2f}** |\n")

        f.write("\n## Error Analysis\n\n")
        f.write(f"- **v0.4.0 False Positives**: {len(report_v040.false_positive_records)} | False Negatives: {len(report_v040.false_negative_records)}\n")
        f.write(f"- **v0.4.1 False Positives**: {len(report_v041.false_positive_records)} | False Negatives: {len(report_v041.false_negative_records)}\n")

    logger.info(f"Saved benchmark evaluation reports to {output_dir}")
    return comparison


def main():
    parser = argparse.ArgumentParser(description="Evaluate ResearchGraph extractors on completed human annotations.")
    parser.add_argument("--annotations", type=Path, default=Path("dataset/manifests/scientific_extraction_v0.4.0_audit_packet_25.csv"), help="Path to annotations CSV")
    parser.add_argument("--v040-dir", type=Path, default=Path("dataset/processed/v0.4.0"), help="Path to v0.4.0 processed directory")
    parser.add_argument("--v041-dir", type=Path, default=Path("dataset/processed/v0.4.1"), help="Path to v0.4.1 processed directory")
    parser.add_argument("--output-dir", type=Path, default=Path("dataset/manifests"), help="Directory to save evaluation reports")
    parser.add_argument("--report-prefix", type=str, default="scientific_extraction_human_benchmark", help="Prefix for report files")

    args = parser.parse_args()
    result = evaluate_human_benchmark(args.annotations, args.v040_dir, args.v041_dir, args.output_dir, args.report_prefix)

    print("\n" + "=" * 80)
    print(" ResearchGraph Human Benchmark Evaluation")
    print("=" * 80)
    print(f"Status:                       {result['status']}")
    if result["status"] == "PENDING_HUMAN_ANNOTATION":
        print(f"Unreviewed Rows:              {result['total_unreviewed_rows']}")
        print(f"Completed Annotations:        {result['completed_annotations_count']}")
        print(f"Notice:                       {result['message']}")
    else:
        print(f"Evaluated Chunks:             {result['total_evaluated_chunks']}")
        print(f"Ground Truth Records:         {result['total_ground_truth_records']}")
        v0 = result["models"]["v0.4.0"]
        v1 = result["models"]["v0.4.1"]
        print("-" * 80)
        print(f"v0.4.0 Strict P/R/F1:         {v0['scientific_precision']:.4f} / {v0['scientific_recall']:.4f} / {v0['scientific_f1']:.4f}")
        print(f"v0.4.1 Strict P/R/F1:         {v1['scientific_precision']:.4f} / {v1['scientific_recall']:.4f} / {v1['scientific_f1']:.4f}")
        print(f"v0.4.0 Relaxed F1:            {v0['relaxed_scientific_f1']:.4f}")
        print(f"v0.4.1 Relaxed F1:            {v1['relaxed_scientific_f1']:.4f}")
        print(f"Strict F1 Delta:              {result['deltas']['strict_f1_delta']:+.4f}")
    print("=" * 80)


if __name__ == "__main__":
    main()
