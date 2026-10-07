#!/usr/bin/env python3
"""Run query-driven on-demand full-text acquisition pilot (v0.1.2 experiment).

Tests the metadata-first candidate retrieval and on-demand acquisition strategy
on a small, representative sample of 20-30 papers from the v0.1.1 corpus.
Measures storage, download performance, PDF validity, and basic parseability.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Ensure repository root is in sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from dataset.schemas.canonical_paper import (
    AcquisitionResult,
    CanonicalPaper,
    DocumentProcessingStatus,
    FullTextAcquisitionStatus,
    PDFValidationStatus,
)
from pipelines.ingestion.config import config
from pipelines.ingestion.fulltext.acquirer import OnDemandFullTextAcquirer
from pipelines.ingestion.fulltext.retrieval import MetadataCandidateRetriever
from pipelines.ingestion.fulltext.validator import PDFValidator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_v011_papers() -> List[CanonicalPaper]:
    jsonl_path = config.processed_dir / "v0.1.1" / "canonical_papers.jsonl"
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Canonical v0.1.1 dataset not found at {jsonl_path}")
    papers: List[CanonicalPaper] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                papers.append(CanonicalPaper(**json.loads(line)))
    return papers


def get_dir_size_bytes(directory: Path) -> int:
    if not directory.exists():
        return 0
    total = 0
    for root, _, files in os.walk(directory):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    return total


def select_pilot_sample(
    papers: List[CanonicalPaper],
    retriever: MetadataCandidateRetriever,
    target_count: int = 25,
) -> List[Tuple[CanonicalPaper, str, float]]:
    """Select a mixed, realistic sample of ~25 candidate papers via queries + diverse fallbacks."""
    queries = [
        "deep learning neural networks in medical diagnosis and healthcare",
        "machine learning algorithms for cybersecurity threat detection",
        "artificial intelligence ethics privacy and sustainability",
    ]

    selected_ids: Set[str] = set()
    sampled_candidates: List[Tuple[CanonicalPaper, str, float]] = []

    # 1. Retrieve candidates for each query
    for q in queries:
        candidates = retriever.retrieve_candidates(papers, q, top_k=7)
        for p, score, _ in candidates:
            if p.canonical_id not in selected_ids:
                selected_ids.add(p.canonical_id)
                sampled_candidates.append((p, f"Query: '{q[:35]}...'", score))

    # 2. Add deliberately varied edge cases to test diverse document types and source origins
    # - Direct PDF URL
    direct_pdf_papers = [
        p for p in papers
        if p.canonical_id not in selected_ids
        and p.open_access
        and p.open_access.oa_url
        and (p.open_access.oa_url.endswith(".pdf") or "pdf" in p.open_access.oa_url.lower())
    ]
    for p in direct_pdf_papers[:3]:
        selected_ids.add(p.canonical_id)
        sampled_candidates.append((p, "Direct PDF URL Edge Case", 0.90))

    # - Repository URLs (e.g. Zenodo, OSF, SSRN)
    repo_papers = [
        p for p in papers
        if p.canonical_id not in selected_ids
        and p.open_access
        and p.open_access.oa_url
        and any(r in p.open_access.oa_url.lower() for r in ["zenodo", "osf", "ssrn"])
    ]
    for p in repo_papers[:3]:
        selected_ids.add(p.canonical_id)
        sampled_candidates.append((p, "Repository URL Edge Case", 0.85))

    # - Unavailable / Paywalled Book Chapters (to test clean UNAVAILABLE handling)
    unavailable_papers = [
        p for p in papers
        if p.canonical_id not in selected_ids
        and p.document_type.value == "BOOK_CHAPTER"
        and (not p.open_access or not p.open_access.oa_url)
    ]
    for p in unavailable_papers[:3]:
        selected_ids.add(p.canonical_id)
        sampled_candidates.append((p, "Paywalled Book Chapter Edge Case", 0.70))

    return sampled_candidates[:target_count]


def run_experiment() -> None:
    logger.info("=== Starting Query-Driven Full-Text Acquisition Pilot (v0.1.2) ===")
    papers = load_v011_papers()
    logger.info(f"Loaded {len(papers)} canonical papers from v0.1.1.")

    retriever = MetadataCandidateRetriever()
    cache_dir = config.fulltext_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    storage_before = get_dir_size_bytes(cache_dir)

    pilot_sample = select_pilot_sample(papers, retriever, target_count=25)
    logger.info(f"Selected {len(pilot_sample)} pilot candidate papers across queries and document types.")

    acquirer = OnDemandFullTextAcquirer(cache_dir=cache_dir)
    results: List[AcquisitionResult] = []
    updated_papers: List[CanonicalPaper] = []

    start_pilot_time = time.time()

    for idx, (paper, reason, score) in enumerate(pilot_sample, 1):
        logger.info(f"[{idx}/{len(pilot_sample)}] Processing: {paper.canonical_id} | Type: {paper.document_type.value} | Reason: {reason}")
        up_paper, res = acquirer.fetch_paper(paper)
        res.notes = f"{reason} (Score: {score:.2f}) | {res.notes or ''}".strip()
        results.append(res)
        updated_papers.append(up_paper)
        # Polite throttling between requests
        time.sleep(0.4)

    total_pilot_duration = round(time.time() - start_pilot_time, 2)
    storage_after = get_dir_size_bytes(cache_dir)
    total_storage_used = storage_after - storage_before

    # Verify Idempotency on 1 downloaded paper (if any succeeded)
    downloaded_samples = [p for p in updated_papers if p.fulltext_status == FullTextAcquisitionStatus.DOWNLOADED]
    idempotency_tested = False
    idempotency_success = False
    if downloaded_samples:
        test_p = downloaded_samples[0]
        logger.info(f"Testing cache hit / idempotency on {test_p.canonical_id}...")
        _, second_res = acquirer.fetch_paper(test_p, force_redownload=False)
        idempotency_tested = True
        idempotency_success = "local cache" in (second_res.notes or "")
        logger.info(f"Idempotency result: {second_res.notes} (Success: {idempotency_success})")

    acquirer.close()

    # Aggregate Statistics
    total_attempted = len(results)
    downloaded_count = sum(1 for r in results if r.download_success)
    valid_pdf_count = sum(1 for r in results if r.is_valid_pdf)
    unavailable_count = sum(1 for r in results if r.validation_status == PDFValidationStatus.UNAVAILABLE)
    failed_count = sum(1 for r in results if not r.download_success and r.validation_status != PDFValidationStatus.UNAVAILABLE)
    parsed_count = sum(1 for r in results if r.parse_success)

    file_sizes = [r.file_size_bytes for r in results if r.is_valid_pdf and r.file_size_bytes > 0]
    avg_size = (sum(file_sizes) / len(file_sizes)) if file_sizes else 0
    median_size = sorted(file_sizes)[len(file_sizes) // 2] if file_sizes else 0
    largest_size = max(file_sizes) if file_sizes else 0
    smallest_size = min(file_sizes) if file_sizes else 0

    # Source breakdown
    source_counts: Dict[str, int] = {}
    validation_breakdown: Dict[str, int] = {}
    for r in results:
        src = r.source_type or "none"
        source_counts[src] = source_counts.get(src, 0) + 1
        v_stat = r.validation_status.value
        validation_breakdown[v_stat] = validation_breakdown.get(v_stat, 0) + 1

    # 1. Export CSV
    csv_path = config.manifests_dir / "fulltext_pilot_v0.1.2_results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "canonical_id",
            "title",
            "document_type",
            "source",
            "source_type",
            "fulltext_url",
            "http_status",
            "download_success",
            "file_size_bytes",
            "download_time_seconds",
            "mime_type",
            "file_hash_sha256",
            "is_valid_pdf",
            "validation_status",
            "parse_attempted",
            "parse_success",
            "extracted_pages",
            "extracted_char_count",
            "parse_error",
            "notes",
        ])
        for r in results:
            writer.writerow([
                r.canonical_id,
                r.title,
                r.document_type.value,
                r.source,
                r.source_type or "",
                r.fulltext_url or "",
                r.http_status or "",
                r.download_success,
                r.file_size_bytes,
                r.download_time_seconds,
                r.mime_type or "",
                r.file_hash or "",
                r.is_valid_pdf,
                r.validation_status.value,
                r.parse_attempted,
                r.parse_success,
                r.extracted_pages or 0,
                r.extracted_char_count or 0,
                r.parse_error or "",
                r.notes or "",
            ])
    logger.info(f"Saved results CSV: {csv_path}")

    # 2. Export Manifest JSON
    manifest_data = {
        "experiment_version": "v0.1.2-fulltext-pilot",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_attempted": total_attempted,
        "downloaded_count": downloaded_count,
        "valid_pdf_count": valid_pdf_count,
        "parsed_count": parsed_count,
        "unavailable_count": unavailable_count,
        "failed_count": failed_count,
        "success_rate": round(downloaded_count / total_attempted, 4) if total_attempted else 0.0,
        "storage_metrics": {
            "storage_before_bytes": storage_before,
            "storage_after_bytes": storage_after,
            "total_storage_used_bytes": total_storage_used,
            "total_storage_used_mb": round(total_storage_used / (1024 * 1024), 2),
            "avg_pdf_size_bytes": round(avg_size, 2),
            "avg_pdf_size_kb": round(avg_size / 1024, 2),
            "median_pdf_size_bytes": median_size,
            "largest_pdf_bytes": largest_size,
            "smallest_pdf_bytes": smallest_size,
        },
        "source_breakdown": source_counts,
        "validation_breakdown": validation_breakdown,
        "idempotency_verification": {
            "tested": idempotency_tested,
            "success": idempotency_success,
        },
        "total_duration_seconds": total_pilot_duration,
    }

    manifest_path = config.manifests_dir / "fulltext_pilot_v0.1.2_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    logger.info(f"Saved manifest JSON: {manifest_path}")

    # 3. Export Report Markdown
    report_md = f"""# ResearchGraph — Query-Driven Full-Text Pilot Report (v0.1.2)

