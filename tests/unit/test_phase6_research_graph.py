"""Unit tests for Phase 6: Mechanistic Scientific Knowledge Graph.

Verifies:
1. Typed node and edge creation with validation.
2. Graph builder ingestion from SQLite knowledge base.
3. Referential integrity and duplicate edge suppression.
4. Default trusted edge policy excluding unsupported relationships.
5. Neighborhood extraction at depths 1 and 2.
6. Multi-hop path finding and evidence chain collection.
7. Visualization-ready graph export format.
"""

from __future__ import annotations

import pytest

from dataset.schemas.scientific_knowledge import AttributionType
from dataset.schemas.scientific_knowledge_base import (
    EvidenceSupportStatus,
    HumanVerificationStatus,
    StructuralValidityStatus,
)
from pipelines.graph.builder import (
    ResearchGraph,
    ResearchGraphBuilder,
)
from pipelines.graph.schema import (
    GraphEdge,
    GraphNode,
    GraphNodeType,
    GraphRelationPredicate,
)
from pipelines.graph.traversal import GraphTraversalEngine


class TestResearchGraphSchema:
    """Test suite for graph node and edge primitives."""

    def test_node_creation(self):
        node = GraphNode(
            node_id="kb_ent_method_01",
            node_type=GraphNodeType.METHOD,
            name="Federated Learning",
            description="Collaborative decentralized optimization",
            paper_ids=["rg_doi_01"],
            domain="Distributed Systems",
        )
        assert node.node_id == "kb_ent_method_01"
        assert node.node_type == GraphNodeType.METHOD
        assert node.name == "Federated Learning"

    def test_edge_referential_integrity(self):
        graph = ResearchGraph()
        n1 = GraphNode(node_id="n1", node_type=GraphNodeType.METHOD, name="Method A")
        n2 = GraphNode(node_id="n2", node_type=GraphNodeType.PROBLEM, name="Problem B")
        graph.add_node(n1)
        graph.add_node(n2)

        valid_edge = GraphEdge(
            edge_id="e1",
            source_id="n1",
            target_id="n2",
            predicate=GraphRelationPredicate.ADDRESSES,
            evidence_support=EvidenceSupportStatus.SUPPORTED,
        )
        assert graph.add_edge(valid_edge) is True

        dangling_edge = GraphEdge(
            edge_id="e2",
            source_id="n1",
            target_id="n_missing",
            predicate=GraphRelationPredicate.ADDRESSES,
        )
        assert graph.add_edge(dangling_edge) is False


class TestResearchGraphBuilderFromDB:
    """Test suite for building the graph from the persisted v0.5.1 database."""

    def test_build_graph_from_kb(self):
        builder = ResearchGraphBuilder()
        graph, report = builder.build_graph(include_unsupported_edges=True, max_papers=50)

        assert report.total_nodes > 0
        assert report.total_edges > 0
        assert report.referential_integrity_pass_rate == 1.0

        # Verify papers, entities, and statements exist as graph nodes
        assert GraphNodeType.PAPER.value in report.nodes_by_type
        assert GraphNodeType.METHOD.value in report.nodes_by_type
        assert GraphNodeType.STATEMENT.value in report.nodes_by_type or "CLAIM" in report.nodes_by_type or "RESULT" in report.nodes_by_type

        # Verify the 9 Cartesian-product relationships from v0.5.1 are marked UNSUPPORTED
        unsupported_edges = [
            e for e in graph.edges.values()
            if e.evidence_support == EvidenceSupportStatus.UNSUPPORTED
        ]
        assert len(unsupported_edges) == 9

        # In trusted export, unsupported edges must be omitted
        trusted_export = graph.export_visualization(trusted_only=True)
        unsupported_in_export = [
            e for e in trusted_export.edges
            if e.get("evidence_support") == "UNSUPPORTED"
        ]
        assert len(unsupported_in_export) == 0

        # In diagnostic export, they are preserved
        all_export = graph.export_visualization(trusted_only=False)
        assert any(e.get("evidence_support") == "UNSUPPORTED" for e in all_export.edges)


