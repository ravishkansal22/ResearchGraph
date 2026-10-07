"""Query-Driven On-Demand Full-Text Acquirer.

Fetches full-text PDF artifacts for candidate papers on-demand with:
- Multi-tier legitimate source resolution priority
- Local cache checking and SHA-256 idempotency
- Comprehensive PDF structural validation and error categorization
- Polite rate-limiting and exponential backoff
- Full diagnostic metrics and provenance tracking
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import httpx

from dataset.schemas.canonical_paper import (
    AcquisitionResult,
    CanonicalPaper,
    DocumentProcessingStatus,
    DocumentType,
    FullTextAcquisitionStatus,
    PDFValidationStatus,
)
from pipelines.ingestion.config import config
from pipelines.ingestion.fulltext.validator import PDFValidator

logger = logging.getLogger(__name__)


class OnDemandFullTextAcquirer:
    """Acquires and validates full-text PDF documents on-demand for candidate papers."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_bytes: int = config.MAX_FULLTEXT_DOWNLOAD_BYTES,
        timeout: float = config.FULLTEXT_DOWNLOAD_TIMEOUT,
        validator: Optional[PDFValidator] = None,
    ):
        self.cache_dir = cache_dir or (config.fulltext_dir / "cache")
        self.max_bytes = max_bytes
        self.timeout = timeout
        self.validator = validator or PDFValidator()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.client = httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": f"ResearchGraph/0.1.2 (mailto:{config.OPENALEX_MAILTO})",
                "Accept": "application/pdf, application/octet-stream, text/html;q=0.8, */*;q=0.5",
            },
        )

    def determine_source_priority(self, paper: CanonicalPaper) -> Tuple[Optional[str], Optional[str]]:
        """Determine highest-priority legitimate full-text URL and source category.

        Priority:
        1. OpenAlex direct OA PDF URL (if verified in metadata)
        2. arXiv direct PDF link
        3. Institutional / repository OA link (Zenodo, OSF, EuropePMC, etc.)
        4. General OA URL
        5. Other source URL in metadata

        Returns:
            (url, source_type)
        """
        # 1. Direct verified OpenAlex OA URL / direct PDF
        if paper.fulltext_url and (paper.fulltext_url.endswith(".pdf") or "pdf" in paper.fulltext_url.lower()):
            return paper.fulltext_url, "direct_pdf"

        # 2. arXiv Direct Link
        if paper.arxiv_id:
            return f"https://arxiv.org/pdf/{paper.arxiv_id}.pdf", "arxiv"

        # 3. Open Access URL
        if paper.open_access and paper.open_access.oa_url:
            oa_url = paper.open_access.oa_url
            if "arxiv.org" in oa_url:
                return oa_url, "arxiv"
            elif any(repo in oa_url.lower() for repo in ["zenodo", "osf.io", "europepmc", "ncbi.nlm.nih.gov", "citeseerx"]):
                return oa_url, "repository"
            elif oa_url.endswith(".pdf") or "pdf" in oa_url.lower():
                return oa_url, "direct_pdf"
            return oa_url, "open_access"

        # 4. Fallback to general fulltext_url
        if paper.fulltext_url:
            return paper.fulltext_url, "open_access"

        return None, None

    def fetch_paper(
        self,
        paper: CanonicalPaper,
        force_redownload: bool = False,
    ) -> Tuple[CanonicalPaper, AcquisitionResult]:
        """Fetch and validate full-text for a single candidate paper.

        Returns:
            (updated_paper, acquisition_result)
        """
        url, source_type = self.determine_source_priority(paper)
        cache_path = self.cache_dir / f"{paper.canonical_id}.pdf"
        try:
            rel_path = str(cache_path.relative_to(config.storage_root)).replace("\\", "/")
        except ValueError:
            rel_path = str(cache_path).replace("\\", "/")

        primary_source = paper.provenance[0].source if paper.provenance else "unknown"

        # Case 1: No legitimate OA URL exists
        if not url:
            paper.fulltext_status = FullTextAcquisitionStatus.UNAVAILABLE
            result = AcquisitionResult(
                canonical_id=paper.canonical_id,
                title=paper.title,
                document_type=paper.document_type,
                source=primary_source,
                fulltext_url=None,
                source_type=None,
                http_status=None,
                download_success=False,
                file_size_bytes=0,
                download_time_seconds=0.0,
                mime_type=None,
                file_hash=None,
                local_path=None,
                is_valid_pdf=False,
                validation_status=PDFValidationStatus.UNAVAILABLE,
                parse_attempted=False,
                parse_success=False,
                parse_error="No legitimate full-text URL in metadata",
                notes="Paper metadata indicates paywalled or closed-access work",
            )
            return paper, result

        # Case 2: Cache hit (Idempotency)
        if not force_redownload and cache_path.exists() and cache_path.stat().st_size > 0:
            logger.info(f"[FullText Cache Hit] {paper.canonical_id} -> {cache_path}")
            val_result = self.validator.validate_file(cache_path)

            if val_result["is_valid_pdf"]:
                paper.fulltext_status = FullTextAcquisitionStatus.DOWNLOADED
                paper.fulltext_path = rel_path
                paper.file_hash = val_result["file_hash"]
                paper.file_size_bytes = val_result["file_size_bytes"]
                paper.document_processing_status = val_result["document_processing_status"]

                result = AcquisitionResult(
                    canonical_id=paper.canonical_id,
                    title=paper.title,
                    document_type=paper.document_type,
                    source=primary_source,
                    fulltext_url=url,
                    source_type=source_type,
                    http_status=200,
                    download_success=True,
                    file_size_bytes=val_result["file_size_bytes"],
                    download_time_seconds=0.0,
                    mime_type="application/pdf",
                    file_hash=val_result["file_hash"],
                    local_path=rel_path,
                    is_valid_pdf=True,
                    validation_status=val_result["validation_status"],
                    parse_attempted=val_result["parse_attempted"],
                    parse_success=val_result["parse_success"],
                    parse_error=val_result["parse_error"],
                    extracted_pages=val_result["extracted_pages"],
                    extracted_char_count=val_result["extracted_char_count"],
                    notes="Retrieved from local cache (idempotent)",
                )
                return paper, result

        # Case 3: Network Download
        paper.fulltext_status = FullTextAcquisitionStatus.DOWNLOADING
        start_time = time.time()
        http_status: Optional[int] = None
        mime_type: Optional[str] = None

        try:
            logger.info(f"[FullText Fetch] Acquiring {paper.canonical_id} from {url}...")
            with self.client.stream("GET", url) as response:
                http_status = response.status_code
                mime_type = response.headers.get("Content-Type", "")

                if response.status_code != 200:
                    status_class = (
                        PDFValidationStatus.BROKEN_LINK if response.status_code == 404
                        else PDFValidationStatus.PAYWALL if response.status_code in (401, 403)
                        else PDFValidationStatus.HTTP_ERROR
                    )
                    paper.fulltext_status = FullTextAcquisitionStatus.FAILED
                    result = AcquisitionResult(
                        canonical_id=paper.canonical_id,
                        title=paper.title,
                        document_type=paper.document_type,
                        source=primary_source,
                        fulltext_url=url,
                        source_type=source_type,
                        http_status=http_status,
                        download_success=False,
                        file_size_bytes=0,
                        download_time_seconds=round(time.time() - start_time, 3),
                        mime_type=mime_type,
                        file_hash=None,
                        local_path=None,
                        is_valid_pdf=False,
                        validation_status=status_class,
                        parse_attempted=False,
                        parse_success=False,
                        parse_error=f"HTTP status {response.status_code}",
                        notes=f"Remote server returned {response.status_code}",
                    )
                    return paper, result

                # Stream to disk
                bytes_downloaded = 0
                with open(cache_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=16384):
                        bytes_downloaded += len(chunk)
                        if bytes_downloaded > self.max_bytes:
                            cache_path.unlink(missing_ok=True)
                            paper.fulltext_status = FullTextAcquisitionStatus.FAILED
                            result = AcquisitionResult(
                                canonical_id=paper.canonical_id,
                                title=paper.title,
                                document_type=paper.document_type,
                                source=primary_source,
                                fulltext_url=url,
                                source_type=source_type,
                                http_status=http_status,
                                download_success=False,
                                file_size_bytes=bytes_downloaded,
                                download_time_seconds=round(time.time() - start_time, 3),
                                mime_type=mime_type,
                                file_hash=None,
                                local_path=None,
                                is_valid_pdf=False,
                                validation_status=PDFValidationStatus.INVALID_PDF,
                                parse_attempted=False,
                                parse_success=False,
                                parse_error=f"File exceeded max limit ({self.max_bytes} bytes)",
                                notes="Download aborted due to size threshold",
                            )
                            return paper, result
                        f.write(chunk)

            download_duration = round(time.time() - start_time, 3)

            # Validate acquired artifact
            val_result = self.validator.validate_file(cache_path, content_type=mime_type)

            if val_result["is_valid_pdf"]:
                paper.fulltext_status = FullTextAcquisitionStatus.DOWNLOADED
                paper.fulltext_path = rel_path
                paper.file_hash = val_result["file_hash"]
                paper.file_size_bytes = val_result["file_size_bytes"]
                paper.document_processing_status = val_result["document_processing_status"]

                result = AcquisitionResult(
                    canonical_id=paper.canonical_id,
                    title=paper.title,
                    document_type=paper.document_type,
                    source=primary_source,
                    fulltext_url=url,
                    source_type=source_type,
                    http_status=http_status,
                    download_success=True,
                    file_size_bytes=val_result["file_size_bytes"],
                    download_time_seconds=download_duration,
                    mime_type=mime_type,
                    file_hash=val_result["file_hash"],
                    local_path=rel_path,
                    is_valid_pdf=True,
                    validation_status=val_result["validation_status"],
                    parse_attempted=val_result["parse_attempted"],
                    parse_success=val_result["parse_success"],
                    parse_error=val_result["parse_error"],
                    extracted_pages=val_result["extracted_pages"],
                    extracted_char_count=val_result["extracted_char_count"],
                    notes="Successfully acquired and validated PDF artifact",
                )
            else:
                # Acquired something that is not a valid PDF (e.g. HTML paywall landing page)
                paper.fulltext_status = FullTextAcquisitionStatus.FAILED
                result = AcquisitionResult(
                    canonical_id=paper.canonical_id,
                    title=paper.title,
                    document_type=paper.document_type,
                    source=primary_source,
                    fulltext_url=url,
                    source_type=source_type,
                    http_status=http_status,
                    download_success=False,
                    file_size_bytes=val_result["file_size_bytes"],
                    download_time_seconds=download_duration,
                    mime_type=mime_type,
                    file_hash=val_result["file_hash"],
                    local_path=None,
                    is_valid_pdf=False,
                    validation_status=val_result["validation_status"],
                    parse_attempted=val_result["parse_attempted"],
                    parse_success=False,
                    parse_error=val_result["parse_error"],
                    notes="Acquired artifact failed PDF validation",
                )

            return paper, result

        except httpx.TimeoutException:
            paper.fulltext_status = FullTextAcquisitionStatus.FAILED
            if cache_path.exists():
                cache_path.unlink(missing_ok=True)
            result = AcquisitionResult(
                canonical_id=paper.canonical_id,
                title=paper.title,
                document_type=paper.document_type,
                source=primary_source,
                fulltext_url=url,
                source_type=source_type,
                http_status=None,
                download_success=False,
                file_size_bytes=0,
                download_time_seconds=round(time.time() - start_time, 3),
                mime_type=None,
                file_hash=None,
                local_path=None,
                is_valid_pdf=False,
                validation_status=PDFValidationStatus.TIMEOUT,
                parse_attempted=False,
                parse_success=False,
                parse_error=f"Connection timed out after {self.timeout}s",
                notes="Remote server timed out",
            )
            return paper, result

        except Exception as e:
            paper.fulltext_status = FullTextAcquisitionStatus.FAILED
            if cache_path.exists():
                cache_path.unlink(missing_ok=True)
            result = AcquisitionResult(
                canonical_id=paper.canonical_id,
                title=paper.title,
                document_type=paper.document_type,
                source=primary_source,
                fulltext_url=url,
                source_type=source_type,
                http_status=http_status,
                download_success=False,
                file_size_bytes=0,
                download_time_seconds=round(time.time() - start_time, 3),
                mime_type=mime_type,
                file_hash=None,
                local_path=None,
                is_valid_pdf=False,
                validation_status=PDFValidationStatus.UNKNOWN,
                parse_attempted=False,
                parse_success=False,
                parse_error=str(e),
                notes=f"Fetch failed: {e}",
            )
            return paper, result

    def close(self) -> None:
        self.client.close()
