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
    pipeline.output_dir = tmp_path / "processed"
    pipeline.manifest_dir = tmp_path / "manifests"
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


def test_discover_expansion_inputs():
    """Verify that discover_expansion_inputs identifies all 50 valid cached PDFs."""
    pipeline = DocumentProcessingPipeline(processor_version="v0.3.0")
    inputs = pipeline.discover_expansion_inputs()
    assert len(inputs) == 50
    for item in inputs:
        assert item["canonical_id"].startswith("rg_doi_")
        assert Path(item["absolute_pdf_path"]).exists()
        assert len(item["file_hash"]) == 64


def test_expansion_v0_3_0_artifacts_integrity():
    """Verify that the 50-paper v0.3.0 artifacts exist and conform to schemas."""
    pipeline = DocumentProcessingPipeline(processor_version="v0.3.0")
    output_dir = pipeline.output_dir
    manifest_dir = pipeline.manifest_dir

    assert (output_dir / "documents.jsonl").exists()
    assert (output_dir / "chunks.jsonl").exists()
    assert (output_dir / "chunks_strategy_a.jsonl").exists()
    assert (output_dir / "chunks_strategy_b.jsonl").exists()
    assert (output_dir / "chunks.parquet").exists()

    manifest_path = manifest_dir / "document_processing_v0.3.0_manifest.json"
    assert manifest_path.exists()
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["target_input_count"] == 50
    assert manifest["successfully_processed_count"] == 50
    assert manifest["total_pages_processed"] == 1009
    assert manifest["extracted_pages_count"] == 1009
    assert len(manifest["documents"]) == 50

    # Verify manual review CSV exists and has all human evaluation columns blank
    review_path = manifest_dir / "document_processing_v0.3.0_manual_review.csv"
    assert review_path.exists()
    with open(review_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) > 100  # At least 3 samples per paper (header + rows)

    # Validate chunks parquet
    df = pl.read_parquet(output_dir / "chunks.parquet")
    assert len(df) == manifest["chunk_comparison"]["strategy_a_paragraph_based"]["total_chunks"]
    assert "chunk_id" in df.columns
    assert "canonical_id" in df.columns
    assert "section_id" in df.columns
    assert "text" in df.columns

