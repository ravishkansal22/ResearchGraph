"""ResearchGraph Literature Ingestion Pipeline Orchestrator.

Orchestrates multi-source acquisition, normalization, deduplication,
full-text acquisition, dataset storage, and quality report generation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dataset.schemas.canonical_paper import CanonicalPaper, RawRecord
from pipelines.ingestion.config import config
from pipelines.ingestion.filters.relevance import AIRelevanceFilter
from pipelines.ingestion.fulltext.collector import FullTextCollector
from pipelines.ingestion.quality.reporter import QualityReporter
from pipelines.ingestion.resolution.deduplicator import Deduplicator
from pipelines.ingestion.sources.arxiv import ArxivAdapter
from pipelines.ingestion.sources.base import BaseSourceAdapter
from pipelines.ingestion.sources.crossref import CrossrefAdapter
from pipelines.ingestion.sources.openalex import OpenAlexAdapter
from pipelines.ingestion.sources.semantic_scholar import SemanticScholarAdapter
from pipelines.ingestion.storage.manager import DatasetStorageManager

logger = logging.getLogger(__name__)


class LiteratureIngestionPipeline:
    """End-to-end literature acquisition and curation pipeline for ResearchGraph Phase 1."""

    def __init__(
        self,
        dataset_version: str = config.DEFAULT_DATASET_VERSION,
        storage_manager: Optional[DatasetStorageManager] = None,
        deduplicator: Optional[Deduplicator] = None,
        quality_reporter: Optional[QualityReporter] = None,
    ):
        self.dataset_version = dataset_version
        self.storage = storage_manager or DatasetStorageManager()
        self.deduplicator = deduplicator or Deduplicator()
        self.reporter = quality_reporter or QualityReporter()

        # Initialize adapters
        self.adapters: Dict[str, BaseSourceAdapter] = {
            "openalex": OpenAlexAdapter(),
            "semantic_scholar": SemanticScholarAdapter(),
            "arxiv": ArxivAdapter(),
            "crossref": CrossrefAdapter(),
        }

    def get_adapter(self, source_name: str) -> BaseSourceAdapter:
        if source_name not in self.adapters:
            raise ValueError(f"Unknown source adapter: '{source_name}'. Supported: {list(self.adapters.keys())}")
        return self.adapters[source_name]

    def run(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        limit_per_source: int = 250,
        filter_mode: str = "broad_ai",
        acquire_fulltext: bool = False,
        fulltext_limit: Optional[int] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute complete literature ingestion pipeline run.

        Stages:
        1. Acquire raw literature records from specified sources.
        2. Persist raw records to storage/raw tier.
        3. Normalize records to canonical schema.
        4. Persist interim normalized records.
        5. Apply configurable AI relevance filter.
        6. Perform identity resolution and deduplication.
        7. (Optional) Discover and download accessible full-text artifacts.
        8. Persist canonical dataset to Parquet and JSONL.
        9. Generate and save release manifest and quality report.
        """
        run_id = self.storage.get_run_timestamp()
        sources_to_run = sources or list(self.adapters.keys())
        config.ensure_directories()

        logger.info(
            f"=== Starting ResearchGraph Ingestion Run ({run_id}) ===\n"
            f"  Dataset Version:   {self.dataset_version}\n"
            f"  Query:             '{query}'\n"
            f"  Sources:           {sources_to_run}\n"
            f"  Target per Source: {limit_per_source}\n"
            f"  Relevance Filter:  {filter_mode}\n"
            f"  Acquire FullText:  {acquire_fulltext}\n"
            f"  Dry Run:           {dry_run}"
        )

        all_raw_records: List[RawRecord] = []
        all_normalized_papers: List[CanonicalPaper] = []

        # Stage 1 & 2: Acquisition and Raw Storage
        for src_name in sources_to_run:
            adapter = self.get_adapter(src_name)
            logger.info(f"--- Acquiring from source: {src_name} ---")

            checkpoint_file = (
                config.raw_dir / src_name / run_id / f"{src_name}_checkpoint.jsonl"
                if not dry_run else None
            )

            try:
                raw_records = adapter.search(
                    query=query,
                    limit=limit_per_source,
                    checkpoint_file=checkpoint_file,
                )
            except Exception as e:
                logger.error(f"Error collecting from {src_name}: {e}")
                raw_records = []

            all_raw_records.extend(raw_records)

            if not dry_run and raw_records:
                self.storage.save_raw_records(
                    source=src_name,
                    records=raw_records,
                    run_id=run_id,
                )

            # Stage 3: Normalization
            for rec in raw_records:
                try:
                    norm_paper = adapter.normalize(rec)
                    all_normalized_papers.append(norm_paper)
                except Exception as norm_err:
                    logger.error(f"Normalization error for {src_name} record {rec.source_record_id}: {norm_err}")

        logger.info(f"Total raw records acquired: {len(all_raw_records)}")
        logger.info(f"Total records normalized: {len(all_normalized_papers)}")

        # Stage 4: Interim Storage
        if not dry_run and all_normalized_papers:
            self.storage.save_interim_records(all_normalized_papers, run_id)

        # Stage 5: Relevance Filtering
        rel_filter = AIRelevanceFilter(mode=filter_mode)
        filtered_papers, relevance_stats = rel_filter.filter_papers(all_normalized_papers)
        logger.info(
            f"Relevance filtering complete ({filter_mode}): "
            f"{len(filtered_papers)}/{len(all_normalized_papers)} passed ({relevance_stats.get('pass_rate', 0.0):.1%})"
        )

        # Stage 6: Identity Resolution & Deduplication
        canonical_papers, dedup_stats = self.deduplicator.deduplicate(filtered_papers)
        logger.info(
            f"Deduplication complete: {len(filtered_papers)} -> {len(canonical_papers)} canonical papers "
            f"({dedup_stats.get('duplicates_merged', 0)} duplicates merged)"
        )

        # Stage 7: Full-Text Acquisition (Optional)
        fulltext_stats = {}
        if acquire_fulltext and not dry_run:
            logger.info("--- Starting Full-Text Discovery and Acquisition ---")
            collector = FullTextCollector()
            canonical_papers, fulltext_stats = collector.process_papers(
                papers=canonical_papers,
                dataset_version=self.dataset_version,
                limit_downloads=fulltext_limit,
            )
            collector.close()

        # Stage 8: Processed Dataset Storage
        if not dry_run and canonical_papers:
            jsonl_path, parquet_path = self.storage.save_canonical_dataset(
                papers=canonical_papers,
                dataset_version=self.dataset_version,
            )
        else:
            jsonl_path, parquet_path = None, None

        # Stage 9: Manifest & Quality Report Generation
        manifest = self.reporter.generate_manifest(
            canonical_papers=canonical_papers,
            dataset_version=self.dataset_version,
            sources_used=sources_to_run,
            dedup_stats=dedup_stats,
            relevance_stats=relevance_stats,
            fulltext_stats=fulltext_stats,
        )

        quality_report_dict, quality_report_md = self.reporter.compute_quality_report(
            canonical_papers=canonical_papers,
            manifest=manifest,
        )

        if not dry_run:
            self.storage.save_manifest(manifest, dataset_version=self.dataset_version)
            self.storage.save_quality_report(
                report_data=quality_report_dict,
                markdown_content=quality_report_md,
                dataset_version=self.dataset_version,
            )

        summary = {
            "run_id": run_id,
            "dataset_version": self.dataset_version,
            "raw_records_count": len(all_raw_records),
            "canonical_papers_count": len(canonical_papers),
            "duplicates_merged": dedup_stats.get("duplicates_merged", 0),
            "quality_report": quality_report_dict,
            "manifest": manifest,
            "parquet_file": str(parquet_path) if parquet_path else None,
            "jsonl_file": str(jsonl_path) if jsonl_path else None,
        }

        logger.info(
            f"=== Pipeline Run Finished Successfully ===\n"
            f"  Canonical Papers: {len(canonical_papers)}\n"
            f"  Dataset Version:  {self.dataset_version}\n"
        )
        return summary

    def close(self) -> None:
        for adapter in self.adapters.values():
            adapter.close()
