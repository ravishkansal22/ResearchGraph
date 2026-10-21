"""Structured Query Engine for the Scientific Knowledge Base.

Provides relational, provenance-preserving query interfaces over the persistent
knowledge base without embedding models or semantic search heuristics.
Schema Version: 0.5.0
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


class KnowledgeBaseQueryEngine:
    """Relational structured query interface over the persisted SQLite knowledge base."""

    def __init__(self, db_path: Optional[Path | str] = None):
        if db_path is None:
            repo_root = Path(__file__).resolve().parents[2]
            candidates = [
                Path("dataset/processed/v0.5.1/knowledge_base.db"),
                repo_root / "dataset/processed/v0.5.1/knowledge_base.db",
                Path("dataset/processed/v0.5.0/knowledge_base.db"),
                repo_root / "dataset/processed/v0.5.0/knowledge_base.db",
            ]
            self.db_path = next((p for p in candidates if p.exists()), candidates[0])
        else:
            self.db_path = Path(db_path)
            if not self.db_path.exists():
                repo_root = Path(__file__).resolve().parents[2]
                candidate = repo_root / db_path
                if candidate.exists():
                    self.db_path = candidate
            
        if not self.db_path.exists():
            raise FileNotFoundError(f"Knowledge base SQLite database not found at {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Create a row-factory enabled SQLite connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _has_column(self, conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
        """Check if a table contains a specific column."""
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table_name})")
        columns = [row["name"] for row in cur.fetchall()]
        return column_name in columns

    def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a paper by canonical paper ID."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,))
            row = cur.fetchone()
            if not row:
                return None
            return dict(row)

    def list_entities_by_type(self, category: str, limit: int = 100) -> List[Dict[str, Any]]:
        """List canonical entities of a specified category (e.g. 'METHOD', 'PROBLEM')."""
        cat_upper = category.strip().upper()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT entity_id, category, canonical_name, mentions_count,
                       aliases_json, paper_ids_json, validation_status, alias_resolution_status
                FROM entities
                WHERE category = ?
                ORDER BY mentions_count DESC, canonical_name ASC
                LIMIT ?
                """,
                (cat_upper, limit),
            )
            results = []
            for r in cur.fetchall():
                d = dict(r)
                d["aliases"] = json.loads(d.pop("aliases_json"))
                d["paper_ids"] = json.loads(d.pop("paper_ids_json"))
                results.append(d)
            return results

    def get_statements_for_paper(
        self,
        paper_id: str,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find all evidence-backed statements associated with a canonical paper."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            if category:
                cur.execute(
                    """
                    SELECT * FROM statements
                    WHERE paper_id = ? AND category = ?
                    ORDER BY start_char ASC
                    """,
                    (paper_id, category.strip().upper()),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM statements
                    WHERE paper_id = ?
                    ORDER BY start_char ASC
                    """,
                    (paper_id,),
                )
            results = []
            for r in cur.fetchall():
                d = dict(r)
                d["provenance"] = json.loads(d.pop("provenance_json"))
                d["validation_notes"] = json.loads(d.pop("validation_notes_json"))
                d["related_entity_ids"] = json.loads(d.pop("related_entity_ids_json"))
                results.append(d)
            return results

    def get_records_for_chunk(self, chunk_id: str) -> Dict[str, Any]:
        """Retrieve all entity mentions, statements, and relationships originating from a chunk."""
        with self._get_connection() as conn:
            cur = conn.cursor()

            # Mentions
            cur.execute("SELECT * FROM entity_mentions WHERE chunk_id = ?", (chunk_id,))
            mentions = []
            for r in cur.fetchall():
                d = dict(r)
                d["provenance"] = json.loads(d.pop("provenance_json"))
                mentions.append(d)

            # Statements
            cur.execute("SELECT * FROM statements WHERE chunk_id = ?", (chunk_id,))
            statements = []
            for r in cur.fetchall():
                d = dict(r)
                d["provenance"] = json.loads(d.pop("provenance_json"))
                d["validation_notes"] = json.loads(d.pop("validation_notes_json"))
                d["related_entity_ids"] = json.loads(d.pop("related_entity_ids_json"))
                statements.append(d)

            # Relationships
            cur.execute("SELECT * FROM relationships WHERE chunk_id = ?", (chunk_id,))
            relationships = []
            for r in cur.fetchall():
                d = dict(r)
                d["provenance"] = json.loads(d.pop("provenance_json"))
                relationships.append(d)

            return {
                "chunk_id": chunk_id,
                "mentions": mentions,
                "statements": statements,
                "relationships": relationships,
            }

    def find_methods_for_problem(
        self,
        problem_query: str,
        trusted_only: bool = True,
        include_unsupported: bool = False,
        evidence_support: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find methods associated with a specified problem via semantic relationships.
        
        Args:
            problem_query: Query string to match against problem entity names/aliases.
            trusted_only: When True (default), strictly requires evidence_support == 'SUPPORTED'.
                          Excludes 'UNSUPPORTED', 'AMBIGUOUS', and 'NOT_ASSESSED'.
            include_unsupported: If True, bypasses trusted_only and includes unsupported records.
            evidence_support: Explicit evidence support status to filter on (e.g. 'UNSUPPORTED').
        """
        norm_query = problem_query.strip().lower()
        with self._get_connection() as conn:
            cur = conn.cursor()
            # Match canonical problem entities
            cur.execute(
                """
                SELECT entity_id, canonical_name FROM entities
                WHERE category = 'PROBLEM' AND (
                    canonical_name LIKE ? OR
                    aliases_json LIKE ?
                )
                """,
                (f"%{norm_query}%", f"%{norm_query}%"),
            )
            problem_entities = cur.fetchall()
            if not problem_entities:
                return []

            has_es = self._has_column(conn, "relationships", "evidence_support")

            results = []
            for prob in problem_entities:
                prob_id = prob["entity_id"]
                prob_name = prob["canonical_name"]

                query_sql = """
                    SELECT r.*,
                           e.canonical_name AS method_name, e.category AS method_category
                    FROM relationships r
                    JOIN entities e ON r.source_id = e.entity_id
                    WHERE r.target_id = ?
                """
                params: List[Any] = [prob_id]

                if has_es:
                    if evidence_support:
                        query_sql += " AND r.evidence_support = ?"
                        params.append(evidence_support.strip().upper())
                    elif trusted_only and not include_unsupported:
                        query_sql += " AND r.evidence_support = 'SUPPORTED'"

                cur.execute(query_sql, params)
                for r in cur.fetchall():
                    row_dict = dict(r)
                    if "provenance_json" in row_dict:
                        row_dict["provenance"] = json.loads(row_dict.pop("provenance_json"))
                    row_dict["problem_id"] = prob_id
                    row_dict["problem_name"] = prob_name
                    results.append(row_dict)
            return results

    def get_relationships_for_entity(
        self,
        entity_id: str,
        trusted_only: bool = True,
        include_unsupported: bool = False,
        evidence_support: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve all incoming and outgoing semantic relationships for a given canonical entity.
        
        Args:
            entity_id: Canonical entity ID.
            trusted_only: When True (default), strictly requires evidence_support == 'SUPPORTED'.
            include_unsupported: If True, bypasses trusted_only.
            evidence_support: Explicit evidence support status filter.
        """
        with self._get_connection() as conn:
            cur = conn.cursor()
            has_es = self._has_column(conn, "relationships", "evidence_support")

            query_sql = """
                SELECT r.*,
                       s.canonical_name AS source_name,
                       t.canonical_name AS target_name
                FROM relationships r
                LEFT JOIN entities s ON r.source_id = s.entity_id
                LEFT JOIN entities t ON r.target_id = t.entity_id
                WHERE (r.source_id = ? OR r.target_id = ?)
            """
            params: List[Any] = [entity_id, entity_id]

            if has_es:
                if evidence_support:
                    query_sql += " AND r.evidence_support = ?"
                    params.append(evidence_support.strip().upper())
                elif trusted_only and not include_unsupported:
                    query_sql += " AND r.evidence_support = 'SUPPORTED'"

            cur.execute(query_sql, params)
            results = []
            for r in cur.fetchall():
                d = dict(r)
                if "provenance_json" in d:
                    d["provenance"] = json.loads(d.pop("provenance_json"))
                results.append(d)
            return results

    def get_excluded_relationships(
        self,
        reason: Optional[str] = None,
        evidence_support: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve excluded/unsupported relationships for diagnostic audit.
        
        Returns relationships where evidence_support is not 'SUPPORTED' (e.g. 'UNSUPPORTED',
        'AMBIGUOUS', 'NOT_ASSESSED'), along with entity names, provenance, and diagnostic notes.
        """
        with self._get_connection() as conn:
            has_es = self._has_column(conn, "relationships", "evidence_support")
            if not has_es:
                return []
            cur = conn.cursor()
            clauses = []
            params: List[Any] = []
            if evidence_support:
                clauses.append("r.evidence_support = ?")
                params.append(evidence_support.strip().upper())
            else:
                clauses.append("r.evidence_support != 'SUPPORTED'")

            if reason:
                clauses.append("r.correction_notes LIKE ?")
                params.append(f"%{reason}%")

            where_sql = f"WHERE {' AND '.join(clauses)}"
            cur.execute(
                f"""
                SELECT r.*,
                       s.canonical_name AS source_name,
                       t.canonical_name AS target_name
                FROM relationships r
                LEFT JOIN entities s ON r.source_id = s.entity_id
                LEFT JOIN entities t ON r.target_id = t.entity_id
                {where_sql}
                ORDER BY r.relationship_id ASC
                LIMIT ?
                """,
                (*params, limit),
            )
            results = []
            for r in cur.fetchall():
                d = dict(r)
                if "provenance_json" in d:
                    d["provenance"] = json.loads(d.pop("provenance_json"))
                results.append(d)
            return results

    def trace_entity_mentions(self, entity_id: str) -> Dict[str, Any]:
        """Trace a canonical entity back to its original chunk mentions, character spans, and papers."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM entities WHERE entity_id = ?", (entity_id,))
            ent_row = cur.fetchone()
            if not ent_row:
                return {}

            entity = dict(ent_row)
            entity["aliases"] = json.loads(entity.pop("aliases_json"))
            entity["paper_ids"] = json.loads(entity.pop("paper_ids_json"))
            entity["chunk_ids"] = json.loads(entity.pop("chunk_ids_json"))

            cur.execute(
                """
                SELECT * FROM entity_mentions
                WHERE entity_id = ?
                ORDER BY paper_id ASC, chunk_id ASC, start_char ASC
                """,
                (entity_id,),
            )
            mentions = []
            for m in cur.fetchall():
                d = dict(m)
                d["provenance"] = json.loads(d.pop("provenance_json"))
                mentions.append(d)

            return {
                "entity": entity,
                "mentions_count": len(mentions),
                "mentions": mentions,
            }

    def filter_records(
        self,
        extractor_version: Optional[str] = None,
        validation_status: Optional[str] = None,
        structural_validity: Optional[str] = None,
        evidence_support: Optional[str] = None,
        human_verification: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Filter mentions, statements, and relationships by extractor version or validation statuses."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            clauses = []
            params = []
            if extractor_version:
                clauses.append("extraction_version = ?")
                params.append(extractor_version)
            if validation_status:
                clauses.append("validation_status = ?")
                params.append(validation_status.strip().upper())

            where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

            # Mentions
            cur.execute(
                f"SELECT * FROM entity_mentions {where_sql} LIMIT ?",
                (*params, limit),
            )
            mentions = [dict(r) for r in cur.fetchall()]

            # Statements
            cur.execute(
                f"SELECT * FROM statements {where_sql} LIMIT ?",
                (*params, limit),
            )
            statements = [dict(r) for r in cur.fetchall()]

            # Relationships: can also filter by structural_validity, evidence_support, human_verification
            rel_clauses = list(clauses)
            rel_params = list(params)
            has_sv = self._has_column(conn, "relationships", "structural_validity")
            if has_sv:
                if structural_validity:
                    rel_clauses.append("structural_validity = ?")
                    rel_params.append(structural_validity.strip().upper())
                if evidence_support:
                    rel_clauses.append("evidence_support = ?")
                    rel_params.append(evidence_support.strip().upper())
                if human_verification:
                    rel_clauses.append("human_verification = ?")
                    rel_params.append(human_verification.strip().upper())

            rel_where = f"WHERE {' AND '.join(rel_clauses)}" if rel_clauses else ""
            cur.execute(
                f"SELECT * FROM relationships {rel_where} LIMIT ?",
                (*rel_params, limit),
            )
            relationships = [dict(r) for r in cur.fetchall()]

            return {
                "filter_criteria": {
                    "extractor_version": extractor_version,
                    "validation_status": validation_status,
                    "structural_validity": structural_validity,
                    "evidence_support": evidence_support,
                    "human_verification": human_verification,
                },
                "mentions": mentions,
                "statements": statements,
                "relationships": relationships,
            }

    def inspect_quarantined_records(
        self,
        reason: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Inspect quarantined records filtered optionally by failure diagnostic reason."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            if reason:
                cur.execute(
                    """
                    SELECT * FROM quarantined_records
                    WHERE quarantine_reason = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (reason.strip().upper(), limit),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM quarantined_records
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            results = []
            for r in cur.fetchall():
                d = dict(r)
                d["raw_payload"] = json.loads(d.pop("raw_payload_json"))
                results.append(d)
            return results

    def inspect_alias_mappings(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Inspect explicit alias mappings."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            if status:
                cur.execute("SELECT * FROM alias_mappings WHERE status = ? ORDER BY surface_form ASC", (status.strip().upper(),))
            else:
                cur.execute("SELECT * FROM alias_mappings ORDER BY status ASC, surface_form ASC")
            return [dict(r) for r in cur.fetchall()]
