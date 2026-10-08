"""Unit tests for processing quality auditor."""

from dataset.schemas.document_processing import (
    ChunkStrategy,
    DocumentMetadata,
    DocumentProcessingMetadata,
    LayoutType,
    ProcessedChunk,
    ProcessedDocument,
    ProcessedPage,
    ProcessedParagraph,
    ProcessedSection,
    ProcessingStatus,
)
from pipelines.processing.quality import ProcessingQualityAuditor


def test_quality_auditor_clean_document():
    doc = ProcessedDocument(
        document_id="doc_test_1",
        canonical_id="rg_test_1",
        metadata=DocumentMetadata(
            canonical_id="rg_test_1",
            title="Clean Test Paper",
            source="openalex",
            local_pdf_path="test.pdf",
            file_hash="123456",
        ),
        processing=DocumentProcessingMetadata(
            page_count=2,
            extracted_page_count=2,
            empty_page_count=0,
            character_count=500,
            word_count=80,
            layout_detected=LayoutType.SINGLE_COLUMN,
        ),
        pages=[
            ProcessedPage(page_number=1, text="Clean page 1 text", char_count=250, word_count=40),
            ProcessedPage(page_number=2, text="Clean page 2 text", char_count=250, word_count=40),
        ],
        sections=[
            ProcessedSection(section_id="sec_01", section_title="1. Introduction", section_order=1, start_page=1, end_page=2)
        ],
        paragraphs=[
            ProcessedParagraph(
                paragraph_id="p_01",
                canonical_id="rg_test_1",
                section_id="sec_01",
                section_title="1. Introduction",
                page_number=1,
                paragraph_order=1,
                text="Clean paragraph 1 contains sufficient characters and words to represent a legitimate scientific section body paragraph.",
                char_count=120,
                word_count=18,
            ),
            ProcessedParagraph(
                paragraph_id="p_02",
                canonical_id="rg_test_1",
                section_id="sec_01",
                section_title="1. Introduction",
                page_number=2,
                paragraph_order=2,
                text="Clean paragraph 2 describes additional methodology and contextual background without any anomalous replacement tokens.",
                char_count=118,
                word_count=16,
            ),
        ],
        chunks_strategy_a=[
            ProcessedChunk(
                chunk_id="chk_1",
                canonical_id="rg_test_1",
                section_id="sec_01",
                section_title="1. Introduction",
                page_start=1,
                page_end=2,
                paragraph_start_order=1,
                paragraph_end_order=2,
                text="Clean paragraph 1 contains sufficient characters... Clean paragraph 2 describes additional...",
                char_count=238,
                word_count=34,
                strategy=ChunkStrategy.STRATEGY_A_PARAGRAPH,
            )
        ],

    )

    audit = ProcessingQualityAuditor.audit_document(doc)
    assert audit["status"] == "SUCCESS"
    assert audit["usable_pages"] if "usable_pages" in audit else audit["page_success_rate"] == 1.0
    assert audit["is_potentially_corrupted"] is False
