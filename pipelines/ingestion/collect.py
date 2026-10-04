"""Command-Line Interface (CLI) for ResearchGraph Literature Collection Pipeline.

Usage:
    python -m pipelines.ingestion.collect --query "transformer attention deep learning" --limit 250
    python -m pipelines.ingestion.collect --sources openalex,arxiv --limit 500 --version v0.1.0
    python -m pipelines.ingestion.collect --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List

from pipelines.ingestion.config import config
from pipelines.ingestion.pipeline import LiteratureIngestionPipeline


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured console logging."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ResearchGraph Literature Ingestion and Dataset Curation Pipeline (Phase 1)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--query",
        type=str,
        default="artificial intelligence machine learning neural network",
        help="Search query to execute against scholarly sources",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default="openalex,semantic_scholar,arxiv,crossref",
        help="Comma-separated scholarly source adapters to query (openalex, semantic_scholar, arxiv, crossref)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=250,
        help="Target number of records to fetch per source (total ~ 4x limit)",
    )
    parser.add_argument(
        "--version",
        type=str,
        default=config.DEFAULT_DATASET_VERSION,
        help="Dataset version tag (e.g. v0.1.0)",
    )
    parser.add_argument(
        "--filter-mode",
        type=str,
        choices=["strict_ai", "broad_ai", "all"],
        default="broad_ai",
        help="AI relevance filter stringency",
    )
    parser.add_argument(
        "--fulltext",
        action="store_true",
        help="Attempt open-access full-text artifact discovery and download",
    )
    parser.add_argument(
        "--fulltext-limit",
        type=int,
        default=None,
        help="Max number of full-text PDF artifacts to download during the run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute collection and normalization without persisting artifacts to disk",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=config.LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity level",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    sources_list = [s.strip().lower() for s in args.sources.split(",") if s.strip()]

    pipeline = LiteratureIngestionPipeline(dataset_version=args.version)

    try:
        results = pipeline.run(
            query=args.query,
            sources=sources_list,
            limit_per_source=args.limit,
            filter_mode=args.filter_mode,
            acquire_fulltext=args.fulltext,
            fulltext_limit=args.fulltext_limit,
            dry_run=args.dry_run,
        )

        print("\n" + "=" * 60)
        print("  RESEARCHGRAPH PHASE 1 INGESTION COMPLETE")
        print("=" * 60)
        print(f"Dataset Version:       {results.get('dataset_version')}")
        print(f"Raw Records Ingested:  {results.get('raw_records_count')}")
        print(f"Canonical Papers:      {results.get('canonical_papers_count')}")
        print(f"Duplicates Merged:     {results.get('duplicates_merged')}")
        if results.get("parquet_file"):
            print(f"Canonical Parquet:     {results.get('parquet_file')}")
        if results.get("jsonl_file"):
            print(f"Canonical JSONL:       {results.get('jsonl_file')}")
        print("=" * 60 + "\n")

    except KeyboardInterrupt:
        print("\nIngestion interrupted by user.")
        sys.exit(130)
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
