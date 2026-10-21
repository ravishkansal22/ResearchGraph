"""ResearchGraph Phase 9: Dead-End Graveyard & Negative Knowledge Engine.

Catalogs, indexes, and queries documented negative results, empirical regressions,
method limitations, computational bottlenecks, and boundary conditions across
the literature corpus.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from dataset.schemas.scientific_knowledge import AttributionType
from pipelines.knowledge_base.query import KnowledgeBaseQueryEngine
from pipelines.negative_knowledge.schema import (
    FailureCategory,
    NegativeEvidenceType,
    NegativeKnowledgeRecord,
)

logger = logging.getLogger(__name__)

# Lexical trigger patterns for detecting documented failure modes and limitations
NEGATIVE_MARKERS = [
    (re.compile(r"(?:fails? to|cannot|unable to)\s+([a-z\s]+)", re.IGNORECASE), FailureCategory.EMPIRICAL_REGRESSION),
    (re.compile(r"(?:limited by|limitation of|bottleneck of)\s+([a-z\s]+)", re.IGNORECASE), FailureCategory.METHOD_LIMITATION),
    (re.compile(r"(?:high computational cost|prohibitive memory|latency constraint)", re.IGNORECASE), FailureCategory.COMPUTATIONAL_BOTTLENECK),
    (re.compile(r"(?:under non-iid|data imbalance|label skew|heterogeneity)", re.IGNORECASE), FailureCategory.BOUNDARY_CONDITION),
    (re.compile(r"(?:degrades?|regresses?|drops? significantly)", re.IGNORECASE), FailureCategory.EMPIRICAL_REGRESSION),
]


class DeadEndGraveyard:
    """Catalog and index of negative knowledge, method failures, and empirical limitations."""

    def __init__(self, query_engine: Optional[KnowledgeBaseQueryEngine] = None):
        self.query_engine = query_engine or KnowledgeBaseQueryEngine()
        self.records: Dict[str, NegativeKnowledgeRecord] = {}
        self.records_by_method: Dict[str, List[str]] = defaultdict(list)
        self.records_by_category: Dict[FailureCategory, List[str]] = defaultdict(list)
        self._is_indexed = False

    def build_index(self) -> int:
        """Populate the graveyard from knowledge base statements, relationships, and markers."""
        self.records.clear()
        self.records_by_method.clear()
        self.records_by_category.clear()

        # 1. Ingest from Statements (LIMITATION & FAILURE_MODE)
        with self.query_engine._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM statements
                WHERE category IN ('LIMITATION', 'FAILURE_MODE')
                """
            )
            for r in cur.fetchall():
                d = dict(r)
                stmt_text = d["normalized_statement"]
                cat_str = d["category"].upper()
                fail_cat = (
                    FailureCategory.METHOD_LIMITATION
                    if cat_str == "LIMITATION"
                    else FailureCategory.EMPIRICAL_REGRESSION
                )
                
                # Check for computational bottlenecks
                if any(w in stmt_text.lower() for w in ["computational", "cost", "memory", "latency", "storage"]):
                    fail_cat = FailureCategory.COMPUTATIONAL_BOTTLENECK
                elif any(w in stmt_text.lower() for w in ["assumption", "assumes"]):
                    fail_cat = FailureCategory.ASSUMPTION_FAILURE

                rec_id = f"neg_stmt_{d['statement_id']}"
                rel_entities = json.loads(d["related_entity_ids_json"]) if d.get("related_entity_ids_json") else []
                concept_name = "scientific method"
                if rel_entities:
                    # Attempt to resolve entity name
                    cur.execute("SELECT canonical_name FROM entities WHERE entity_id = ?", (rel_entities[0],))
                    ent_row = cur.fetchone()
                    if ent_row:
                        concept_name = ent_row[0]

                record = NegativeKnowledgeRecord(
                    record_id=rec_id,
                    method_or_concept=concept_name,
                    failure_category=fail_cat,
                    evidence_type=NegativeEvidenceType.AUTHOR_STATED_LIMITATION,
                    description=stmt_text,
                    conditions_or_task="Empirical benchmark evaluation",
                    evidence_text=d["surface_text"],
                    paper_id=d["paper_id"],
                    chunk_id=d["chunk_id"],
                    attribution=AttributionType.AUTHOR_STATED,
                    confidence=float(d.get("confidence_score", 1.0)),
                )
                self._add_record(record)

        # 2. Ingest from Relationships (LIMITED_BY & CONTRADICTS)
        with self.query_engine._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT r.*, s.canonical_name AS source_name, t.canonical_name AS target_name
                FROM relationships r
                LEFT JOIN entities s ON r.source_id = s.entity_id
                LEFT JOIN entities t ON r.target_id = t.entity_id
                WHERE r.relation_type IN ('LIMITED_BY', 'CONTRADICTS')
                """
            )
            for r in cur.fetchall():
                d = dict(r)
                src_name = d.get("source_name") or d["source_id"]
                tgt_name = d.get("target_name") or d["target_id"]
                rel_type = d["relation_type"].upper()

                fail_cat = (
                    FailureCategory.CONTRADICTION
                    if rel_type == "CONTRADICTS"
                    else FailureCategory.COMPUTATIONAL_BOTTLENECK
                    if "computational" in tgt_name.lower() or "cost" in tgt_name.lower()
                    else FailureCategory.METHOD_LIMITATION
                )

                rec_id = f"neg_rel_{d['relationship_id']}"
                ev_text = d.get("surface_text") or f"{src_name} is {rel_type} {tgt_name}"
                record = NegativeKnowledgeRecord(
                    record_id=rec_id,
                    method_or_concept=src_name,
                    failure_category=fail_cat,
                    evidence_type=NegativeEvidenceType.AUTHOR_STATED_LIMITATION,
                    description=f"{src_name} is constrained by {tgt_name}",
                    conditions_or_task="Documented constraint",
                    evidence_text=ev_text,
                    paper_id=d["paper_id"],
                    chunk_id=d["chunk_id"],
                    attribution=AttributionType.AUTHOR_STATED,
                    confidence=float(d.get("confidence_score", 1.0)),
                )
                self._add_record(record)

        self._is_indexed = True
        logger.info("DeadEndGraveyard indexed %d negative knowledge records", len(self.records))
        return len(self.records)

    def _add_record(self, record: NegativeKnowledgeRecord) -> None:
        """Register a single negative knowledge record in dictionary and indexes."""
        self.records[record.record_id] = record
        norm_method = record.method_or_concept.strip().lower()
        self.records_by_method[norm_method].append(record.record_id)
        self.records_by_category[record.failure_category].append(record.record_id)

    def find_method_limitations(self, method_name: str) -> List[NegativeKnowledgeRecord]:
        """Query all documented limitations and failure modes for a specified method."""
        if not self._is_indexed:
            self.build_index()

        norm = method_name.strip().lower()
        matched_ids: Set[str] = set()

        for m_key, r_ids in self.records_by_method.items():
            if norm in m_key or m_key in norm:
                matched_ids.update(r_ids)

        return [self.records[rid] for rid in matched_ids]

    def check_contradiction_risk(
        self,
        method_name: str,
        problem_or_task: str,
    ) -> List[NegativeKnowledgeRecord]:
        """Evaluate if any negative knowledge or contradiction exists for the method/problem pair."""
        if not self._is_indexed:
            self.build_index()

        method_records = self.find_method_limitations(method_name)
        prob_lower = problem_or_task.strip().lower()

        flagged: List[NegativeKnowledgeRecord] = []
        for r in method_records:
            desc_lower = r.description.lower()
            if any(term in desc_lower for term in prob_lower.split() if len(term) > 3):
                flagged.append(r)

        return flagged

    def list_recurring_bottlenecks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Identify which limitations and bottlenecks occur most frequently across the corpus."""
        if not self._is_indexed:
            self.build_index()

        counts: Dict[str, int] = defaultdict(int)
        for r in self.records.values():
            counts[r.failure_category.value] += 1

        results = [{"category": cat, "count": cnt} for cat, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True)]
        return results[:limit]
