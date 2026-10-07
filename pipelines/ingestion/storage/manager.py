"""Dataset Storage Manager and Multi-Tier Serialization Engine.

Handles raw, interim, and processed tiers using high-performance Parquet and JSONL formats.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import polars as pl

from dataset.schemas.canonical_paper import CanonicalPaper, RawRecord
from pipelines.ingestion.config import config

logger = logging.getLogger(__name__)


class DatasetStorageManager:
    """Manages reading and writing data across raw, interim, and processed tiers."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or config.storage_root

    def get_run_timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # --- RAW TIER ---
    def save_raw_records(
        self,
        source: str,
        records: List[RawRecord],
        run_id: str,
    ) -> Path:
        """Save raw API payloads to dataset/raw/{source}/{run_id}/{source}_records.jsonl."""
        dest_dir = self.root_dir / "raw" / source / run_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        file_path = dest_dir / f"{source}_records.jsonl"

        with open(file_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(rec.model_dump_json() + "\n")

        logger.info(f"[Storage] Saved {len(records)} raw {source} records to {file_path}")
        return file_path

    # --- INTERIM TIER ---
    def save_interim_records(
        self,
        papers: List[CanonicalPaper],
        run_id: str,
    ) -> Path:
        """Save normalized but pre-deduplicated records to dataset/interim/{run_id}/normalized_records.jsonl."""
        dest_dir = self.root_dir / "interim" / run_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        file_path = dest_dir / "normalized_records.jsonl"

        with open(file_path, "w", encoding="utf-8") as f:
            for paper in papers:
                f.write(paper.model_dump_json() + "\n")

        logger.info(f"[Storage] Saved {len(papers)} interim records to {file_path}")
        return file_path

    # --- PROCESSED TIER ---
    def save_canonical_dataset(
        self,
        papers: List[CanonicalPaper],
        dataset_version: str = config.DEFAULT_DATASET_VERSION,
    ) -> Tuple[Path, Path]:
        """Save deduplicated canonical dataset to Parquet and JSONL formats in dataset/processed/{version}/."""
        dest_dir = self.root_dir / "processed" / dataset_version
        dest_dir.mkdir(parents=True, exist_ok=True)

        jsonl_path = dest_dir / "canonical_papers.jsonl"
        parquet_path = dest_dir / "canonical_papers.parquet"

        # 1. Write rich JSONL
        records_dicts: List[Dict[str, Any]] = []
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for paper in papers:
                d = paper.model_dump()
                f.write(json.dumps(d) + "\n")
                records_dicts.append(d)

        # 2. Write optimized Parquet using Polars / PyArrow
        if records_dicts:
            flat_rows: List[Dict[str, Any]] = []
            for d in records_dicts:
                flat_row = {
                    "canonical_id": str(d.get("canonical_id") or ""),
                    "title": str(d.get("title") or ""),
                    "document_type": str(d.get("document_type") or "UNKNOWN"),
                    "abstract": str(d.get("abstract")) if d.get("abstract") is not None else None,
                    "published_date": str(d.get("published_date")) if d.get("published_date") is not None else (str(d.get("publication_date")) if d.get("publication_date") is not None else None),
                    "online_publication_date": str(d.get("online_publication_date")) if d.get("online_publication_date") is not None else None,
                    "print_publication_date": str(d.get("print_publication_date")) if d.get("print_publication_date") is not None else None,
                    "issued_date": str(d.get("issued_date")) if d.get("issued_date") is not None else None,
                    "publication_year": int(d.get("publication_year")) if d.get("publication_year") is not None else None,
                    "doi": str(d.get("doi")) if d.get("doi") is not None else None,
                    "arxiv_id": str(d.get("arxiv_id")) if d.get("arxiv_id") is not None else None,
                    "author_names": [str(a.get("name")) for a in d.get("authors", []) if a.get("name")],
                    "author_count": len(d.get("authors", [])),
                    "venue_name": str(d.get("venue", {}).get("name")) if d.get("venue") and d.get("venue", {}).get("name") else None,
                    "topics": [str(t.get("name")) for t in d.get("topics", []) if t.get("name")],
                    "keywords": [str(k) for k in d.get("keywords", []) if k],
                    "citation_count": int(d.get("citation_count")) if d.get("citation_count") is not None else None,
                    "influential_citation_count": int(d.get("influential_citation_count")) if d.get("influential_citation_count") is not None else None,
                    "is_open_access": bool(d.get("open_access", {}).get("is_oa", False)),
                    "fulltext_status": str(d.get("fulltext_status") or "NOT_CHECKED"),
                    "fulltext_available": str(d.get("fulltext_available") or "NOT_CHECKED"),
                    "fulltext_url": str(d.get("fulltext_url")) if d.get("fulltext_url") is not None else None,
                    "fulltext_path": str(d.get("fulltext_path")) if d.get("fulltext_path") is not None else None,
                    "sources": [str(p.get("source")) for p in d.get("provenance", []) if p.get("source")],
                    "identity_confidence": str(d.get("identity_confidence")),
                    "created_at": str(d.get("created_at")),
                }
                flat_rows.append(flat_row)

            explicit_schema = {
                "canonical_id": pl.Utf8,
                "title": pl.Utf8,
                "document_type": pl.Utf8,
                "abstract": pl.Utf8,
                "published_date": pl.Utf8,
                "online_publication_date": pl.Utf8,
                "print_publication_date": pl.Utf8,
                "issued_date": pl.Utf8,
                "publication_year": pl.Int64,
                "doi": pl.Utf8,
                "arxiv_id": pl.Utf8,
                "author_names": pl.List(pl.Utf8),
                "author_count": pl.Int64,
                "venue_name": pl.Utf8,
                "topics": pl.List(pl.Utf8),
                "keywords": pl.List(pl.Utf8),
                "citation_count": pl.Int64,
                "influential_citation_count": pl.Int64,
                "is_open_access": pl.Boolean,
                "fulltext_status": pl.Utf8,
                "fulltext_available": pl.Utf8,
                "fulltext_url": pl.Utf8,
                "fulltext_path": pl.Utf8,
                "sources": pl.List(pl.Utf8),
                "identity_confidence": pl.Utf8,
                "created_at": pl.Utf8,
            }

            df = pl.DataFrame(flat_rows, schema=explicit_schema)
            df.write_parquet(parquet_path)

        logger.info(
            f"[Storage] Saved canonical dataset (version {dataset_version}):\n"
            f"  JSONL:   {jsonl_path}\n"
            f"  Parquet: {parquet_path}"
        )
        return jsonl_path, parquet_path

    # --- MANIFESTS & REPORTS ---
    def save_manifest(
        self,
        manifest_data: Dict[str, Any],
        dataset_version: str = config.DEFAULT_DATASET_VERSION,
    ) -> Path:
        """Save dataset manifest to dataset/manifests/{version}_manifest.json."""
        dest_dir = self.root_dir / "manifests"
        dest_dir.mkdir(parents=True, exist_ok=True)
        file_path = dest_dir / f"{dataset_version}_manifest.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        logger.info(f"[Storage] Saved dataset manifest to {file_path}")
        return file_path

    def save_quality_report(
        self,
        report_data: Dict[str, Any],
        markdown_content: str,
        dataset_version: str = config.DEFAULT_DATASET_VERSION,
    ) -> Tuple[Path, Path]:
        """Save dataset quality report in both JSON and Markdown formats."""
        dest_dir = self.root_dir / "manifests"
        dest_dir.mkdir(parents=True, exist_ok=True)

        json_path = dest_dir / f"{dataset_version}_quality_report.json"
        md_path = dest_dir / f"{dataset_version}_quality_report.md"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        logger.info(f"[Storage] Saved quality report to {json_path} and {md_path}")
        return json_path, md_path
