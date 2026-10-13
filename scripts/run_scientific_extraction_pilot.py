#!/usr/bin/env python3
"""Run ResearchGraph Phase 3: Scientific Information Extraction Pilot.

Usage:
    python scripts/run_scientific_extraction_pilot.py
    python scripts/run_scientific_extraction_pilot.py --sample-size 75 --seed 42
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure repository root is in sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from dataset.schemas.scientific_knowledge import (
    ScientificEntityRecord,
    ScientificRelationRecord,
    ScientificStatementRecord,
)
from pipelines.extraction.config import ExtractionConfig
from pipelines.extraction.pipeline import ScientificExtractionPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("Phase3PilotRunner")


def export_schemas(output_dir: Path) -> None:
    """Export formal JSON schemas for scientific knowledge models."""
    output_dir.mkdir(parents=True, exist_ok=True)
    schemas = {
        "scientific_entity": ScientificEntityRecord.model_json_schema(),
        "scientific_statement": ScientificStatementRecord.model_json_schema(),
        "scientific_relation": ScientificRelationRecord.model_json_schema(),
    }
    target = output_dir / "scientific_knowledge.json"
    with open(target, "w", encoding="utf-8") as f:
        json.dump(schemas, f, indent=2)
    logger.info(f"Exported JSON schemas to {target}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute Phase 3 Scientific Information Extraction Pilot.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=75,
        help="Number of chunks to sample from Phase 2 corpus",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed for sampling",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v0.4.0",
        help="Extraction pipeline and output release version",
    )

    args = parser.parse_args()

    config = ExtractionConfig(
        EXTRACTION_PIPELINE_VERSION=args.version,
        DEFAULT_SAMPLE_SIZE=args.sample_size,
        DEFAULT_RANDOM_SEED=args.seed,
    )

    export_schemas(config.schemas_dir)

    pipeline = ScientificExtractionPipeline(config=config)
    batch_result, eval_report = pipeline.run_pilot(
        target_size=args.sample_size,
        seed=args.seed,
    )

    print("\n" + "=" * 80)
    print(" ResearchGraph Phase 3 Pilot Execution Summary")
    print("=" * 80)
    print(f"Pipeline Version:             {eval_report.pipeline_version}")
    print(f"Chunks Processed:             {eval_report.total_chunks}")
    print(f"Total Candidate Records:      {eval_report.total_candidate_records}")
    print(f"  - Validated Records:        {eval_report.total_validated_records}")
    print(f"  - Needs Review:             {eval_report.total_needs_review_records}")
    print(f"  - Rejected Records:         {eval_report.total_rejected_records}")
    print(f"Validation Pass Rate:         {eval_report.validation_pass_rate * 100:.2f}%")
    print(f"Evidence Grounding Accuracy:  {eval_report.evidence_grounding_accuracy * 100:.2f}% (Exact Char Span Match)")
    print(f"Provenance Validity Rate:     {eval_report.provenance_validity_rate * 100:.2f}%")
    print(f"Unsupported Claim Rate:       {eval_report.unsupported_claim_rate * 100:.2f}%")
    print(f"Entities Extracted:           {eval_report.total_entities_extracted}")
    print(f"Statements Extracted:         {eval_report.total_statements_extracted}")
    print(f"Relationships Extracted:      {eval_report.total_relations_extracted}")
    print(f"Ground Truth Status:          {eval_report.ground_truth_status}")
    print(f"Total Latency:                {eval_report.total_duration_ms:.1f} ms ({eval_report.avg_latency_per_chunk_ms:.2f} ms/chunk)")
    print("=" * 80)
    print(f"Outputs written to:           {config.output_dir}")
    print(f"Manifest written to:          {config.manifests_dir / f'scientific_extraction_pilot_{args.version}_manifest.json'}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
