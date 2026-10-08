"""Scientific Sentence Segmentation Engine.

Provides robust, lightweight sentence boundary disambiguation designed specifically
for scholarly literature, handling scientific abbreviations, floating-point decimals,
citations, initials, and equation tokens.
"""

from __future__ import annotations

import logging
import re
from typing import List

from dataset.schemas.document_processing import ProcessedSentence

logger = logging.getLogger(__name__)

# Known scholarly and general abbreviations that end with a period but DO NOT end sentences
ABBREVIATIONS = {
    "al.", "et al.", "e.g.", "i.e.", "cf.", "ca.", "vs.", "v.", "approx.",
    "fig.", "figs.", "figure.", "figures.", "tab.", "tabs.", "table.", "tables.",
    "eq.", "eqs.", "equation.", "equations.", "sec.", "secs.", "section.",
    "ref.", "refs.", "reference.", "references.",
    "vol.", "vols.", "no.", "nos.", "pp.", "p.", "ed.", "eds.",
    "univ.", "dept.", "proc.", "conf.", "trans.", "assoc.", "soc.",
    "dr.", "prof.", "mr.", "mrs.", "ms.", "jr.", "sr.", "st.",
    "inc.", "ltd.", "corp.", "co.", "stat.", "min.", "max.", "avg.",
    "jan.", "feb.", "mar.", "apr.", "jun.", "jul.", "aug.", "sep.", "sept.", "oct.", "nov.", "dec.",
}

# Regex to find potential sentence boundaries (period, question mark, exclamation point followed by space/newline and capital letter)
RE_SENTENCE_BOUNDARY = re.compile(r'([.?!])\s+(?=[A-Z0-9"\'\(\[\{\b])')
# Regex for floating point numbers / decimals
RE_DECIMAL = re.compile(r'\b\d+\.\d+\b')
# Regex for author initials (e.g. "A. B. Smith")
RE_INITIAL = re.compile(r'\b[A-Z]\.$')


class ScientificSentenceSegmenter:
    """Lightweight scientific sentence segmenter."""

    def __init__(self, min_sentence_chars: int = 6):
        self.min_sentence_chars = min_sentence_chars

    def segment_text(self, text: str, paragraph_id: str) -> List[ProcessedSentence]:
        """Segment paragraph text into ordered ProcessedSentence instances."""
        cleaned = text.strip()
        if not cleaned:
            return []

        # Fast path for single short line
        if len(cleaned) < 50 and not any(punc in cleaned for punc in [".", "?", "!"]):
            return [
                ProcessedSentence(
                    sentence_id=f"s_{paragraph_id}_01",
                    paragraph_id=paragraph_id,
                    sentence_order=1,
                    text=cleaned,
                    char_count=len(cleaned),
                    word_count=len(cleaned.split()),
                )
            ]

        # Use placeholder replacement for protected periods
        protected_text = self._protect_scientific_patterns(cleaned)

        # Split on sentence boundaries
        raw_splits = RE_SENTENCE_BOUNDARY.split(protected_text)

        # Recombine punctuation with sentences
        reconstructed: List[str] = []
        i = 0
        while i < len(raw_splits):
            part = raw_splits[i]
            if i + 1 < len(raw_splits) and raw_splits[i + 1] in [".", "?", "!"]:
                punct = raw_splits[i + 1]
                full_sent = (part + punct).strip()
                i += 2
            else:
                full_sent = part.strip()
                i += 1

            # Restore protected patterns
            restored = self._unprotect_scientific_patterns(full_sent)
            if len(restored) >= self.min_sentence_chars:
                reconstructed.append(restored)

        # Build ProcessedSentence models
        sentences: List[ProcessedSentence] = []
        for s_idx, s_text in enumerate(reconstructed, 1):
            sentences.append(
                ProcessedSentence(
                    sentence_id=f"s_{paragraph_id}_{s_idx:02d}",
                    paragraph_id=paragraph_id,
                    sentence_order=s_idx,
                    text=s_text,
                    char_count=len(s_text),
                    word_count=len(s_text.split()),
                )
            )

        if not sentences and cleaned:
            sentences.append(
                ProcessedSentence(
                    sentence_id=f"s_{paragraph_id}_01",
                    paragraph_id=paragraph_id,
                    sentence_order=1,
                    text=cleaned,
                    char_count=len(cleaned),
                    word_count=len(cleaned.split()),
                )
            )

        return sentences

    def _protect_scientific_patterns(self, text: str) -> str:
        """Replace periods in abbreviations, decimals, and initials with a placeholder symbol."""
        protected = text

        # Protect decimals (e.g. 3.14 -> 3<DECIMAL_DOT>14)
        def replace_decimal(m):
            return m.group(0).replace(".", "___DEC_DOT___")
        protected = RE_DECIMAL.sub(replace_decimal, protected)

        # Protect abbreviations (case-insensitive)
        for abbr in sorted(ABBREVIATIONS, key=lambda x: -len(x)):
            pattern = re.compile(r'\b' + re.escape(abbr), re.IGNORECASE)
            def replace_abbr(m):
                return m.group(0).replace(".", "___ABBR_DOT___")
            protected = pattern.sub(replace_abbr, protected)

        # Protect single capital initials (e.g. "J. ")
        protected = re.sub(r'\b([A-Z])\.\s+', r'\1___INIT_DOT___ ', protected)

        return protected

    def _unprotect_scientific_patterns(self, text: str) -> str:
        """Restore protected placeholder markers back to standard periods."""
        return (
            text.replace("___DEC_DOT___", ".")
            .replace("___ABBR_DOT___", ".")
            .replace("___INIT_DOT___", ".")
        )
