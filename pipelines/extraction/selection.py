"""Deterministic Chunk Sampler for Extraction Pilot (Phase 3).

Selects a reproducible, stratified, and deliberately diverse sample of 50-100 chunks
from the upstream processed corpus (v0.3.0 Strategy A chunks), covering diverse
papers, scientific sections, and edge cases (short chunks, metrics, equations).
"""

from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dataset.schemas.document_processing import ProcessedChunk

logger = logging.getLogger(__name__)


# Section category categorization patterns
RE_ABSTRACT = re.compile(r"abstract|summary", re.IGNORECASE)
RE_INTRO = re.compile(r"intro|background|overview|motivation|related\s*work", re.IGNORECASE)
RE_METHODS = re.compile(r"method|methodology|approach|architecture|system|model|implementation|framework", re.IGNORECASE)
RE_RESULTS = re.compile(r"result|experiment|evaluation|finding|empirical|performance|analysis", re.IGNORECASE)
RE_CONCLUSION = re.compile(r"conclusion|limit|future|threat|discussion", re.IGNORECASE)

# Patterns for edge cases
RE_METRICS_NUMERICAL = re.compile(r"(\b\d+(\.\d+)?%|\bp\s*[<>=]\s*\d|\bF1\b|\bAUC\b|\baccuracy\b|\b\d+\.\d+\b)", re.IGNORECASE)
RE_MATH_EQUATIONS = re.compile(r"(=|\+|\-|\*|\/|\^|\\sum|\\alpha|\\beta|\\theta|\\sigma|\\in|\bargmax\b)", re.IGNORECASE)


@dataclass
class SampledChunkRecord:
    """Diagnostic manifest entry for each sampled chunk."""
    sample_index: int
    canonical_id: str
    document_id: Optional[str]
    chunk_id: str
    section_id: str
    section_title: str
    section_bucket: str
    page_start: int
    page_end: int
    char_count: int
    word_count: int
    is_edge_case: bool
    edge_case_reason: Optional[str]
    text_preview: str


