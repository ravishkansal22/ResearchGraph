#!/usr/bin/env python3
"""CLI Script to Build ResearchGraph Phase 4: Scientific Knowledge Base.

Usage:
    python scripts/build_scientific_knowledge_base.py
    python scripts/build_scientific_knowledge_base.py --output-dir dataset/processed/v0.5.0
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.knowledge_base.config import KnowledgeBaseConfig
from pipelines.knowledge_base.pipeline import ScientificKnowledgeBasePipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build ResearchGraph Scientific Knowledge Base (v0.5.1)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dataset/processed/v0.5.1"),
        help="Target output directory for persistent snapshots and database",
    )
    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=Path("dataset/manifests"),
        help="Directory to save build manifest and quality report",
    )
    parser.add_argument(
        "--no-parquet",
        action="store_true",
        help="Skip generating columnar Parquet snapshots",
    )
    parser.add_argument(
        "--no-sqlite",
        action="store_true",
        help="Skip populating SQLite database",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = KnowledgeBaseConfig(
        output_dir=args.output_dir,
        manifest_dir=args.manifest_dir,
        save_parquet=not args.no_parquet,
        save_sqlite=not args.no_sqlite,
    )

    pipeline = ScientificKnowledgeBasePipeline(config=config)
    manifest = pipeline.run()

    print("\n" + "=" * 70)
    print("PHASE 4: SCIENTIFIC KNOWLEDGE BASE BUILD SUCCESSFUL")
    print("=" * 70)
    print(f"KB Version:                      {manifest.kb_version}")
    print(f"Schema Version:                  {manifest.schema_version}")
    print(f"Total Papers Ingested:           {manifest.total_papers_count}")
    print(f"Canonical Entities Consolidated: {manifest.total_canonical_entities_count}")
    print(f"Entity Mentions Grounded:        {manifest.total_entity_mentions_count}")
    print(f"Scientific Statements:           {manifest.total_statements_count}")
    print(f"Total Relationships:             {manifest.total_relationships_count}")
    print(f"  - Trusted (Supported):         {manifest.trusted_relationships_count}")
    print(f"  - Unsupported (Diagnostic):    {manifest.unsupported_relationships_count}")
    print(f"Quarantined Records:             {manifest.total_quarantined_records_count}")
    print(f"Referential Integrity Pass Rate: {manifest.referential_integrity_pass_rate * 100:.2f}%")
    print(f"Provenance Completeness:         {manifest.provenance_completeness_rate * 100:.2f}%")
    print(f"Output Directory:                {config.output_dir.resolve()}")
    print("=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
