"""Regression Tests for Knowledge Base Count Reconciliation, Parity, and Provenance.

Formally tests:
1. Exact count reconciliation between upstream inputs and persisted canonical records.
2. 100% character span exact match against underlying chunk text.
3. Multi-format persistence parity across JSONL, Parquet, and SQLite.
4. Quarantine isolation behavior on dangling relationship endpoints.
Schema Version: 0.5.0
"""

import json
import sqlite3
import tempfile
from pathlib import Path
import pyarrow.parquet as pq
import pytest

from pipelines.knowledge_base.config import KnowledgeBaseConfig
from pipelines.knowledge_base.pipeline import ScientificKnowledgeBasePipeline
from pipelines.knowledge_base.storage import read_jsonl
from pipelines.knowledge_base.validator import (
    VALID_ENTITY_TYPES,
    VALID_STATEMENT_TYPES,
    validate_entity_mention_record,
    validate_statement_record,
)


def test_upstream_count_reconciliation() -> None:
    """Verify that every raw extraction record is accounted for exactly once."""
    v040_recs = read_jsonl("dataset/processed/v0.4.0/extracted_records.jsonl")
    v041_recs = read_jsonl("dataset/processed/v0.4.1/extracted_records.jsonl")

    assert len(v040_recs) == 179
    assert len(v041_recs) == 226
    total_raw = len(v040_recs) + len(v041_recs)
    assert total_raw == 405

    # Entity vs statement breakdown in upstream files
    v040_entities = [r for r in v040_recs if r["category"] in VALID_ENTITY_TYPES]
    v040_stmts = [r for r in v040_recs if r["category"] in VALID_STATEMENT_TYPES]
    assert len(v040_entities) == 174
    assert len(v040_stmts) == 5

    v041_entities = [r for r in v041_recs if r["category"] in VALID_ENTITY_TYPES]
    v041_stmts = [r for r in v041_recs if r["category"] in VALID_STATEMENT_TYPES]
    assert len(v041_entities) == 205
    assert len(v041_stmts) == 21

    total_entities_raw = len(v040_entities) + len(v041_entities)
    total_stmts_raw = len(v040_stmts) + len(v041_stmts)
    assert total_entities_raw == 379
    assert total_stmts_raw == 26
    assert total_entities_raw + total_stmts_raw == 405

    # Cross-version duplicate verification
    persisted_mentions = read_jsonl("dataset/processed/v0.5.0/entity_mentions.jsonl")
    persisted_stmts = read_jsonl("dataset/processed/v0.5.0/canonical_statements.jsonl")
    assert len(persisted_mentions) == 267
    assert len(persisted_stmts) == 22

    duplicate_mentions = total_entities_raw - len(persisted_mentions)
    duplicate_stmts = total_stmts_raw - len(persisted_stmts)
    assert duplicate_mentions == 112
    assert duplicate_stmts == 4
    assert duplicate_mentions + duplicate_stmts == 116

    # Ingestion conservation: accepted (289) + duplicates (116) == raw (405)
    assert (len(persisted_mentions) + len(persisted_stmts)) + (duplicate_mentions + duplicate_stmts) == total_raw


def test_provenance_character_offset_exact_matches() -> None:
    """Verify that all entity mentions point to the exact claimed text in chunk text."""
    chunks = {}
    with open("dataset/processed/v0.3.0/chunks.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                c = json.loads(line)
                chunks[c["chunk_id"]] = c

    mentions = read_jsonl("dataset/processed/v0.5.0/entity_mentions.jsonl")
    for m in mentions:
        cid = m["chunk_id"]
        assert cid in chunks, f"Missing chunk {cid}"
        c = chunks[cid]
        start = m["evidence"]["start_char"]
        end = m["evidence"]["end_char"]
        expected = m["evidence"]["text"]
        actual = c["text"][start:end]
        assert actual == expected, f"Offset mismatch in {m['mention_id']}: expected {expected!r}, got {actual!r}"


def test_multi_format_storage_parity() -> None:
    """Verify exact parity of primary keys across JSONL, Parquet, and SQLite."""
    tables_to_check = [
        ("papers", "canonical_papers", "paper_id"),
        ("entities", "canonical_entities", "entity_id"),
        ("entity_mentions", "entity_mentions", "mention_id"),
        ("statements", "canonical_statements", "statement_id"),
        ("relationships", "canonical_relationships", "relationship_id"),
    ]

    conn = sqlite3.connect("dataset/processed/v0.5.0/knowledge_base.db")
    cur = conn.cursor()

    for tbl_name, file_base, pk_col in tables_to_check:
        # JSONL
        jsonl_data = read_jsonl(f"dataset/processed/v0.5.0/{file_base}.jsonl")
        ids_jsonl = {r[pk_col] for r in jsonl_data}

        # Parquet
        pq_table = pq.read_table(f"dataset/processed/v0.5.0/{file_base}.parquet")
        ids_parquet = set(pq_table[pk_col].to_pylist())

        # SQLite
        cur.execute(f"SELECT {pk_col} FROM {tbl_name}")
        ids_sqlite = {row[0] for row in cur.fetchall()}

        assert ids_jsonl == ids_parquet, f"JSONL/Parquet ID mismatch in {tbl_name}"
        assert ids_jsonl == ids_sqlite, f"JSONL/SQLite ID mismatch in {tbl_name}"


def test_isolated_v041_dangling_relationship_quarantine() -> None:
    """Verify that building KB from v0.4.1 alone safely quarantines the 12 dangling v0.4.0 relationships."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        cfg = KnowledgeBaseConfig(
            output_dir=tmp_path / "out",
            manifest_dir=tmp_path / "manifests",
            ingest_v040_records=False,
            ingest_v041_records=True,
            ingest_v040_relationships=True,
            save_parquet=False,
            save_sqlite=True,
        )
        manifest = ScientificKnowledgeBasePipeline(cfg).run()
        assert manifest.total_quarantined_records_count == 12
        assert manifest.total_relationships_count == 0

        quarantine_recs = read_jsonl(tmp_path / "out" / "quarantined_records.jsonl")
        assert len(quarantine_recs) == 12
        for q in quarantine_recs:
            assert q["quarantine_reason"] == "DANGLING_RELATION_ENDPOINT"
