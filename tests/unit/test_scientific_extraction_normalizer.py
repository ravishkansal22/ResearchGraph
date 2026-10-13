"""Unit Tests for Conservative Scientific Knowledge Normalizer."""

from __future__ import annotations

import pytest

from pipelines.extraction.normalizer import ScientificNormalizer


def test_normalize_entity_strips_bullets():
    normalizer = ScientificNormalizer()
    assert normalizer.normalize_entity_name("1. Convolutional Neural Network") == "Convolutional Neural Network"
    assert normalizer.normalize_entity_name("• Support Vector Machine") == "Support Vector Machine"
    assert normalizer.normalize_entity_name("- Random Forest") == "Random Forest"
    assert normalizer.normalize_entity_name("(a) Deep Neural Network") == "Deep Neural Network"


def test_normalize_entity_preserves_acronym_casing():
    normalizer = ScientificNormalizer()
    assert normalizer.normalize_entity_name("lstm") == "LSTM"
    assert normalizer.normalize_entity_name("Cnn") == "CNN"
    assert normalizer.normalize_entity_name("BERT") == "BERT"
    assert normalizer.normalize_entity_name("nsl-kdd") == "NSL-KDD"
    assert normalizer.normalize_entity_name("cicids2017") == "CICIDS2017"


def test_normalize_entity_cleans_surrounding_punctuation():
    normalizer = ScientificNormalizer()
    assert normalizer.normalize_entity_name('"Intrusion Detection System",') == "Intrusion Detection System"
    assert normalizer.normalize_entity_name("['Transformer']") == "Transformer"


def test_normalize_statement_preserves_modals_and_polarity():
    normalizer = ScientificNormalizer()
    raw = "  • The model fails to detect zero-day attacks, but may improve throughput.  "
    norm = normalizer.normalize_statement_text(raw)
    assert norm == "The model fails to detect zero-day attacks, but may improve throughput."
    assert "fails to" in norm
    assert "may" in norm


def test_extract_evidence_span_offsets():
    normalizer = ScientificNormalizer()
    chunk_text = "Recent studies show that LSTM networks outperform standard RNN models in cyber threat detection."
    span = normalizer.extract_evidence_span(chunk_text, "LSTM networks")
    assert span is not None
    start, end = span
    assert chunk_text[start:end] == "LSTM networks"


def test_extract_evidence_span_absent():
    normalizer = ScientificNormalizer()
    chunk_text = "Recent studies show that LSTM networks outperform standard RNN models."
    span = normalizer.extract_evidence_span(chunk_text, "Quantum entanglement")
    assert span is None
