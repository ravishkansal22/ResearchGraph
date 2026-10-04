"""Unit tests for scholarly source adapters and response normalization."""

import json
from pathlib import Path
from dataset.schemas.canonical_paper import FulltextStatus, RawRecord
from pipelines.ingestion.sources.arxiv import ArxivAdapter
from pipelines.ingestion.sources.crossref import CrossrefAdapter
from pipelines.ingestion.sources.openalex import OpenAlexAdapter
from pipelines.ingestion.sources.semantic_scholar import SemanticScholarAdapter

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_openalex_normalization():
    fixture_path = FIXTURES_DIR / "openalex_response.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    work_data = data["results"][0]
    raw_rec = RawRecord(
        source="openalex",
        source_record_id="W2741809807",
        raw_data=work_data,
    )

    adapter = OpenAlexAdapter()
    paper = adapter.normalize(raw_rec)

    assert paper.title == "Attention Is All You Need"
    assert paper.doi == "10.48550/arxiv.1706.03762"
    assert paper.arxiv_id == "1706.03762"
    assert paper.publication_year == 2017
    assert len(paper.authors) == 2
    assert paper.authors[0].name == "Ashish Vaswani"
    assert paper.authors[0].orcid == "0000-0002-1234-5678"
    assert "Google (United States)" in paper.authors[0].affiliations
    assert paper.citation_count == 115000
    assert paper.open_access.is_oa is True
    assert paper.fulltext_available == FulltextStatus.FULLTEXT_AVAILABLE
    assert paper.source_records.openalex == "W2741809807"
    assert len(paper.provenance) == 1


def test_semantic_scholar_normalization():
    fixture_path = FIXTURES_DIR / "semantic_scholar_response.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    paper_data = data["data"][0]
    raw_rec = RawRecord(
        source="semantic_scholar",
        source_record_id=paper_data["paperId"],
        raw_data=paper_data,
    )

    adapter = SemanticScholarAdapter()
    paper = adapter.normalize(raw_rec)

    assert "Attention is All you Need" in paper.title
    assert paper.doi == "10.48550/arxiv.1706.03762"
    assert paper.arxiv_id == "1706.03762"
    assert paper.publication_year == 2017
    assert len(paper.authors) == 2
    assert paper.citation_count == 115200
    assert paper.influential_citation_count == 12400
    assert paper.fulltext_available == FulltextStatus.FULLTEXT_AVAILABLE
    assert paper.fulltext_url == "https://arxiv.org/pdf/1706.03762.pdf"


def test_arxiv_feed_normalization():
    fixture_path = FIXTURES_DIR / "arxiv_feed.xml"
    with open(fixture_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    adapter = ArxivAdapter()
    entries = adapter._parse_feed(xml_content)
    assert len(entries) == 1

    raw_rec = RawRecord(
        source="arxiv",
        source_record_id=entries[0]["arxiv_id"],
        raw_data=entries[0],
    )

    paper = adapter.normalize(raw_rec)

    assert paper.arxiv_id == "1706.03762"
    assert paper.title == "Attention Is All You Need"
    assert paper.doi == "10.48550/arxiv.1706.03762"
    assert len(paper.authors) == 2
    assert paper.open_access.is_oa is True
    assert paper.fulltext_available == FulltextStatus.FULLTEXT_AVAILABLE
    assert paper.fulltext_url == "http://arxiv.org/pdf/1706.03762v7"


def test_crossref_normalization():
    fixture_path = FIXTURES_DIR / "crossref_response.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    item = data["message"]["items"][0]
    raw_rec = RawRecord(
        source="crossref",
        source_record_id="10.48550/arxiv.1706.03762",
        raw_data=item,
    )

    adapter = CrossrefAdapter()
    paper = adapter.normalize(raw_rec)

    assert paper.title == "Attention Is All You Need"
    assert paper.doi == "10.48550/arxiv.1706.03762"
    assert paper.publication_year == 2017
    assert paper.publication_date == "2017-06-12"
    assert len(paper.authors) == 2
    assert paper.authors[0].name == "Ashish Vaswani"
    assert paper.authors[0].affiliations == ["Google Brain"]
    assert paper.venue.name == "Advances in Neural Information Processing Systems"
