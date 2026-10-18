#!/usr/bin/env python3
"""Reconcile and Adjudicate Independent Dual-Reviewer Scientific Extraction Annotations.

Calculates Inter-Annotator Agreement (Observed Agreement Rate & Cohen's Kappa),
identifies concordant vs discordant annotations, and outputs an adjudicated consensus CSV
ready for evaluation.

Usage:
    python scripts/reconcile_human_annotations.py \
        --reviewer1 dataset/manifests/scientific_extraction_v0.4.0_audit_packet_reviewer1.csv \
        --reviewer2 dataset/manifests/scientific_extraction_v0.4.0_audit_packet_reviewer2.csv \
        --output-consensus dataset/manifests/scientific_extraction_benchmark_consensus_25.csv \
        --output-report dataset/manifests/scientific_extraction_adjudication_report.md
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AnnotationReconciler")


def compute_cohens_kappa(
    verdicts_r1: List[str],
    verdicts_r2: List[str],
    categories: List[str],
) -> Tuple[float, float, float]:
    """Compute Observed Agreement (Po), Chance Agreement (Pe), and Cohen's Kappa."""
    n = len(verdicts_r1)
    if n == 0:
        return 0.0, 0.0, 0.0

    agreed = sum(1 for v1, v2 in zip(verdicts_r1, verdicts_r2) if v1 == v2)
    po = agreed / n

    # Marginals
    count_r1: Dict[str, int] = {c: 0 for c in categories}
    count_r2: Dict[str, int] = {c: 0 for c in categories}

    for v1, v2 in zip(verdicts_r1, verdicts_r2):
        if v1 in count_r1:
            count_r1[v1] += 1
        if v2 in count_r2:
            count_r2[v2] += 1

    pe = sum((count_r1[c] / n) * (count_r2[c] / n) for c in categories)

    if pe >= 1.0:
        kappa = 1.0 if po >= 1.0 else 0.0
    else:
        kappa = (po - pe) / (1.0 - pe)

    return round(po, 4), round(pe, 4), round(kappa, 4)


