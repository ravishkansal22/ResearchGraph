"""Pytest test configuration and fixtures for ResearchGraph backend tests.

Ensures that reproducible test SQLite databases and Parquet chunk artifacts
are initialized if the production datasets are absent in the testing environment (such as CI).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from researchgraph.core.config import settings


def _seed_sqlite_database(db_path: Path) -> None:
    """Create schema and populate minimal seed records for backend integration tests."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS papers (
        paper_id TEXT PRIMARY KEY,
        schema_version TEXT NOT NULL,
        doi TEXT,
        arxiv_id TEXT,
        title TEXT NOT NULL,
        abstract TEXT,
        publication_year INTEGER,
        venue_name TEXT,
        venue_json TEXT,
        open_access_url TEXT,
        file_hash TEXT,
        total_entities_count INTEGER DEFAULT 0,
        total_statements_count INTEGER DEFAULT 0,
        total_relationships_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS entities (
        entity_id TEXT PRIMARY KEY,
        schema_version TEXT NOT NULL,
        category TEXT NOT NULL,
        canonical_name TEXT NOT NULL,
        aliases_json TEXT NOT NULL,
        mentions_count INTEGER DEFAULT 1,
        paper_ids_json TEXT NOT NULL,
        chunk_ids_json TEXT NOT NULL,
        description TEXT,
        validation_status TEXT NOT NULL,
        alias_resolution_status TEXT NOT NULL,
        first_seen_version TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS entity_mentions (
        mention_id TEXT PRIMARY KEY,
        entity_id TEXT NOT NULL,
        paper_id TEXT NOT NULL,
        chunk_id TEXT NOT NULL,
        category TEXT NOT NULL,
        surface_text TEXT NOT NULL,
        normalized_name TEXT NOT NULL,
        evidence_text TEXT NOT NULL,
        start_char INTEGER NOT NULL,
        end_char INTEGER NOT NULL,
        provenance_json TEXT NOT NULL,
        attribution TEXT NOT NULL,
        confidence_score REAL NOT NULL,
        extraction_version TEXT NOT NULL,
        validation_status TEXT NOT NULL,
        upstream_record_id TEXT NOT NULL,
        FOREIGN KEY(entity_id) REFERENCES entities(entity_id),
        FOREIGN KEY(paper_id) REFERENCES papers(paper_id)
    );

    CREATE TABLE IF NOT EXISTS statements (
        statement_id TEXT PRIMARY KEY,
        schema_version TEXT NOT NULL,
        category TEXT NOT NULL,
        surface_text TEXT NOT NULL,
        normalized_statement TEXT NOT NULL,
        paper_id TEXT NOT NULL,
        chunk_id TEXT NOT NULL,
        evidence_text TEXT NOT NULL,
        start_char INTEGER NOT NULL,
        end_char INTEGER NOT NULL,
        provenance_json TEXT NOT NULL,
        attribution TEXT NOT NULL,
        confidence_score REAL NOT NULL,
        extraction_version TEXT NOT NULL,
        validation_status TEXT NOT NULL,
        validation_notes_json TEXT NOT NULL,
        related_entity_ids_json TEXT NOT NULL,
        upstream_record_id TEXT NOT NULL,
        FOREIGN KEY(paper_id) REFERENCES papers(paper_id)
    );

    CREATE TABLE IF NOT EXISTS relationships (
        relationship_id TEXT PRIMARY KEY,
        schema_version TEXT NOT NULL,
        relation_type TEXT NOT NULL,
        source_id TEXT NOT NULL,
        target_id TEXT NOT NULL,
        source_type TEXT NOT NULL,
        target_type TEXT NOT NULL,
        paper_id TEXT NOT NULL,
        chunk_id TEXT NOT NULL,
        surface_text TEXT,
        evidence_text TEXT NOT NULL,
        start_char INTEGER NOT NULL,
        end_char INTEGER NOT NULL,
        provenance_json TEXT NOT NULL,
        attribution TEXT NOT NULL,
        is_directed INTEGER NOT NULL DEFAULT 1,
        confidence_score REAL NOT NULL,
        extraction_version TEXT NOT NULL,
        validation_status TEXT NOT NULL,
        structural_validity TEXT NOT NULL DEFAULT 'STRUCTURALLY_VALID',
        evidence_support TEXT NOT NULL DEFAULT 'STRONG',
        human_verification TEXT NOT NULL DEFAULT 'VERIFIED',
        correction_notes TEXT,
        upstream_relation_id TEXT NOT NULL,
        FOREIGN KEY(paper_id) REFERENCES papers(paper_id)
    );

    CREATE TABLE IF NOT EXISTS quarantined_records (
        quarantine_id TEXT PRIMARY KEY,
        record_type TEXT NOT NULL,
        quarantine_reason TEXT NOT NULL,
        error_message TEXT NOT NULL,
        source_version TEXT NOT NULL,
        upstream_id TEXT,
        raw_payload_json TEXT NOT NULL,
        timestamp TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS alias_mappings (
        surface_form TEXT PRIMARY KEY,
        canonical_name TEXT NOT NULL,
        category TEXT NOT NULL,
        status TEXT NOT NULL,
        rationale TEXT NOT NULL
    );
    """)

    papers_sql = """
    INSERT OR IGNORE INTO papers (
        paper_id, schema_version, doi, title, abstract, publication_year, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    papers_data = [
        (
            "paper_seed_01",
            "0.5.0",
            "10.1000/1",
            "Federated Learning for Clinical Oncology",
            "A study of privacy-preserving machine learning in oncology.",
            2023,
            "2023-01-01T00:00:00Z",
        ),
        (
            "paper_seed_02",
            "0.5.0",
            "10.1000/2",
            "Distributed Optimization in Healthcare",
            "Addressing communication bandwidth bottlenecks in hospital networks.",
            2024,
            "2024-01-01T00:00:00Z",
        ),
    ]
    cur.executemany(papers_sql, papers_data)

    entities_sql = """
    INSERT OR IGNORE INTO entities (
        entity_id, schema_version, category, canonical_name, aliases_json,
        paper_ids_json, chunk_ids_json, validation_status, alias_resolution_status,
        first_seen_version, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    entities_data = [
        (
            "ent_seed_01",
            "0.5.0",
            "METHOD",
            "Federated Learning",
            '["FL", "federated learning"]',
            '["paper_seed_01"]',
            '["chunk_seed_01"]',
            "VALIDATED",
            "RESOLVED",
            "v0.5.0",
            "2023-01-01T00:00:00Z",
        ),
        (
            "ent_seed_02",
            "0.5.0",
            "PROBLEM",
            "Clinical Oncology Privacy Constraints",
            '["oncology privacy"]',
            '["paper_seed_01"]',
            '["chunk_seed_01"]',
            "VALIDATED",
            "RESOLVED",
            "v0.5.0",
            "2023-01-01T00:00:00Z",
        ),
        (
            "ent_seed_03",
            "0.5.0",
            "BOTTLENECK",
            "Communication Latency",
            '["bandwidth bottleneck"]',
            '["paper_seed_02"]',
            '["chunk_seed_02"]',
            "VALIDATED",
            "RESOLVED",
            "v0.5.0",
            "2024-01-01T00:00:00Z",
        ),
    ]
    cur.executemany(entities_sql, entities_data)

    mentions_sql = """
    INSERT OR IGNORE INTO entity_mentions (
        mention_id, entity_id, paper_id, chunk_id, category, surface_text,
        normalized_name, evidence_text, start_char, end_char, provenance_json,
        attribution, confidence_score, extraction_version, validation_status,
        upstream_record_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    mentions_data = [
        (
            "ment_seed_01",
            "ent_seed_01",
            "paper_seed_01",
            "chunk_seed_01",
            "METHOD",
            "federated learning",
            "federated learning",
            "In federated learning settings",
            0,
            18,
            "{}",
            "author",
            0.98,
            "v0.3.0",
            "VALIDATED",
            "up_seed_01",
        )
    ]
    cur.executemany(mentions_sql, mentions_data)

    statements_sql = """
    INSERT OR IGNORE INTO statements (
        statement_id, schema_version, category, surface_text,
        normalized_statement, paper_id, chunk_id, evidence_text,
        start_char, end_char, provenance_json, attribution,
        confidence_score, extraction_version, validation_status,
        validation_notes_json, related_entity_ids_json, upstream_record_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    statements_data = [
        (
            "stmt_seed_01",
            "0.5.0",
            "LIMITATION",
            "Federated learning experiences communication latency in healthcare networks.",
            "Federated learning suffers from network bottleneck in hospitals.",
            "paper_seed_01",
            "chunk_seed_01",
            "Evidence text for limitation.",
            0,
            50,
            "{}",
            "author",
            0.92,
            "v0.3.0",
            "VALIDATED",
            "[]",
            '["ent_seed_01", "ent_seed_03"]',
            "up_stmt_seed_01",
        )
    ]
    cur.executemany(statements_sql, statements_data)

    relationships_sql = """
    INSERT OR IGNORE INTO relationships (
        relationship_id, schema_version, relation_type, source_id,
        target_id, source_type, target_type, paper_id, chunk_id,
        surface_text, evidence_text, start_char, end_char,
        provenance_json, attribution, is_directed, confidence_score,
        extraction_version, validation_status, structural_validity,
        evidence_support, human_verification, upstream_relation_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    relationships_data = [
        (
            "rel_seed_01",
            "0.5.0",
            "HAS_LIMITATION",
            "ent_seed_01",
            "ent_seed_03",
            "METHOD",
            "BOTTLENECK",
            "paper_seed_01",
            "chunk_seed_01",
            "has limitation",
            "Evidence text for rel.",
            0,
            20,
            "{}",
            "author",
            1,
            0.95,
            "v0.3.0",
            "VALIDATED",
            "STRUCTURALLY_VALID",
            "STRONG",
            "VERIFIED",
            "up_rel_seed_01",
        )
    ]
    cur.executemany(relationships_sql, relationships_data)

    alias_sql = """
    INSERT OR IGNORE INTO alias_mappings (
        surface_form, canonical_name, category, status, rationale
    ) VALUES (?, ?, ?, ?, ?)
    """
    alias_data = [
        ("federated learning", "Federated Learning", "METHOD", "RESOLVED", "Exact match")
    ]
    cur.executemany(alias_sql, alias_data)

    conn.commit()
    conn.close()


def _seed_chunks_parquet(chunks_path: Path) -> None:
    """Create a minimal Parquet chunk dataset for retrieval testing."""
    chunks_path.parent.mkdir(parents=True, exist_ok=True)
    tbl = pa.Table.from_arrays(
        [
            pa.array(["chunk_seed_01", "chunk_seed_02", "chunk_seed_03"]),
            pa.array(["paper_seed_01", "paper_seed_01", "paper_seed_02"]),
            pa.array([
                "Federated learning preserves privacy in clinical oncology hospital systems.",
                "Differential privacy and secure aggregation guard against reconstruction attacks.",
                "Communication latency limits the scaling of edge model training in healthcare.",
            ]),
        ],
        names=["chunk_id", "canonical_id", "text"],
    )
    pq.write_table(tbl, str(chunks_path))


@pytest.fixture(scope="session", autouse=True)
def ensure_test_artifacts() -> Generator[None, None, None]:
    """Ensure SQLite database and Parquet chunks exist before executing backend tests."""
    db_path = settings.sqlite_db_path
    chunks_path = settings.chunks_parquet_path

    # If the database does not exist or has 0 papers, seed it
    should_seed_db = False
    if not db_path.exists():
        should_seed_db = True
    else:
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM papers")
            count = cur.fetchone()[0]
            conn.close()
            if count == 0:
                should_seed_db = True
        except Exception:
            should_seed_db = True

    if should_seed_db:
        _seed_sqlite_database(db_path)

    if not chunks_path.exists():
        _seed_chunks_parquet(chunks_path)

    yield
