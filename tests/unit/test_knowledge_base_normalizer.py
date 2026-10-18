"""Unit Tests for Normalization, Stable ID Generation, and Alias Resolution.

Verifies deterministic stable identifiers, Unicode NFKC normalization,
confirmed alias mapping, candidate alias retention, and distinct concept boundaries.
Schema Version: 0.5.0
"""

import pytest
from dataset.schemas.scientific_knowledge import ScientificEntityType
from dataset.schemas.scientific_knowledge_base import AliasResolutionStatus
from pipelines.knowledge_base.normalizer import (
    generate_canonical_entity_id,
    generate_canonical_relationship_id,
    generate_canonical_statement_id,
    generate_mention_id,
    generate_quarantine_id,
    normalize_text,
    resolve_canonical_entity,
)


def test_normalize_text() -> None:
    assert normalize_text("  Convolutional  Neural  Network  ") == "convolutional neural network"
    assert normalize_text('"Deep Learning,"') == "deep learning"
    assert normalize_text("Machine-Learning") == "machine-learning"
    assert normalize_text("(NLP)") == "nlp"
    assert normalize_text("") == ""


def test_resolve_confirmed_aliases() -> None:
    # CNN -> convolutional neural network
    canon, aliases, status = resolve_canonical_entity("CNN", ScientificEntityType.METHOD)
    assert canon == "convolutional neural network"
    assert status == AliasResolutionStatus.CONFIRMED

    # NLP -> natural language processing
    canon, aliases, status = resolve_canonical_entity("nlp", ScientificEntityType.METHOD)
    assert canon == "natural language processing"
    assert status == AliasResolutionStatus.CONFIRMED

    # VOSviewer -> vosviewer in METHOD
    canon, aliases, status = resolve_canonical_entity("VOSviewer", ScientificEntityType.METHOD)
    assert canon == "vosviewer"
    assert status == AliasResolutionStatus.CONFIRMED


def test_resolve_candidate_aliases() -> None:
    # Candidate aliases should NOT prematurely merge to canonical label
    canon, aliases, status = resolve_canonical_entity("generative ai", ScientificEntityType.METHOD)
    assert status == AliasResolutionStatus.CANDIDATE
    assert canon == "generative ai"  # Retains clean surface form

    canon_km, aliases_km, status_km = resolve_canonical_entity("k-means clustering", ScientificEntityType.METHOD)
    assert status_km == AliasResolutionStatus.CANDIDATE
    assert canon_km == "k-means clustering"


def test_separate_concepts_boundary() -> None:
    from pipelines.knowledge_base.alias_registry import SEPARATE_CONCEPTS
    # Verify that distinct concepts are registered in SEPARATE_CONCEPTS
    assert ("METHOD", "machine learning", "deep learning") in SEPARATE_CONCEPTS
    assert ("METRIC", "precision", "recall") in SEPARATE_CONCEPTS



def test_stable_id_reproducibility() -> None:
    id1 = generate_canonical_entity_id(ScientificEntityType.METHOD, "convolutional neural network")
    id2 = generate_canonical_entity_id(ScientificEntityType.METHOD, "convolutional neural network")
    id3 = generate_canonical_entity_id(ScientificEntityType.METHOD, "Convolutional Neural Network  ")
    assert id1 == id2
    assert id1 == id3
    assert id1.startswith("kb_ent_method_")

    men_id1 = generate_mention_id("chk_01", ScientificEntityType.METHOD, 10, 25)
    men_id2 = generate_mention_id("chk_01", ScientificEntityType.METHOD, 10, 25)
    assert men_id1 == men_id2
    assert men_id1.startswith("ent_men_")

    stmt_id1 = generate_canonical_statement_id("rg_p1", "chk_01", "CLAIM", "Our model achieves 99% accuracy")
    stmt_id2 = generate_canonical_statement_id("rg_p1", "chk_01", "CLAIM", "our model achieves 99% accuracy  ")
    assert stmt_id1 == stmt_id2
    assert stmt_id1.startswith("kb_stmt_")

    rel_id1 = generate_canonical_relationship_id("kb_ent_1", "ADDRESSES", "kb_ent_2", "chk_01")
    rel_id2 = generate_canonical_relationship_id("kb_ent_1", "addresses", "kb_ent_2", "chk_01")
    assert rel_id1 == rel_id2
    assert rel_id1.startswith("kb_rel_")

    q_id1 = generate_quarantine_id("bad_rel_1", "DANGLING_RELATION_ENDPOINT")
    q_id2 = generate_quarantine_id("bad_rel_1", "DANGLING_RELATION_ENDPOINT")
    assert q_id1 == q_id2
    assert q_id1.startswith("kb_quar_")
