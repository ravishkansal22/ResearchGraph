"""ResearchGraph Phase 8: Research-Gap and Novelty Verification Engine.

Rigorous epistemic evaluation determining whether a candidate research gap is
genuinely supported by literature rather than a simple retrieval artifact.
Enforces the mandatory rule: Absence from current corpus does not establish novelty!
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from pipelines.embeddings.bm25 import tokenize
from pipelines.embeddings.retrieval import ScientificRetrievalEngine
from pipelines.gap_verification.schema import (
    GapStatus,
    RelatedWorkFinding,
    RelatedWorkRelation,
    ResearchGapDossier,
    SearchAuditRecord,
)
from pipelines.knowledge_base.query import KnowledgeBaseQueryEngine

logger = logging.getLogger(__name__)


class ResearchGapVerifier:
    """Verifies candidate research gaps against literature, statements, and trusted relationships."""

    def __init__(
        self,
        retrieval_engine: Optional[ScientificRetrievalEngine] = None,
        kb_query_engine: Optional[KnowledgeBaseQueryEngine] = None,
    ):
        self.retrieval = retrieval_engine or ScientificRetrievalEngine()
        self.kb_query = kb_query_engine or KnowledgeBaseQueryEngine()

    def verify_gap(
        self,
        proposed_gap: str,
        target_domains: Optional[List[str]] = None,
        top_search_k: int = 10,
    ) -> ResearchGapDossier:
        """Execute the multi-stage research gap verification workflow."""
        audit_trail: List[SearchAuditRecord] = []
        tokens = tokenize(proposed_gap)
        key_concepts = tokens[:6] if len(tokens) >= 6 else tokens
        domains = target_domains or ["General Artificial Intelligence"]

        # 1. Lexical BM25 Search
        t0 = time.perf_counter()
        bm25_hits = self.retrieval.retrieve_lexical(proposed_gap, top_k=top_search_k)
        t_bm25 = (time.perf_counter() - t0) * 1000.0

        top_bm25_score = bm25_hits[0].score if bm25_hits else 0.0
        audit_trail.append(
            SearchAuditRecord(
                search_strategy="bm25",
                query_string=proposed_gap,
                hits_count=len(bm25_hits),
                top_score=round(top_bm25_score, 4),
                execution_time_ms=round(t_bm25, 2),
            )
        )

        # 2. Dense Semantic Search
        t0 = time.perf_counter()
        dense_hits = self.retrieval.retrieve_dense(proposed_gap, top_k=top_search_k)
        t_dense = (time.perf_counter() - t0) * 1000.0

        top_dense_score = dense_hits[0].score if dense_hits else 0.0
        audit_trail.append(
            SearchAuditRecord(
                search_strategy="dense_vector",
                query_string=proposed_gap,
                hits_count=len(dense_hits),
                top_score=round(top_dense_score, 4),
                execution_time_ms=round(t_dense, 2),
            )
        )

        # 3. Structured Knowledge Base Search (Statements & Relationships)
        t0 = time.perf_counter()
        kb_matches: List[Dict[str, Any]] = []
        with self.kb_query._get_connection() as conn:
            cur = conn.cursor()
            # Search for statements discussing limitations or failure modes
            cur.execute(
                """
                SELECT * FROM statements
                WHERE category IN ('LIMITATION', 'FAILURE_MODE', 'RESULT', 'CLAIM')
                """
            )
            for r in cur.fetchall():
                d = dict(r)
                text = d.get("normalized_statement", "").lower()
                overlap = sum(1 for tok in tokens if tok in text)
                if overlap >= 2:
                    kb_matches.append(d)

        t_kb = (time.perf_counter() - t0) * 1000.0
        audit_trail.append(
            SearchAuditRecord(
                search_strategy="kb_statements",
                query_string=proposed_gap,
                hits_count=len(kb_matches),
                top_score=1.0 if kb_matches else 0.0,
                execution_time_ms=round(t_kb, 2),
            )
        )

        # 4. Analyze Findings: Distinguish direct precedents, contradictions, and supporting evidence
        supporting: List[RelatedWorkFinding] = []
        opposing: List[RelatedWorkFinding] = []

        # Analyze BM25 and Dense hits
        all_hits = {h.record_id: h for h in (bm25_hits + dense_hits)}.values()
        for hit in all_hits:
            text_lower = hit.text.lower()
            paper_id = hit.metadata.get("paper_id", "unknown_paper")
            paper_info = self.kb_query.get_paper(paper_id)
            title = paper_info["title"] if paper_info else f"Paper {paper_id}"

            # Check if hit contains explicit indication that the problem is already solved
            has_method_and_prob = sum(1 for tok in tokens[:3] if tok in text_lower) >= 2
            is_solution = any(kw in text_lower for kw in ["we propose", "we present", "we demonstrate", "our method achieves"])

            if has_method_and_prob and is_solution and hit.score > 0.65:
                opposing.append(
                    RelatedWorkFinding(
                        paper_id=paper_id,
                        paper_title=title,
                        chunk_id=hit.record_id,
                        relationship=RelatedWorkRelation.DIRECT_PRECEDENT,
                        excerpt=hit.text[:250] + "...",
                        relevance_score=hit.score,
                        analysis="Direct prior work: Documented approach already implements analogous mechanism on this problem.",
                    )
                )
            elif any(kw in text_lower for kw in ["remains open", "challenging", "unsolved", "bottleneck", "limitation", "lack of"]):
                supporting.append(
                    RelatedWorkFinding(
                        paper_id=paper_id,
                        paper_title=title,
                        chunk_id=hit.record_id,
                        relationship=RelatedWorkRelation.SUPPORTING_EVIDENCE,
                        excerpt=hit.text[:250] + "...",
                        relevance_score=hit.score,
                        analysis="Supporting evidence: Author explicitly states this challenge or constraint is an open research bottleneck.",
                    )
                )

        # Analyze KB statements
        for stmt in kb_matches:
            category = stmt.get("category")
            p_id = stmt.get("paper_id", "")
            paper_info = self.kb_query.get_paper(p_id)
            title = paper_info["title"] if paper_info else f"Paper {p_id}"
            stmt_text = stmt.get("normalized_statement", "")

            if category in {"LIMITATION", "FAILURE_MODE"}:
                supporting.append(
                    RelatedWorkFinding(
                        paper_id=p_id,
                        paper_title=title,
                        chunk_id=stmt.get("chunk_id"),
                        relationship=RelatedWorkRelation.SUPPORTING_EVIDENCE,
                        excerpt=stmt_text,
                        relevance_score=0.90,
                        analysis=f"Evidence from structured {category} statement confirming existing method constraints.",
                    )
                )
            elif category == "RESULT" and any(neg in stmt_text.lower() for neg in ["failed", "degraded", "ineffective", "did not improve"]):
                opposing.append(
                    RelatedWorkFinding(
                        paper_id=p_id,
                        paper_title=title,
                        chunk_id=stmt.get("chunk_id"),
                        relationship=RelatedWorkRelation.CONTRADICTORY_FINDING,
                        excerpt=stmt_text,
                        relevance_score=0.85,
                        analysis="Contradictory result: Literature documents that this direction suffered empirical degradation or failure.",
                    )
                )

        # 5. Determine Epistemic Status
        corpus_limitations = (
            "Current analysis is strictly bounded by the 50 canonical papers and 3,582 text chunks in the ResearchGraph "
            "v0.1-v0.5 local corpus. Absence of prior work in this corpus does not constitute proof of global novelty. "
            "External indexing via OpenAlex, arXiv, Crossref, and PubMed is required before declaring absolute novelty."
        )

        additional_searches = [
            f"OpenAlex query: '{proposed_gap}'",
            f"arXiv cs.AI / cs.LG title/abstract search: '{' '.join(key_concepts[:3])}'",
            f"Semantic Scholar citation graph traversal for top supporting papers",
        ]

        if opposing:
            direct_precedents = [f for f in opposing if f.relationship == RelatedWorkRelation.DIRECT_PRECEDENT]
            if direct_precedents:
                final_status = GapStatus.EVIDENCE_AGAINST_GAP
                rationale = (
                    f"Evidence against gap: Found {len(direct_precedents)} direct prior precedents in the indexed corpus "
                    f"describing equivalent methodology for this task (e.g. Paper '{direct_precedents[0].paper_title}')."
                )
            else:
                final_status = GapStatus.REQUIRES_REVIEW
                rationale = (
                    f"Contradictory findings or empirical regressions located in indexed literature. "
                    f"Requires senior domain adjudication before pursuing."
                )
        elif not supporting and len(all_hits) < 2:
            final_status = GapStatus.INSUFFICIENT_EVIDENCE
            rationale = (
                "Insufficient evidence in local corpus: Fewer than 2 relevant passages retrieved. "
                "The current 50-paper corpus does not provide sufficient empirical density to evaluate this gap."
            )
        else:
            final_status = GapStatus.POSSIBLE_GAP
            rationale = (
                f"Identified as a possible research gap: Supporting literature confirms the bottleneck exists "
                f"({len(supporting)} supporting evidence items), and no direct precedent was identified within "
                f"the indexed 50-paper corpus. Subject to stated corpus boundary limitations."
            )

        dossier_id = f"gap_dos_{hashlib.sha256(proposed_gap.encode()).hexdigest()[:12]}"

        return ResearchGapDossier(
            dossier_id=dossier_id,
            proposed_gap_statement=proposed_gap,
            key_concepts=key_concepts,
            domains_involved=domains,
            search_audit_trail=audit_trail,
            supporting_evidence=supporting[:5],
            opposing_or_prior_work=opposing[:5],
            corpus_coverage_limitations=corpus_limitations,
            confidence_rationale=rationale,
            additional_searches_required=additional_searches,
            final_status=final_status,
        )
