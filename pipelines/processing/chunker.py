"""Structure-Aware Chunking Strategies for Scientific Documents.

Implements two distinct chunking approaches designed specifically for
scholarly literature with full provenance tracking:
- Strategy A: Paragraph-based grouping (preserves atomic paragraph semantics)
- Strategy B: Structure-aware fixed-size with sentence-boundary overlap
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from dataset.schemas.document_processing import (
    ChunkStrategy,
    DocumentMetadata,
    ProcessedChunk,
    ProcessedParagraph,
    ProcessedSection,
)

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Generates structure-aware, provenance-preserving chunks from structured documents."""

    def __init__(
        self,
        target_char_size: int = 1200,      # Target chunk size in characters (~250-300 words)
        max_char_size: int = 2000,         # Maximum threshold before forcing a split
        min_char_size: int = 150,          # Minimum chunk size threshold
        overlap_char_size: int = 200,      # Overlap size for Strategy B
    ):
        self.target_char_size = target_char_size
        self.max_char_size = max_char_size
        self.min_char_size = min_char_size
        self.overlap_char_size = overlap_char_size

    def chunk_strategy_a_paragraph_based(
        self,
        sections: List[ProcessedSection],
        paragraphs: List[ProcessedParagraph],
        metadata: DocumentMetadata,
    ) -> List[ProcessedChunk]:
        """Strategy A: Group atomic paragraphs within sections without cross-section bleeding."""
        chunks: List[ProcessedChunk] = []
        chunk_order = 1

        # Map paragraphs by section
        p_by_sec: Dict[str, List[ProcessedParagraph]] = {}
        for p in paragraphs:
            p_by_sec.setdefault(p.section_id, []).append(p)

        for sec in sections:
            sec_pars = p_by_sec.get(sec.section_id, [])
            if not sec_pars:
                continue

            current_group: List[ProcessedParagraph] = []
            current_len = 0

            for p in sec_pars:
                p_len = len(p.text)

                # If single paragraph is oversized (> max_char_size), flush current and create dedicated chunk(s)
                if p_len > self.max_char_size:
                    if current_group:
                        chunks.append(
                            self._create_chunk_from_paragraphs(
                                current_group,
                                sec,
                                metadata,
                                ChunkStrategy.STRATEGY_A_PARAGRAPH,
                                chunk_order,
                            )
                        )
                        chunk_order += 1
                        current_group = []
                        current_len = 0

                    # Create chunk for this oversized paragraph
                    chunks.append(
                        self._create_chunk_from_paragraphs(
                            [p],
                            sec,
                            metadata,
                            ChunkStrategy.STRATEGY_A_PARAGRAPH,
                            chunk_order,
                        )
                    )
                    chunk_order += 1
                    continue

                # If adding this paragraph exceeds target size and current group is non-empty, flush
                if (current_len + p_len > self.target_char_size) and current_group:
                    chunks.append(
                        self._create_chunk_from_paragraphs(
                            current_group,
                            sec,
                            metadata,
                            ChunkStrategy.STRATEGY_A_PARAGRAPH,
                            chunk_order,
                        )
                    )
                    chunk_order += 1
                    current_group = [p]
                    current_len = p_len
                else:
                    current_group.append(p)
                    current_len += p_len + 2  # account for join space

            # Flush remaining group for this section
            if current_group:
                chunks.append(
                    self._create_chunk_from_paragraphs(
                        current_group,
                        sec,
                        metadata,
                        ChunkStrategy.STRATEGY_A_PARAGRAPH,
                        chunk_order,
                    )
                )
                chunk_order += 1

        return chunks

    def chunk_strategy_b_structure_aware_fixed(
        self,
        sections: List[ProcessedSection],
        paragraphs: List[ProcessedParagraph],
        metadata: DocumentMetadata,
    ) -> List[ProcessedChunk]:
        """Strategy B: Target fixed-size character windows with sentence-aware overlap respecting sections."""
        chunks: List[ProcessedChunk] = []
        chunk_order = 1

        p_by_sec: Dict[str, List[ProcessedParagraph]] = {}
        for p in paragraphs:
            p_by_sec.setdefault(p.section_id, []).append(p)

        for sec in sections:
            sec_pars = p_by_sec.get(sec.section_id, [])
            if not sec_pars:
                continue

            # Collect all sentences in section with their paragraph metadata
            sec_sentences: List[Tuple[str, ProcessedParagraph]] = []
            for p in sec_pars:
                if p.sentences:
                    for s in p.sentences:
                        sec_sentences.append((s.text, p))
                else:
                    sec_sentences.append((p.text, p))

            if not sec_sentences:
                continue

            # Sliding sentence window over section
            s_idx = 0
            while s_idx < len(sec_sentences):
                window_sentences: List[str] = []
                window_pars: List[ProcessedParagraph] = []
                window_len = 0
                adv_idx = s_idx

                while adv_idx < len(sec_sentences):
                    s_txt, p_obj = sec_sentences[adv_idx]
                    s_len = len(s_txt)

                    if window_len + s_len > self.target_char_size and window_sentences:
                        break

                    window_sentences.append(s_txt)
                    if not window_pars or window_pars[-1].paragraph_id != p_obj.paragraph_id:
                        window_pars.append(p_obj)
                    window_len += s_len + 1
                    adv_idx += 1

                if not window_sentences:
                    # Single sentence longer than target size
                    s_txt, p_obj = sec_sentences[s_idx]
                    window_sentences.append(s_txt)
                    window_pars.append(p_obj)
                    adv_idx = s_idx + 1

                chunk_text = " ".join(window_sentences).strip()
                p_start = window_pars[0].paragraph_order if window_pars else 1
                p_end = window_pars[-1].paragraph_order if window_pars else p_start
                pg_start = min((p.page_number for p in window_pars), default=sec.start_page)
                pg_end = max((p.page_number for p in window_pars), default=sec.end_page)
                p_ids = [p.paragraph_id for p in window_pars]

                words = len(chunk_text.split())
                tokens_est = int(words * 1.3)

                chk = ProcessedChunk(
                    chunk_id=f"chk_{metadata.canonical_id}_B_{chunk_order:04d}",
                    canonical_id=metadata.canonical_id,
                    section_id=sec.section_id,
                    section_title=sec.section_title,
                    section_level=sec.section_level,
                    page_start=pg_start,
                    page_end=pg_end,
                    paragraph_start_order=p_start,
                    paragraph_end_order=p_end,
                    paragraph_ids=p_ids,
                    text=chunk_text,
                    char_count=len(chunk_text),
                    word_count=words,
                    token_count_est=tokens_est,
                    strategy=ChunkStrategy.STRATEGY_B_STRUCTURE_FIXED,
                    provenance={
                        "canonical_id": metadata.canonical_id,
                        "title": metadata.title,
                        "doi": metadata.doi,
                        "source": metadata.source,
                        "section_id": sec.section_id,
                        "section_title": sec.section_title,
                        "section_level": sec.section_level,
                        "page_start": pg_start,
                        "page_end": pg_end,
                        "paragraph_ids": p_ids,
                        "file_hash": metadata.file_hash,
                    },
                )
                chunks.append(chk)
                chunk_order += 1

                # Calculate next s_idx with overlap
                if adv_idx >= len(sec_sentences):
                    break

                # Step forward with overlap
                overlap_accum = 0
                step_back_count = 0
                for back_i in range(adv_idx - 1, s_idx, -1):
                    back_len = len(sec_sentences[back_i][0])
                    if overlap_accum + back_len <= self.overlap_char_size:
                        overlap_accum += back_len
                        step_back_count += 1
                    else:
                        break

                s_idx = max(s_idx + 1, adv_idx - step_back_count)

        return chunks

    def _create_chunk_from_paragraphs(
        self,
        pars: List[ProcessedParagraph],
        sec: ProcessedSection,
        metadata: DocumentMetadata,
        strategy: ChunkStrategy,
        order: int,
    ) -> ProcessedChunk:
        """Helper to create a ProcessedChunk from a list of paragraphs."""
        strat_code = "A" if strategy == ChunkStrategy.STRATEGY_A_PARAGRAPH else "B"
        chunk_text = "\n\n".join(p.text for p in pars).strip()
        words = len(chunk_text.split())
        tokens_est = int(words * 1.3)

        p_start = pars[0].paragraph_order if pars else 1
        p_end = pars[-1].paragraph_order if pars else p_start
        pg_start = min((p.page_number for p in pars), default=sec.start_page)
        pg_end = max((p.page_number for p in pars), default=sec.end_page)
        p_ids = [p.paragraph_id for p in pars]

        return ProcessedChunk(
            chunk_id=f"chk_{metadata.canonical_id}_{strat_code}_{order:04d}",
            canonical_id=metadata.canonical_id,
            section_id=sec.section_id,
            section_title=sec.section_title,
            section_level=sec.section_level,
            page_start=pg_start,
            page_end=pg_end,
            paragraph_start_order=p_start,
            paragraph_end_order=p_end,
            paragraph_ids=p_ids,
            text=chunk_text,
            char_count=len(chunk_text),
            word_count=words,
            token_count_est=tokens_est,
            strategy=strategy,
            provenance={
                "canonical_id": metadata.canonical_id,
                "title": metadata.title,
                "doi": metadata.doi,
                "source": metadata.source,
                "section_id": sec.section_id,
                "section_title": sec.section_title,
                "section_level": sec.section_level,
                "page_start": pg_start,
                "page_end": pg_end,
                "paragraph_ids": p_ids,
                "file_hash": metadata.file_hash,
            },
        )
