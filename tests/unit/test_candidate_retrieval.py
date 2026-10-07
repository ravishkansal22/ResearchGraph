"""Unit tests for metadata-based candidate retrieval and missing abstract handling."""

import pytest
from dataset.schemas.canonical_paper import CanonicalPaper, Topic
from pipelines.ingestion.fulltext.retrieval import MetadataCandidateRetriever


def test_candidate_retriever_tokenize():
    tokens = MetadataCandidateRetriever._tokenize("Deep Learning & Neural-Networks for NLP!")
    assert "deep" in tokens
    assert "learning" in tokens
    assert "neural-networks" in tokens or ("neural" in tokens and "networks" in tokens)
    assert "nlp" in tokens


def test_candidate_retriever_scoring_with_abstract():
    retriever = MetadataCandidateRetriever()
    paper = CanonicalPaper(
        canonical_id="rg_test_retrieval_1",
        title="Deep Learning for Medical Diagnosis",
        abstract="This paper introduces neural networks for healthcare and diagnostic imaging.",
        topics=[Topic(name="Medicine"), Topic(name="Artificial Intelligence")],
    )

    query = "deep learning neural networks in medical diagnosis"
    score, components = retriever.score_paper(paper, query)
    assert score >= 0.4
    assert components["has_abstract"] == 1.0
    assert components["title_score"] > 0.0
    assert components["abstract_score"] > 0.0


def test_candidate_retriever_handling_missing_abstract():
    retriever = MetadataCandidateRetriever()
    paper_no_abs = CanonicalPaper(
        canonical_id="rg_test_no_abs",
        title="Deep Learning for Medical Diagnosis",
        abstract=None,  # Missing abstract
        topics=[Topic(name="Artificial Intelligence")],
    )

    query = "deep learning medical diagnosis"
    score, components = retriever.score_paper(paper_no_abs, query)
    assert score > 0.5
    assert components["has_abstract"] == 0.0
    assert components["abstract_score"] == 0.0
    # Dynamic weight rebalancing ensures title weight absorbs missing abstract weight


def test_candidate_retriever_ranking():
    retriever = MetadataCandidateRetriever()
    paper1 = CanonicalPaper(
        canonical_id="rg_p1",
        title="Deep Learning for Cybersecurity Threat Detection",
        abstract="Neural network models for network intrusion detection.",
    )
    paper2 = CanonicalPaper(
        canonical_id="rg_p2",
        title="Plant Breeding and Crop Genetics in Agriculture",
        abstract="Studying genetic markers in wheat and rice crops.",
    )

    query = "cybersecurity neural network intrusion detection"
    results = retriever.retrieve_candidates([paper1, paper2], query, top_k=5)
    assert len(results) == 1
    assert results[0][0].canonical_id == "rg_p1"
