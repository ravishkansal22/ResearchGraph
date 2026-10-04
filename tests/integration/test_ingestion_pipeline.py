"""Integration tests for the end-to-end literature ingestion pipeline."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import httpx
import polars as pl
import pytest

from pipelines.ingestion.config import config
from pipelines.ingestion.pipeline import LiteratureIngestionPipeline

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture
def mock_network_responses():
    """Mock HTTP responses for all 4 scholarly source adapters using local fixture files."""
    with open(FIXTURES_DIR / "openalex_response.json", "r", encoding="utf-8") as f:
        openalex_json = json.load(f)

    with open(FIXTURES_DIR / "semantic_scholar_response.json", "r", encoding="utf-8") as f:
        s2_json = json.load(f)

    with open(FIXTURES_DIR / "arxiv_feed.xml", "r", encoding="utf-8") as f:
        arxiv_xml = f.read()

    with open(FIXTURES_DIR / "crossref_response.json", "r", encoding="utf-8") as f:
        crossref_json = json.load(f)

    def mock_request_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "api.openalex.org" in url:
            return httpx.Response(200, json=openalex_json, request=request)
        elif "api.semanticscholar.org" in url:
            return httpx.Response(200, json=s2_json, request=request)
        elif "export.arxiv.org" in url:
            return httpx.Response(200, text=arxiv_xml, request=request)
        elif "api.crossref.org" in url:
            return httpx.Response(200, json=crossref_json, request=request)
        return httpx.Response(404, request=request)

    return mock_request_handler


def test_end_to_end_pipeline_integration(tmp_path, mock_network_responses):
    """Test full pipeline run from raw collection to canonical Parquet/JSONL and quality report."""
    test_version = "v0.1.0-integration-test"

    # Patch storage directory to isolated temporary directory
    with patch.object(config, "DATASET_STORAGE_ROOT", str(tmp_path)):
        pipeline = LiteratureIngestionPipeline(dataset_version=test_version)

        # Mock adapter HTTP clients
        mock_transport = httpx.MockTransport(mock_network_responses)
        for adapter in pipeline.adapters.values():
            adapter.client = httpx.Client(transport=mock_transport)

        # Execute pipeline across all 4 sources
        summary = pipeline.run(
            query="attention transformer",
            sources=["openalex", "semantic_scholar", "arxiv", "crossref"],
            limit_per_source=5,
            filter_mode="broad_ai",
            acquire_fulltext=False,
            dry_run=False,
        )

        assert summary["raw_records_count"] == 4
        # All 4 sources return records for "Attention Is All You Need" with DOI 10.48550/arxiv.1706.03762
        # They should deduplicate into exactly 1 canonical paper
        assert summary["canonical_papers_count"] == 1
        assert summary["duplicates_merged"] == 3

        # Verify filesystem outputs
        raw_openalex = tmp_path / "raw" / "openalex"
        assert raw_openalex.exists()

        interim_dir = tmp_path / "interim"
        assert interim_dir.exists()

        processed_dir = tmp_path / "processed" / test_version
        assert (processed_dir / "canonical_papers.jsonl").exists()
        assert (processed_dir / "canonical_papers.parquet").exists()

        manifest_file = tmp_path / "manifests" / f"{test_version}_manifest.json"
        assert manifest_file.exists()
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            assert manifest["paper_count"] == 1
            assert manifest["sources"] == ["openalex", "semantic_scholar", "arxiv", "crossref"]

        report_md_file = tmp_path / "manifests" / f"{test_version}_quality_report.md"
        assert report_md_file.exists()

        # Read parquet output using Polars and verify schema
        df = pl.read_parquet(processed_dir / "canonical_papers.parquet")
        assert df.shape[0] == 1
        assert "Attention Is All You Need" in df["title"][0]
        assert df["doi"][0] == "10.48550/arxiv.1706.03762"
        assert df["arxiv_id"][0] == "1706.03762"

        pipeline.close()
