"""Unit tests for identifier and text normalizers."""

from pipelines.ingestion.normalizers.identifiers import normalize_arxiv_id, normalize_doi, normalize_orcid
from pipelines.ingestion.normalizers.text import (
    clean_text,
    normalize_title_for_matching,
    parse_author_name,
    reconstruct_openalex_abstract,
)


def test_normalize_doi():
    assert normalize_doi("https://doi.org/10.1145/3308558.3313508") == "10.1145/3308558.3313508"
    assert normalize_doi("http://dx.doi.org/10.1007/978-3-030-01246-5_1") == "10.1007/978-3-030-01246-5_1"
    assert normalize_doi("doi:10.48550/arXiv.1706.03762") == "10.48550/arxiv.1706.03762"
    assert normalize_doi("10.1016/j.artint.2020.103318.") == "10.1016/j.artint.2020.103318"
    assert normalize_doi("invalid-doi-string") is None
    assert normalize_doi(None) is None


def test_normalize_arxiv_id():
    assert normalize_arxiv_id("https://arxiv.org/abs/2301.07094v2") == "2301.07094"
    assert normalize_arxiv_id("arXiv:1706.03762v7") == "1706.03762"
    assert normalize_arxiv_id("2401.12345") == "2401.12345"
    assert normalize_arxiv_id("arXiv:cs/0601001v1") == "cs/0601001"
    assert normalize_arxiv_id(None) is None


def test_normalize_orcid():
    assert normalize_orcid("https://orcid.org/0000-0002-1825-0097") == "0000-0002-1825-0097"
    assert normalize_orcid("0000-0001-5000-000X") == "0000-0001-5000-000X"
    assert normalize_orcid("invalid") is None
    assert normalize_orcid(None) is None


def test_clean_text():
    raw_html = "<p>Deep learning &amp; neural networks are <b>effective</b>.</p>"
    assert clean_text(raw_html) == "Deep learning & neural networks are effective."
    assert clean_text("   Too    many    spaces  \n ") == "Too many spaces"
    assert clean_text(None) is None


def test_normalize_title_for_matching():
    title1 = "Attention Is All You Need!"
    title2 = "attention is all you need"
    assert normalize_title_for_matching(title1) == normalize_title_for_matching(title2)
    assert normalize_title_for_matching(title1) == "attention is all you need"

    # Diacritics and hyphens
    title_complex = "A Self-Supervised Réseau for Point Clouds (2024)."
    assert normalize_title_for_matching(title_complex) == "a self supervised reseau for point clouds 2024"


def test_reconstruct_openalex_abstract():
    inverted_index = {
        "Attention": [0],
        "is": [1],
        "all": [2],
        "you": [3],
        "need.": [4],
    }
    abstract = reconstruct_openalex_abstract(inverted_index)
    assert abstract == "Attention is all you need."


def test_parse_author_name():
    assert parse_author_name("Ashish Vaswani") == ("Ashish Vaswani", "Ashish", "Vaswani")
    assert parse_author_name("Vaswani, Ashish") == ("Ashish Vaswani", "Ashish", "Vaswani")
    assert parse_author_name("Bengio, Yoshua") == ("Yoshua Bengio", "Yoshua", "Bengio")
    assert parse_author_name("Aristotle") == ("Aristotle", None, "Aristotle")
