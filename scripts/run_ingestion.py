#!/usr/bin/env python3
"""Ingestion Workflow Runner Script.

Provides convenient preset execution profiles for Phase 1 literature acquisition runs.

Presets:
    - pilot     : Quick ~1,000-paper multi-source pilot acquisition
    - focused   : Targeted query collection on a specific sub-discipline (e.g. LLM reasoning, GNNs)
    - dry-run   : Test network connectivity and normalization without writing dataset artifacts

Usage:
    python scripts/run_ingestion.py --preset pilot
    python scripts/run_ingestion.py --preset focused --query "graph neural networks" --limit 100
    python scripts/run_ingestion.py --preset dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repository root is in sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from pipelines.ingestion.collect import setup_logging
from pipelines.ingestion.config import config
from pipelines.ingestion.pipeline import LiteratureIngestionPipeline


def run_preset(preset: str, query: str, limit: int, version: str, fulltext: bool) -> None:
    setup_logging("INFO")
    pipeline = LiteratureIngestionPipeline(dataset_version=version)

    if preset == "dry-run":
        print("[Preset: dry-run] Running live validation with disk write disabled...")
        pipeline.run(
            query=query or "artificial intelligence machine learning",
            sources=["openalex", "crossref", "semantic_scholar"],
            limit_per_source=min(limit, 5),
            filter_mode="broad_ai",
            acquire_fulltext=False,
            dry_run=True,
        )
    elif preset == "pilot":
        print(f"[Preset: pilot] Running multi-source pilot ingestion (~{limit * 3} target records)...")
        pipeline.run(
            query=query or "artificial intelligence machine learning deep learning",
            sources=["openalex", "crossref", "semantic_scholar"],
            limit_per_source=limit or 350,
            filter_mode="broad_ai",
            acquire_fulltext=fulltext,
            dry_run=False,
        )
    elif preset == "focused":
        print(f"[Preset: focused] Running focused search for '{query}'...")
        pipeline.run(
            query=query,
            sources=["openalex", "crossref", "arxiv", "semantic_scholar"],
            limit_per_source=limit or 100,
            filter_mode="broad_ai",
            acquire_fulltext=fulltext,
            dry_run=False,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run literature ingestion presets.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--preset",
        type=str,
        choices=["pilot", "focused", "dry-run"],
        default="pilot",
        help="Operational preset to execute",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="Custom search query (overrides preset default)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=250,
        help="Target records per source",
    )
    parser.add_argument(
        "--version",
        type=str,
        default=config.DEFAULT_DATASET_VERSION,
        help="Target dataset release version",
    )
    parser.add_argument(
        "--fulltext",
        action="store_true",
        help="Attempt open-access full-text artifact download",
    )

    args = parser.parse_args()
    run_preset(
        preset=args.preset,
        query=args.query,
        limit=args.limit,
        version=args.version,
        fulltext=args.fulltext,
    )


if __name__ == "__main__":
    main()
