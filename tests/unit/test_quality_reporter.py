"""Unit tests for Quality Reporter and Manifest Generator."""

from dataset.schemas.canonical_paper import (
    Author,
    CanonicalPaper,
    FulltextStatus,
    ProvenanceRecord,
    SourceRecords,
    Topic,
)
from pipelines.ingestion.quality.reporter import QualityReporter


def test_quality_report_generation():
    reporter = QualityReporter(schema_version="0.1.0", pipeline_version="0.1.0")

    papers = [
        CanonicalPaper(
            canonical_id="p1",
            title="Transformer Networks for Machine Translation",
            abstract="In this work we propose a novel transformer model for machine translation.",
            authors=[Author(name="A. Vaswani", last_name="Vaswani")],
            publication_year=2017,
            doi="10.48550/arxiv.1706.03762",
            arxiv_id="1706.03762",
            topics=[Topic(name="AI")],
            citation_count=1000,
            fulltext_available=FulltextStatus.FULLTEXT_AVAILABLE,
            provenance=[
                ProvenanceRecord(source="openalex", source_record_id="W1"),
                ProvenanceRecord(source="semantic_scholar", source_record_id="S1"),
            ],
            source_records=SourceRecords(openalex="W1", semantic_scholar="S1"),
        )
    ]

    dedup_stats = {
        "total_input_records": 2,
        "duplicates_merged": 1,
        "duplicate_rate": 0.5,
        "unresolved_possible_matches": 0,
    }

    manifest = reporter.generate_manifest(
        canonical_papers=papers,
        dataset_version="v0.1.0-test",
        sources_used=["openalex", "semantic_scholar"],
        dedup_stats=dedup_stats,
    )

    assert manifest["dataset_version"] == "v0.1.0-test"
    assert manifest["paper_count"] == 1
    assert manifest["statistics"]["duplicates_merged"] == 1
    assert manifest["statistics"]["papers_per_source"]["openalex"] == 1
    assert manifest["statistics"]["papers_per_source"]["semantic_scholar"] == 1

    report_dict, md_text = reporter.compute_quality_report(papers, manifest)
    assert report_dict["paper_count"] == 1
    assert report_dict["metadata_completeness"]["title_pct"] == 100.0
    assert report_dict["metadata_completeness"]["abstract_pct"] == 100.0
    assert "ResearchGraph Dataset Quality Report" in md_text
    assert "v0.1.0-test" in md_text
