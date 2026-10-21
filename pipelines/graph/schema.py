"""ResearchGraph Phase 6: Typed Scientific Knowledge Graph Schema.

Defines typed nodes, semantic relation predicates, provenance attributes,
evidence-support states, and visualization-ready export structures.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from dataset.schemas.scientific_knowledge import (
    AttributionType,
    EvidenceSpan,
    ExtractionProvenance,
    ScientificEntityType,
    ScientificRelationType,
    ScientificStatementType,
    ValidationStatus,
)
from dataset.schemas.scientific_knowledge_base import (
    EvidenceSupportStatus,
    HumanVerificationStatus,
    StructuralValidityStatus,
)


class GraphNodeType(str, Enum):
    """Scientific ontology node categories."""
    PAPER = "PAPER"
    METHOD = "METHOD"
    PROBLEM = "PROBLEM"
    BOTTLENECK = "BOTTLENECK"
    TASK = "TASK"
    DATASET = "DATASET"
    METRIC = "METRIC"
    ASSUMPTION = "ASSUMPTION"
    LIMITATION = "LIMITATION"
    FUTURE_DIRECTION = "FUTURE_DIRECTION"
    CLAIM = "CLAIM"
    RESULT = "RESULT"
    STATEMENT = "STATEMENT"
    CHUNK = "CHUNK"


class GraphRelationPredicate(str, Enum):
    """Mechanistic and operational predicates between scientific nodes."""
    ADDRESSES = "ADDRESSES"
    LIMITED_BY = "LIMITED_BY"
    EVALUATED_ON = "EVALUATED_ON"
    ASSUMES = "ASSUMES"
    IMPROVES = "IMPROVES"
    CONTRADICTS = "CONTRADICTS"
    EXTENDS = "EXTENDS"
    DERIVED_FROM = "DERIVED_FROM"
    USES = "USES"
    REPORTS = "REPORTS"
    SUGGESTS = "SUGGESTS"
    CONTAINS = "CONTAINS"
    MENTIONS = "MENTIONS"
    ANALOGOUS_TO = "ANALOGOUS_TO"


class GraphNode(BaseModel):
    """Typed scientific entity, passage, or document node in the research graph."""
    node_id: str = Field(..., description="Unique node identifier (e.g. kb_ent_xxx, rg_doi_xxx)")
    node_type: GraphNodeType = Field(..., description="Semantic entity or document category")
    name: str = Field(..., description="Canonical or display label")
    description: Optional[str] = Field(default=None, description="Detailed grounded description")
    paper_ids: List[str] = Field(default_factory=list, description="Originating canonical papers")
    chunk_ids: List[str] = Field(default_factory=list, description="Associated document chunks")
    domain: Optional[str] = Field(default=None, description="Disciplinary domain or topic")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Domain-specific properties")


class GraphEdge(BaseModel):
    """Evidence-grounded directional or bidirectional semantic link between scientific nodes."""
    edge_id: str = Field(..., description="Unique edge identifier (e.g. edge_xxx)")
    source_id: str = Field(..., description="Subject node identifier")
    target_id: str = Field(..., description="Object node identifier")
    predicate: GraphRelationPredicate = Field(..., description="Semantic relation predicate")
    is_directed: bool = Field(default=True, description="True if relationship is directed")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction or inference confidence")
    paper_id: Optional[str] = Field(default=None, description="Originating paper ID")
    chunk_id: Optional[str] = Field(default=None, description="Originating chunk ID")
    evidence_text: Optional[str] = Field(default=None, description="Exact cited evidence sentence/clause")
    start_char: Optional[int] = Field(default=None, description="Character offset start in chunk")
    end_char: Optional[int] = Field(default=None, description="Character offset end in chunk")
    attribution: AttributionType = Field(default=AttributionType.AUTHOR_STATED)
    structural_validity: StructuralValidityStatus = Field(default=StructuralValidityStatus.STRUCTURALLY_VALID)
    evidence_support: EvidenceSupportStatus = Field(default=EvidenceSupportStatus.NOT_ASSESSED)
    human_verification: HumanVerificationStatus = Field(default=HumanVerificationStatus.PENDING)
    correction_notes: Optional[str] = Field(default=None, description="Audit or validation notes")
    extractor_version: str = Field(default="v0.6.0")


class GraphNeighborhood(BaseModel):
    """Subgraph centered on a target focal node with 1-hop or k-hop context."""
    center_node_id: str
    depth: int = 1
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_neighbors: int


class GraphPath(BaseModel):
    """Multi-hop mechanistic traversal connecting two distant nodes."""
    source_node_id: str
    target_node_id: str
    path_length: int
    node_sequence: List[str]
    predicate_sequence: List[str]
    edges: List[GraphEdge]
    evidence_chain: List[str]
    is_trusted: bool = True


class GraphVisualizationExport(BaseModel):
    """Frontend-ready graph structure formatted for interactive graph visualization."""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    metadata: Dict[str, Any] = Field(default_factory=dict)
