"""Unit tests for document chunking strategies."""

from dataset.schemas.document_processing import (
    ChunkStrategy,
    DocumentMetadata,
    ProcessedParagraph,
    ProcessedSection,
)
from pipelines.processing.chunker import DocumentChunker


def test_chunk_strategy_a_section_isolation():
    chunker = DocumentChunker(target_char_size=200, max_char_size=400)
    metadata = DocumentMetadata(
        canonical_id="rg_chk_test",
        title="Test Paper",
        doi="10.1234/test",
        source="openalex",
        local_pdf_path="test.pdf",
        file_hash="abc123hash",
    )

    sec1 = ProcessedSection(
        section_id="sec_01",
        section_title="1. Introduction",
        section_level=1,
        section_order=1,
        start_page=1,
        end_page=1,
        text="",
    )
    sec2 = ProcessedSection(
        section_id="sec_02",
        section_title="2. Methods",
        section_level=1,
        section_order=2,
        start_page=2,
        end_page=2,
        text="",
    )

    p1 = ProcessedParagraph(
        paragraph_id="p_01",
        canonical_id="rg_chk_test",
        section_id="sec_01",
        section_title="1. Introduction",
        page_number=1,
        paragraph_order=1,
        text="Introduction paragraph 1 text that is relatively short.",
    )
    p2 = ProcessedParagraph(
        paragraph_id="p_02",
        canonical_id="rg_chk_test",
        section_id="sec_01",
        section_title="1. Introduction",
        page_number=1,
        paragraph_order=2,
        text="Introduction paragraph 2 text that completes section 1.",
    )
    p3 = ProcessedParagraph(
        paragraph_id="p_03",
        canonical_id="rg_chk_test",
        section_id="sec_02",
        section_title="2. Methods",
        page_number=2,
        paragraph_order=3,
        text="Methods paragraph 1 which should definitely be in its own chunk.",
    )

    chunks_a = chunker.chunk_strategy_a_paragraph_based([sec1, sec2], [p1, p2, p3], metadata)

    # Chunks should strictly separate sec_01 from sec_02
    assert len(chunks_a) >= 2
    for c in chunks_a:
        if "p_01" in c.paragraph_ids or "p_02" in c.paragraph_ids:
            assert c.section_id == "sec_01"
            assert "p_03" not in c.paragraph_ids
        if "p_03" in c.paragraph_ids:
            assert c.section_id == "sec_02"
            assert "p_01" not in c.paragraph_ids

    # Check provenance
    assert chunks_a[0].provenance["canonical_id"] == "rg_chk_test"
    assert chunks_a[0].provenance["file_hash"] == "abc123hash"


def test_chunk_strategy_b_fixed_size():
    chunker = DocumentChunker(target_char_size=150, overlap_char_size=30)
    metadata = DocumentMetadata(
        canonical_id="rg_chk_test2",
        title="Test Paper 2",
        doi="10.1234/test2",
        source="openalex",
        local_pdf_path="test2.pdf",
        file_hash="def456hash",
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
    p1 = ProcessedParagraph(
        paragraph_id="p_01",
        canonical_id="rg_chk_test2",
        section_id="sec_01",
        section_title="1. Introduction",
        page_number=1,
        paragraph_order=1,
        text="First long sentence in the paragraph. Second long sentence in the paragraph. Third long sentence here.",
    )

    chunks_b = chunker.chunk_strategy_b_structure_aware_fixed([sec], [p1], metadata)
    assert len(chunks_b) >= 1
    assert all(c.strategy == ChunkStrategy.STRATEGY_B_STRUCTURE_FIXED for c in chunks_b)
    assert all(c.section_id == "sec_01" for c in chunks_b)
