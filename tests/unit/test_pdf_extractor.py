"""Unit tests for PDF text extractor and layout disambiguation."""

from pathlib import Path
import pytest
from dataset.schemas.document_processing import LayoutType
from pipelines.processing.extractor import PDFExtractor, TextBlock, TextLine, TextSpan


def test_pdf_extractor_file_not_found(tmp_path):
    extractor = PDFExtractor()
    non_existent = tmp_path / "missing.pdf"
    with pytest.raises(FileNotFoundError):
        extractor.extract_document(non_existent)


def test_order_blocks_single_column():
    extractor = PDFExtractor()
    blocks = [
        TextBlock(block_id=0, text="First block", bbox=(50.0, 100.0, 500.0, 150.0), page_number=1),
        TextBlock(block_id=1, text="Second block", bbox=(50.0, 200.0, 500.0, 250.0), page_number=1),
        TextBlock(block_id=2, text="Third block", bbox=(50.0, 300.0, 500.0, 350.0), page_number=1),
    ]
    layout, ordered = extractor._order_blocks_for_reading(blocks, page_width=600.0, page_height=800.0)
    assert layout == LayoutType.SINGLE_COLUMN
    assert len(ordered) == 3
    assert [b.text for b in ordered] == ["First block", "Second block", "Third block"]


def test_order_blocks_two_column_reordering():
    extractor = PDFExtractor()
    # Interleaved coordinates simulating 2 columns
    blocks = [
        TextBlock(block_id=0, text="Title Wide", bbox=(50.0, 50.0, 550.0, 80.0), page_number=1),
        TextBlock(block_id=1, text="Col1 Line1", bbox=(50.0, 100.0, 250.0, 150.0), page_number=1),
        TextBlock(block_id=2, text="Col2 Line1", bbox=(350.0, 100.0, 550.0, 150.0), page_number=1),
        TextBlock(block_id=3, text="Col1 Line2", bbox=(50.0, 160.0, 250.0, 200.0), page_number=1),
        TextBlock(block_id=4, text="Col2 Line2", bbox=(350.0, 160.0, 550.0, 200.0), page_number=1),
    ]
    layout, ordered = extractor._order_blocks_for_reading(blocks, page_width=600.0, page_height=800.0)
    assert layout == LayoutType.TWO_COLUMN
    texts = [b.text for b in ordered]
    assert texts[0] == "Title Wide"
    assert texts[1] == "Col1 Line1"
    assert texts[2] == "Col1 Line2"
    assert texts[3] == "Col2 Line1"
    assert texts[4] == "Col2 Line2"


def test_pilot_pdf_real_extraction():
    cache_pdf = Path("dataset/fulltext/cache/rg_doi_b29976e1c44e.pdf")
    if not cache_pdf.exists():
        pytest.skip("Pilot PDF not cached on disk")

    extractor = PDFExtractor()
    pages, meta = extractor.extract_document(cache_pdf)
    assert len(pages) == 5
    assert meta["parser_used"] == "fitz-pymupdf"
    assert sum(p.char_count for p in pages) > 20000
    assert not any(p.is_blank for p in pages)
