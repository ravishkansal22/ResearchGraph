#!/usr/bin/env python3
"""Dataset Quality Report Generator.

Computes or re-evaluates completeness metrics, cross-source overlap, temporal distributions,
and generates both JSON and Markdown reports for any existing dataset release.

Usage:
    python scripts/generate_quality_report.py --version v0.1.0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

# Ensure repository root is in sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from dataset.schemas.canonical_paper import CanonicalPaper
from pipelines.ingestion.config import config
from pipelines.ingestion.quality.reporter import QualityReporter
from pipelines.ingestion.storage.manager import DatasetStorageManager


def generate_report(version: str) -> None:
    storage = DatasetStorageManager()
    reporter = QualityReporter()

    jsonl_path = config.processed_dir / version / "canonical_papers.jsonl"
    manifest_path = config.manifests_dir / f"{version}_manifest.json"

    if not jsonl_path.exists():
        print(f"ERROR: Dataset JSONL not found at {jsonl_path}")
        sys.exit(1)

    if not manifest_path.exists():
        print(f"ERROR: Dataset manifest not found at {manifest_path}")
        sys.exit(1)

    with open(jsonl_path, "r", encoding="utf-8") as f:
        papers = [CanonicalPaper.model_validate_json(line) for line in f if line.strip()]

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"[QualityReport] Computing quality metrics for {len(papers)} canonical papers ({version})...")
    report_dict, report_md = reporter.compute_quality_report(papers, manifest)

    storage.save_quality_report(
        report_data=report_dict,
        markdown_content=report_md,
        dataset_version=version,
    )

    print(f"[QualityReport] Successfully regenerated quality reports for '{version}' in {config.manifests_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate quality report for a processed dataset release.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v0.1.0",
        help="Dataset version to analyze",
    )

    args = parser.parse_args()
    generate_report(args.version)


if __name__ == "__main__":
    main()
