#!/usr/bin/env python3
"""Export Canonical Paper JSON Schema.

Generates the formal JSON Schema definition from Pydantic models for external tools,
API validation, and frontend contract binding.

Usage:
    python scripts/export_schema.py
    python scripts/export_schema.py --output dataset/schemas/canonical_paper.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure repository root is in sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from dataset.schemas.canonical_paper import CanonicalPaper
from pipelines.ingestion.config import config


def export_schema(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    schema = CanonicalPaper.model_json_schema()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    print(f"[Schema] Exported CanonicalPaper JSON schema to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export CanonicalPaper JSON schema.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=config.schemas_dir / "canonical_paper.json",
        help="Target output path for the JSON schema",
    )

    args = parser.parse_args()
    export_schema(args.output)


if __name__ == "__main__":
    main()
