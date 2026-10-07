"""PDF Quality Validator and Basic Feasibility Checker.

Performs rigorous structural validation on downloaded artifacts:
- Checks magic bytes (%PDF-)
- Detects HTML error/paywall/login pages masquerading as PDFs
- Computes SHA-256 checksums
- Tests basic text extraction feasibility using pypdf/fitz
- Produces explicit failure classifications (PDFValidationStatus).
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dataset.schemas.canonical_paper import DocumentProcessingStatus, PDFValidationStatus

logger = logging.getLogger(__name__)

# Patterns indicative of HTML landing pages or paywalls
HTML_INDICATORS = [
    re.compile(rb"<!doctype\s+html", re.IGNORECASE),
    re.compile(rb"<html\b", re.IGNORECASE),
    re.compile(rb"<head\b", re.IGNORECASE),
    re.compile(rb"<body\b", re.IGNORECASE),
    re.compile(rb"access\s+denied", re.IGNORECASE),
    re.compile(rb"sign\s+in\s+to\s+view", re.IGNORECASE),
    re.compile(rb"purchase\s+pdf", re.IGNORECASE),
    re.compile(rb"subscription\s+required", re.IGNORECASE),
    re.compile(rb"cloudflare", re.IGNORECASE),
    re.compile(rb"captcha", re.IGNORECASE),
]


class PDFValidator:
    """Validates structural integrity and extractability of acquired PDF documents."""

    def __init__(
        self,
        min_bytes: int = 100,                 # 100 bytes min
        max_bytes: int = 60 * 1024 * 1024,    # 60 MB max
    ):
        self.min_bytes = min_bytes
        self.max_bytes = max_bytes

    @staticmethod
    def calculate_sha256(file_path: Path) -> str:
        """Compute cryptographic SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def validate_file(
        self,
        file_path: Path,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform comprehensive validation on an acquired file artifact.

        Returns:
            Dictionary with:
            - is_valid_pdf: bool
            - validation_status: PDFValidationStatus
            - file_size_bytes: int
            - file_hash: str
            - parse_attempted: bool
            - parse_success: bool
            - parse_error: Optional[str]
            - extracted_pages: Optional[int]
            - extracted_char_count: Optional[int]
            - document_processing_status: DocumentProcessingStatus
        """
        if not file_path.exists():
            return {
                "is_valid_pdf": False,
                "validation_status": PDFValidationStatus.EMPTY_FILE,
                "file_size_bytes": 0,
                "file_hash": None,
                "parse_attempted": False,
                "parse_success": False,
                "parse_error": "File does not exist on disk",
                "extracted_pages": 0,
                "extracted_char_count": 0,
                "document_processing_status": DocumentProcessingStatus.PARSE_FAILED,
            }

        file_size = file_path.stat().st_size
        if file_size == 0:
            return {
                "is_valid_pdf": False,
                "validation_status": PDFValidationStatus.EMPTY_FILE,
                "file_size_bytes": 0,
                "file_hash": None,
                "parse_attempted": False,
                "parse_success": False,
                "parse_error": "Zero-byte file received",
                "extracted_pages": 0,
                "extracted_char_count": 0,
                "document_processing_status": DocumentProcessingStatus.PARSE_FAILED,
            }

        file_hash = self.calculate_sha256(file_path)

        # Read header / prefix to check magic bytes and HTML markers
        with open(file_path, "rb") as f:
            header_sample = f.read(4096)

        # 1. Check for HTML markers masquerading as PDF
        is_html = any(pattern.search(header_sample) for pattern in HTML_INDICATORS)
        if is_html or (content_type and "text/html" in content_type.lower() and b"%PDF-" not in header_sample[:1024]):
            if any(term in header_sample.lower() for term in [b"access denied", b"paywall", b"purchase", b"subscription"]):
                status = PDFValidationStatus.PAYWALL
            else:
                status = PDFValidationStatus.HTML_NOT_PDF

            return {
                "is_valid_pdf": False,
                "validation_status": status,
                "file_size_bytes": file_size,
                "file_hash": file_hash,
                "parse_attempted": False,
                "parse_success": False,
                "parse_error": f"Artifact is an HTML page (detected {status.value})",
                "extracted_pages": 0,
                "extracted_char_count": 0,
                "document_processing_status": DocumentProcessingStatus.PARSE_FAILED,
            }

        # 2. Check Magic Bytes (%PDF-)
        if b"%PDF-" not in header_sample[:1024]:
            return {
                "is_valid_pdf": False,
                "validation_status": PDFValidationStatus.INVALID_PDF,
                "file_size_bytes": file_size,
                "file_hash": file_hash,
                "parse_attempted": False,
                "parse_success": False,
                "parse_error": "Missing %PDF- magic signature in file header",
                "extracted_pages": 0,
                "extracted_char_count": 0,
                "document_processing_status": DocumentProcessingStatus.PARSE_FAILED,
            }

        # 3. Check File Size Bounds
        if file_size < self.min_bytes:
            return {
                "is_valid_pdf": False,
                "validation_status": PDFValidationStatus.INVALID_PDF,
                "file_size_bytes": file_size,
                "file_hash": file_hash,
                "parse_attempted": False,
                "parse_success": False,
                "parse_error": f"File size too small ({file_size} bytes < {self.min_bytes} threshold)",
                "extracted_pages": 0,
                "extracted_char_count": 0,
                "document_processing_status": DocumentProcessingStatus.PARSE_FAILED,
            }

        # 4. Lightweight Parsing & Feasibility Check (using pypdf or pymupdf)
        parse_success = False
        parse_error = None
        extracted_pages = 0
        extracted_char_count = 0

        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            extracted_pages = len(reader.pages)
            if extracted_pages > 0:
                # Extract text from first 2 pages for validation check
                sample_text = ""
                for page in reader.pages[:2]:
                    sample_text += page.extract_text() or ""
                extracted_char_count = len(sample_text)
                parse_success = True
        except Exception as pypdf_err:
            try:
                import fitz
                doc = fitz.open(str(file_path))
                extracted_pages = len(doc)
                if extracted_pages > 0:
                    sample_text = ""
                    for i in range(min(2, extracted_pages)):
                        sample_text += doc[i].get_text() or ""
                    extracted_char_count = len(sample_text)
                    parse_success = True
                doc.close()
            except Exception as fitz_err:
                parse_success = False
                parse_error = f"PDF parsing error: pypdf({pypdf_err}), fitz({fitz_err})"

        validation_status = PDFValidationStatus.SUCCESS_PDF if parse_success else PDFValidationStatus.INVALID_PDF
        doc_proc_status = DocumentProcessingStatus.PARSED if parse_success else DocumentProcessingStatus.PARSE_FAILED

        return {
            "is_valid_pdf": parse_success,
            "validation_status": validation_status,
            "file_size_bytes": file_size,
            "file_hash": file_hash,
            "parse_attempted": True,
            "parse_success": parse_success,
            "parse_error": parse_error,
            "extracted_pages": extracted_pages,
            "extracted_char_count": extracted_char_count,
            "document_processing_status": doc_proc_status,
        }
