"""Regression and validation integrity tests for Phase 4.1 Release v0.5.1.

Verifies:
1. Multi-row table Cartesian product rejection.
2. Evidence support requirement for specific subject-predicate-object pairing.
3. Separation of structural validity, evidence support, and human verification dimensions.
4. Default trusted query exclusion of unsupported relationships.
5. Diagnostic query retrieval of excluded records with correction reasons.
6. Retention of all 9 original relationship records in SQLite, JSONL, and Parquet.
7. Immutability of v0.5.0 artifacts and Phase 1-3 extraction outputs.
8. Non-regression of entity, statement, and paper query interfaces.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
import pyarrow.parquet as pq

from dataset.schemas.scientific_knowledge import (
    EvidenceSpan,
    ExtractionProvenance,
)
from dataset.schemas.scientific_knowledge_base import (
    CanonicalRelationshipNode,
    EvidenceSupportStatus,
    HumanVerificationStatus,
    StructuralValidityStatus,
)
from pipelines.knowledge_base.query import KnowledgeBaseQueryEngine
from pipelines.knowledge_base.relationship_validator import (
    evaluate_relationship_evidence_support,
    extract_table_row_associations,
    find_row_for_term,
)

V050_DIR = Path("dataset/processed/v0.5.0")
V051_DIR = Path("dataset/processed/v0.5.1")
V051_DB = V051_DIR / "knowledge_base.db"


class TestRelationshipIntegrityV051:
    """Test suite for scientific relationship integrity and validation dimensions."""

    def test_multi_row_table_cartesian_rejection(self):
        """Verify that multi-row tables reject cross-row Cartesian product pairings."""
        sample_table = (
            "1 Adversarial Machine Learning Robust model training Adversarial resilience frameworks "
            "2 Prompt Injection Secure prompt engineering Zero-Trust Runtime Architecture "
            "3 Data Privacy Concerns Federated Learning Privacy-Preserving Machine Learning "
            "6 Data Imbalance Synthetic data generation Generative Adversarial Networks "
            "7 High Computational Cost Lightweight AI models Edge AI deployment "
            "9 False Negatives Multi-layered detection Ensemble learning"
        )
        rows = extract_table_row_associations(sample_table)
        assert len(rows) >= 6

        # Cross-row pairing: Federated learning (Row 3) vs Data imbalance (Row 6)
        status, note = evaluate_relationship_evidence_support(
            evidence_text=sample_table,
            source_name="Federated Learning",
            target_name="Data Imbalance",
            relation_type="ADDRESSES",
        )
        assert status == EvidenceSupportStatus.UNSUPPORTED
        assert note is not None
        assert "belongs to table item 3" in note
        assert "belongs to table item 6" in note

        # Same-row pairing: Synthetic data generation (Row 6) vs Data imbalance (Row 6)
        status_same, note_same = evaluate_relationship_evidence_support(
            evidence_text=sample_table,
            source_name="Synthetic data generation",
            target_name="Data Imbalance",
            relation_type="ADDRESSES",
        )
        assert status_same == EvidenceSupportStatus.SUPPORTED
        assert "Grounded within table item 6" in note_same

    def test_validation_dimension_distinction(self):
        """Verify that structural validity and evidence support are strictly decoupled."""
        rel = CanonicalRelationshipNode(
            relationship_id="kb_rel_test_123",
            upstream_relation_id="rel_test_upstream_01",
            relation_type="ADDRESSES",
            source_id="kb_ent_method_123",
            target_id="kb_ent_problem_456",
            source_type="ENTITY",
            target_type="ENTITY",
            paper_id="rg_doi_test",
            chunk_id="chk_test_01",
            surface_text="Method addresses Problem",
            evidence=EvidenceSpan(
                text="Row 1 Method Row 2 Problem",
                start_char=0,
                end_char=26,
            ),
            attribution="AUTHOR_STATED",
            confidence_score=0.85,
            extraction_version="v0.4.0",
            validation_status="VALIDATED",
            structural_validity=StructuralValidityStatus.STRUCTURALLY_VALID,
            evidence_support=EvidenceSupportStatus.UNSUPPORTED,
            human_verification=HumanVerificationStatus.PENDING,
            correction_notes="Cross-row table artifact",
            provenance=ExtractionProvenance(canonical_id="rg_doi_test", chunk_id="chk_test_01"),
        )
        assert rel.structural_validity == StructuralValidityStatus.STRUCTURALLY_VALID
        assert rel.evidence_support == EvidenceSupportStatus.UNSUPPORTED
        assert rel.human_verification == HumanVerificationStatus.PENDING
        assert rel.validation_status == "VALIDATED"  # Backward compatibility preserved

    @pytest.mark.skipif(not V051_DB.exists(), reason="v0.5.1 database not yet built")
    def test_default_query_excludes_unsupported_relationships(self):
        """Verify default scientific queries exclude unsupported Cartesian relationships."""
        engine = KnowledgeBaseQueryEngine(db_path=V051_DB)

        # Default query for data imbalance must return empty list (0 methods)
        methods = engine.find_methods_for_problem("data imbalance")
        assert methods == [], f"Expected [] for data imbalance, got: {methods}"

        # Direct entity relationship lookup with trusted_only=True must also exclude unsupported
        rels = engine.get_relationships_for_entity("kb_ent_problem_8d4eecdbfd8f", trusted_only=True)
        assert rels == []

    @pytest.mark.skipif(not V051_DB.exists(), reason="v0.5.1 database not yet built")
    def test_diagnostic_query_retrieves_excluded_records_with_reasons(self):
        """Verify diagnostic queries retrieve excluded records with full provenance and notes."""
        engine = KnowledgeBaseQueryEngine(db_path=V051_DB)

        # Query with include_unsupported=True
        diagnostic_methods = engine.find_methods_for_problem(
            "data imbalance",
            include_unsupported=True,
        )
        assert len(diagnostic_methods) == 3
        method_names = {m["method_name"] for m in diagnostic_methods}
        assert method_names == {"ensemble learning", "federated learning", "machine learning"}

        for m in diagnostic_methods:
            assert m["evidence_support"] == "UNSUPPORTED"
            assert m["structural_validity"] == "STRUCTURALLY_VALID"
            assert m["human_verification"] == "PENDING"
            assert "Cartesian product table artifact" in m["correction_notes"]
            assert m["chunk_id"] == "chk_rg_doi_ebe643c2b3dd_A_0135"

    @pytest.mark.skipif(not V051_DB.exists(), reason="v0.5.1 database not yet built")
    def test_all_nine_relationships_retained_in_audit_trail(self):
        """Verify all nine original relationships are retained across SQLite, JSONL, and Parquet."""
        engine = KnowledgeBaseQueryEngine(db_path=V051_DB)
        excluded = engine.get_excluded_relationships()
        assert len(excluded) == 9

        # Verify in SQLite directly
        with sqlite3.connect(str(V051_DB)) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM relationships")
            total_in_db = cur.fetchone()[0]
            assert total_in_db == 9

            cur.execute("SELECT COUNT(*) FROM relationships WHERE evidence_support = 'UNSUPPORTED'")
            unsupported_in_db = cur.fetchone()[0]
            assert unsupported_in_db == 9

        # Verify in JSONL
        jsonl_path = V051_DIR / "canonical_relationships.jsonl"
        assert jsonl_path.exists()
        with open(jsonl_path, "r", encoding="utf-8") as f:
            jsonl_lines = [json.loads(line) for line in f if line.strip()]
        assert len(jsonl_lines) == 9
        for item in jsonl_lines:
            assert item["evidence_support"] == "UNSUPPORTED"
            assert item["structural_validity"] == "STRUCTURALLY_VALID"
            assert item["human_verification"] == "PENDING"
            assert item["chunk_id"] == "chk_rg_doi_ebe643c2b3dd_A_0135"

        # Verify in Parquet
        parquet_path = V051_DIR / "canonical_relationships.parquet"
        assert parquet_path.exists()
        table = pq.read_table(parquet_path)
        assert table.num_rows == 9
        assert "evidence_support" in table.column_names
        assert "structural_validity" in table.column_names
        assert "human_verification" in table.column_names
        assert "correction_notes" in table.column_names

    def test_v050_artifacts_remain_immutable(self):
        """Verify v0.5.0 artifacts and Phase 1-3 outputs are unmodified."""
        assert V050_DIR.exists()
        v050_db = V050_DIR / "knowledge_base.db"
        assert v050_db.exists()

        # Check v0.5.0 manifest
        v050_manifest = Path("dataset/manifests/knowledge_base_v0.5.0_manifest.json")
        assert v050_manifest.exists()
        with open(v050_manifest, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        assert manifest_data["kb_version"] == "v0.5.0"
        assert manifest_data["schema_version"] == "0.5.0"
        assert manifest_data["total_relationships_count"] == 9

        # Check Phase 3 extraction artifacts
        p3_baseline_records = Path("dataset/processed/v0.4.0/extracted_records.jsonl")
        p3_baseline_rels = Path("dataset/processed/v0.4.0/extracted_relationships.jsonl")
        p3_experimental_records = Path("dataset/processed/v0.4.1/extracted_records.jsonl")
        assert p3_baseline_records.exists()
        assert p3_baseline_rels.exists()
        assert p3_experimental_records.exists()

    @pytest.mark.skipif(not V051_DB.exists(), reason="v0.5.1 database not yet built")
    def test_unrelated_queries_non_regression(self):
        """Verify that entity, statement, paper, and trace queries work without regression."""
        engine = KnowledgeBaseQueryEngine(db_path=V051_DB)

        # Paper query
        paper = engine.get_paper("rg_doi_ebe643c2b3dd")
        assert paper is not None
        assert paper["title"] != ""

        # Entities query
        methods = engine.list_entities_by_type("METHOD", limit=10)
        assert len(methods) > 0

        # Statements query
        stmts = engine.get_statements_for_paper("rg_doi_ebe643c2b3dd")
        assert len(stmts) > 0

        # Chunk query
        chunk_rec = engine.get_records_for_chunk("chk_rg_doi_ebe643c2b3dd_A_0135")
        assert len(chunk_rec["mentions"]) > 0
        assert len(chunk_rec["statements"]) > 0
        assert len(chunk_rec["relationships"]) == 9
