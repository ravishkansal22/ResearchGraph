"""Integration tests for Phase 2 Document Processing Pilot."""

import json
from pathlib import Path
import polars as pl
import pytest

from dataset.schemas.document_processing import ChunkStrategy, ProcessedDocument
from pipelines.processing.pipeline import DocumentProcessingPipeline


def test_discover_pilot_inputs():
    pipeline = DocumentProcessingPipeline()
    inputs = pipeline.discover_pilot_inputs()
    assert len(inputs) == 8
    for item in inputs:
        assert item["canonical_id"].startswith("rg_doi_")
        assert Path(item["absolute_pdf_path"]).exists()
        assert len(item["file_hash"]) == 64


def test_end_to_end_pilot_execution_and_artifacts(tmp_path):
    pipeline = DocumentProcessingPipeline()
    docs, audit = pipeline.run_pilot()

    assert len(docs) == 8
    assert audit["total_documents_processed"] == 8
    assert audit["successful_documents"] == 8
    assert audit["total_pages"] == 214
    assert audit["extracted_pages"] == 214
    assert audit["empty_pages"] == 0

    # Verify generated artifact files exist
    output_dir = pipeline.output_dir
    manifest_dir = pipeline.manifest_dir

    assert (output_dir / "documents.jsonl").exists()
    assert (output_dir / "chunks.jsonl").exists()
    assert (output_dir / "chunks_strategy_a.jsonl").exists()
    assert (output_dir / "chunks_strategy_b.jsonl").exists()
    assert (output_dir / "chunks.parquet").exists()
    assert (manifest_dir / "document_processing_pilot_v0.2.0_manifest.json").exists()
    assert (manifest_dir / "document_processing_pilot_v0.2.0_quality_report.json").exists()
    assert (manifest_dir / "document_processing_pilot_v0.2.0_manual_review.csv").exists()
    assert (manifest_dir / "document_processing_pilot_v0.2.0_report.md").exists()

    # Validate parquet read
    df = pl.read_parquet(output_dir / "chunks.parquet")
    assert len(df) > 500
    assert "chunk_id" in df.columns
    assert "canonical_id" in df.columns
    assert "section_id" in df.columns
    assert "text" in df.columns
    assert "char_count" in df.columns


def test_pipeline_determinism():
    """Verify that processing the same document twice produces identical hash and structure."""
    pipeline = DocumentProcessingPipeline()
    inputs = pipeline.discover_pilot_inputs()
    sample_input = inputs[0]

    doc1 = pipeline.process_single_pdf(sample_input)
    doc2 = pipeline.process_single_pdf(sample_input)

    assert doc1.processing.character_count == doc2.processing.character_count
    assert len(doc1.sections) == len(doc2.sections)
    assert len(doc1.paragraphs) == len(doc2.paragraphs)
    assert len(doc1.chunks_strategy_a) == len(doc2.chunks_strategy_a)
    assert [c.chunk_id for c in doc1.chunks_strategy_a] == [c.chunk_id for c in doc2.chunks_strategy_a]
