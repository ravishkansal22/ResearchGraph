"""Full-Text Acquisition and Artifact Organization Module.

Handles legitimate open-access artifact discovery, polite downloading, and linking
to canonical ResearchGraph entities.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import httpx

from dataset.schemas.canonical_paper import CanonicalPaper, FulltextStatus
from pipelines.ingestion.config import config

logger = logging.getLogger(__name__)


class FullTextCollector:
    """Acquires legitimate open-access full-text PDFs/artifacts for canonical papers."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        max_bytes: int = config.MAX_FULLTEXT_DOWNLOAD_BYTES,
        timeout: float = config.FULLTEXT_DOWNLOAD_TIMEOUT,
    ):
        self.output_dir = output_dir or config.fulltext_dir
        self.max_bytes = max_bytes
        self.timeout = timeout
        self.client = httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": f"ResearchGraph/0.1.0 (mailto:{config.OPENALEX_MAILTO})",
                "Accept": "application/pdf, application/octet-stream, text/html",
            },
        )

    def determine_fulltext_url(self, paper: CanonicalPaper) -> Optional[str]:
        """Identify the highest quality legitimate full-text source URL."""
        if paper.fulltext_url:
            return paper.fulltext_url

        # Check arXiv
        if paper.arxiv_id:
            return f"https://arxiv.org/pdf/{paper.arxiv_id}.pdf"

        # Check Open Access URL
        if paper.open_access and paper.open_access.oa_url:
            return paper.open_access.oa_url

        return None

    def download_fulltext(
        self,
        paper: CanonicalPaper,
        version_dir: Path,
    ) -> Tuple[FulltextStatus, Optional[str]]:
        """Attempt to download full-text artifact for a single canonical paper."""
        url = self.determine_fulltext_url(paper)
        if not url:
            return FulltextStatus.FULLTEXT_UNAVAILABLE, None

        version_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = version_dir / f"{paper.canonical_id}.pdf"

        if artifact_path.exists() and artifact_path.stat().st_size > 0:
            logger.debug(f"[FullText] Artifact already exists: {artifact_path}")
            return FulltextStatus.FULLTEXT_AVAILABLE, str(artifact_path.relative_to(config.storage_root))

        try:
            logger.info(f"[FullText] Downloading from {url} for {paper.canonical_id}...")
            with self.client.stream("GET", url) as response:
                if response.status_code != 200:
                    logger.warning(f"[FullText] Status {response.status_code} for {url}")
                    return FulltextStatus.FULLTEXT_FAILED, None

                content_type = response.headers.get("Content-Type", "").lower()
                # Check for HTML login walls or paywall landing pages
                if "text/html" in content_type and not ("arxiv.org" in url or "pdf" in url):
                    logger.warning(f"[FullText] Encountered HTML landing page rather than PDF for {url}")
                    return FulltextStatus.FULLTEXT_FAILED, None

                bytes_downloaded = 0
                with open(artifact_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        bytes_downloaded += len(chunk)
                        if bytes_downloaded > self.max_bytes:
                            logger.warning(f"[FullText] Exceeded max file size ({self.max_bytes} bytes)")
                            artifact_path.unlink(missing_ok=True)
                            return FulltextStatus.FULLTEXT_FAILED, None
                        f.write(chunk)

            rel_path = str(artifact_path.relative_to(config.storage_root))
            return FulltextStatus.FULLTEXT_AVAILABLE, rel_path

        except Exception as e:
            logger.warning(f"[FullText] Failed to download {url}: {e}")
            if artifact_path.exists():
                artifact_path.unlink(missing_ok=True)
            return FulltextStatus.FULLTEXT_FAILED, None

    def process_papers(
        self,
        papers: List[CanonicalPaper],
        dataset_version: str = config.DEFAULT_DATASET_VERSION,
        limit_downloads: Optional[int] = None,
    ) -> Tuple[List[CanonicalPaper], Dict[str, Any]]:
        """Process full-text discovery and download for a list of canonical papers."""
        version_dir = self.output_dir / dataset_version
        version_dir.mkdir(parents=True, exist_ok=True)

        downloaded_count = 0
        unavailable_count = 0
        failed_count = 0
        skipped_count = 0

        for i, paper in enumerate(papers):
            if limit_downloads is not None and downloaded_count >= limit_downloads:
                paper.fulltext_available = FulltextStatus.FULLTEXT_NOT_CHECKED
                skipped_count += 1
                continue

            status, rel_path = self.download_fulltext(paper, version_dir)
            paper.fulltext_available = status
            if rel_path:
                paper.fulltext_path = rel_path
                downloaded_count += 1
            elif status == FulltextStatus.FULLTEXT_UNAVAILABLE:
                unavailable_count += 1
            elif status == FulltextStatus.FULLTEXT_FAILED:
                failed_count += 1

            # Polite delay between fulltext downloads
            time.sleep(0.5)

        stats = {
            "total_papers": len(papers),
            "fulltext_available": downloaded_count,
            "fulltext_unavailable": unavailable_count,
            "fulltext_failures": failed_count,
            "fulltext_skipped": skipped_count,
        }
        return papers, stats

    def close(self) -> None:
        self.client.close()
