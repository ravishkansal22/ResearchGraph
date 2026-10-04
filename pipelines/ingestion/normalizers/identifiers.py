"""Identifier Normalization Utilities.

Standardizes DOIs, arXiv IDs, and source-specific identifiers.
"""

from __future__ import annotations

import re
from typing import Optional


# Regular expressions for DOI extraction and validation
DOI_PREFIX_REGEX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", re.IGNORECASE)
DOI_VALID_REGEX = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$", re.IGNORECASE)

# Regular expressions for arXiv identifier normalization
ARXIV_PREFIX_REGEX = re.compile(r"^(?:https?://arxiv\.org/(?:abs|pdf)/|arxiv:)", re.IGNORECASE)
ARXIV_MODERN_REGEX = re.compile(r"^(?:arXiv:)?(\d{4}\.\d{4,5})(?:v\d+)?$", re.IGNORECASE)
ARXIV_LEGACY_REGEX = re.compile(r"^(?:arXiv:)?([a-zA-Z\-]+(?:\.[a-zA-Z\-]+)?/\d{7})(?:v\d+)?$", re.IGNORECASE)


def normalize_doi(raw_doi: Optional[str]) -> Optional[str]:
    """Normalize a Digital Object Identifier (DOI).

    Strips URLs (e.g. https://doi.org/), 'doi:' prefixes, leading/trailing whitespace,
    and returns a clean, lowercase DOI string.

    Examples:
        'https://doi.org/10.1145/3308558.3313508' -> '10.1145/3308558.3313508'
        'doi:10.48550/arXiv.2401.00001' -> '10.48550/arxiv.2401.00001'
    """
    if not raw_doi or not isinstance(raw_doi, str):
        return None

    cleaned = raw_doi.strip()
    cleaned = DOI_PREFIX_REGEX.sub("", cleaned).strip()
    cleaned = cleaned.lower()

    # Remove any trailing periods or slash artifacts
    cleaned = cleaned.rstrip(".")

    if DOI_VALID_REGEX.match(cleaned):
        return cleaned

    # Secondary check if string starts with 10.xxxx
    if cleaned.startswith("10.") and "/" in cleaned:
        return cleaned

    return None


def normalize_arxiv_id(raw_id: Optional[str]) -> Optional[str]:
    """Normalize an arXiv identifier.

    Strips URLs (e.g. https://arxiv.org/abs/2401.12345v2), 'arxiv:' prefixes,
    and returns the standardized base arXiv ID (without version for canonical matching).

    Examples:
        'https://arxiv.org/abs/2301.07094v1' -> '2301.07094'
        'arXiv:cs/0601001v2' -> 'cs/0601001'
    """
    if not raw_id or not isinstance(raw_id, str):
        return None

    cleaned = raw_id.strip()
    cleaned = ARXIV_PREFIX_REGEX.sub("", cleaned).strip()

    # Match modern arXiv ID format: YYMM.NNNNN
    modern_match = ARXIV_MODERN_REGEX.match(cleaned)
    if modern_match:
        return modern_match.group(1).lower()

    # Match legacy format: arch-ive/YYMMNNN
    legacy_match = ARXIV_LEGACY_REGEX.match(cleaned)
    if legacy_match:
        return legacy_match.group(1).lower()

    return None


def normalize_orcid(raw_orcid: Optional[str]) -> Optional[str]:
    """Normalize an ORCID identifier to format '0000-0000-0000-0000'."""
    if not raw_orcid or not isinstance(raw_orcid, str):
        return None

    cleaned = re.sub(r"^(?:https?://orcid\.org/)", "", raw_orcid.strip())
    match = re.match(r"^(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$", cleaned, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None
