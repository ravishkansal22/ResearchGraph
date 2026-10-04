"""Unit tests for deduplication and metadata consolidation."""

from dataset.schemas.canonical_paper import (
    Author,
    CanonicalPaper,
    FulltextStatus,
    ProvenanceRecord,
    SourceRecords,
    Topic,
    Venue,
)
from pipelines.ingestion.resolution.deduplicator import (
    Deduplicator,
    merge_two_canonical_papers,
)


def test_merge_two_canonical_papers():
    p_openalex = CanonicalPaper(
        canonical_id="temp_oa",
        title="Attention Is All You Need",
        abstract="The dominant sequence transduction models...",
        authors=[
            Author(
                name="Ashish Vaswani",
                first_name="Ashish",
                last_name="Vaswani",
                orcid="0000-0002-1234-5678",
                affiliations=["Google Brain"],
            )
        ],
        publication_year=2017,
        doi="10.48550/arxiv.1706.03762",
        arxiv_id="1706.03762",
        topics=[Topic(name="Transformer (machine learning model)")],
        citation_count=115000,
        source_records=SourceRecords(openalex="W2741809807"),
        provenance=[
            ProvenanceRecord(source="openalex", source_record_id="W2741809807")
        ],
    )

    p_s2 = CanonicalPaper(
        canonical_id="temp_s2",
        title="Attention is All you Need",
        abstract="The dominant sequence transduction models are based on complex neural networks.",
        authors=[
            Author(name="Ashish Vaswani", first_name="Ashish", last_name="Vaswani"),
            Author(name="Noam Shazeer", first_name="Noam", last_name="Shazeer"),
        ],
        publication_year=2017,
        doi="10.48550/arxiv.1706.03762",
        arxiv_id="1706.03762",
        venue=Venue(name="NIPS"),
        topics=[Topic(name="Computer Science")],
        citation_count=115200,
        influential_citation_count=12400,
        fulltext_available=FulltextStatus.FULLTEXT_AVAILABLE,
        fulltext_url="https://arxiv.org/pdf/1706.03762.pdf",
        source_records=SourceRecords(semantic_scholar="204e3073870fae3d05bcbc2f6a8e263c9b72e776"),
        provenance=[
            ProvenanceRecord(source="semantic_scholar", source_record_id="204e3073870fae3d05bcbc2f6a8e263c9b72e776")
        ],
    )

    merged = merge_two_canonical_papers(p_openalex, p_s2)

    # Validate consolidation
    assert merged.doi == "10.48550/arxiv.1706.03762"
    assert merged.arxiv_id == "1706.03762"
    assert len(merged.authors) == 2
    assert merged.authors[0].orcid == "0000-0002-1234-5678"
    assert merged.venue.name == "NIPS"
    assert merged.citation_count == 115200
    assert merged.influential_citation_count == 12400
    assert merged.fulltext_available == FulltextStatus.FULLTEXT_AVAILABLE
    assert merged.source_records.openalex == "W2741809807"
    assert merged.source_records.semantic_scholar == "204e3073870fae3d05bcbc2f6a8e263c9b72e776"
    assert len(merged.provenance) == 2
    assert len(merged.topics) == 2


def test_deduplicator_stream():
    deduplicator = Deduplicator()
    papers = [
        CanonicalPaper(
            canonical_id="p1",
            title="Attention Is All You Need",
            doi="10.48550/arxiv.1706.03762",
            source_records=SourceRecords(openalex="W1"),
            provenance=[ProvenanceRecord(source="openalex", source_record_id="W1")],
        ),
        CanonicalPaper(
            canonical_id="p2",
            title="Attention Is All You Need",
            doi="10.48550/arxiv.1706.03762",
            source_records=SourceRecords(semantic_scholar="S1"),
            provenance=[ProvenanceRecord(source="semantic_scholar", source_record_id="S1")],
        ),
        CanonicalPaper(
            canonical_id="p3",
            title="Distinct Completely Unrelated Paper on Quantum Systems",
            doi="10.1103/physrevd.99.12345",
            source_records=SourceRecords(crossref="10.1103/physrevd.99.12345"),
            provenance=[ProvenanceRecord(source="crossref", source_record_id="10.1103/physrevd.99.12345")],
        ),
    ]

    canonical, stats = deduplicator.deduplicate(papers)
    assert len(canonical) == 2
    assert stats["duplicates_merged"] == 1
    assert stats["total_input_records"] == 3