class TestGraphTraversalEngine:
    """Test suite for neighborhoods, paths, and evidence tracing."""

    @pytest.fixture
    def sample_traversal_graph(self) -> GraphTraversalEngine:
        graph = ResearchGraph()
        n_fl = GraphNode(node_id="n_fl", node_type=GraphNodeType.METHOD, name="Federated Learning")
        n_priv = GraphNode(node_id="n_priv", node_type=GraphNodeType.PROBLEM, name="Data Privacy")
        n_hc = GraphNode(node_id="n_hc", node_type=GraphNodeType.TASK, name="Clinical Healthcare")
        n_diag = GraphNode(node_id="n_diag", node_type=GraphNodeType.METHOD, name="Diagnostic Model")

        for n in [n_fl, n_priv, n_hc, n_diag]:
            graph.add_node(n)

        # n_fl --ADDRESSES--> n_priv (SUPPORTED)
        e1 = GraphEdge(
            edge_id="e1",
            source_id="n_fl",
            target_id="n_priv",
            predicate=GraphRelationPredicate.ADDRESSES,
            evidence_support=EvidenceSupportStatus.SUPPORTED,
            evidence_text="Federated learning ensures privacy in patient records",
            paper_id="rg_doi_01",
            chunk_id="chk_01",
        )
        # n_priv --LIMITED_BY--> n_hc (SUPPORTED)
        e2 = GraphEdge(
            edge_id="e2",
            source_id="n_priv",
            target_id="n_hc",
            predicate=GraphRelationPredicate.LIMITED_BY,
            evidence_support=EvidenceSupportStatus.SUPPORTED,
            evidence_text="Healthcare applications are limited by strict regulatory privacy requirements",
            paper_id="rg_doi_02",
            chunk_id="chk_02",
        )
        # n_fl --IMPROVES--> n_diag (UNSUPPORTED - Cartesian artifact)
        e3 = GraphEdge(
            edge_id="e3",
            source_id="n_fl",
            target_id="n_diag",
            predicate=GraphRelationPredicate.IMPROVES,
            evidence_support=EvidenceSupportStatus.UNSUPPORTED,
            evidence_text="Row 1 Federated Learning Row 9 Diagnostic Model",
            correction_notes="Cartesian table artifact",
            paper_id="rg_doi_03",
            chunk_id="chk_03",
        )

        for e in [e1, e2, e3]:
            graph.add_edge(e)

        return GraphTraversalEngine(graph)

    def test_neighborhood_depth_1_and_2(self, sample_traversal_graph):
        engine = sample_traversal_graph

        # Depth 1 from n_fl (trusted only)
        hood1 = engine.get_neighborhood("n_fl", depth=1, trusted_only=True)
        node_ids_1 = {n.node_id for n in hood1.nodes}
        assert "n_fl" in node_ids_1
        assert "n_priv" in node_ids_1
        assert "n_diag" not in node_ids_1  # Omitted because e3 is UNSUPPORTED

        # Depth 2 from n_fl (trusted only)
        hood2 = engine.get_neighborhood("n_fl", depth=2, trusted_only=True)
        node_ids_2 = {n.node_id for n in hood2.nodes}
        assert "n_hc" in node_ids_2

    def test_path_finding_and_evidence_chain(self, sample_traversal_graph):
        engine = sample_traversal_graph
        paths = engine.find_paths("n_fl", "n_hc", max_depth=3, trusted_only=True)
        assert len(paths) == 1
        path = paths[0]
        assert path.node_sequence == ["n_fl", "n_priv", "n_hc"]
        assert path.predicate_sequence == ["ADDRESSES", "LIMITED_BY"]
        assert len(path.evidence_chain) == 2
        assert path.is_trusted is True

    def test_trace_edge_evidence(self, sample_traversal_graph):
        engine = sample_traversal_graph
        trace = engine.trace_edge_evidence("e1")
        assert trace is not None
        assert trace["edge_id"] == "e1"
        assert trace["predicate"] == "ADDRESSES"
        assert trace["evidence_support"] == "SUPPORTED"
        assert "Federated learning ensures privacy" in trace["evidence_text"]
