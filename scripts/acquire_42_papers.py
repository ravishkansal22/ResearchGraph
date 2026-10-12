"""Controlled acquisition of 42 additional diverse papers for Phase 2 expansion.

Reuses the existing 8 pilot papers, evaluates candidate open-access URLs from the
v0.1.1 canonical corpus, rejects paywalls/HTML pages, and acquires exactly 42
additional valid PDFs with cryptographic checksums and provenance.
"""

import csv
import json
import logging
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import httpx

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from dataset.schemas.canonical_paper import (
    AcquisitionResult,
    CanonicalPaper,
    DocumentProcessingStatus,
    FullTextAcquisitionStatus,
    PDFValidationStatus,
)
from pipelines.ingestion.config import config
from pipelines.ingestion.fulltext.validator import PDFValidator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def build_candidate_url_map() -> Dict[str, List[str]]:
    """Build mapping of canonical paper IDs or DOIs to direct PDF URLs from OpenAlex raw data."""
    raw_files = list(Path("dataset/raw/openalex").glob("**/openalex_records.jsonl"))
    mapping: Dict[str, List[str]] = {}
    for p in raw_files:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                raw = rec.get("raw_data", {})
                wid = raw.get("id")
                doi = raw.get("doi")
                urls = []
                best_oa = raw.get("best_oa_location") or {}
                if best_oa.get("pdf_url"):
                    urls.append(best_oa.get("pdf_url"))
                for loc in raw.get("locations") or []:
                    u = loc.get("pdf_url")
                    if u and u not in urls:
                        urls.append(u)
                if wid and urls:
                    mapping[wid] = urls
                if doi and urls:
                    clean_doi = doi.lower().replace("https://doi.org/", "").strip()
                    mapping[clean_doi] = urls
    return mapping


def load_canonical_candidates(pilot_ids: Set[str], openalex_map: Dict[str, List[str]]) -> List[Tuple[CanonicalPaper, List[str]]]:
    """Load canonical papers from v0.1.1 and attach prioritized direct URLs."""
    jsonl_path = Path("dataset/processed/v0.1.1/canonical_papers.jsonl")
    candidates: List[Tuple[CanonicalPaper, List[str]]] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            p = CanonicalPaper(**json.loads(line))
            if p.canonical_id in pilot_ids:
                continue

            urls: List[str] = []
            # 1. arXiv direct link
            if p.arxiv_id:
                urls.append(f"https://arxiv.org/pdf/{p.arxiv_id}.pdf")
            # 2. OpenAlex raw locations
            if p.doi:
                clean_doi = p.doi.lower().replace("https://doi.org/", "").strip()
                if clean_doi in openalex_map:
                    urls.extend(openalex_map[clean_doi])
            srecs = p.source_records
            if isinstance(srecs, dict):
                for wid in srecs.get("openalex") or []:
                    if wid in openalex_map:
                        urls.extend(openalex_map[wid])
            # 3. Direct PDF from metadata
            if p.fulltext_url and ("pdf" in p.fulltext_url.lower() or "arxiv.org" in p.fulltext_url):
                urls.append(p.fulltext_url)
            # 4. OpenAccess oa_url if direct PDF
            if p.open_access and p.open_access.oa_url and ("pdf" in p.open_access.oa_url.lower() or "arxiv.org" in p.open_access.oa_url):
                urls.append(p.open_access.oa_url)
            # 5. OpenAccess oa_url general fallback
            if p.open_access and p.open_access.oa_url:
                urls.append(p.open_access.oa_url)

            # Deduplicate preserving order
            seen = set()
            dedup_urls = []
            for u in urls:
                if u and u not in seen:
                    seen.add(u)
                    dedup_urls.append(u)

            if dedup_urls:
                candidates.append((p, dedup_urls))

    return candidates


