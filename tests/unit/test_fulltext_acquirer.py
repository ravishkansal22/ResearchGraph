"""Unit tests for OnDemandFullTextAcquirer source priority, caching, and lifecycle."""

from pathlib import Path
import pytest
from dataset.schemas.canonical_paper import (
    CanonicalPaper,
    FullTextAcquisitionStatus,
    OpenAccessInfo,
    PDFValidationStatus,
)
from pipelines.ingestion.fulltext.acquirer import OnDemandFullTextAcquirer


def test_source_priority_resolution():
    acquirer = OnDemandFullTextAcquirer()

    # Priority 1: Direct PDF in fulltext_url
    p1 = CanonicalPaper(
        canonical_id="rg_direct",
        title="Direct PDF Paper",
        fulltext_url="https://example.com/paper.pdf",
        arxiv_id="2401.00001",
    )
    url, src_type = acquirer.determine_source_priority(p1)
    assert url == "https://example.com/paper.pdf"
    assert src_type == "direct_pdf"

    # Priority 2: arXiv ID
    p2 = CanonicalPaper(
        canonical_id="rg_arxiv",
        title="arXiv Paper",
        arxiv_id="2401.12345",
    )
    url, src_type = acquirer.determine_source_priority(p2)
    assert url == "https://arxiv.org/pdf/2401.12345.pdf"
    assert src_type == "arxiv"

    # Priority 3: Open Access URL
    p3 = CanonicalPaper(
        canonical_id="rg_oa",
        title="OA Paper",
        open_access=OpenAccessInfo(is_oa=True, oa_url="https://zenodo.org/record/12345"),
    )
    url, src_type = acquirer.determine_source_priority(p3)
    assert url == "https://zenodo.org/record/12345"
    assert src_type == "repository"


def test_acquirer_unavailable_handling():
    acquirer = OnDemandFullTextAcquirer()
    paper = CanonicalPaper(
        canonical_id="rg_closed",
        title="Paywalled Closed Book",
        open_access=OpenAccessInfo(is_oa=False, oa_url=None),
        fulltext_url=None,
    )
    up_paper, res = acquirer.fetch_paper(paper)
    assert up_paper.fulltext_status == FullTextAcquisitionStatus.UNAVAILABLE
    assert res.validation_status == PDFValidationStatus.UNAVAILABLE
    assert not res.download_success


def test_acquirer_idempotency_cache_hit(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True)

    paper = CanonicalPaper(
        canonical_id="rg_cached_doc",
        title="Cached Document",
        fulltext_url="https://example.com/some_doc.pdf",
    )

    # Pre-populate cache with a minimal valid PDF
    pdf_path = cache_dir / "rg_cached_doc.pdf"
    # Simple minimal valid PDF structure
    minimal_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF\n"
    )
    pdf_path.write_bytes(minimal_pdf)

    acquirer = OnDemandFullTextAcquirer(cache_dir=cache_dir)
    up_paper, res = acquirer.fetch_paper(paper, force_redownload=False)

    assert up_paper.fulltext_status == FullTextAcquisitionStatus.DOWNLOADED
    assert res.download_success
    assert res.is_valid_pdf
    assert "local cache" in res.notes
