"""Mechanistic Knowledge Graph Query & Visualization Endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pipelines.graph.builder import ResearchGraph, ResearchGraphBuilder
from pipelines.graph.schema import (
    GraphNeighborhood,
    GraphPath,
    GraphVisualizationExport,
)
from pipelines.graph.traversal import GraphTraversalEngine

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])

_graph: ResearchGraph | None = None
_traversal: GraphTraversalEngine | None = None


def get_graph_traversal() -> GraphTraversalEngine:
    global _graph, _traversal
    if _traversal is None:
        builder = ResearchGraphBuilder()
        _graph, _ = builder.build_graph(include_unsupported_edges=True)
        _traversal = GraphTraversalEngine(_graph)
    return _traversal


@router.get("/neighborhood/{node_id}", response_model=GraphNeighborhood)
def get_node_neighborhood(
    node_id: str,
    depth: int = Query(default=1, ge=1, le=3),
    trusted_only: bool = Query(default=True, description="Exclude unsupported relationships"),
    traversal: GraphTraversalEngine = Depends(get_graph_traversal),
) -> GraphNeighborhood:
    """Retrieve the k-hop subgraph around a focal scientific node."""
    try:
        return traversal.get_neighborhood(node_id=node_id, depth=depth, trusted_only=trusted_only)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/paths", response_model=list[GraphPath])
def find_graph_paths(
    source_id: str = Query(..., description="Source node ID"),
    target_id: str = Query(..., description="Target node ID"),
    max_depth: int = Query(default=3, ge=1, le=5),
    trusted_only: bool = Query(default=True),
    traversal: GraphTraversalEngine = Depends(get_graph_traversal),
) -> list[GraphPath]:
    """Find directed multi-hop paths connecting two scientific concepts."""
    paths: list[GraphPath] = traversal.find_paths(
        source_id=source_id,
        target_id=target_id,
        max_depth=max_depth,
        trusted_only=trusted_only,
    )
    return paths


@router.get("/edges/{edge_id}/trace")
def trace_edge_evidence(
    edge_id: str,
    traversal: GraphTraversalEngine = Depends(get_graph_traversal),
) -> dict[str, Any]:
    """Trace a relationship edge back to cited text, offsets, and status."""
    trace = traversal.trace_edge_evidence(edge_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Edge {edge_id} not found.")
    res: dict[str, Any] = dict(trace)
    return res


@router.get("/export", response_model=GraphVisualizationExport)
def export_visualization(
    trusted_only: bool = Query(default=True, description="Include only evidence-supported edges"),
    traversal: GraphTraversalEngine = Depends(get_graph_traversal),
) -> GraphVisualizationExport:
    """Export the graph for interactive frontend rendering."""
    return traversal.graph.export_visualization(trusted_only=trusted_only)
