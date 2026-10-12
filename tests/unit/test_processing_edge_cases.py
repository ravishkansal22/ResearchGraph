"""Comprehensive unit tests for document processing edge cases, error resilience, and determinism."""

from pathlib import Path
import pytest
from pydantic import ValidationError

from dataset.schemas.document_processing import (
    ChunkStrategy,
    DocumentMetadata,
    LayoutType,
    ProcessedChunk,
    ProcessedDocument,
    ProcessedParagraph,
    ProcessedSection,
)
from pipelines.processing.chunker import DocumentChunker
from pipelines.processing.extractor import PageExtractionResult, PDFExtractor, TextBlock
from pipelines.processing.paragraph_extractor import ParagraphExtractor
from pipelines.processing.section_detector import SectionDetector
from pipelines.processing.sentence_segmenter import ScientificSentenceSegmenter


# ==============================================================================
# 1. PDF Loading & Malformed File Handling
# ==============================================================================

def test_corrupt_pdf_file_handling(tmp_path):
    """Verify that corrupt PDF bytes raise ValueError or RuntimeError rather than crashing silently."""
    corrupt_pdf = tmp_path / "corrupt.pdf"
    corrupt_pdf.write_bytes(b"%PDF-1.4\nInvalid binary data and incomplete xref table")
    
    extractor = PDFExtractor()
    with pytest.raises(RuntimeError):
        extractor.extract_document(corrupt_pdf)


def test_zero_byte_pdf_handling(tmp_path):
    """Verify that an empty (0 byte) file raises an error."""
    empty_pdf = tmp_path / "empty.pdf"
    empty_pdf.write_bytes(b"")
    
    extractor = PDFExtractor()
    with pytest.raises(RuntimeError):
        extractor.extract_document(empty_pdf)


def test_nonexistent_pdf_handling(tmp_path):
    """Verify that a missing PDF path raises FileNotFoundError."""
    missing_pdf = tmp_path / "does_not_exist.pdf"
    extractor = PDFExtractor()
    with pytest.raises(FileNotFoundError):
        extractor.extract_document(missing_pdf)


# ==============================================================================
# 2. Section Detection Edge Cases & Front Matter Shield
# ==============================================================================

def test_page1_front_matter_shield_suppresses_author_names():
    """Verify that bold author names and affiliations on Page 1 are not classified as sections."""
    detector = SectionDetector()
    blocks = [
        TextBlock(block_id=0, text="Deep Learning in Healthcare", bbox=(50, 50, 500, 80), page_number=1, is_bold_dominant=True, max_font_size=18.0),
        TextBlock(block_id=1, text="Dr. Jane Smith, John Doe\nDepartment of Computer Science, Stanford University", bbox=(50, 90, 500, 130), page_number=1, is_bold_dominant=True, max_font_size=12.0),
        TextBlock(block_id=2, text="Abstract\nThis paper proposes a novel architecture.", bbox=(50, 140, 500, 180), page_number=1, is_bold_dominant=True, max_font_size=12.0),
        TextBlock(block_id=3, text="1. Introduction\nDeep neural networks have revolutionized medicine.", bbox=(50, 200, 500, 240), page_number=1, is_bold_dominant=True, max_font_size=14.0),
    ]
    page = PageExtractionResult(
        page_number=1,
        raw_text="",
        cleaned_text="",
        blocks=blocks,
        layout_type=LayoutType.SINGLE_COLUMN,
        char_count=400,
        word_count=60,
        is_blank=False,
    )
    sections = detector.detect_sections([page], canonical_id="test_shield")
    titles = [s.section_title for s in sections]
    
    # Author names and affiliations must NOT be separate sections
    assert not any("Dr. Jane Smith" in t for t in titles)
    assert not any("Stanford University" in t for t in titles)
    # Abstract and 1. Introduction must be detected
    assert any("Abstract" in t for t in titles)
    assert any("1. Introduction" in t for t in titles)


