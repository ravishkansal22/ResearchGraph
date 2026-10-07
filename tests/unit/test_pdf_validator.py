"""Unit tests for PDFValidator and structural checks."""

import tempfile
from pathlib import Path
import pytest
from dataset.schemas.canonical_paper import PDFValidationStatus
from pipelines.ingestion.fulltext.validator import PDFValidator


def test_validator_detects_html_masquerade(tmp_path: Path):
    html_file = tmp_path / "fake_paper.pdf"
    html_file.write_bytes(b"<!DOCTYPE html><html><head><title>Login</title></head><body>Access Denied</body></html>")

    validator = PDFValidator()
    result = validator.validate_file(html_file, content_type="text/html")
    assert not result["is_valid_pdf"]
    assert result["validation_status"] in (PDFValidationStatus.HTML_NOT_PDF, PDFValidationStatus.PAYWALL)


def test_validator_detects_empty_file(tmp_path: Path):
    empty_file = tmp_path / "empty.pdf"
    empty_file.write_bytes(b"")

    validator = PDFValidator()
    result = validator.validate_file(empty_file)
    assert not result["is_valid_pdf"]
    assert result["validation_status"] == PDFValidationStatus.EMPTY_FILE


def test_validator_detects_invalid_magic_bytes(tmp_path: Path):
    corrupt_file = tmp_path / "corrupt.pdf"
    corrupt_file.write_bytes(b"SOME_RANDOM_BINARY_DATA_WITHOUT_PDF_HEADER_PADDING_BYTES" * 50)

    validator = PDFValidator()
    result = validator.validate_file(corrupt_file)
    assert not result["is_valid_pdf"]
    assert result["validation_status"] == PDFValidationStatus.INVALID_PDF


def test_validator_sha256_calculation(tmp_path: Path):
    sample_file = tmp_path / "sample.pdf"
    sample_file.write_bytes(b"%PDF-1.4 test content")

    hash_val = PDFValidator.calculate_sha256(sample_file)
    assert isinstance(hash_val, str)
    assert len(hash_val) == 64
