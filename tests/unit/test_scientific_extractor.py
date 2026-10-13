"""Unit Tests for RuleBasedScientificExtractor."""

from __future__ import annotations

import pytest

from dataset.schemas.document_processing import ChunkStrategy, ProcessedChunk
from dataset.schemas.scientific_knowledge import (
    ScientificEntityType,
    ScientificRelationType,
    ScientificStatementType,
)
from pipelines.extraction.extractor import RuleBasedScientificExtractor


@pytest.fixture
def extractor() -> RuleBasedScientificExtractor:
    return RuleBasedScientificExtractor()


def make_chunk(text: str, cid: str = "rg_doi_001", chk_id: str = "chk_001") -> ProcessedChunk:
    return ProcessedChunk(
        chunk_id=chk_id,
        canonical_id=cid,
        section_id="sec_01",
        section_title="Methods",
        page_start=1,
        page_end=1,
        paragraph_start_order=1,
        paragraph_end_order=1,
        text=text,
        strategy=ChunkStrategy.STRATEGY_A_PARAGRAPH,
    )


def test_extract_entities_lexicon_and_frames(extractor):
    text = (
        "We propose an adaptive intrusion detection system using deep learning and "
        "convolutional neural networks to address the challenge of adversarial attacks "
        "in cybersecurity. The model was evaluated on the NSL-KDD benchmark."
    )
    chunk = make_chunk(text)
    entities, statements, relations = extractor.extract(chunk)

    entity_categories = {e.category for e in entities}
    assert ScientificEntityType.METHOD in entity_categories
    assert ScientificEntityType.PROBLEM in entity_categories
    assert ScientificEntityType.DATASET in entity_categories
    assert ScientificEntityType.DOMAIN in entity_categories

    # Verify exact character alignment for all extracted entities
    for ent in entities:
        assert chunk.text[ent.evidence.start_char : ent.evidence.end_char] == ent.evidence.text


def test_extract_statements(extractor):
    text = (
        "This paper examines how machine learning mitigates cyber threats. "
        "The model achieved an accuracy of 99.2% on the test partition. "
        "A limitation of this study is the high latency overhead under heavy loads. "
        "Future research should explore distributed federated architectures."
    )
    chunk = make_chunk(text)
    entities, statements, relations = extractor.extract(chunk)

    stmt_categories = {s.category for s in statements}
    assert ScientificStatementType.CLAIM in stmt_categories
    assert ScientificStatementType.RESULT in stmt_categories
    assert ScientificStatementType.LIMITATION in stmt_categories
    assert ScientificStatementType.FUTURE_DIRECTION in stmt_categories

    for stmt in statements:
        assert chunk.text[stmt.evidence.start_char : stmt.evidence.end_char] == stmt.evidence.text


def test_extract_relationships(extractor):
    text = (
        "We propose an adaptive intrusion detection system that addresses adversarial attacks. "
        "The system is evaluated on the NSL-KDD dataset."
    )
    chunk = make_chunk(text)
    entities, statements, relations = extractor.extract(chunk)

    rel_types = {r.relation_type for r in relations}
    assert ScientificRelationType.ADDRESSES in rel_types or ScientificRelationType.EVALUATED_ON in rel_types

    for rel in relations:
        assert rel.is_directed is True
        assert rel.source_id is not None
        assert rel.target_id is not None


def test_extract_empty_or_trivial_chunk(extractor):
    chunk = make_chunk("   \n  ")
    entities, statements, relations = extractor.extract(chunk)
    assert len(entities) == 0
    assert len(statements) == 0
    assert len(relations) == 0
