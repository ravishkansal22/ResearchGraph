"""Unit tests for paragraph extractor and lineage tracking."""

from dataset.schemas.document_processing import ProcessedSection
from pipelines.processing.paragraph_extractor import ParagraphExtractor


def test_extract_paragraphs_with_provenance():
    extractor = ParagraphExtractor()
    sec1 = ProcessedSection(
        section_id="sec_doc1_01",
        section_title="1. Introduction",
        section_level=1,
        section_number="1",
        section_order=1,
        start_page=1,
        end_page=1,
        text="This is paragraph one of introduction.\nIt has a line wrap.\n\nThis is paragraph two of introduction.",
    )
    sec2 = ProcessedSection(
        section_id="sec_doc1_02",
        section_title="2. Methods",
        section_level=1,
        section_number="2",
        section_order=2,
        start_page=2,
        end_page=2,
        text="This is paragraph three describing methods.",
    )

    paragraphs, updated_secs = extractor.extract_paragraphs([sec1, sec2], canonical_id="doc1")

    assert len(paragraphs) == 3
    assert paragraphs[0].paragraph_id == "p_doc1_0001"
    assert paragraphs[0].section_id == "sec_doc1_01"
    assert paragraphs[0].section_title == "1. Introduction"
    assert paragraphs[0].page_number == 1
    assert "This is paragraph one of introduction. It has a line wrap." == paragraphs[0].text

    assert paragraphs[1].paragraph_id == "p_doc1_0002"
    assert paragraphs[1].section_id == "sec_doc1_01"

    assert paragraphs[2].paragraph_id == "p_doc1_0003"
    assert paragraphs[2].section_id == "sec_doc1_02"
    assert paragraphs[2].page_number == 2

    assert updated_secs[0].paragraph_count == 2
    assert updated_secs[1].paragraph_count == 1
    assert updated_secs[0].paragraph_ids == ["p_doc1_0001", "p_doc1_0002"]
