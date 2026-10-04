"""Unit tests for identity resolution and confidence scoring."""

from dataset.schemas.canonical_paper import Author, CanonicalPaper, ConfidenceLevel
from pipelines.ingestion.resolution.identity import (
    IdentityResolver,
    compute_title_similarity,
    generate_deterministic_canonical_id,
)


def test_title_similarity():
    sim_exact = compute_title_similarity(
        "Attention Is All You Need",
        "attention is all you need"
    )
    assert sim_exact == 1.0

    sim_high = compute_title_similarity(
        "Deep Residual Learning for Image Recognition",
        "Deep Residual Learning for Image Recognition: An Overview"
    )
    assert sim_high >= 0.70

    sim_diff = compute_title_similarity(
        "Generative Adversarial Nets",
        "Attention Is All You Need"
    )
    assert sim_diff < 0.30


def test_identity_matching_by_doi():
    resolver = IdentityResolver()
    p1 = CanonicalPaper(
        canonical_id="test1",
        title="Paper A",
        doi="10.1145/123456",
    )
    p2 = CanonicalPaper(
        canonical_id="test2",
        title="Paper A (Extended)",
        doi="10.1145/123456",
    )
    is_match, conf, reason = resolver.match_papers(p1, p2)
    assert is_match is True
    assert conf == ConfidenceLevel.EXACT
    assert "DOI" in reason


def test_identity_matching_by_arxiv():
    resolver = IdentityResolver()
    p1 = CanonicalPaper(
        canonical_id="test1",
        title="Paper Title",
        arxiv_id="1706.03762",
    )
    p2 = CanonicalPaper(
        canonical_id="test2",
        title="Paper Title",
        arxiv_id="1706.03762",
    )
    is_match, conf, reason = resolver.match_papers(p1, p2)
    assert is_match is True
    assert conf == ConfidenceLevel.EXACT
    assert "arXiv" in reason


def test_identity_matching_by_title_and_author():
    resolver = IdentityResolver()
    p1 = CanonicalPaper(
        canonical_id="test1",
        title="Attention Is All You Need",
        publication_year=2017,
        authors=[Author(name="Ashish Vaswani", last_name="Vaswani")],
    )
    p2 = CanonicalPaper(
        canonical_id="test2",
        title="Attention is all you need!",
        publication_year=2017,
        authors=[Author(name="A. Vaswani", last_name="Vaswani")],
    )
    is_match, conf, _ = resolver.match_papers(p1, p2)
    assert is_match is True
    assert conf in (ConfidenceLevel.EXACT, ConfidenceLevel.HIGH_CONFIDENCE)


def test_deterministic_canonical_id_generation():
    p1 = CanonicalPaper(canonical_id="tmp", title="Test Paper", doi="10.1145/9999")
    id1 = generate_deterministic_canonical_id(p1)
    assert id1.startswith("rg_doi_")

    p2 = CanonicalPaper(canonical_id="tmp", title="Test Paper 2", arxiv_id="2401.0001")
    id2 = generate_deterministic_canonical_id(p2)
    assert id2.startswith("rg_arx_")

    p3 = CanonicalPaper(canonical_id="tmp", title="Unique Paper Title Without Identifiers")
    id3 = generate_deterministic_canonical_id(p3)
    assert id3.startswith("rg_tit_")
