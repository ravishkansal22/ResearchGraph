#!/usr/bin/env python3
"""Dataset Verification and Integrity Checker.

Validates schema compliance, record count parity between JSONL and Parquet formats,
manifest alignment, and metadata completeness for a specified dataset version.

Usage:
    python scripts/verify_dataset.py --version v0.1.0
    python scripts/verify_dataset.py --version v0.1.0 --strict
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure repository root is in sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import polars as pl
from pydantic import ValidationError

from dataset.schemas.canonical_paper import CanonicalPaper
from pipelines.ingestion.config import config


def verify_dataset(version: str, strict: bool = False) -> bool:
    """Validate all artifacts for a given dataset version."""
    storage_root = config.storage_root
    processed_dir = storage_root / "processed" / version
    manifest_file = storage_root / "manifests" / f"{version}_manifest.json"
    quality_report_file = storage_root / "manifests" / f"{version}_quality_report.md"

    print("=" * 70)
    print(f"  ResearchGraph Dataset Integrity Verification: {version}")
    print("=" * 70)

    all_passed = True

    # 1. Check directory and file existence
    jsonl_path = processed_dir / "canonical_papers.jsonl"
    parquet_path = processed_dir / "canonical_papers.parquet"

    print(f"\n[1/5] Checking file existence for version '{version}':")
    for name, path in [
        ("Processed Directory", processed_dir),
        ("Canonical JSONL", jsonl_path),
        ("Canonical Parquet", parquet_path),
        ("Dataset Manifest", manifest_file),
        ("Quality Report", quality_report_file),
    ]:
        exists = path.exists()
        status = "PASSED" if exists else "FAILED"
        print(f"  - {name:<22}: {'FOUND' if exists else 'MISSING'} [{status}]")
        if not exists:
            all_passed = False

    if not jsonl_path.exists() or not parquet_path.exists():
        print("\nERROR: Required processed dataset files are missing. Cannot proceed with verification.")
        return False

    # 2. Validate JSONL records against Pydantic schema
    print("\n[2/5] Validating JSONL records against CanonicalPaper Pydantic Schema:")
    jsonl_records: List[Dict[str, Any]] = []
    validation_errors = 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                CanonicalPaper.model_validate(data)
                jsonl_records.append(data)
            except (json.JSONDecodeError, ValidationError) as e:
                validation_errors += 1
                if validation_errors <= 3:
                    print(f"  ! Record #{idx} failed schema validation: {e}")

    jsonl_count = len(jsonl_records)
    print(f"  - Total JSONL records read  : {jsonl_count}")
    print(f"  - Schema validation errors : {validation_errors}")
    if validation_errors == 0:
        print("  - Schema Conformance       : 100% VALID [PASSED]")
    else:
        print("  - Schema Conformance       : FAILED [FAIL]")
        all_passed = False

    # 3. Validate Parquet readability and schema via Polars
    print("\n[3/5] Validating Parquet file structure and columnar integrity:")
    try:
        df = pl.read_parquet(parquet_path)
        parquet_count = df.shape[0]
        parquet_cols = df.shape[1]
        print(f"  - Parquet rows count       : {parquet_count}")
        print(f"  - Parquet columns count    : {parquet_cols}")
        print(f"  - Parquet Schema           : {list(df.schema.keys())[:6]} ...")
        print("  - Parquet Readability      : VALID [PASSED]")
    except Exception as e:
        print(f"  - Parquet Read Error       : {e} [FAIL]")
        parquet_count = -1
        all_passed = False

    # 4. Cross-format row parity check
    print("\n[4/5] Checking record count parity between JSONL and Parquet:")
    if jsonl_count == parquet_count:
        print(f"  - Parity Check             : EXACT MATCH ({jsonl_count} == {parquet_count}) [PASSED]")
    else:
        print(f"  - Parity Check             : MISMATCH (JSONL: {jsonl_count}, Parquet: {parquet_count}) [FAIL]")
        all_passed = False

    # 5. Manifest alignment check
    print("\n[5/5] Verifying Manifest alignment:")
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            manifest_paper_count = manifest.get("paper_count")
            print(f"  - Manifest paper_count     : {manifest_paper_count}")
            print(f"  - Actual canonical count   : {jsonl_count}")
            if manifest_paper_count == jsonl_count:
                print("  - Manifest Alignment       : IN SYNC [PASSED]")
            else:
                print("  - Manifest Alignment       : OUT OF SYNC [FAIL]")
                all_passed = False
        except Exception as e:
            print(f"  - Manifest Parse Error     : {e} [FAIL]")
            all_passed = False
    else:
        print("  - Manifest File Missing    : SKIPPED [FAIL]")
        all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print(f"  OVERALL RESULT: Dataset '{version}' is 100% VALID & INTEGRAL.")
    else:
        print(f"  OVERALL RESULT: Dataset '{version}' has INTEGRITY ISSUES.")
    print("=" * 70 + "\n")

    return all_passed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify ResearchGraph dataset artifacts and schema conformance.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v0.1.0",
        help="Dataset version tag to verify (e.g. v0.1.0)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero status code if any verification check fails",
    )

    args = parser.parse_args()
    success = verify_dataset(version=args.version, strict=args.strict)
    if args.strict and not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
