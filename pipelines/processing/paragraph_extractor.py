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
    ) -> Tuple[List[ProcessedParagraph], List[ProcessedSection]]:
        """Extract paragraphs for each section and link paragraph IDs back to sections."""
        all_paragraphs: List[ProcessedParagraph] = []
        doc_paragraph_order = 1

        for sec in sections:
            sec_raw_text = sec.text.strip()
            if not sec_raw_text:
                continue

            # Split text on double line breaks or major structural breaks
            raw_blocks = [p.strip() for p in re.split(r"\n\s*\n+", sec_raw_text) if p.strip()]

            sec_paragraph_ids: List[str] = []

            for blk in raw_blocks:
                # Normalize internal linebreaks within the paragraph
                normalized_text = self._normalize_paragraph_text(blk)
                if not normalized_text:
                    continue

                p_id = f"p_{canonical_id}_{doc_paragraph_order:04d}"
                sentences = self.segmenter.segment_text(normalized_text, p_id)

                p_obj = ProcessedParagraph(
                    paragraph_id=p_id,
                    canonical_id=canonical_id,
                    section_id=sec.section_id,
                    section_title=sec.section_title,
                    page_number=sec.start_page,
                    paragraph_order=doc_paragraph_order,
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