**Generated**: {datetime.now(timezone.utc).isoformat()}  
**Pilot Objective**: Evaluate empirical feasibility, storage footprint, and PDF extractability of query-driven on-demand full-text acquisition.

---

## 1. Executive Summary

| Metric | Measured Value |
|---|---|
| **Papers Evaluated in Pilot** | **{total_attempted}** |
| **Successfully Downloaded** | **{downloaded_count}** ({round(downloaded_count/total_attempted*100, 1)}%) |
| **Valid & Verified PDFs** | **{valid_pdf_count}** ({round(valid_pdf_count/total_attempted*100, 1)}%) |
| **Parseable Documents (Text Extracted)** | **{parsed_count}** ({round(parsed_count/max(1, valid_pdf_count)*100, 1)}% of valid PDFs) |
| **Confirmed Unavailable / Paywalled** | **{unavailable_count}** ({round(unavailable_count/total_attempted*100, 1)}%) |
| **Network / Validation Failures** | **{failed_count}** ({round(failed_count/total_attempted*100, 1)}%) |
| **Total Pilot Storage Added** | **{round(total_storage_used / (1024*1024), 2)} MB** ({total_storage_used:,} bytes) |
| **Average Valid PDF Size** | **{round(avg_size / (1024*1024), 2)} MB** ({round(avg_size / 1024, 1)} KB) |
| **Median Valid PDF Size** | **{round(median_size / 1024, 1)} KB** |
| **Idempotency / Caching** | **{"PASSED" if idempotency_success else "FAILED"}** (Zero redundant network transfers) |

