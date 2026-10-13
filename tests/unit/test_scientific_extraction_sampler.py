"""Unit Tests for Deterministic Stratified Chunk Sampler."""

from __future__ import annotations

import pytest

from dataset.schemas.document_processing import ChunkStrategy, ProcessedChunk
from pipelines.extraction.selection import ChunkSampler


@pytest.fixture
def mock_chunks():
    chunks = []
    sections = [
        ("Abstract", "ABSTRACT"),
        ("1. Introduction", "INTRO_BACKGROUND"),
        ("2. Research Methodology", "METHODS"),
        ("3. Experimental Results", "RESULTS"),
        ("4. Discussion & Limitations", "CONCLUSION_LIMITATIONS"),
    ]

    for p_idx in range(1, 21):  # 20 papers
        cid = f"rg_doi_paper_{p_idx:02d}"
        for s_title, _ in sections:
            for c_order in range(1, 3):
                chk_id = f"chk_{cid}_{s_title[:4]}_{c_order}"
                text = f"Substantive scientific content for {s_title} in paper {p_idx}. Evaluating accuracy."
                if p_idx == 1 and s_title == "Abstract":
                    text = "Short text."  # edge case: short chunk
                chunks.append(
                    ProcessedChunk(
                        chunk_id=chk_id,
                        canonical_id=cid,
                        document_id=f"doc_{cid}",
                        section_id=f"sec_{cid}",
                        section_title=s_title,
                        page_start=1,
                        page_end=1,
                        paragraph_start_order=c_order,
                        paragraph_end_order=c_order,
                        text=text,
                        char_count=len(text),
                        word_count=len(text.split()),
                        token_count_est=len(text.split()),
                        strategy=ChunkStrategy.STRATEGY_A_PARAGRAPH,
                    )
                )
    return chunks


def test_sampler_reproducibility(mock_chunks):
    sampler1 = ChunkSampler(seed=42, target_size=30)
    selected1, manifest1 = sampler1.select_pilot_chunks(mock_chunks)

    sampler2 = ChunkSampler(seed=42, target_size=30)
    selected2, manifest2 = sampler2.select_pilot_chunks(mock_chunks)

    ids1 = [c.chunk_id for c in selected1]
    ids2 = [c.chunk_id for c in selected2]
    assert ids1 == ids2
    assert len(selected1) == 30


def test_sampler_stratification_and_paper_diversity(mock_chunks):
    sampler = ChunkSampler(seed=42, target_size=40)
    selected, manifest = sampler.select_pilot_chunks(mock_chunks)

    assert len(selected) == 40
    unique_papers = len({c.canonical_id for c in selected})
    assert unique_papers >= 10  # Promotes high paper diversity

    buckets = {m.section_bucket for m in manifest}
    assert "ABSTRACT" in buckets
    assert "METHODS" in buckets
    assert "RESULTS" in buckets
    assert "INTRO_BACKGROUND" in buckets
    assert "CONCLUSION_LIMITATIONS" in buckets


def test_sampler_detects_edge_cases(mock_chunks):
    sampler = ChunkSampler(seed=42, target_size=20)
    selected, manifest = sampler.select_pilot_chunks(mock_chunks)

    edge_cases = [m for m in manifest if m.is_edge_case]
    assert len(edge_cases) > 0
