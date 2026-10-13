"""Integration Tests for Scientific Information Extraction Pipeline."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from dataset.schemas.document_processing import ChunkStrategy, ProcessedChunk
from dataset.schemas.scientific_knowledge import (
    ScientificEntityRecord,
    ScientificRelationRecord,
    ScientificStatementRecord,
)
from pipelines.extraction.config import ExtractionConfig
from pipelines.extraction.pipeline import ScientificExtractionPipeline


@pytest.fixture
def mock_pilot_dataset(tmp_path: Path):
    """Create a temporary synthetic corpus and directories for integration testing."""
    root = tmp_path / "dataset"
    processed = root / "processed" / "v0.3.0"
    processed.mkdir(parents=True, exist_ok=True)
    manifests = root / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)

    chunks_file = processed / "chunks.jsonl"

    chunks = []
    sections = [
        ("Abstract", "The paper examines how deep learning strengthens intrusion detection."),
        ("1. Introduction", "Cyber threats challenge security teams. We propose a CNN model."),
        ("2. Methods", "The convolutional neural network uses gradient descent."),
        ("3. Results", "The model achieved an accuracy of 98.7% on the NSL-KDD dataset."),
        ("4. Conclusion", "Future research will explore federated learning in cybersecurity."),
    ]

    for p in range(1, 15):
        cid = f"rg_doi_syn_{p:02d}"
        for s_idx, (sec_title, text) in enumerate(sections, 1):
            chunks.append(
                ProcessedChunk(
                    chunk_id=f"chk_{cid}_{s_idx}",
                    canonical_id=cid,
                    document_id=f"doc_{cid}",
                    section_id=f"sec_{cid}_{s_idx}",
                    section_title=sec_title,
                    page_start=1,
                    page_end=1,
                    paragraph_start_order=s_idx,
                    paragraph_end_order=s_idx,
                    text=f"{text} Additional context for evaluation.",
                    strategy=ChunkStrategy.STRATEGY_A_PARAGRAPH,
                )
            )

    with open(chunks_file, "w", encoding="utf-8") as f:
        for chk in chunks:
            f.write(json.dumps(chk.model_dump()) + "\n")

    return root, chunks_file


def test_pipeline_end_to_end_execution(mock_pilot_dataset, tmp_path: Path):
    root, chunks_file = mock_pilot_dataset

    config = ExtractionConfig(
        DATASET_STORAGE_ROOT=str(root),
        EXTRACTION_PIPELINE_VERSION="v0.4.0-test",
        DEFAULT_SAMPLE_SIZE=25,
        DEFAULT_RANDOM_SEED=42,
    )

    pipeline = ScientificExtractionPipeline(config=config)
    batch_result, report = pipeline.run_pilot(
        target_size=25,
        seed=42,
        chunks_jsonl_path=chunks_file,
    )

    # 1. Verify batch result and report objects
    assert batch_result.total_chunks_processed == 25
    assert len(batch_result.entities) > 0
    assert len(batch_result.statements) > 0
    assert report.total_chunks == 25
    assert report.evidence_grounding_accuracy == 1.0
    assert report.provenance_validity_rate == 1.0

    # 2. Verify disk persistence
    out_dir = config.output_dir
    assert (out_dir / "extracted_records.jsonl").exists()
    assert (out_dir / "extracted_relationships.jsonl").exists()
    assert (out_dir / "rejected_records.jsonl").exists()

    # 3. Verify manifest and report generation
    m_dir = config.manifests_dir
    v = config.EXTRACTION_PIPELINE_VERSION
    assert (m_dir / f"scientific_extraction_pilot_{v}_manifest.json").exists()
    assert (m_dir / f"scientific_extraction_pilot_{v}_quality_report.json").exists()
    assert (m_dir / f"scientific_extraction_pilot_{v}_report.md").exists()
    assert (m_dir / f"scientific_extraction_{v}_annotation_template.csv").exists()
    assert (m_dir / f"scientific_extraction_{v}_annotation_guidelines.md").exists()

    # 4. Verify deserialization of generated record files
    with open(out_dir / "extracted_records.jsonl", "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == len(batch_result.entities) + len(batch_result.statements)
        for line in lines[:5]:
            data = json.loads(line)
            if "normalized_name" in data:
                ScientificEntityRecord.model_validate(data)
            else:
                ScientificStatementRecord.model_validate(data)
