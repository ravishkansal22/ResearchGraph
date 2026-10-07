"""Unit tests for FulltextStatus distinctions."""

import pytest
from dataset.schemas.canonical_paper import FulltextStatus, CanonicalPaper


def test_fulltext_status_values():
    assert FulltextStatus.DISCOVERABLE.value == "DISCOVERABLE"
    assert FulltextStatus.DOWNLOADED.value == "DOWNLOADED"
    assert FulltextStatus.UNAVAILABLE.value == "UNAVAILABLE"
    assert FulltextStatus.NOT_CHECKED.value == "NOT_CHECKED"
    assert FulltextStatus.FAILED.value == "FAILED"


def test_fulltext_discoverable_is_not_downloaded():
    paper = CanonicalPaper(
        canonical_id="rg_oa_test",
        title="Open Access Paper",
        fulltext_status=FulltextStatus.DISCOVERABLE,
        fulltext_url="https://example.com/paper.pdf",
        fulltext_path=None,
    )
    assert paper.fulltext_status == FulltextStatus.DISCOVERABLE
    assert paper.fulltext_path is None
    assert paper.fulltext_status != FulltextStatus.DOWNLOADED


def test_fulltext_status_backward_compatibility():
    paper = CanonicalPaper(
        canonical_id="rg_oa_legacy",
        title="Legacy Status Paper",
        fulltext_status="DISCOVERABLE",
        fulltext_available="AVAILABLE",
    )
    assert paper.fulltext_status == FulltextStatus.DISCOVERABLE
    assert paper.fulltext_available == FulltextStatus.DISCOVERABLE