def run_controlled_acquisition(target_new_count: int = 42):
    """Acquire target_new_count valid diverse PDFs."""
    pilot_8 = {
        "rg_doi_b29976e1c44e",
        "rg_doi_3891d117baca",
        "rg_doi_cb0ceeff2e31",
        "rg_doi_da062bd35ba4",
        "rg_doi_7c2fa4c39358",
        "rg_doi_4e5057959cae",
        "rg_doi_5c65e2d95d8f",
        "rg_doi_21feca2c78f6",
    }

    cache_dir = Path("dataset/fulltext/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir = Path("dataset/manifests")
    manifest_dir.mkdir(parents=True, exist_ok=True)

    validator = PDFValidator()

    logger.info("Building OpenAlex direct URL map...")
    openalex_map = build_candidate_url_map()
    logger.info(f"Built {len(openalex_map)} URL mappings.")

    logger.info("Loading candidates...")
    candidates = load_canonical_candidates(pilot_8, openalex_map)
    logger.info(f"Found {len(candidates)} candidates with available URLs.")

    timeout_config = httpx.Timeout(12.0, connect=6.0, read=12.0)
    client = httpx.Client(
        timeout=timeout_config,
        follow_redirects=True,
        headers={
            "User-Agent": "ResearchGraph/0.3.0 (mailto:researchgraph-pilot@deepmind-academic.org)",
            "Accept": "application/pdf, application/octet-stream, text/html;q=0.8, */*;q=0.5",
        },
    )

    acquired_new: List[Tuple[CanonicalPaper, Dict[str, Any]]] = []
    attempt_records: List[Dict[str, Any]] = []

    publisher_counts = Counter()
    logger.info(f"Targeting {target_new_count} additional valid papers...")

    t_start = time.time()

    for idx, (paper, urls) in enumerate(candidates, start=1):
        if len(acquired_new) >= target_new_count:
            break

        cid = paper.canonical_id
        target_path = cache_dir / f"{cid}.pdf"

        # Check if already cached and valid
        if target_path.exists() and target_path.stat().st_size > 0:
            val = validator.validate_file(target_path)
            if val["is_valid_pdf"] and val["extracted_pages"] > 0:
                logger.info(f"[{len(acquired_new)+1}/{target_new_count}] Existing valid cached PDF: {cid} ({paper.title[:50]})")
                rec = {
                    "canonical_id": cid,
                    "title": paper.title,
                    "doi": paper.doi,
                    "document_type": paper.document_type.value if hasattr(paper.document_type, "value") else str(paper.document_type),
                    "url": urls[0],
                    "status": "CACHE_HIT",
                    "http_status": 200,
                    "download_time_s": 0.0,
                    "file_size": val["file_size_bytes"],
                    "file_hash": val["file_hash"],
                    "pages": val["extracted_pages"],
                    "char_count": val["extracted_char_count"],
                    "host": urlparse(urls[0]).netloc,
                    "notes": "Valid cached PDF",
                }
                acquired_new.append((paper, rec))
                attempt_records.append(rec)
                publisher_counts[rec["host"]] += 1
                continue

        # Try urls in priority order
        for u in urls:
            host = urlparse(u).netloc
            # Skip known unviable / paywalled endpoints
            if any(bad in host for bad in ["api.elsevier.com", "xplorestaging.ieee.org"]):
                continue
            if "doi.org" in host and not u.endswith(".pdf"):
                continue

            logger.info(f"[{len(acquired_new)+1}/{target_new_count}] Fetching {cid} via {u[:75]}...")
            t0 = time.time()
            try:
                with client.stream("GET", u) as resp:
                    dt = time.time() - t0
                    if resp.status_code == 200:
                        cl = resp.headers.get("content-length")
                        if cl and int(cl) > 35 * 1024 * 1024:
                            logger.info(f"Skipping oversized artifact ({int(cl):,} bytes)")
                            continue

                        chunks = []
                        tot = 0
                        timed_out = False
                        for chunk in resp.iter_bytes(chunk_size=65536):
                            if time.time() - t0 > 10.0:
                                timed_out = True
                                break
                            tot += len(chunk)
                            if tot > 35 * 1024 * 1024:
                                break
                            chunks.append(chunk)

                        if timed_out:
                            logger.info(f"Transfer timed out (>10s) for {cid} from {host}")
                            continue

                        content = b"".join(chunks)
                        temp_path = cache_dir / f"{cid}.tmp.pdf"
                        temp_path.write_bytes(content)

                        val = validator.validate_file(temp_path)
                        if val["is_valid_pdf"] and val["extracted_pages"] > 0:
                            temp_path.replace(target_path)
                            logger.info(f"SUCCESS: {cid} ({val['extracted_pages']} pages, {val['file_size_bytes']:,} bytes)")
                            rec = {
                                "canonical_id": cid,
                                "title": paper.title,
                                "doi": paper.doi,
                                "document_type": paper.document_type.value if hasattr(paper.document_type, "value") else str(paper.document_type),
                                "url": u,
                                "status": "SUCCESS_PDF",
                                "http_status": 200,
                                "download_time_s": round(dt, 2),
                                "file_size": val["file_size_bytes"],
                                "file_hash": val["file_hash"],
                                "pages": val["extracted_pages"],
                                "char_count": val["extracted_char_count"],
                                "host": host,
                                "notes": f"Acquired from {host}",
                            }
                            acquired_new.append((paper, rec))
                            attempt_records.append(rec)
                            publisher_counts[host] += 1
                            break
                        else:
                            temp_path.unlink(missing_ok=True)
                            logger.info(f"Rejected: {cid} -> {val['validation_status'].value}")
                            attempt_records.append({
                                "canonical_id": cid,
                                "title": paper.title,
                                "doi": paper.doi,
                                "document_type": paper.document_type.value if hasattr(paper.document_type, "value") else str(paper.document_type),
                                "url": u,
                                "status": val["validation_status"].value,
                                "http_status": 200,
                                "download_time_s": round(dt, 2),
                                "file_size": len(content),
                                "file_hash": None,
                                "pages": 0,
                                "char_count": 0,
                                "host": host,
                                "notes": f"Failed validation: {val['validation_status'].value}",
                            })
                    else:
                        logger.info(f"HTTP {resp.status_code} for {cid}")
                        attempt_records.append({
                            "canonical_id": cid,
                            "title": paper.title,
                            "doi": paper.doi,
                            "document_type": paper.document_type.value if hasattr(paper.document_type, "value") else str(paper.document_type),
                            "url": u,
                            "status": f"HTTP_{resp.status_code}",
                            "http_status": resp.status_code,
                            "download_time_s": round(dt, 2),
                            "file_size": 0,
                            "file_hash": None,
                            "pages": 0,
                            "char_count": 0,
                            "host": host,
                            "notes": f"Remote server returned {resp.status_code}",
                        })
            except Exception as e:
                logger.info(f"Exception for {cid}: {e}")
                attempt_records.append({
                    "canonical_id": cid,
                    "title": paper.title,
                    "doi": paper.doi,
                    "document_type": paper.document_type.value if hasattr(paper.document_type, "value") else str(paper.document_type),
                    "url": u,
                    "status": "TIMEOUT" if "timeout" in str(e).lower() else "ERROR",
                    "http_status": 0,
                    "download_time_s": 0.0,
                    "file_size": 0,
                    "file_hash": None,
                    "pages": 0,
                    "char_count": 0,
                    "host": host,
                    "notes": str(e),
                })
            time.sleep(0.25)

    duration = time.time() - t_start
    logger.info(f"Acquired {len(acquired_new)} / {target_new_count} valid additional papers in {duration:.1f}s.")

    # Export results CSV
    results_csv_path = manifest_dir / "fulltext_expansion_v0.3.0_results.csv"
    fieldnames = [
        "canonical_id", "title", "doi", "document_type", "url", "status",
        "http_status", "download_time_s", "file_size", "file_hash",
        "pages", "char_count", "host", "notes"
    ]
    with open(results_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in attempt_records:
            writer.writerow(r)

    # Export manifest JSON
    manifest_json_path = manifest_dir / "fulltext_expansion_v0.3.0_manifest.json"
    manifest_data = {
        "version": "v0.3.0-expansion",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_attempted": len(attempt_records),
        "target_new_count": target_new_count,
        "successfully_acquired_new": len(acquired_new),
        "pilot_baseline_count": len(pilot_8),
        "total_available_corpus": len(pilot_8) + len(acquired_new),
        "duration_seconds": round(duration, 2),
        "publisher_distribution": dict(publisher_counts),
        "acquired_inventory": [r for _, r in acquired_new],
    }
    with open(manifest_json_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    logger.info(f"Exported acquisition manifest to {manifest_json_path}")
    logger.info(f"Exported acquisition results to {results_csv_path}")

    return acquired_new, attempt_records


if __name__ == "__main__":
    acquired, attempts = run_controlled_acquisition(target_new_count=42)
    print(f"\nFinal Acquired Count: {len(acquired)} papers.")
