"""Persistence Engine for the Scientific Knowledge Base.

Supports writing and loading versioned JSONL snapshots, columnar Parquet files,
and an embedded relational SQLite database with indexed constraints.
Schema Version: 0.5.0
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pyarrow as pa
import pyarrow.parquet as pq

from dataset.schemas.scientific_knowledge_base import (
    AliasMapping,
    CanonicalEntityNode,
    CanonicalPaperNode,
    CanonicalRelationshipNode,
    CanonicalStatementNode,
    EntityMention,
    QuarantinedRecord,
)

logger = logging.getLogger(__name__)


def write_jsonl(path: Path | str, items: Iterable[Any]) -> int:
    """Write an iterable of Pydantic models or dicts to a JSONL file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with p.open("w", encoding="utf-8") as f:
        for item in items:
            if hasattr(item, "model_dump"):
                line = json.dumps(item.model_dump(mode="json"), ensure_ascii=False)
            elif isinstance(item, dict):
                line = json.dumps(item, ensure_ascii=False)
            else:
                line = json.dumps(dict(item), ensure_ascii=False)
            f.write(line + "\n")
            count += 1
    return count


def read_jsonl(path: Path | str) -> List[Dict[str, Any]]:
    """Read records from a JSONL file as a list of dictionaries."""
    p = Path(path)
    if not p.exists():
        return []
    records = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                records.append(json.loads(line_str))
    return records


