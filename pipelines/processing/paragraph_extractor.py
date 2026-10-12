"""Paragraph Extraction and Lineage Linker.

Divides section text into coherent paragraphs, joins soft-wrapped lines,
performs sentence segmentation, and establishes complete provenance links.
"""

from __future__ import annotations

import logging
import re
from typing import List, Tuple

from dataset.schemas.document_processing import ProcessedParagraph, ProcessedSection
from pipelines.processing.sentence_segmenter import ScientificSentenceSegmenter

logger = logging.getLogger(__name__)


class ParagraphExtractor:
    """Extracts and normalizes paragraphs from structured sections."""

    def __init__(self, sentence_segmenter: ScientificSentenceSegmenter | None = None):
        self.segmenter = sentence_segmenter or ScientificSentenceSegmenter()

    def extract_paragraphs(
        self,
        sections: List[ProcessedSection],
        canonical_id: str,
        document_id: Optional[str] = None,
        file_hash: Optional[str] = None,
        processing_version: str = "v0.2.0",
    ) -> Tuple[List[ProcessedParagraph], List[ProcessedSection]]:
        """Extract paragraphs for each section with true page provenance and lineage linking."""
        all_paragraphs: List[ProcessedParagraph] = []
        doc_paragraph_order = 1
        doc_id = document_id or f"doc_{canonical_id}"

        for sec in sections:
            block_entries = getattr(sec, "_block_entries", None)
            raw_entries: List[Tuple[int, str]] = []

            if block_entries:
                for pno, b_txt in block_entries:
                    for sub_p in re.split(r"\n\s*\n+", b_txt):
                        sub_p = sub_p.strip()
                        if sub_p:
                            raw_entries.append((pno, sub_p))
            else:
                sec_raw_text = sec.text.strip()
                if sec_raw_text:
                    for sub_p in re.split(r"\n\s*\n+", sec_raw_text):
                        sub_p = sub_p.strip()
                        if sub_p:
                            raw_entries.append((sec.start_page, sub_p))

            if not raw_entries:
                continue

            # Merge cross-page paragraphs where a sentence spans page boundaries
            merged_entries: List[Tuple[int, int, str]] = []
            idx = 0
            while idx < len(raw_entries):
                p_page, p_text = raw_entries[idx]
                end_page = p_page

                while idx + 1 < len(raw_entries):
                    next_page, next_text = raw_entries[idx + 1]
                    if next_page == end_page + 1:
                        ends_with_punc = bool(re.search(r'[.?!]["\']?\s*$', p_text))
                        starts_lower = bool(re.match(r'^[a-z]', next_text))
                        if not ends_with_punc and starts_lower:
                            if p_text.endswith("-"):
                                p_text = p_text[:-1] + next_text
                            else:
                                p_text = p_text + " " + next_text
                            end_page = next_page
                            idx += 1
                            continue
                    break

                merged_entries.append((p_page, end_page, p_text))
                idx += 1

            sec_paragraph_ids: List[str] = []

            for p_start_pg, p_end_pg, blk in merged_entries:
                normalized_text = self._normalize_paragraph_text(blk)
                if not normalized_text:
                    continue

                p_id = f"p_{canonical_id}_{doc_paragraph_order:04d}"
                sentences = self.segmenter.segment_text(normalized_text, p_id)

                p_obj = ProcessedParagraph(
                    paragraph_id=p_id,
                    canonical_id=canonical_id,
                    document_id=doc_id,
                    file_hash=file_hash,
                    section_id=sec.section_id,
                    section_title=sec.section_title,
                    page_number=p_start_pg,
                    page_end=p_end_pg,
                    paragraph_order=doc_paragraph_order,
                    processing_version=processing_version,
                    text=normalized_text,
                    char_count=len(normalized_text),
                    word_count=len(normalized_text.split()),
                    sentence_count=len(sentences),
                    sentences=sentences,
                )

                all_paragraphs.append(p_obj)
                sec_paragraph_ids.append(p_id)
                doc_paragraph_order += 1

            # Update section metadata with paragraph provenance
            sec.paragraph_ids = sec_paragraph_ids
            sec.paragraph_count = len(sec_paragraph_ids)

        return all_paragraphs, sections

    def _normalize_paragraph_text(self, text: str) -> str:
        """Join soft line breaks, fix hyphens across lines, and clean whitespace."""
        # Fix hyphenation at line breaks (e.g. "com-\nputer" -> "computer")
        text = re.sub(r'(\b[A-Za-z]+)-\n\s*([a-z]+)\b', r'\1\2', text)
        # Replace remaining newlines with spaces
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        joined = " ".join(lines)
        # Collapse multiple spaces
        joined = re.sub(r"\s+", " ", joined).strip()
        return joined