---

## 2. Source Breakdown & Acquisition Outcomes

| Source Type | Attempted | Downloaded | Valid PDF |
|---|---|---|---|
"""
    for src, cnt in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        src_d = sum(1 for r in results if (r.source_type or "none") == src and r.download_success)
        src_v = sum(1 for r in results if (r.source_type or "none") == src and r.is_valid_pdf)
        report_md += f"| `{src}` | {cnt} | {src_d} | {src_v} |\n"

    report_md += f"""
---

## 3. PDF Validation & Failure Classification

| Validation Status | Count | Percentage | Description |
|---|---|---|---|
"""
    for v_stat, cnt in sorted(validation_breakdown.items(), key=lambda x: x[1], reverse=True):
        report_md += f"| `{v_stat}` | {cnt} | {round(cnt/total_attempted*100, 1)}% | {PDFValidationStatus(v_stat).name} |\n"

    report_md += f"""
---

## 4. Empirical Storage Projections

Based on the empirical PDF size distribution (average = **{round(avg_size / (1024*1024), 2)} MB**, median = **{round(median_size / (1024*1024), 2)} MB**), the projected storage requirements for full-text retention are:

| Corpus Size | Storage (Average Size Basis) | Storage (Median Size Basis) |
|---|---|---|
| **500 Papers** | **{round(500 * avg_size / (1024*1024*1024), 2)} GB** (~{round(500 * avg_size / (1024*1024), 0):.0f} MB) | **{round(500 * median_size / (1024*1024*1024), 2)} GB** (~{round(500 * median_size / (1024*1024), 0):.0f} MB) |
| **5,000 Papers** | **{round(5000 * avg_size / (1024*1024*1024), 2)} GB** | **{round(5000 * median_size / (1024*1024*1024), 2)} GB** |
| **10,000 Papers** | **{round(10000 * avg_size / (1024*1024*1024), 2)} GB** | **{round(10000 * median_size / (1024*1024*1024), 2)} GB** |

---

## 5. Architectural Recommendations

1. **Query-Driven On-Demand Acquisition (RECOMMENDED)**:
   - Metadata-first candidate retrieval limits full-text downloads strictly to papers relevant to the active research query (typically 10–30 papers per query rather than 5,000+ PDFs).
2. **Hybrid Storage with Ephemeral PDF Cache**:
   - Downloaded PDFs should be stored in a bounded local LRU cache (`dataset/fulltext/cache/`).
   - Downstream extracted representations (structured JSON / markdown / sections) should be persisted permanently in lightweight form, allowing the heavy raw PDF binaries to be evicted when cache limits are reached.
3. **Robust Quality Validation**:
   - HTML detection and magic byte verification are essential: scholarly APIs often return HTML paywalls or cookie gates under 200 OK statuses when resolving DOI links.
"""

    report_path = config.manifests_dir / "fulltext_pilot_v0.1.2_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    logger.info(f"Saved quality report Markdown: {report_path}")

    print("\n============================================================")
    print("  Full-Text Acquisition Pilot (v0.1.2) Completed")
    print(f"  Total Attempted : {total_attempted}")
    print(f"  Downloaded      : {downloaded_count}")
    print(f"  Valid PDFs      : {valid_pdf_count}")
    print(f"  Parseable       : {parsed_count}")
    print(f"  Storage Added   : {round(total_storage_used / (1024*1024), 2)} MB")
    print("============================================================\n")


if __name__ == "__main__":
    run_experiment()
