"""Unit Tests for Phase 4 Canonical Scientific Knowledge Base Schemas.

Validates schema constraints, field definitions, and serialization for
papers, entities, mentions, statements, relationships, quarantine, and manifests.
Schema Version: 0.5.0
"""

import pytest
from dataset.schemas.scientific_knowledge import (
    AttributionType,
    EvidenceSpan,
    ExtractionProvenance,
    ScientificEntityType,
    ScientificRelationType,
    ScientificStatementType,
    ValidationStatus,
)
from dataset.schemas.scientific_knowledge_base import (
    AliasMapping,
    AliasResolutionStatus,
    CanonicalEntityNode,
    CanonicalPaperNode,
    CanonicalRelationshipNode,
    CanonicalStatementNode,
    EntityMention,
    KnowledgeBaseManifest,
    QuarantineReason,
    QuarantinedRecord,
)


def test_canonical_paper_node_instantiation() -> None:
    paper = CanonicalPaperNode(
        paper_id="rg_doi_test12345678",
        title="Deep Learning in Ophthalmology",
        publication_year=2023,
        doi="10.1234/test.2023",
    )
    assert paper.paper_id == "rg_doi_test12345678"
    assert paper.schema_version == "0.5.0"
    assert paper.total_entities_count == 0
    d = paper.model_dump()
    assert d["title"] == "Deep Learning in Ophthalmology"


def test_entity_mention_and_canonical_entity_node() -> None:
    evidence = EvidenceSpan(
        text="convolutional neural networks",
        start_char=10,
        end_char=39,
        is_exact_match=True,
    )
    provenance = ExtractionProvenance(
        canonical_id="rg_doi_test12345678",
        document_id="doc_test12345678",
        chunk_id="chk_test12345678_A_0001",
    )
    mention = EntityMention(
        mention_id="ent_men_123456789abc",
        entity_id="kb_ent_method_33efe2f81a36",
        paper_id="rg_doi_test12345678",
        chunk_id="chk_test12345678_A_0001",
        category=ScientificEntityType.METHOD,
        surface_text="CNNs",
        normalized_name="cnns",
        evidence=evidence,
        provenance=provenance,
        attribution=AttributionType.AUTHOR_STATED,
        extraction_version="v0.4.1",
        validation_status=ValidationStatus.VALIDATED,
        upstream_record_id="ent_chk_test_01",
    )
    assert mention.category == ScientificEntityType.METHOD
    assert mention.mention_id == "ent_men_123456789abc"

    entity = CanonicalEntityNode(
        entity_id="kb_ent_method_33efe2f81a36",
        category=ScientificEntityType.METHOD,
        canonical_name="convolutional neural network",
        aliases=["CNN", "CNNs", "convolutional neural network"],
        mentions_count=1,
        paper_ids=["rg_doi_test12345678"],
        chunk_ids=["chk_test12345678_A_0001"],
        mention_ids=[mention.mention_id],
        alias_resolution_status=AliasResolutionStatus.CONFIRMED,
    )
    assert entity.entity_id == "kb_ent_method_33efe2f81a36"
    assert "CNNs" in entity.aliases


def test_canonical_statement_node() -> None:
    evidence = EvidenceSpan(
        text="The proposed model outperforms standard baselines by 12%.",
        start_char=50,
        end_char=108,
    )
    provenance = ExtractionProvenance(
        canonical_id="rg_doi_test12345678",
        document_id="doc_test12345678",
        chunk_id="chk_test12345678_A_0001",
    )
    stmt = CanonicalStatementNode(
        statement_id="kb_stmt_abcdef123456",
        category=ScientificStatementType.RESULT,
        surface_text="The proposed model outperforms standard baselines by 12%.",
        normalized_statement="the proposed model outperforms standard baselines by 12%",
        paper_id="rg_doi_test12345678",
        chunk_id="chk_test12345678_A_0001",
        evidence=evidence,
        provenance=provenance,
        attribution=AttributionType.AUTHOR_STATED,
        upstream_record_id="stmt_chk_test_01",
    )
    assert stmt.category == ScientificStatementType.RESULT
    assert stmt.statement_id.startswith("kb_stmt_")


def test_canonical_relationship_node() -> None:
    evidence = EvidenceSpan(text="CNNs address image distortion", start_char=0, end_char=29)
    provenance = ExtractionProvenance(
        canonical_id="rg_doi_test12345678",
        document_id="doc_test12345678",
        chunk_id="chk_test12345678_A_0001",
    )
    rel = CanonicalRelationshipNode(
        relationship_id="kb_rel_9876543210ab",
        relation_type=ScientificRelationType.ADDRESSES,
        source_id="kb_ent_method_33efe2f81a36",
        target_id="kb_ent_problem_8d4eecdbfd8f",
        paper_id="rg_doi_test12345678",
        chunk_id="chk_test12345678_A_0001",
        surface_text="CNNs address image distortion",
        evidence=evidence,
        provenance=provenance,
        upstream_relation_id="rel_chk_test_01",
    )
    assert rel.relation_type == ScientificRelationType.ADDRESSES
    assert rel.is_directed is True


def test_quarantined_record() -> None:
    quar = QuarantinedRecord(
        quarantine_id="kb_quar_112233445566",
        record_type="RELATIONSHIP",
        quarantine_reason=QuarantineReason.DANGLING_RELATION_ENDPOINT,
        error_message="Referential integrity failure: unresolvable endpoint",
        source_version="v0.4.0",
        raw_payload={"relation_id": "rel_bad_01"},
    )
    assert quar.quarantine_reason == QuarantineReason.DANGLING_RELATION_ENDPOINT
    assert quar.raw_payload["relation_id"] == "rel_bad_01"


def test_manifest_validation() -> None:
    manifest = KnowledgeBaseManifest(
        kb_version="v0.5.0",
        schema_version="0.5.0",
        total_papers_count=528,
        total_canonical_entities_count=68,
        total_entity_mentions_count=267,
        total_statements_count=22,
        total_relationships_count=9,
        referential_integrity_pass_rate=1.0,
        provenance_completeness_rate=1.0,
    )
    assert manifest.kb_version == "v0.5.0"
    assert manifest.referential_integrity_pass_rate == 1.0
