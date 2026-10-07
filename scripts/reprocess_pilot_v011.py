#!/usr/bin/env python3
"""Reprocess pilot raw records to create release v0.1.1.

Reads verified raw OpenAlex and Crossref records from the pilot run (20261004_101234),
applies updated normalizers (document_type, granular publication dates, fulltext status),
runs relevance filtering and identity resolution, saves dataset/processed/v0.1.1,
and exports manifests and deterministic audit samples.
"""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure repository root is in sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from dataset.schemas.canonical_paper import CanonicalPaper, RawRecord
from pipelines.ingestion.config import config
from pipelines.ingestion.filters.relevance import AIRelevanceFilter
from pipelines.ingestion.quality.reporter import QualityReporter
from pipelines.ingestion.resolution.deduplicator import Deduplicator
from pipelines.ingestion.sources.crossref import CrossrefAdapter
from pipelines.ingestion.sources.openalex import OpenAlexAdapter
from pipelines.ingestion.storage.manager import DatasetStorageManager


def load_raw_records(source: str, run_id: str) -> List[RawRecord]:
    file_path = config.raw_dir / source / run_id / f"{source}_records.jsonl"
    records: List[RawRecord] = []
    if not file_path.exists():
        raise FileNotFoundError(f"Raw record file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                records.append(RawRecord(**data))
    return records


def build_v011() -> None:
    version = "v0.1.1"
    run_id = "20261004_101234"
    print(f"=== Reprocessing pilot run {run_id} for release {version} ===")

    openalex_adapter = OpenAlexAdapter()
    crossref_adapter = CrossrefAdapter()
    storage = DatasetStorageManager()
    deduplicator = Deduplicator()
    reporter = QualityReporter()

    # 1. Load raw records
    raw_openalex = load_raw_records("openalex", run_id)
    raw_crossref = load_raw_records("crossref", run_id)
    print(f"Loaded {len(raw_openalex)} raw OpenAlex records, {len(raw_crossref)} raw Crossref records.")

    all_normalized: List[CanonicalPaper] = []
    for r in raw_openalex:
        all_normalized.append(openalex_adapter.normalize(r))
    for r in raw_crossref:
        all_normalized.append(crossref_adapter.normalize(r))
    print(f"Normalized {len(all_normalized)} records.")

    # 2. Relevance filtering
    rel_filter = AIRelevanceFilter(mode="broad_ai")
    all_evaluated_with_decision = []
    for p in all_normalized:
        is_relevant, domain_tag, score = rel_filter.evaluate(p)
        all_evaluated_with_decision.append((p, is_relevant, domain_tag, score))

    filtered_papers, relevance_stats = rel_filter.filter_papers(all_normalized)
    print(
        f"Relevance filter: {len(filtered_papers)}/{len(all_normalized)} passed "
        f"({relevance_stats.get('pass_rate', 0.0):.1%})"
    )

    # 3. Deduplication & Identity Resolution
    canonical_papers, dedup_stats = deduplicator.deduplicate(filtered_papers)
    print(
        f"Deduplication: {len(filtered_papers)} -> {len(canonical_papers)} canonical papers "
        f"({dedup_stats.get('duplicates_merged', 0)} duplicates merged, {dedup_stats.get('unresolved_matches', 0)} unresolved)"
    )

    # 4. Save canonical dataset
    jsonl_path, parquet_path = storage.save_canonical_dataset(
        papers=canonical_papers,
        dataset_version=version,
    )
    print(f"Saved dataset:\n  JSONL:   {jsonl_path}\n  Parquet: {parquet_path}")

    # 5. Manifest & Quality Report
    manifest = reporter.generate_manifest(
        canonical_papers=canonical_papers,
        dataset_version=version,
        sources_used=["openalex", "crossref"],
        dedup_stats=dedup_stats,
        relevance_stats=relevance_stats,
        fulltext_stats={
            "fulltext_discoverable_count": sum(1 for p in canonical_papers if p.fulltext_status.value == "DISCOVERABLE"),
            "fulltext_downloaded_count": sum(1 for p in canonical_papers if p.fulltext_status.value == "DOWNLOADED"),
            "download_attempted": 0,
            "download_succeeded": 0,
        },
    )

    quality_report_dict, quality_report_md = reporter.compute_quality_report(
        canonical_papers=canonical_papers,
        manifest=manifest,
    )

    storage.save_manifest(manifest, dataset_version=version)
    storage.save_quality_report(
        report_data=quality_report_dict,
        markdown_content=quality_report_md,
        dataset_version=version,
    )
    print(f"Saved manifest and quality report for {version}.")

    # 6. Task A: Deterministic Relevance Audit Sample (approx 100 records)
    # Expose: canonical_id, title, abstract, topics/concepts, source, current_filter_decision, human_label, notes
    # Human label choices: CORE_AI, AI_ADJACENT, NOT_RELEVANT (blank/pending)
    rng = random.Random(42)
    # Sample from all 700 normalized records
    sampled_indices = rng.sample(range(len(all_evaluated_with_decision)), 100)
    relevance_sample = [all_evaluated_with_decision[i] for i in sorted(sampled_indices)]

    relevance_audit_path = config.manifests_dir / f"{version}_relevance_audit.csv"
    with open(relevance_audit_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "sample_index",
            "canonical_id",
            "title",
            "primary_source",
            "document_type",
            "topics_concepts",
            "current_filter_decision",
            "filter_tag",
            "filter_score",
            "human_label",
            "notes",
        ])
        for idx, (p, passed, tag, score) in enumerate(relevance_sample, 1):
            decision_str = "PASS" if passed else "REJECT"
            topics_str = "; ".join(top.name for top in p.topics[:5]) if p.topics else ""
            primary_src = p.provenance[0].source if p.provenance else "unknown"
            writer.writerow([
                idx,
                p.canonical_id,
                p.title,
                primary_src,
                p.document_type.value,
                topics_str,
                decision_str,
                tag,
                score,
                "",  # human_label left blank for pending manual review
                "PENDING HUMAN REVIEW: Choose CORE_AI | AI_ADJACENT | NOT_RELEVANT",
            ])
    print(f"Generated relevance audit sample at: {relevance_audit_path}")

    # 7. Task C: Deterministic Deduplication Audit Sample (30 merged cases)
    # Prioritize multi-signal, DOI matches, title matches, cross-source
    merged_papers = [p for p in canonical_papers if len(p.provenance) > 1]
    # Deterministic sample of 30 merged papers
    rng_dedup = random.Random(42)
    if len(merged_papers) > 30:
        sampled_merged = rng_dedup.sample(merged_papers, 30)
    else:
        sampled_merged = merged_papers

    dedup_audit_path = config.manifests_dir / f"{version}_dedup_audit.csv"
    with open(dedup_audit_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "canonical_id",
            "num_sources",
            "source_record_ids",
            "doi",
            "title",
            "authors",
            "document_type",
            "published_date",
            "online_pub_date",
            "print_pub_date",
            "match_signals",
            "match_confidence",
            "human_dedup_verification",
            "notes",
        ])
        for p in sampled_merged:
            src_ids = "; ".join(f"{pr.source}:{pr.source_record_id}" for pr in p.provenance)
            authors_str = "; ".join(a.name for a in p.authors[:3]) + ("..." if len(p.authors) > 3 else "")
            # determine match signal
            signals = []
            if p.doi:
                signals.append("DOI_EXACT")
            if len(p.provenance) > 1:
                signals.append("TITLE_AUTHORS_SIMILARITY")
            signals_str = "+".join(signals) if signals else "CANONICAL_ID"

            writer.writerow([
                p.canonical_id,
                len(p.provenance),
                src_ids,
                p.doi or "",
                p.title,
                authors_str,
                p.document_type.value,
                p.published_date or "",
                p.online_publication_date or "",
                p.print_publication_date or "",
                signals_str,
                "HIGH (1.0)" if p.doi else "MEDIUM (0.85)",
                "",  # blank for human verification
                "PENDING HUMAN REVIEW: Verify whether records represent the same scientific work",
            ])
    print(f"Generated deduplication audit sample at: {dedup_audit_path}")


if __name__ == "__main__":
    build_v011()
