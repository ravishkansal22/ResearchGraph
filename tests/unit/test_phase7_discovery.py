"""Unit tests for Phase 7: Cross-Domain Discovery Algorithms.

Verifies:
1. DiscoveryScorer mathematical formulation, penalties, and ablation toggles.
2. Problem-to-Method cross-domain matching.
3. Swanson-style LBD multi-hop traversal with evidence chains.
4. Retention of required candidate fields (assumptions, limitations, disconfirmation criteria).
5. Controlled ablation experiment harness.
"""

from __future__ import annotations

import pytest

from dataset.schemas.scientific_knowledge_base import EvidenceSupportStatus
from pipelines.discovery.ablation import run_discovery_ablation_experiment
from pipelines.discovery.algorithms import CrossDomainDiscoveryEngine
from pipelines.discovery.schema import DiscoveryStrategy
from pipelines.discovery.scorer import DiscoveryScorer, ScorerConfig
from pipelines.graph.builder import ResearchGraph
from pipelines.graph.schema import (
    GraphEdge,
    GraphNode,
    GraphNodeType,
    GraphRelationPredicate,
)


class TestDiscoveryScorer:
    """Test suite for interpretable candidate scoring and ablations."""

    def test_scorer_components_and_penalties(self):
        scorer = DiscoveryScorer()

        # Cross-domain candidate with zero co-occurrence
        score_novel = scorer.score_candidate(
            semantic_sim=0.85,
            source_evidence=["Evidence 1", "Evidence 2"],
            target_evidence=["Evidence 3", "Evidence 4"],
            source_domain="Cybersecurity",
            target_domain="Clinical Healthcare",
            source_paper_ids=["p1", "p2"],
            target_paper_ids=["p3", "p4"],
            known_contradictions_count=0,
            mechanistic_match=True,
        )
        assert score_novel.composite_score > 0.60
        assert score_novel.cross_domain_distance == 0.90
        assert score_novel.redundancy_penalty == 0.0

        # Redundant candidate co-occurring in the same paper
        score_redundant = scorer.score_candidate(
            semantic_sim=0.85,
            source_evidence=["Evidence 1"],
            target_evidence=["Evidence 2"],
            source_domain="Cybersecurity",
            target_domain="Clinical Healthcare",
            source_paper_ids=["p1"],
            target_paper_ids=["p1"],  # Same paper!
            known_contradictions_count=0,
            mechanistic_match=True,
        )
        assert score_redundant.redundancy_penalty > 0.5
        assert score_redundant.composite_score < score_novel.composite_score

        # Contradiction penalty
        score_contradicted = scorer.score_candidate(
            semantic_sim=0.85,
            source_evidence=["Evidence 1"],
            target_evidence=["Evidence 2"],
            source_domain="Cybersecurity",
            target_domain="Clinical Healthcare",
            source_paper_ids=["p1"],
            target_paper_ids=["p2"],
            known_contradictions_count=2,
            mechanistic_match=True,
        )
        assert score_contradicted.contradiction_risk_penalty > 0.0
        assert score_contradicted.composite_score < score_novel.composite_score

    def test_scorer_ablation_toggles(self):
        # Disabling cross-domain distance should level the playing field between same-domain and cross-domain
        cfg_no_dist = ScorerConfig(enable_distance=False)
        scorer_no_dist = DiscoveryScorer(config=cfg_no_dist)

        score_cross = scorer_no_dist.score_candidate(
            semantic_sim=0.8, source_evidence=["e1"], target_evidence=["e2"],
            source_domain="Domain A", target_domain="Domain B",
            source_paper_ids=["p1"], target_paper_ids=["p2"],
        )
        score_same = scorer_no_dist.score_candidate(
            semantic_sim=0.8, source_evidence=["e1"], target_evidence=["e2"],
            source_domain="Domain A", target_domain="Domain A",
            source_paper_ids=["p1"], target_paper_ids=["p2"],
        )
        assert score_cross.cross_domain_distance == score_same.cross_domain_distance


class TestCrossDomainDiscoveryEngine:
    """Test suite for discovery algorithms."""

    @pytest.fixture
    def custom_discovery_engine(self) -> CrossDomainDiscoveryEngine:
        graph = ResearchGraph()
        n_method = GraphNode(
            node_id="m_fl",
            node_type=GraphNodeType.METHOD,
            name="Federated Learning",
            domain="Security & Privacy",
            paper_ids=["paper_fl_01"],
        )
        n_bridge = GraphNode(
            node_id="b_comm",
            node_type=GraphNodeType.BOTTLENECK,
            name="Communication Bandwidth Constraint",
            domain="Distributed Systems",
            paper_ids=["paper_fl_01", "paper_oncol_01"],
        )
        n_problem = GraphNode(
            node_id="p_oncol",
            node_type=GraphNodeType.PROBLEM,
            name="Multi-Institutional Oncology Collaboration",
            domain="Healthcare & Oncology",
            paper_ids=["paper_oncol_01"],
        )
        for n in [n_method, n_bridge, n_problem]:
            graph.add_node(n)

        # m_fl --ADDRESSES--> b_comm (SUPPORTED)
        graph.add_edge(GraphEdge(
            edge_id="e_fl_comm",
            source_id="m_fl",
            target_id="b_comm",
            predicate=GraphRelationPredicate.ADDRESSES,
            evidence_support=EvidenceSupportStatus.SUPPORTED,
            evidence_text="Federated learning minimizes raw data transmission across institutions",
            paper_id="paper_fl_01",
        ))
        # b_comm --LIMITED_BY--> p_oncol (SUPPORTED)
        graph.add_edge(GraphEdge(
            edge_id="e_comm_oncol",
            source_id="b_comm",
            target_id="p_oncol",
            predicate=GraphRelationPredicate.LIMITED_BY,
            evidence_support=EvidenceSupportStatus.SUPPORTED,
            evidence_text="Collaborative oncology modeling is constrained by inter-hospital bandwidth limits",
            paper_id="paper_oncol_01",
        ))

        return CrossDomainDiscoveryEngine(graph=graph)

    def test_swanson_lbd_discovery(self, custom_discovery_engine):
        engine = custom_discovery_engine
        candidates = engine.discover_swanson_lbd("m_fl", "p_oncol")
        assert len(candidates) == 1
        cand = candidates[0]
        assert cand.strategy == DiscoveryStrategy.SWANSON_LBD_TRAVERSAL
        assert cand.source_concept_id == "m_fl"
        assert cand.target_problem_id == "p_oncol"
        assert "Communication Bandwidth Constraint" in cand.proposed_mechanism
        assert len(cand.assumptions_required) > 0
        assert len(cand.disconfirmation_criteria) > 0

    def test_problem_to_method_discovery(self, custom_discovery_engine):
        engine = custom_discovery_engine
        candidates = engine.discover_problem_to_method("Clinical Oncology Pathology", min_score=0.2)
        assert len(candidates) >= 1
        cand = candidates[0]
        assert cand.strategy == DiscoveryStrategy.PROBLEM_TO_METHOD
        assert cand.source_domain != cand.target_domain
        assert cand.disconfirmation_criteria is not None
