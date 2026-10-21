"""ResearchGraph Phase 6: Graph Traversal & Evidence Tracing Engine.

Supports:
1. Multi-hop path finding between distant concepts.
2. Neighborhood subgraphs with trusted-edge filtering.
3. Complete evidence provenance tracing for each edge.
4. Swanson-style discovery traversal ($A \rightarrow B \rightarrow C$).
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from dataset.schemas.scientific_knowledge_base import EvidenceSupportStatus
from pipelines.graph.builder import ResearchGraph
from pipelines.graph.schema import (
    GraphEdge,
    GraphNeighborhood,
    GraphNode,
    GraphNodeType,
    GraphPath,
    GraphRelationPredicate,
)

logger = logging.getLogger(__name__)


class GraphTraversalEngine:
    """Traverses the research graph with strict evidence support and provenance tracking."""

    def __init__(self, graph: ResearchGraph):
        self.graph = graph

    def get_neighborhood(
        self,
        node_id: str,
        depth: int = 1,
        trusted_only: bool = True,
    ) -> GraphNeighborhood:
        """Extract a k-hop subgraph surrounding the specified focal node."""
        if node_id not in self.graph.nodes:
            raise KeyError(f"Node {node_id} not found in research graph.")

        visited_nodes: Set[str] = {node_id}
        visited_edges: Set[str] = set()
        queue: deque[Tuple[str, int]] = deque([(node_id, 0)])

        while queue:
            curr_id, curr_depth = queue.popleft()
            if curr_depth >= depth:
                continue

            # Check outgoing edges
            for edge_id in self.graph.outgoing.get(curr_id, []):
                edge = self.graph.edges[edge_id]
                if trusted_only and edge.evidence_support != EvidenceSupportStatus.SUPPORTED:
                    continue
                visited_edges.add(edge_id)
                target_id = edge.target_id
                if target_id not in visited_nodes:
                    visited_nodes.add(target_id)
                    queue.append((target_id, curr_depth + 1))

            # Check incoming edges
            for edge_id in self.graph.incoming.get(curr_id, []):
                edge = self.graph.edges[edge_id]
                if trusted_only and edge.evidence_support != EvidenceSupportStatus.SUPPORTED:
                    continue
                visited_edges.add(edge_id)
                source_id = edge.source_id
                if source_id not in visited_nodes:
                    visited_nodes.add(source_id)
                    queue.append((source_id, curr_depth + 1))

        nodes = [self.graph.nodes[nid] for nid in visited_nodes]
        edges = [self.graph.edges[eid] for eid in visited_edges]

        return GraphNeighborhood(
            center_node_id=node_id,
            depth=depth,
            nodes=nodes,
            edges=edges,
            total_neighbors=len(nodes) - 1,
        )

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3,
        trusted_only: bool = True,
        max_paths: int = 10,
    ) -> List[GraphPath]:
        """Find directed paths between two scientific nodes using BFS."""
        if source_id not in self.graph.nodes or target_id not in self.graph.nodes:
            return []

        paths_found: List[GraphPath] = []
        # Queue contains: (current_node, [edge_ids], [node_ids])
        queue: deque[Tuple[str, List[str], List[str]]] = deque([(source_id, [], [source_id])])

        while queue and len(paths_found) < max_paths:
            curr_node, current_edges, current_path = queue.popleft()

            if curr_node == target_id and len(current_edges) > 0:
                edge_objects = [self.graph.edges[eid] for eid in current_edges]
                predicates = [e.predicate.value for e in edge_objects]
                evidence = [e.evidence_text or "" for e in edge_objects]
                is_all_trusted = all(e.evidence_support == EvidenceSupportStatus.SUPPORTED for e in edge_objects)

                paths_found.append(
                    GraphPath(
                        source_node_id=source_id,
                        target_node_id=target_id,
                        path_length=len(current_edges),
                        node_sequence=current_path,
                        predicate_sequence=predicates,
                        edges=edge_objects,
                        evidence_chain=evidence,
                        is_trusted=is_all_trusted,
                    )
                )
                continue

            if len(current_edges) >= max_depth:
                continue

            for edge_id in self.graph.outgoing.get(curr_node, []):
                edge = self.graph.edges[edge_id]
                if trusted_only and edge.evidence_support != EvidenceSupportStatus.SUPPORTED:
                    continue
                nxt_node = edge.target_id
                # Avoid cycles in path
                if nxt_node not in current_path:
                    queue.append((
                        nxt_node,
                        current_edges + [edge_id],
                        current_path + [nxt_node],
                    ))

        return paths_found

    def trace_edge_evidence(self, edge_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full provenance and evidence verification details for a graph edge."""
        edge = self.graph.edges.get(edge_id)
        if not edge:
            return None

        src_node = self.graph.nodes.get(edge.source_id)
        tgt_node = self.graph.nodes.get(edge.target_id)

        return {
            "edge_id": edge.edge_id,
            "source": {
                "node_id": edge.source_id,
                "name": src_node.name if src_node else "",
                "type": src_node.node_type.value if src_node else "",
            },
            "predicate": edge.predicate.value,
            "target": {
                "node_id": edge.target_id,
                "name": tgt_node.name if tgt_node else "",
                "type": tgt_node.node_type.value if tgt_node else "",
            },
            "paper_id": edge.paper_id,
            "chunk_id": edge.chunk_id,
            "evidence_text": edge.evidence_text,
            "start_char": edge.start_char,
            "end_char": edge.end_char,
            "attribution": edge.attribution.value,
            "structural_validity": edge.structural_validity.value,
            "evidence_support": edge.evidence_support.value,
            "human_verification": edge.human_verification.value,
            "correction_notes": edge.correction_notes,
            "extractor_version": edge.extractor_version,
        }

    def list_nodes_by_type(self, node_type: GraphNodeType) -> List[GraphNode]:
        """Retrieve all registered nodes of a given scientific category."""
        node_ids = self.graph.nodes_by_type.get(node_type, set())
        return [self.graph.nodes[nid] for nid in sorted(node_ids)]