def reconcile_reviewers(
    r1_path: Path,
    r2_path: Path,
    output_consensus_path: Optional[Path] = None,
    output_report_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Reconcile two independent review packets and produce consensus CSV and report."""
    with open(r1_path, "r", encoding="utf-8") as f1, open(r2_path, "r", encoding="utf-8") as f2:
        rows_r1 = list(csv.DictReader(f1))
        rows_r2 = list(csv.DictReader(f2))

    if len(rows_r1) != len(rows_r2):
        raise ValueError(f"Packet row count mismatch: Reviewer 1 ({len(rows_r1)}) vs Reviewer 2 ({len(rows_r2)})")

    total_rows = len(rows_r1)
    valid_verdicts = ["CORRECT", "PARTIALLY_CORRECT", "UNSUPPORTED", "MISSING"]

    paired_v1: List[str] = []
    paired_v2: List[str] = []
    concordant_rows: List[Dict[str, Any]] = []
    discordant_rows: List[Dict[str, Any]] = []
    unreviewed_rows: List[Dict[str, Any]] = []

    consensus_rows: List[Dict[str, Any]] = []

    for idx, (r1, r2) in enumerate(zip(rows_r1, rows_r2), 1):
        v1 = (r1.get("human_verdict") or "").strip().upper()
        v2 = (r2.get("human_verdict") or "").strip().upper()

        cid = r1.get("chunk_id", "")
        pidx = r1.get("packet_index", str(idx))
        sys_type = r1.get("system_record_type", "")
        sys_cat = r1.get("system_predicted_category", "")
        sys_surf = r1.get("system_predicted_surface_text", "")

        is_r1_reviewed = bool(v1 and v1 in valid_verdicts)
        is_r2_reviewed = bool(v2 and v2 in valid_verdicts)

        consensus_row = dict(r1)  # Base copy of metadata
        consensus_row["reviewer_id"] = "consensus_adjudicated"

        if not is_r1_reviewed and not is_r2_reviewed:
            unreviewed_rows.append({
                "row_index": idx,
                "packet_index": pidx,
                "chunk_id": cid,
                "system_record_type": sys_type,
                "status": "UNREVIEWED_BY_BOTH",
            })
            consensus_row["human_verdict"] = ""
            consensus_row["human_reviewer_comments"] = ""
            consensus_rows.append(consensus_row)
            continue

        if is_r1_reviewed != is_r2_reviewed:
            discordant_rows.append({
                "row_index": idx,
                "packet_index": pidx,
                "chunk_id": cid,
                "discrepancy_type": "SINGLE_REVIEWER_COMPLETED",
                "reviewer1_verdict": v1 or "UNREVIEWED",
                "reviewer2_verdict": v2 or "UNREVIEWED",
                "system_predicted_category": sys_cat,
                "system_predicted_surface_text": sys_surf,
                "details": f"Reviewer 1={'REVIEWED' if is_r1_reviewed else 'BLANK'}, Reviewer 2={'REVIEWED' if is_r2_reviewed else 'BLANK'}",
            })
            consensus_row["human_verdict"] = "NEEDS_ADJUDICATION"
            consensus_row["human_reviewer_comments"] = f"[NEEDS_ADJUDICATION] Rev1: {v1 or 'BLANK'} | Rev2: {v2 or 'BLANK'}"
            consensus_rows.append(consensus_row)
            continue

        # Both reviewed
        paired_v1.append(v1)
        paired_v2.append(v2)

        # Check verdict agreement
        if v1 == v2:
            # Check attribute agreement for PARTIALLY_CORRECT or MISSING
            cat1 = (r1.get("human_ground_truth_category") or sys_cat).strip().upper()
            cat2 = (r2.get("human_ground_truth_category") or sys_cat).strip().upper()
            norm1 = (r1.get("human_ground_truth_normalized_text") or sys_surf).strip().lower()
            norm2 = (r2.get("human_ground_truth_normalized_text") or sys_surf).strip().lower()

            if v1 in ("CORRECT", "UNSUPPORTED") or (cat1 == cat2 and norm1 == norm2):
                concordant_rows.append({
                    "row_index": idx,
                    "packet_index": pidx,
                    "chunk_id": cid,
                    "verdict": v1,
                    "category": cat1,
                    "normalized_text": norm1,
                })
                consensus_row["human_verdict"] = v1
                consensus_row["human_ground_truth_category"] = r1.get("human_ground_truth_category") or r2.get("human_ground_truth_category", "")
                consensus_row["human_ground_truth_normalized_text"] = r1.get("human_ground_truth_normalized_text") or r2.get("human_ground_truth_normalized_text", "")
                consensus_row["human_ground_truth_evidence_span"] = r1.get("human_ground_truth_evidence_span") or r2.get("human_ground_truth_evidence_span", "")
                consensus_row["human_attribution"] = r1.get("human_attribution") or r2.get("human_attribution") or "AUTHOR_STATED"
                consensus_row["human_reviewer_comments"] = f"[AGREED] Rev1: {r1.get('human_reviewer_comments', '')} | Rev2: {r2.get('human_reviewer_comments', '')}".strip()
            else:
                discordant_rows.append({
                    "row_index": idx,
                    "packet_index": pidx,
                    "chunk_id": cid,
                    "discrepancy_type": "CATEGORY_OR_SPAN_DISAGREEMENT",
                    "reviewer1_verdict": f"{v1} ({cat1}: {norm1})",
                    "reviewer2_verdict": f"{v2} ({cat2}: {norm2})",
                    "system_predicted_category": sys_cat,
                    "system_predicted_surface_text": sys_surf,
                    "details": f"Rev1 Category='{cat1}', Rev2 Category='{cat2}'",
                })
                consensus_row["human_verdict"] = "NEEDS_ADJUDICATION"
                consensus_row["human_reviewer_comments"] = f"[NEEDS_ADJUDICATION_ATTRIBUTES] Rev1: {cat1} '{norm1}' vs Rev2: {cat2} '{norm2}'"
        else:
            discordant_rows.append({
                "row_index": idx,
                "packet_index": pidx,
                "chunk_id": cid,
                "discrepancy_type": "VERDICT_DISAGREEMENT",
                "reviewer1_verdict": v1,
                "reviewer2_verdict": v2,
                "system_predicted_category": sys_cat,
                "system_predicted_surface_text": sys_surf,
                "details": f"Reviewer 1 marked '{v1}', Reviewer 2 marked '{v2}'",
            })
            consensus_row["human_verdict"] = "NEEDS_ADJUDICATION"
            consensus_row["human_reviewer_comments"] = f"[NEEDS_ADJUDICATION_VERDICT] Rev1: {v1} vs Rev2: {v2}"

        consensus_rows.append(consensus_row)

    # Compute Agreement Statistics
    both_reviewed_count = len(paired_v1)
    if both_reviewed_count > 0:
        po, pe, kappa = compute_cohens_kappa(paired_v1, paired_v2, valid_verdicts)
    else:
        po, pe, kappa = 0.0, 0.0, 0.0

    full_concordance_rate = (len(concordant_rows) / both_reviewed_count) if both_reviewed_count > 0 else 0.0

    summary = {
        "total_rows": total_rows,
        "both_reviewed_count": both_reviewed_count,
        "concordant_count": len(concordant_rows),
        "discordant_count": len(discordant_rows),
        "unreviewed_count": len(unreviewed_rows),
        "observed_agreement_rate": po,
        "full_concordance_rate": round(full_concordance_rate, 4),
        "expected_chance_agreement": pe,
        "cohens_kappa": kappa,
        "reviewer1_reviewed_count": sum(1 for r in rows_r1 if (r.get("human_verdict") or "").strip().upper() in valid_verdicts),
        "reviewer2_reviewed_count": sum(1 for r in rows_r2 if (r.get("human_verdict") or "").strip().upper() in valid_verdicts),
    }

    # Save Consensus CSV if path provided
    if output_consensus_path:
        output_consensus_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [k for k in consensus_rows[0].keys() if k is not None] if consensus_rows else []
        with open(output_consensus_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(consensus_rows)
        logger.info(f"Saved consensus template CSV to {output_consensus_path}")

    # Generate Markdown Report if path provided
    if output_report_path:
        output_report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_report_path, "w", encoding="utf-8") as f:
            f.write("# ResearchGraph Human Annotation Reconciliation & Adjudication Report\n\n")
            f.write(f"- **Reviewer 1 Packet**: `{r1_path.name}` ({summary['reviewer1_reviewed_count']} reviewed)\n")
            f.write(f"- **Reviewer 2 Packet**: `{r2_path.name}` ({summary['reviewer2_reviewed_count']} reviewed)\n")
            f.write(f"- **Total Rows Evaluated**: {total_rows}\n")
            f.write(f"- **Dual-Reviewed Rows**: {both_reviewed_count}\n")
            f.write(f"- **Concordant (Agreed) Rows**: {summary['concordant_count']}\n")
            f.write(f"- **Discordant (Discrepant) Rows**: {summary['discordant_count']}\n")
            f.write(f"- **Observed Agreement Rate**: {po * 100:.2f}%\n")
            f.write(f"- **Cohen's Kappa (kappa)**: **{kappa:.4f}**\n\n")

            if discordant_rows:
                f.write("## Discrepancies Requiring Adjudication\n\n")
                f.write("| Row | Packet Index | Chunk ID | Discrepancy Type | Reviewer 1 | Reviewer 2 | Target Text / Details |\n")
                f.write("| :---: | :---: | :--- | :--- | :--- | :--- | :--- |\n")
                for d in discordant_rows:
                    f.write(f"| {d['row_index']} | {d['packet_index']} | `{d['chunk_id']}` | {d['discrepancy_type']} | `{d['reviewer1_verdict']}` | `{d['reviewer2_verdict']}` | {d['details']} |\n")
            else:
                f.write("## Discrepancies Requiring Adjudication\n\n*No discrepancies detected. Annotations are unanimous or pending.*\n")

        logger.info(f"Saved adjudication report to {output_report_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Reconcile independent dual-reviewer annotations.")
    parser.add_argument("--reviewer1", type=Path, required=True, help="Path to Reviewer 1 CSV packet")
    parser.add_argument("--reviewer2", type=Path, required=True, help="Path to Reviewer 2 CSV packet")
    parser.add_argument("--output-consensus", type=Path, default=Path("dataset/manifests/scientific_extraction_benchmark_consensus_25.csv"), help="Output path for reconciled consensus CSV")
    parser.add_argument("--output-report", type=Path, default=Path("dataset/manifests/scientific_extraction_adjudication_report.md"), help="Output path for adjudication report")

    args = parser.parse_args()
    summary = reconcile_reviewers(args.reviewer1, args.reviewer2, args.output_consensus, args.output_report)

    print("\n" + "=" * 80)
    print(" Annotation Reconciliation Summary")
    print("=" * 80)
    print(f"Total Rows:                   {summary['total_rows']}")
    print(f"Reviewer 1 Completed:         {summary['reviewer1_reviewed_count']}")
    print(f"Reviewer 2 Completed:         {summary['reviewer2_reviewed_count']}")
    print(f"Dual-Reviewed Rows:           {summary['both_reviewed_count']}")
    print(f"Concordant Rows:              {summary['concordant_count']}")
    print(f"Discordant Rows:              {summary['discordant_count']}")
    print(f"Observed Agreement Rate:      {summary['observed_agreement_rate'] * 100:.2f}%")
    print(f"Cohen's Kappa (kappa):        {summary['cohens_kappa']:.4f}")
    print("=" * 80)


if __name__ == "__main__":
    main()
