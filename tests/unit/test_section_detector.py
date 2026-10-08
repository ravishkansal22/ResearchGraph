"""Unit tests for hierarchical section detector."""

from dataset.schemas.document_processing import LayoutType
from pipelines.processing.extractor import PageExtractionResult, TextBlock, TextLine
from pipelines.processing.section_detector import SectionDetector


def test_detect_numbered_sections_hierarchy():
    detector = SectionDetector()
    blocks = [
        TextBlock(block_id=0, text="Document Title\nAuthor Names", bbox=(50, 50, 500, 80), page_number=1),
        TextBlock(block_id=1, text="1. Introduction\nThis paper introduces...", bbox=(50, 100, 500, 150), page_number=1, is_bold_dominant=True, max_font_size=14.0),
        TextBlock(block_id=2, text="1.1 Background\nSome detailed background context.", bbox=(50, 200, 500, 250), page_number=1, is_bold_dominant=True, max_font_size=12.0),
        TextBlock(block_id=3, text="1.1.1 Historical Context\nEarlier historical works.", bbox=(50, 300, 500, 350), page_number=1, is_bold_dominant=True, max_font_size=11.0),
        TextBlock(block_id=4, text="2. Methodology\nWe propose an approach.", bbox=(50, 400, 500, 450), page_number=2, is_bold_dominant=True, max_font_size=14.0),
    ]

    page1 = PageExtractionResult(
        page_number=1,
        raw_text="",
        cleaned_text="",
        blocks=blocks[:4],
        layout_type=LayoutType.SINGLE_COLUMN,
        char_count=500,
        word_count=80,
        is_blank=False,
    )
    page2 = PageExtractionResult(
        page_number=2,
        raw_text="",
        cleaned_text="",
        blocks=[blocks[4]],
        layout_type=LayoutType.SINGLE_COLUMN,
        char_count=200,
        word_count=30,
        is_blank=False,
    )

    sections = detector.detect_sections([page1, page2], canonical_id="rg_test_01")
    assert len(sections) == 5  # Front Matter + 1. Intro + 1.1 Background + 1.1.1 History + 2. Method

    sec_map = {s.section_title: s for s in sections}
    assert "1. Introduction" in sec_map
    assert sec_map["1. Introduction"].section_level == 1
    assert sec_map["1. Introduction"].parent_section_id is None

    assert "1.1 Background" in sec_map
    assert sec_map["1.1 Background"].section_level == 2
    assert sec_map["1.1 Background"].parent_section_id == sec_map["1. Introduction"].section_id

    assert "1.1.1 Historical Context" in sec_map
    assert sec_map["1.1.1 Historical Context"].section_level == 3
    assert sec_map["1.1.1 Historical Context"].parent_section_id == sec_map["1.1 Background"].section_id

    assert "2. Methodology" in sec_map
    assert sec_map["2. Methodology"].section_level == 1
    assert sec_map["2. Methodology"].parent_section_id is None


def test_detect_roman_numeral_and_unnumbered_sections():
    detector = SectionDetector()
    blocks = [
        TextBlock(block_id=0, text="Abstract\nThis study explores machine learning.", bbox=(50, 50, 500, 80), page_number=1, is_bold_dominant=True),
        TextBlock(block_id=1, text="I. INTRODUCTION\nDeep learning models have grown.", bbox=(50, 100, 500, 150), page_number=1, is_bold_dominant=True),
        TextBlock(block_id=2, text="REFERENCES\n[1] A. Smith, 2020.", bbox=(50, 200, 500, 250), page_number=2, is_bold_dominant=True),
    ]

    p1 = PageExtractionResult(page_number=1, raw_text="", cleaned_text="", blocks=blocks[:2], layout_type=LayoutType.SINGLE_COLUMN, char_count=200, word_count=30, is_blank=False)
    p2 = PageExtractionResult(page_number=2, raw_text="", cleaned_text="", blocks=[blocks[2]], layout_type=LayoutType.SINGLE_COLUMN, char_count=100, word_count=15, is_blank=False)

    sections = detector.detect_sections([p1, p2], canonical_id="rg_test_roman")
    titles = [s.section_title for s in sections]
    assert any("Abstract" in t for t in titles)
    assert any("I. INTRODUCTION" in t for t in titles)
    assert any("REFERENCES" in t for t in titles)