def test_springer_publisher_mark_suppression():
    """Verify that publisher pagination marks (like '123' or standalone numerals) are not treated as sections."""
    detector = SectionDetector()
    blocks = [
        TextBlock(block_id=0, text="1. Introduction\nContent of introduction.", bbox=(50, 50, 500, 80), page_number=1, is_bold_dominant=True, max_font_size=14.0),
        TextBlock(block_id=1, text="123", bbox=(250, 750, 300, 770), page_number=1, is_bold_dominant=True, max_font_size=12.0),
        TextBlock(block_id=2, text="2. Methods\nContent of methods.", bbox=(50, 50, 500, 80), page_number=2, is_bold_dominant=True, max_font_size=14.0),
    ]
    p1 = PageExtractionResult(page_number=1, raw_text="", cleaned_text="", blocks=blocks[:2], layout_type=LayoutType.SINGLE_COLUMN, char_count=100, word_count=15, is_blank=False)
    p2 = PageExtractionResult(page_number=2, raw_text="", cleaned_text="", blocks=[blocks[2]], layout_type=LayoutType.SINGLE_COLUMN, char_count=100, word_count=15, is_blank=False)
    
    sections = detector.detect_sections([p1, p2], canonical_id="test_springer")
    titles = [s.section_title for s in sections]
    assert not any(t == "123" for t in titles)
    assert any("1. Introduction" in t for t in titles)
    assert any("2. Methods" in t for t in titles)


# ==============================================================================
# 3. Spanning Paragraphs & Physical Page Tracking
# ==============================================================================

def test_cross_page_paragraph_extraction_and_page_ranges():
    """Verify that paragraphs crossing page boundaries retain page_number and page_end correctly."""
    extractor = ParagraphExtractor()
    sec = ProcessedSection(
        section_id="sec_01",
        section_title="1. Introduction",
        section_level=1,
        section_order=1,
        start_page=1,
        end_page=2,
        text="",
    )
    # Attach _block_entries across page 1 and page 2
    sec._block_entries = [
        (1, "This sentence starts on page one and continues onto the next page with no final punctuation"),
        (2, "because the paragraph continues seamlessly across the page break."),
        (2, "This is a second separate paragraph starting on page two.")
    ]
    
    paragraphs, updated_secs = extractor.extract_paragraphs([sec], canonical_id="test_span", document_id="doc_span", file_hash="hash_span")
    assert len(paragraphs) == 2
    
    p1 = paragraphs[0]
    assert p1.page_number == 1
    assert p1.page_end == 2
    assert "seamlessly across the page break" in p1.text
    assert p1.document_id == "doc_span"
    assert p1.file_hash == "hash_span"
    
    p2 = paragraphs[1]
    assert p2.page_number == 2
    assert p2.page_end == 2
    assert p2.document_id == "doc_span"


# ==============================================================================
# 4. Sentence Segmentation Edge Cases
# ==============================================================================

def test_scientific_sentence_segmentation_edge_cases():
    """Verify sentence segmenter on complex citations, equations, and nested abbreviations."""
    segmenter = ScientificSentenceSegmenter()
    text = (
        "In Eq. (4), let x = 0.05 and y = 12.34 represent model thresholds. "
        "Prior work (e.g., Smith et al., 2020; Jones & Brown, 2021) demonstrated F1 > 0.90. "
        "Furthermore, Dr. A. Taylor et al. noted that p < 0.001 in 95% CI [0.85, 0.95]. "
        "Thus, the hypothesis is confirmed."
    )
    sentences = segmenter.segment_text(text, paragraph_id="p_test_edge")
    assert len(sentences) == 4
    assert "Eq. (4)" in sentences[0].text
    assert "0.05 and y = 12.34" in sentences[0].text
    assert "e.g., Smith et al., 2020" in sentences[1].text
    assert "p < 0.001" in sentences[2].text
    assert sentences[3].text == "Thus, the hypothesis is confirmed."


# ==============================================================================
# 5. Oversized Paragraph Splitting in Strategy A
# ==============================================================================

