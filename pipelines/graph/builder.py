"""ResearchGraph Phase 6: Mechanistic Scientific Graph Builder.

Constructs an evidence-backed directed research graph connecting papers, methods,
problems, bottlenecks, assumptions, claims, results, and limitations.
Enforces strict referential integrity, duplicate edge deduplication, and
evidence support filtering.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from dataset.schemas.scientific_knowledge import AttributionType
from dataset.schemas.scientific_knowledge_base import (
    EvidenceSupportStatus,
    HumanVerificationStatus,
    StructuralValidityStatus,
)
from pipelines.graph.schema import (
    GraphEdge,
    GraphNode,
    GraphNodeType,
    GraphRelationPredicate,
    GraphVisualizationExport,
)
from pipelines.knowledge_base.query import KnowledgeBaseQueryEngine

logger = logging.getLogger(__name__)


@dataclass
class GraphBuildReport:
    """Summary statistics and validation metrics of the constructed graph."""
    total_nodes: int
    total_edges: int
    trusted_edges_count: int
    unsupported_edges_count: int
    nodes_by_type: Dict[str, int]
    edges_by_predicate: Dict[str, int]
    referential_integrity_pass_rate: float
    duplicate_edges_suppressed: int


class ResearchGraph:
    """In-memory typed adjacency graph with fast traversal and evidence indexing."""

    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        # Adjacency indexes: node_id -> list of edge_ids
        self.outgoing: Dict[str, List[str]] = defaultdict(list)
        self.incoming: Dict[str, List[str]] = defaultdict(list)
        # Type index: NodeType -> set of node_ids
        self.nodes_by_type: Dict[GraphNodeType, Set[str]] = defaultdict(set)
        # Predicate index: Predicate -> set of edge_ids
        self.edges_by_predicate: Dict[GraphRelationPredicate, Set[str]] = defaultdict(set)

    def add_node(self, node: GraphNode) -> None:
        """Add or update a node in the graph."""
        self.nodes[node.node_id] = node
        self.nodes_by_type[node.node_type].add(node.node_id)

    def add_edge(self, edge: GraphEdge) -> bool:
        """Add a verified edge to the graph after referential check."""
        if edge.source_id not in self.nodes:
            logger.warning("Edge source %s not found in graph nodes", edge.source_id)
            return False
        if edge.target_id not in self.nodes:
            logger.warning("Edge target %s not found in graph nodes", edge.target_id)
            return False

        self.edges[edge.edge_id] = edge
        self.outgoing[edge.source_id].append(edge.edge_id)
        self.incoming[edge.target_id].append(edge.edge_id)
        self.edges_by_predicate[edge.predicate].add(edge.edge_id)
        return True

    def export_visualization(self, trusted_only: bool = True) -> GraphVisualizationExport:
        """Generate frontend visualization export payload."""
        export_nodes = []
        for n in self.nodes.values():
            export_nodes.append({
                "id": n.node_id,
                "label": n.name,
                "type": n.node_type.value,
                "domain": n.domain or "General",
                "papers_count": len(n.paper_ids),
                "description": n.description or "",
            })

        export_edges = []
        for e in self.edges.values():
            if trusted_only and e.evidence_support != EvidenceSupportStatus.SUPPORTED:
                continue
            export_edges.append({
                "id": e.edge_id,
                "source": e.source_id,
                "target": e.target_id,
                "predicate": e.predicate.value,
                "is_directed": e.is_directed,
                "confidence": e.confidence,
                "evidence_support": e.evidence_support.value,
                "paper_id": e.paper_id,
                "chunk_id": e.chunk_id,
                "evidence_text": e.evidence_text or "",
            })

        return GraphVisualizationExport(
            nodes=export_nodes,
            edges=export_edges,
            metadata={
                "total_nodes": len(export_nodes),
                "total_edges": len(export_edges),
                "trusted_only": trusted_only,
            },
        )


class ResearchGraphBuilder:
    """Builds the ResearchGraph from canonical database records."""

    def __init__(self, query_engine: Optional[KnowledgeBaseQueryEngine] = None):
        self.query_engine = query_engine or KnowledgeBaseQueryEngine()

    def build_graph(
        self,
        include_unsupported_edges: bool = True,
        max_papers: Optional[int] = None,
    ) -> Tuple[ResearchGraph, GraphBuildReport]:
        """Construct the typed scientific research graph from SQLite knowledge base."""
        graph = ResearchGraph()
        seen_edges: Set[Tuple[str, str, str, str, str]] = set()
        duplicates_count = 0
        invalid_endpoints_count = 0

        # 1. Ingest Canonical Papers
        with self.query_engine._get_connection() as conn:
            cur = conn.cursor()
            query_limit = f"LIMIT {max_papers}" if max_papers else ""
            cur.execute(f"SELECT * FROM papers {query_limit}")
            paper_rows = cur.fetchall()

            for r in paper_rows:
                p_dict = dict(r)
                node = GraphNode(
                    node_id=p_dict["paper_id"],
                    node_type=GraphNodeType.PAPER,
                    name=p_dict["title"],
                    description=p_dict.get("abstract"),
                    paper_ids=[p_dict["paper_id"]],
                    attributes={
                        "doi": p_dict.get("doi"),
                        "year": p_dict.get("publication_year"),
                        "venue": json.loads(p_dict["venue_json"]) if p_dict.get("venue_json") else None,
                    },
                )
                graph.add_node(node)

        # 2. Ingest Canonical Entities
        with self.query_engine._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM entities")
            entity_rows = cur.fetchall()

            for r in entity_rows:
                e_dict = dict(r)
                cat_str = e_dict["category"].upper()
                try:
                    node_type = GraphNodeType(cat_str)
                except ValueError:
                    node_type = GraphNodeType.METHOD

                p_ids = json.loads(e_dict["paper_ids_json"]) if e_dict.get("paper_ids_json") else []
                c_ids = json.loads(e_dict["chunk_ids_json"]) if e_dict.get("chunk_ids_json") else []

                node = GraphNode(
                    node_id=e_dict["entity_id"],
                    node_type=node_type,
                    name=e_dict["canonical_name"],
                    description=e_dict.get("description"),
                    paper_ids=p_ids,
                    chunk_ids=c_ids,
                    attributes={
                        "aliases": json.loads(e_dict["aliases_json"]) if e_dict.get("aliases_json") else [],
                        "mentions_count": e_dict.get("mentions_count", 1),
                    },
                )
                graph.add_node(node)

        # 3. Ingest Canonical Statements
        with self.query_engine._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM statements")
            stmt_rows = cur.fetchall()

            for r in stmt_rows:
                s_dict = dict(r)
                cat_str = s_dict["category"].upper()
                try:
                    node_type = GraphNodeType(cat_str)
                except ValueError:
                    node_type = GraphNodeType.STATEMENT

                rel_entities = json.loads(s_dict["related_entity_ids_json"]) if s_dict.get("related_entity_ids_json") else []

                node = GraphNode(
                    node_id=s_dict["statement_id"],
                    node_type=node_type,
                    name=s_dict["normalized_statement"][:80],
                    description=s_dict["normalized_statement"],
                    paper_ids=[s_dict["paper_id"]],
                    chunk_ids=[s_dict["chunk_id"]],
                    attributes={
                        "category": s_dict["category"],
                        "confidence_score": s_dict.get("confidence_score", 1.0),
                        "related_entity_ids": rel_entities,
                    },
                )
                graph.add_node(node)

                # Add Paper -> Statement edge (CONTAINS)
                if s_dict["paper_id"] in graph.nodes:
                    paper_edge = GraphEdge(
                        edge_id=f"edge_contain_{s_dict['statement_id']}",
                        source_id=s_dict["paper_id"],
                        target_id=s_dict["statement_id"],
                        predicate=GraphRelationPredicate.CONTAINS,
                        is_directed=True,
                        confidence=1.0,
                        paper_id=s_dict["paper_id"],
                        chunk_id=s_dict["chunk_id"],
                        evidence_text=s_dict["surface_text"],
                        attribution=AttributionType.AUTHOR_STATED,
                        structural_validity=StructuralValidityStatus.STRUCTURALLY_VALID,
                        evidence_support=EvidenceSupportStatus.SUPPORTED,
                        human_verification=HumanVerificationStatus.VERIFIED,
                    )
                    graph.add_edge(paper_edge)

                # Add Statement -> Entity links
                for ent_id in rel_entities:
                    if ent_id in graph.nodes:
                        stmt_edge = GraphEdge(
                            edge_id=f"edge_stmt_ent_{s_dict['statement_id']}_{ent_id}",
                            source_id=s_dict["statement_id"],
                            target_id=ent_id,
                            predicate=GraphRelationPredicate.REPORTS,
                            is_directed=True,
                            confidence=s_dict.get("confidence_score", 1.0),
                            paper_id=s_dict["paper_id"],
                            chunk_id=s_dict["chunk_id"],
                            evidence_text=s_dict["surface_text"],
                            attribution=AttributionType.AUTHOR_STATED,
                            structural_validity=StructuralValidityStatus.STRUCTURALLY_VALID,
                            evidence_support=EvidenceSupportStatus.SUPPORTED,
                        )
                        graph.add_edge(stmt_edge)

        # 4. Ingest Semantic Relationships
        trusted_count = 0
        unsupported_count = 0

        with self.query_engine._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM relationships")
            rel_rows = cur.fetchall()

            for r in rel_rows:
                r_dict = dict(r)
                ev_support_str = r_dict.get("evidence_support", "NOT_ASSESSED")
                try:
                    ev_status = EvidenceSupportStatus(ev_support_str)
                except ValueError:
                    ev_status = EvidenceSupportStatus.NOT_ASSESSED

                if ev_status == EvidenceSupportStatus.SUPPORTED:
                    trusted_count += 1
                else:
                    unsupported_count += 1

                if not include_unsupported_edges and ev_status != EvidenceSupportStatus.SUPPORTED:
                    continue

                # Deduplication check
                dedup_key = (
                    r_dict["source_id"],
                    r_dict["target_id"],
                    r_dict["relation_type"],
                    r_dict["paper_id"],
                    r_dict["chunk_id"],
                )
                if dedup_key in seen_edges:
                    duplicates_count += 1
                    continue
                seen_edges.add(dedup_key)

                # Check referential endpoints
                if r_dict["source_id"] not in graph.nodes or r_dict["target_id"] not in graph.nodes:
                    invalid_endpoints_count += 1
                    continue

                try:
                    pred = GraphRelationPredicate(r_dict["relation_type"].upper())
                except ValueError:
                    pred = GraphRelationPredicate.ADDRESSES

                edge = GraphEdge(
                    edge_id=r_dict["relationship_id"],
                    source_id=r_dict["source_id"],
                    target_id=r_dict["target_id"],
                    predicate=pred,
                    is_directed=bool(r_dict.get("is_directed", 1)),
                    confidence=float(r_dict.get("confidence_score", 1.0)),
                    paper_id=r_dict["paper_id"],
                    chunk_id=r_dict["chunk_id"],
                    evidence_text=r_dict.get("evidence_text") or r_dict.get("surface_text"),
                    start_char=r_dict.get("start_char"),
                    end_char=r_dict.get("end_char"),
                    attribution=AttributionType.AUTHOR_STATED,
                    structural_validity=StructuralValidityStatus.STRUCTURALLY_VALID,
                    evidence_support=ev_status,
                    human_verification=HumanVerificationStatus(r_dict.get("human_verification", "PENDING")),
                    correction_notes=r_dict.get("correction_notes"),
                    extractor_version=r_dict.get("extraction_version", "v0.4.1"),
                )
                graph.add_edge(edge)

        # 5. Build Report
        nodes_by_type = {t.value: len(ids) for t, ids in graph.nodes_by_type.items()}
        edges_by_pred = {p.value: len(ids) for p, ids in graph.edges_by_predicate.items()}
        total_edges = len(graph.edges)
        integrity_rate = 1.0 if (total_edges + invalid_endpoints_count) == 0 else (
            total_edges / (total_edges + invalid_endpoints_count)
        )

        report = GraphBuildReport(
            total_nodes=len(graph.nodes),
            total_edges=total_edges,
            trusted_edges_count=sum(
                1 for e in graph.edges.values() if e.evidence_support == EvidenceSupportStatus.SUPPORTED
            ),
            unsupported_edges_count=sum(
                1 for e in graph.edges.values() if e.evidence_support != EvidenceSupportStatus.SUPPORTED
            ),
            nodes_by_type=nodes_by_type,
            edges_by_predicate=edges_by_pred,
            referential_integrity_pass_rate=round(integrity_rate, 4),
            duplicate_edges_suppressed=duplicates_count,
        )

        return graph, report