class KnowledgeBaseStorage:
    """Handles persistence of canonical knowledge base records to disk."""

    def __init__(self, output_dir: Path | str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.output_dir / "knowledge_base.db"

    def save_snapshots_jsonl(
        self,
        papers: List[CanonicalPaperNode],
        entities: List[CanonicalEntityNode],
        mentions: List[EntityMention],
        statements: List[CanonicalStatementNode],
        relationships: List[CanonicalRelationshipNode],
        quarantine: List[QuarantinedRecord],
        aliases: List[AliasMapping],
    ) -> Dict[str, int]:
        """Write all knowledge base components to JSONL snapshots."""
        counts = {
            "papers": write_jsonl(self.output_dir / "canonical_papers.jsonl", papers),
            "entities": write_jsonl(self.output_dir / "canonical_entities.jsonl", entities),
            "mentions": write_jsonl(self.output_dir / "entity_mentions.jsonl", mentions),
            "statements": write_jsonl(self.output_dir / "canonical_statements.jsonl", statements),
            "relationships": write_jsonl(self.output_dir / "canonical_relationships.jsonl", relationships),
            "quarantine": write_jsonl(self.output_dir / "quarantined_records.jsonl", quarantine),
            "aliases": write_jsonl(self.output_dir / "alias_mappings.jsonl", aliases),
        }
        logger.info("JSONL snapshots written successfully to %s: %s", self.output_dir, counts)
        return counts

    def save_parquet(
        self,
        papers: List[CanonicalPaperNode],
        entities: List[CanonicalEntityNode],
        mentions: List[EntityMention],
        statements: List[CanonicalStatementNode],
        relationships: List[CanonicalRelationshipNode],
    ) -> Dict[str, str]:
        """Save flat columnar Parquet files for fast analytical queries."""
        parquet_files = {}

        # 1. Papers Parquet
        if papers:
            paper_data = [
                {
                    "paper_id": p.paper_id,
                    "title": p.title,
                    "doi": p.doi or "",
                    "arxiv_id": p.arxiv_id or "",
                    "publication_year": p.publication_year or 0,
                    "file_hash": p.file_hash or "",
                    "total_entities_count": p.total_entities_count,
                    "total_statements_count": p.total_statements_count,
                    "total_relationships_count": p.total_relationships_count,
                    "created_at": p.created_at,
                }
                for p in papers
            ]
            t_papers = pa.Table.from_pylist(paper_data)
            pq_path = self.output_dir / "canonical_papers.parquet"
            pq.write_table(t_papers, pq_path)
            parquet_files["papers"] = str(pq_path)

        # 2. Entities Parquet
        if entities:
            entity_data = [
                {
                    "entity_id": e.entity_id,
                    "category": e.category.value,
                    "canonical_name": e.canonical_name,
                    "aliases": ",".join(e.aliases),
                    "mentions_count": e.mentions_count,
                    "paper_ids": ",".join(e.paper_ids),
                    "chunk_ids": ",".join(e.chunk_ids),
                    "validation_status": e.validation_status.value,
                    "alias_resolution_status": e.alias_resolution_status.value,
                    "first_seen_version": e.first_seen_version,
                    "updated_at": e.updated_at,
                }
                for e in entities
            ]
            t_entities = pa.Table.from_pylist(entity_data)
            pq_path = self.output_dir / "canonical_entities.parquet"
            pq.write_table(t_entities, pq_path)
            parquet_files["entities"] = str(pq_path)

        # 3. Mentions Parquet
        if mentions:
            mention_data = [
                {
                    "mention_id": m.mention_id,
                    "entity_id": m.entity_id,
                    "paper_id": m.paper_id,
                    "chunk_id": m.chunk_id,
                    "category": m.category.value,
                    "surface_text": m.surface_text,
                    "normalized_name": m.normalized_name,
                    "start_char": m.evidence.start_char,
                    "end_char": m.evidence.end_char,
                    "attribution": m.attribution.value,
                    "confidence_score": m.confidence_score,
                    "extraction_version": m.extraction_version,
                    "upstream_record_id": m.upstream_record_id,
                }
                for m in mentions
            ]
            t_mentions = pa.Table.from_pylist(mention_data)
            pq_path = self.output_dir / "entity_mentions.parquet"
            pq.write_table(t_mentions, pq_path)
            parquet_files["mentions"] = str(pq_path)

        # 4. Statements Parquet
        if statements:
            stmt_data = [
                {
                    "statement_id": s.statement_id,
                    "category": s.category.value,
                    "surface_text": s.surface_text,
                    "normalized_statement": s.normalized_statement,
                    "paper_id": s.paper_id,
                    "chunk_id": s.chunk_id,
                    "start_char": s.evidence.start_char,
                    "end_char": s.evidence.end_char,
                    "attribution": s.attribution.value,
                    "confidence_score": s.confidence_score,
                    "extraction_version": s.extraction_version,
                    "upstream_record_id": s.upstream_record_id,
                }
                for s in statements
            ]
            t_stmts = pa.Table.from_pylist(stmt_data)
            pq_path = self.output_dir / "canonical_statements.parquet"
            pq.write_table(t_stmts, pq_path)
            parquet_files["statements"] = str(pq_path)

        # 5. Relationships Parquet
        if relationships:
            rel_data = [
                {
                    "relationship_id": r.relationship_id,
                    "relation_type": r.relation_type.value,
                    "source_id": r.source_id,
                    "target_id": r.target_id,
                    "source_type": r.source_type,
                    "target_type": r.target_type,
                    "paper_id": r.paper_id,
                    "chunk_id": r.chunk_id,
                    "surface_text": r.surface_text or "",
                    "start_char": r.evidence.start_char,
                    "end_char": r.evidence.end_char,
                    "attribution": r.attribution.value,
                    "confidence_score": r.confidence_score,
                    "extraction_version": r.extraction_version,
                    "structural_validity": r.structural_validity.value,
                    "evidence_support": r.evidence_support.value,
                    "human_verification": r.human_verification.value,
                    "correction_notes": r.correction_notes or "",
                    "upstream_relation_id": r.upstream_relation_id,
                }
                for r in relationships
            ]
            t_rels = pa.Table.from_pylist(rel_data)
            pq_path = self.output_dir / "canonical_relationships.parquet"
            pq.write_table(t_rels, pq_path)
            parquet_files["relationships"] = str(pq_path)

        logger.info("Parquet snapshots written successfully to %s", self.output_dir)
        return parquet_files

    def init_sqlite_schema(self, conn: sqlite3.Connection) -> None:
        """Create relational tables and indices in SQLite database."""
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
            evidence_support TEXT NOT NULL DEFAULT 'NOT_ASSESSED',
            human_verification TEXT NOT NULL DEFAULT 'PENDING',
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

        -- Performance Indices
        CREATE INDEX IF NOT EXISTS idx_entities_category ON entities(category);
        CREATE INDEX IF NOT EXISTS idx_entities_canonical_name ON entities(canonical_name);
        CREATE INDEX IF NOT EXISTS idx_mentions_entity_id ON entity_mentions(entity_id);
        CREATE INDEX IF NOT EXISTS idx_mentions_paper_id ON entity_mentions(paper_id);
        CREATE INDEX IF NOT EXISTS idx_mentions_chunk_id ON entity_mentions(chunk_id);
        CREATE INDEX IF NOT EXISTS idx_mentions_category ON entity_mentions(category);
        CREATE INDEX IF NOT EXISTS idx_statements_paper_id ON statements(paper_id);
        CREATE INDEX IF NOT EXISTS idx_statements_chunk_id ON statements(chunk_id);
        CREATE INDEX IF NOT EXISTS idx_statements_category ON statements(category);
        CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id);
        CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id);
        CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relation_type);
        CREATE INDEX IF NOT EXISTS idx_relationships_paper_id ON relationships(paper_id);
        CREATE INDEX IF NOT EXISTS idx_relationships_evidence_support ON relationships(evidence_support);
        CREATE INDEX IF NOT EXISTS idx_relationships_human_verification ON relationships(human_verification);
        CREATE INDEX IF NOT EXISTS idx_quarantine_reason ON quarantined_records(quarantine_reason);
        """)
        conn.commit()

    def save_sqlite(
        self,
        papers: List[CanonicalPaperNode],
        entities: List[CanonicalEntityNode],
        mentions: List[EntityMention],
        statements: List[CanonicalStatementNode],
        relationships: List[CanonicalRelationshipNode],
        quarantine: List[QuarantinedRecord],
        aliases: List[AliasMapping],
    ) -> str:
        """Populate SQLite database atomically within a single transaction."""
        if self.db_path.exists():
            self.db_path.unlink()

        conn = sqlite3.connect(str(self.db_path))
        try:
            self.init_sqlite_schema(conn)
            cur = conn.cursor()

            # Papers
            cur.executemany(
                """
                INSERT INTO papers (
                    paper_id, schema_version, doi, arxiv_id, title, abstract,
                    publication_year, venue_name, open_access_url, file_hash,
                    total_entities_count, total_statements_count, total_relationships_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        p.paper_id,
                        p.schema_version,
                        p.doi,
                        p.arxiv_id,
                        p.title,
                        p.abstract,
                        p.publication_year,
                        p.venue.name if p.venue else None,
                        p.open_access_url,
                        p.file_hash,
                        p.total_entities_count,
                        p.total_statements_count,
                        p.total_relationships_count,
                        p.created_at,
                    )
                    for p in papers
                ],
            )

            # Entities
            cur.executemany(
                """
                INSERT INTO entities (
                    entity_id, schema_version, category, canonical_name, aliases_json,
                    mentions_count, paper_ids_json, chunk_ids_json, description,
                    validation_status, alias_resolution_status, first_seen_version, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        e.entity_id,
                        e.schema_version,
                        e.category.value,
                        e.canonical_name,
                        json.dumps(e.aliases, ensure_ascii=False),
                        e.mentions_count,
                        json.dumps(e.paper_ids, ensure_ascii=False),
                        json.dumps(e.chunk_ids, ensure_ascii=False),
                        e.description,
                        e.validation_status.value,
                        e.alias_resolution_status.value,
                        e.first_seen_version,
                        e.updated_at,
                    )
                    for e in entities
                ],
            )

            # Mentions
            cur.executemany(
                """
                INSERT INTO entity_mentions (
                    mention_id, entity_id, paper_id, chunk_id, category, surface_text,
                    normalized_name, evidence_text, start_char, end_char, provenance_json,
                    attribution, confidence_score, extraction_version, validation_status, upstream_record_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        m.mention_id,
                        m.entity_id,
                        m.paper_id,
                        m.chunk_id,
                        m.category.value,
                        m.surface_text,
                        m.normalized_name,
                        m.evidence.text,
                        m.evidence.start_char,
                        m.evidence.end_char,
                        json.dumps(m.provenance.model_dump(mode="json"), ensure_ascii=False),
                        m.attribution.value,
                        m.confidence_score,
                        m.extraction_version,
                        m.validation_status.value,
                        m.upstream_record_id,
                    )
                    for m in mentions
                ],
            )

            # Statements
            cur.executemany(
                """
                INSERT INTO statements (
                    statement_id, schema_version, category, surface_text, normalized_statement,
                    paper_id, chunk_id, evidence_text, start_char, end_char, provenance_json,
                    attribution, confidence_score, extraction_version, validation_status,
                    validation_notes_json, related_entity_ids_json, upstream_record_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        s.statement_id,
                        s.schema_version,
                        s.category.value,
                        s.surface_text,
                        s.normalized_statement,
                        s.paper_id,
                        s.chunk_id,
                        s.evidence.text,
                        s.evidence.start_char,
                        s.evidence.end_char,
                        json.dumps(s.provenance.model_dump(mode="json"), ensure_ascii=False),
                        s.attribution.value,
                        s.confidence_score,
                        s.extraction_version,
                        s.validation_status.value,
                        json.dumps(s.validation_notes, ensure_ascii=False),
                        json.dumps(s.related_entity_ids, ensure_ascii=False),
                        s.upstream_record_id,
                    )
                    for s in statements
                ],
            )

            # Relationships
            cur.executemany(
                """
                INSERT INTO relationships (
                    relationship_id, schema_version, relation_type, source_id, target_id,
                    source_type, target_type, paper_id, chunk_id, surface_text, evidence_text,
                    start_char, end_char, provenance_json, attribution, is_directed,
                    confidence_score, extraction_version, validation_status,
                    structural_validity, evidence_support, human_verification, correction_notes,
                    upstream_relation_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r.relationship_id,
                        r.schema_version,
                        r.relation_type.value,
                        r.source_id,
                        r.target_id,
                        r.source_type,
                        r.target_type,
                        r.paper_id,
                        r.chunk_id,
                        r.surface_text,
                        r.evidence.text,
                        r.evidence.start_char,
                        r.evidence.end_char,
                        json.dumps(r.provenance.model_dump(mode="json"), ensure_ascii=False),
                        r.attribution.value,
                        1 if r.is_directed else 0,
                        r.confidence_score,
                        r.extraction_version,
                        r.validation_status.value,
                        r.structural_validity.value,
                        r.evidence_support.value,
                        r.human_verification.value,
                        r.correction_notes,
                        r.upstream_relation_id,
                    )
                    for r in relationships
                ],
            )

            # Quarantined Records
            cur.executemany(
                """
                INSERT INTO quarantined_records (
                    quarantine_id, record_type, quarantine_reason, error_message,
                    source_version, upstream_id, raw_payload_json, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        q.quarantine_id,
                        q.record_type,
                        q.quarantine_reason.value,
                        q.error_message,
                        q.source_version,
                        q.upstream_id,
                        json.dumps(q.raw_payload, ensure_ascii=False),
                        q.timestamp,
                    )
                    for q in quarantine
                ],
            )

            # Alias Mappings
            cur.executemany(
                """
                INSERT INTO alias_mappings (
                    surface_form, canonical_name, category, status, rationale
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        a.surface_form,
                        a.canonical_name,
                        a.category.value,
                        a.status.value,
                        a.rationale,
                    )
                    for a in aliases
                ],
            )

            conn.commit()
            logger.info("SQLite database written successfully to %s", self.db_path)
            return str(self.db_path)
        finally:
            conn.close()
