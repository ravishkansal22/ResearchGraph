"""Unit tests for document type normalization and schema validation."""

import pytest
from dataset.schemas.canonical_paper import DocumentType, CanonicalPaper
from pipelines.ingestion.normalizers.document_type import classify_document_type


def test_document_type_enum_values():
    assert DocumentType.RESEARCH_ARTICLE.value == "RESEARCH_ARTICLE"
    assert DocumentType.CONFERENCE_PAPER.value == "CONFERENCE_PAPER"
    assert DocumentType.REVIEW.value == "REVIEW"
    assert DocumentType.SURVEY.value == "SURVEY"
    assert DocumentType.BOOK_CHAPTER.value == "BOOK_CHAPTER"
    assert DocumentType.EDITORIAL.value == "EDITORIAL"
    assert DocumentType.FRONT_MATTER.value == "FRONT_MATTER"
    assert DocumentType.OTHER.value == "OTHER"
    assert DocumentType.UNKNOWN.value == "UNKNOWN"


def test_document_type_normalization_openalex():
    assert classify_document_type("article", source="openalex") == DocumentType.RESEARCH_ARTICLE
    assert classify_document_type("book-chapter", source="openalex") == DocumentType.BOOK_CHAPTER
    assert classify_document_type("conference-paper", source="openalex") == DocumentType.CONFERENCE_PAPER
    assert classify_document_type("editorial", source="openalex") == DocumentType.EDITORIAL
    assert classify_document_type("peer-review", source="openalex") == DocumentType.OTHER


def test_document_type_normalization_crossref():
    assert classify_document_type("journal-article", source="crossref") == DocumentType.RESEARCH_ARTICLE
    assert classify_document_type("book-chapter", source="crossref") == DocumentType.BOOK_CHAPTER
    assert classify_document_type("proceedings-article", source="crossref") == DocumentType.CONFERENCE_PAPER
    assert classify_document_type("component", source="crossref") == DocumentType.FRONT_MATTER


def test_document_type_title_cues():
    assert classify_document_type("article", source="openalex", title="A Systematic Literature Review of GNNs") == DocumentType.REVIEW
    assert classify_document_type("article", source="openalex", title="A Comprehensive Survey of LLMs") == DocumentType.SURVEY


def test_document_type_unknown_handling():
    assert classify_document_type(None, source="openalex") == DocumentType.UNKNOWN
    assert classify_document_type("", source="crossref") == DocumentType.UNKNOWN


def test_canonical_paper_document_type_schema():
    paper = CanonicalPaper(
        canonical_id="rg_test123",
        title="Testing Document Type",
        document_type=DocumentType.CONFERENCE_PAPER,
    )
    assert paper.document_type == DocumentType.CONFERENCE_PAPER