class ChunkSampler:
    """Reproducible, stratified sampler for scientific information extraction pilot."""

    def __init__(
        self,
        seed: int = 42,
        target_size: int = 75,
        min_papers: int = 15,
    ):
        self.seed = seed
        self.target_size = target_size
        self.min_papers = min_papers

    @staticmethod
    def classify_section_bucket(section_title: str) -> str:
        """Categorize section heading into functional scientific discourse bucket."""
        if not section_title:
            return "OTHER"
        title = section_title.strip()
        if RE_ABSTRACT.search(title):
            return "ABSTRACT"
        if RE_INTRO.search(title):
            return "INTRO_BACKGROUND"
        if RE_METHODS.search(title):
            return "METHODS"
        if RE_RESULTS.search(title):
            return "RESULTS"
        if RE_CONCLUSION.search(title):
            return "CONCLUSION_LIMITATIONS"
        return "OTHER"

    @staticmethod
    def detect_edge_case(chunk: ProcessedChunk) -> Tuple[bool, Optional[str]]:
        """Identify if a chunk presents a notable NLP challenge."""
        text = chunk.text.strip()
        if len(text) < 150:
            return True, "SHORT_CHUNK_UNDER_150_CHARS"
        if len(text) > 1800:
            return True, "LONG_DENSE_CHUNK_OVER_1800_CHARS"
        has_metrics = bool(RE_METRICS_NUMERICAL.search(text))
        has_math = bool(RE_MATH_EQUATIONS.search(text))
        if has_metrics and has_math:
            return True, "DENSE_NUMERICAL_AND_FORMULAS"
        if has_metrics:
            return True, "QUANTITATIVE_METRICS_AND_PERCENTAGES"
        return False, None

    def select_pilot_chunks(
        self,
        chunks: List[ProcessedChunk],
    ) -> Tuple[List[ProcessedChunk], List[SampledChunkRecord]]:
        """Execute deterministic stratified sampling across papers and sections.

        Target distribution for target_size=75:
        - ABSTRACT: ~12 chunks
        - INTRO_BACKGROUND: ~15 chunks
        - METHODS: ~18 chunks
        - RESULTS: ~15 chunks
        - CONCLUSION_LIMITATIONS: ~10 chunks
        - Controlled Edge Cases: ~5 chunks explicitly retained
        """
        if len(chunks) < self.target_size:
            raise ValueError(f"Corpus chunks ({len(chunks)}) fewer than target sample size ({self.target_size})")

        rng = random.Random(self.seed)

        # 1. Bucket chunks by functional section
        bucketed: Dict[str, List[ProcessedChunk]] = {
            "ABSTRACT": [],
            "INTRO_BACKGROUND": [],
            "METHODS": [],
            "RESULTS": [],
            "CONCLUSION_LIMITATIONS": [],
            "OTHER": [],
        }

        edge_candidates: List[Tuple[ProcessedChunk, str]] = []

        for chk in chunks:
            bucket = self.classify_section_bucket(chk.section_title)
            bucketed[bucket].append(chk)

            is_edge, reason = self.detect_edge_case(chk)
            if is_edge and reason:
                edge_candidates.append((chk, reason))

        # Target allocations
        allocations = {
            "ABSTRACT": int(self.target_size * 0.16),               # ~12
            "INTRO_BACKGROUND": int(self.target_size * 0.20),       # ~15
            "METHODS": int(self.target_size * 0.24),                # ~18
            "RESULTS": int(self.target_size * 0.20),                # ~15
            "CONCLUSION_LIMITATIONS": int(self.target_size * 0.13), # ~10
        }
        edge_target = self.target_size - sum(allocations.values())   # ~5

        selected_chunks: List[ProcessedChunk] = []
        selected_ids: set[str] = set()
        edge_reasons: Dict[str, str] = {}

        # First, sample designated edge cases (short, dense quantitative, formulas)
        rng.shuffle(edge_candidates)
        edge_count = 0
        for chk, reason in edge_candidates:
            if edge_count >= edge_target:
                break
            if chk.chunk_id not in selected_ids:
                selected_chunks.append(chk)
                selected_ids.add(chk.chunk_id)
                edge_reasons[chk.chunk_id] = reason
                edge_count += 1

        # Next, sample from each functional section bucket ensuring paper diversity
        for b_name, b_target in allocations.items():
            candidates = bucketed.get(b_name, [])
            # Shuffle candidates deterministically
            rng.shuffle(candidates)

            # Sort by paper appearance frequency in current selection to promote paper diversity
            def paper_count_key(c: ProcessedChunk) -> Tuple[int, str]:
                p_count = sum(1 for sc in selected_chunks if sc.canonical_id == c.canonical_id)
                return (p_count, c.chunk_id)

            candidates.sort(key=paper_count_key)

            count = 0
            for c in candidates:
                if count >= b_target:
                    break
                if c.chunk_id not in selected_ids:
                    selected_chunks.append(c)
                    selected_ids.add(c.chunk_id)
                    count += 1

        # If any remaining slots to reach target_size, fill from remaining chunks
        if len(selected_chunks) < self.target_size:
            remainder = [c for c in chunks if c.chunk_id not in selected_ids]
            rng.shuffle(remainder)
            for c in remainder:
                if len(selected_chunks) >= self.target_size:
                    break
                selected_chunks.append(c)
                selected_ids.add(c.chunk_id)

        # Sort selected chunks deterministically by canonical_id and chunk_id
        selected_chunks.sort(key=lambda x: (x.canonical_id, x.chunk_id))

        # Build diagnostic manifest
        manifest_records: List[SampledChunkRecord] = []
        for idx, chk in enumerate(selected_chunks, 1):
            bucket = self.classify_section_bucket(chk.section_title)
            is_edge = chk.chunk_id in edge_reasons
            reason = edge_reasons.get(chk.chunk_id)
            if not is_edge:
                is_edge, reason = self.detect_edge_case(chk)

            manifest_records.append(
                SampledChunkRecord(
                    sample_index=idx,
                    canonical_id=chk.canonical_id,
                    document_id=chk.document_id,
                    chunk_id=chk.chunk_id,
                    section_id=chk.section_id,
                    section_title=chk.section_title,
                    section_bucket=bucket,
                    page_start=chk.page_start,
                    page_end=chk.page_end,
                    char_count=chk.char_count,
                    word_count=chk.word_count,
                    is_edge_case=is_edge,
                    edge_case_reason=reason,
                    text_preview=chk.text[:120].replace("\n", " ").strip() + "...",
                )
            )

        unique_papers = len({c.canonical_id for c in selected_chunks})
        logger.info(
            f"Selected {len(selected_chunks)} chunks across {unique_papers} distinct papers "
            f"(seed={self.seed}, target={self.target_size})"
        )

        return selected_chunks, manifest_records

    @classmethod
    def load_chunks_from_jsonl(cls, jsonl_path: Path) -> List[ProcessedChunk]:
        """Load ProcessedChunk instances from a jsonl file."""
        chunks: List[ProcessedChunk] = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    chunks.append(ProcessedChunk(**data))
        return chunks
