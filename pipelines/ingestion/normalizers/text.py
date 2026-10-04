"""Text and Bibliographic Field Normalization Utilities.

Provides deterministic cleaning, title fingerprinting, OpenAlex inverted index
reconstruction, and author parsing.
"""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple


# Regex patterns for text cleanup
TAG_RE = re.compile(r"<[^>]+>")
PUNCT_RE = re.compile(r"[^\w\s]")
WHITESPACE_RE = re.compile(r"\s+")
PUNCT_SPACE_RE = re.compile(r"\s+([.,;:!?])")


def clean_text(text: Optional[str]) -> Optional[str]:
    """Clean plain text by decoding HTML entities, removing tags, and collapsing whitespace."""
    if not text or not isinstance(text, str):
        return None
    cleaned = html.unescape(text)
    # Remove HTML/XML tags
    cleaned = TAG_RE.sub("", cleaned)
    # Clean up punctuation spacing artifacts
    cleaned = PUNCT_SPACE_RE.sub(r"\1", cleaned)
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned if cleaned else None


def normalize_title_for_matching(title: Optional[str]) -> str:
    """Normalize a title string for deterministic deduplication and fingerprinting.

    Steps:
    1. Unicode NFKD decomposition (strips accents/diacritics).
    2. Lowercasing.
    3. Removal of punctuation and special symbols.
    4. Collapse whitespace.

    Example:
        'Attention Is All You Need!' -> 'attention is all you need'
        'A Survey on Self-Supervised Learning in 3D Point Clouds.' -> 'a survey on self supervised learning in 3d point clouds'
    """
    if not title or not isinstance(title, str):
        return ""

    # Decode HTML entities if any
    text = html.unescape(title)
    # Decompose unicode characters
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    # Replace hyphens with spaces to keep compound words separated
    text = text.replace("-", " ")
    # Strip punctuation
    text = PUNCT_RE.sub("", text)
    # Collapse multiple whitespaces
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text


def reconstruct_openalex_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> Optional[str]:
    """Reconstruct human-readable abstract text from OpenAlex's abstract_inverted_index.

    OpenAlex delivers abstracts as { 'word': [pos0, pos1], ... }.
    This function reassembles the tokens into their original sequential order.
    """
    if not inverted_index or not isinstance(inverted_index, dict):
        return None

    word_positions: List[Tuple[int, str]] = []
    for word, positions in inverted_index.items():
        if isinstance(positions, list):
            for pos in positions:
                if isinstance(pos, int):
                    word_positions.append((pos, word))

    if not word_positions:
        return None

    # Sort tokens by their 0-indexed position
    word_positions.sort(key=lambda x: x[0])
    ordered_tokens = [word for _, word in word_positions]
    raw_abstract = " ".join(ordered_tokens)
    return clean_text(raw_abstract)


def parse_author_name(raw_name: Optional[str]) -> Tuple[str, Optional[str], Optional[str]]:
    """Parse author name into (full_name, first_name, last_name).

    Handles 'First Last' and 'Last, First' formats.
    """
    if not raw_name or not isinstance(raw_name, str):
        return ("", None, None)

    cleaned = clean_text(raw_name) or ""
    if not cleaned:
        return ("", None, None)

    if "," in cleaned:
        parts = [p.strip() for p in cleaned.split(",", 1)]
        last_name = parts[0]
        first_name = parts[1] if len(parts) > 1 and parts[1] else None
        full_name = f"{first_name} {last_name}".strip() if first_name else last_name
        return (full_name, first_name, last_name)

    parts = cleaned.split()
    if len(parts) == 1:
        return (cleaned, None, parts[0])
    elif len(parts) >= 2:
        first_name = " ".join(parts[:-1])
        last_name = parts[-1]
        return (cleaned, first_name, last_name)

    return (cleaned, None, None)