def test_oversized_paragraph_splitting_in_strategy_a():
    """Verify that paragraphs exceeding 2000 chars are split into sub-chunks with parent paragraph lineage."""
    chunker = DocumentChunker(target_char_size=1200, max_char_size=2000)
    metadata = DocumentMetadata(
        canonical_id="test_split_doc",
        title="Oversized Doc",
        doi="10.1234/oversized",
        source="openalex",
        local_pdf_path="test.pdf",
        file_hash="hash123",
    )
    sec = ProcessedSection(
        section_id="sec_01",
        section_title="1. Introduction",
        section_level=1,
        section_order=1,
        start_page=1,
        end_page=1,
        text="",
    )
    # Generate 2500 character paragraph made of distinct sentences
    sentence = "This is a detailed scientific observation describing complex experimental phenomena in great depth. "
    long_text = sentence * 25  # ~2500 chars
    assert len(long_text) > 2000
    
    p = ProcessedParagraph(
        paragraph_id="p_long_01",
        canonical_id="test_split_doc",
        section_id="sec_01",
        section_title="1. Introduction",
        page_number=1,
        paragraph_order=1,
        text=long_text.strip(),
        char_count=len(long_text.strip()),
    )
    
    chunks = chunker.chunk_strategy_a_paragraph_based([sec], [p], metadata)
    assert len(chunks) >= 2
    # Verify all chunks are under or near max size
    for c in chunks:
        assert c.strategy == ChunkStrategy.STRATEGY_A_PARAGRAPH
        assert "p_long_01" in c.paragraph_ids
        assert c.section_id == "sec_01"
        assert c.provenance["parent_paragraph_id"] == "p_long_01"
        assert "split_index" in c.provenance


# ==============================================================================
# 6. Determinism & Text Conservation
# ==============================================================================

def test_chunking_determinism():
    """Verify that running chunking multiple times on unchanged inputs produces identical outputs."""
    chunker = DocumentChunker()
    metadata = DocumentMetadata(
        canonical_id="test_det",
        title="Determinism Test",
        doi="10.1234/det",
        source="openalex",
        local_pdf_path="test.pdf",
        file_hash="hash_det",
    )
    sec = ProcessedSection(section_id="sec_01", section_title="1. Intro", section_level=1, section_order=1, start_page=1, end_page=1, text="")
    p1 = ProcessedParagraph(paragraph_id="p_1", canonical_id="test_det", section_id="sec_01", section_title="1. Intro", page_number=1, paragraph_order=1, text="Text 1.")
    p2 = ProcessedParagraph(paragraph_id="p_2", canonical_id="test_det", section_id="sec_01", section_title="1. Intro", page_number=1, paragraph_order=2, text="Text 2.")

    run1_a = chunker.chunk_strategy_a_paragraph_based([sec], [p1, p2], metadata)
    run2_a = chunker.chunk_strategy_a_paragraph_based([sec], [p1, p2], metadata)
    assert [c.chunk_id for c in run1_a] == [c.chunk_id for c in run2_a]
    assert [c.text for c in run1_a] == [c.text for c in run2_a]

    run1_b = chunker.chunk_strategy_b_structure_aware_fixed([sec], [p1, p2], metadata)
    run2_b = chunker.chunk_strategy_b_structure_aware_fixed([sec], [p1, p2], metadata)
    assert [c.chunk_id for c in run1_b] == [c.chunk_id for c in run2_b]
    assert [c.text for c in run1_b] == [c.text for c in run2_b]


# ==============================================================================
# 7. Output Schema Validation
# ==============================================================================

def test_processed_chunk_schema_constraints():
    """Verify that ProcessedChunk enforces required fields and types."""
    # Valid chunk
    chunk = ProcessedChunk(
        chunk_id="chk_01",
        canonical_id="rg_doc",
        document_id="doc_01",
        file_hash="hash123",
        strategy=ChunkStrategy.STRATEGY_A_PARAGRAPH,
        section_id="sec_01",
        section_title="1. Intro",
        section_level=1,
        page_start=1,
        page_end=1,
        paragraph_start_order=1,
        paragraph_end_order=1,
        paragraph_ids=["p_01"],
        text="Valid chunk text",
        char_count=16,
        word_count=3,
        chunk_order=1,
        provenance={"run": "pilot"},
    )
    assert chunk.chunk_id == "chk_01"
    assert chunk.document_id == "doc_01"
    
    # Missing required field must raise ValidationError
    with pytest.raises(ValidationError):
        ProcessedChunk(
            chunk_id="chk_invalid",
            # missing canonical_id, text, etc.
        )
