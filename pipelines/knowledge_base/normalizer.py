"""Deterministic Entity Normalization, Alias Resolution, and Stable ID Generation.

Implements reproducible normalization rules and cryptographic stable ID generation
for the ResearchGraph Scientific Knowledge Base (v0.5.0).
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import List, Tuple

from dataset.schemas.scientific_knowledge import ScientificEntityType
from dataset.schemas.scientific_knowledge_base import AliasResolutionStatus
from pipelines.knowledge_base.alias_registry import (
    CANDIDATE_ALIASES,
    CONFIRMED_ALIASES,
    SEPARATE_CONCEPTS,
)

RE_EXTRA_WHITESPACE = re.compile(r"\s+")
RE_STRIP_PUNCTUATION = re.compile(r"^[\s\"'`([{<.,;:-]+|[\s\"'`)\],;:>-]+$")


def normalize_text(text: str) -> str:
    """Conservatively normalize text string (NFKC, whitespace collapse, lowercase, outer punctuation strip)."""
    if not text:
        return ""
    # Unicode NFKC normalization
    s = unicodedata.normalize("NFKC", str(text))
    # Collapse internal whitespace
    s = RE_EXTRA_WHITESPACE.sub(" ", s).strip()
    # Strip leading/trailing punctuation artifacts
    s = RE_STRIP_PUNCTUATION.sub("", s).strip()
    return s.lower()


def resolve_canonical_entity(
    surface_text: str,
    category: ScientificEntityType | str,
) -> Tuple[str, List[str], AliasResolutionStatus]:
    """Resolve surface text to canonical concept name, observed aliases, and resolution status.

    Returns:
        (canonical_name, [original_surface], resolution_status)
    """
    cat_str = (category.value if hasattr(category, "value") else str(category)).strip().upper()
    cleaned = normalize_text(surface_text)
    lookup_key = (cat_str, cleaned)

    # 1. Check Confirmed Aliases
    if lookup_key in CONFIRMED_ALIASES:
        canonical = CONFIRMED_ALIASES[lookup_key]
        return canonical, [surface_text], AliasResolutionStatus.CONFIRMED

    # 2. Check Candidate Aliases
    if lookup_key in CANDIDATE_ALIASES:
        # We record as candidate, but retain specific cleaned surface form as primary canonical name
        # to prevent unverified automatic merges
        return cleaned, [surface_text], AliasResolutionStatus.CANDIDATE

    # 3. Default: cleaned surface form is canonical name
    return cleaned, [surface_text], AliasResolutionStatus.CONFIRMED


def generate_canonical_entity_id(category: ScientificEntityType | str, canonical_name: str) -> str:
    """Generate deterministic, stable identifier for a canonical entity node."""
    cat = (category.value if hasattr(category, "value") else str(category)).strip().lower()
    norm = normalize_text(canonical_name)
    digest = hashlib.sha256(f"{cat}:{norm}".encode("utf-8")).hexdigest()[:12]
    return f"kb_ent_{cat}_{digest}"


def generate_mention_id(chunk_id: str, category: ScientificEntityType | str, start_char: int, end_char: int) -> str:
    """Generate deterministic identifier for an entity mention grounded in a chunk."""
    cat = (category.value if hasattr(category, "value") else str(category)).strip().lower()
    digest = hashlib.sha256(f"{chunk_id}:{cat}:{start_char}:{end_char}".encode("utf-8")).hexdigest()[:12]
    return f"ent_men_{digest}"


def generate_canonical_statement_id(
    paper_id: str,
    chunk_id: str,
    category: str,
    statement_text: str,
) -> str:
    """Generate deterministic identifier for a canonical statement node."""
    norm = normalize_text(statement_text)
    cat = category.strip().lower()
    digest = hashlib.sha256(f"{paper_id}:{chunk_id}:{cat}:{norm}".encode("utf-8")).hexdigest()[:12]
    return f"kb_stmt_{digest}"


def generate_canonical_relationship_id(
    source_id: str,
    relation_type: str,
    target_id: str,
    chunk_id: str,
) -> str:
    """Generate deterministic identifier for a canonical relationship node."""
    rel = relation_type.strip().lower()
    digest = hashlib.sha256(f"{source_id}:{rel}:{target_id}:{chunk_id}".encode("utf-8")).hexdigest()[:12]
    return f"kb_rel_{digest}"


def generate_quarantine_id(upstream_id: str, reason: str) -> str:
    """Generate deterministic identifier for a quarantined record."""
    digest = hashlib.sha256(f"{upstream_id}:{reason}".encode("utf-8")).hexdigest()[:12]
    return f"kb_quar_{digest}"
