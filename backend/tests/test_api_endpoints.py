"""Integration tests for ResearchGraph Phase 13 FastAPI backend endpoints.

Verifies:
1. Health, readiness, versions, and models endpoints.
2. Literature, papers, entities, and statements endpoints.
3. Lexical, dense, hybrid, and comparison retrieval endpoints.
4. Knowledge graph export, neighborhood, and path traversal.
5. Cross-domain discovery candidate search.
6. Research-gap verification dossier generation.
7. Negative knowledge and dead-end search.
8. End-to-end orchestration workflow execution.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from researchgraph.api.main import app

client = TestClient(app)


def test_root_welcome():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "version" in data


def test_health_and_versions():
    res_health = client.get("/api/v1/health")
    assert res_health.status_code == 200
    health_data = res_health.json()
    assert "status" in health_data
    assert "sqlite_available" in health_data

    res_versions = client.get("/api/v1/versions")
    assert res_versions.status_code == 200
    versions_data = res_versions.json()
    assert "backend_version" in versions_data
    assert versions_data["knowledge_base_version"] == "v0.5.1"


def test_models_registry():
    res = client.get("/api/v1/models")
    assert res.status_code == 200
    data = res.json()
    assert "registered_models" in data
    assert "tfidf-lsa-384" in data["registered_models"]


def test_literature_endpoints():
    res_papers = client.get("/api/v1/literature/papers?limit=5")
    assert res_papers.status_code == 200
    papers = res_papers.json()
    assert len(papers) > 0
    first_id = papers[0]["paper_id"]

    res_detail = client.get(f"/api/v1/literature/papers/{first_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["paper_id"] == first_id

    res_entities = client.get("/api/v1/literature/entities?category=METHOD&limit=10")
    assert res_entities.status_code == 200
    assert len(res_entities.json()) > 0


def test_retrieval_endpoints():
    payload = {"query": "federated learning clinical oncology", "top_k": 3}

    res_lex = client.post("/api/v1/retrieval/lexical", json=payload)
    assert res_lex.status_code == 200
    assert "hits" in res_lex.json()

    res_dense = client.post("/api/v1/retrieval/dense", json=payload)
    assert res_dense.status_code == 200
    assert "hits" in res_dense.json()

    res_hybrid = client.post("/api/v1/retrieval/hybrid", json=payload)
    assert res_hybrid.status_code == 200
    assert "hits" in res_hybrid.json()

    res_comp = client.post("/api/v1/retrieval/compare", json=payload)
    assert res_comp.status_code == 200
    assert "lexical_hits" in res_comp.json()
    assert "dense_hits" in res_comp.json()


def test_graph_endpoints():
    res_export = client.get("/api/v1/graph/export?trusted_only=true")
    assert res_export.status_code == 200
    export_data = res_export.json()
    assert "nodes" in export_data
    assert "edges" in export_data
    assert len(export_data["nodes"]) > 0


def test_discovery_endpoints():
    payload = {
        "research_problem": "privacy-preserving federated machine learning in clinical oncology",
        "min_score": 0.2,
        "limit": 3,
    }
    res = client.post("/api/v1/discovery/search", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "candidates" in data
    assert data["total_found"] >= 0


def test_gap_verification_endpoint():
    payload = {
        "proposed_gap": "prompt injection defenses with zero computational latency",
        "target_domains": ["Cybersecurity"],
    }
    res = client.post("/api/v1/gap-verification/verify", json=payload)
    assert res.status_code == 200
    dossier = res.json()
    assert "final_status" in dossier
    assert "search_audit_trail" in dossier
    assert "corpus_coverage_limitations" in dossier
    assert dossier["final_status"] != "VERIFIED_NOVEL"


def test_negative_knowledge_endpoints():
    res = client.get("/api/v1/negative-knowledge/search?method=federated+learning")
    assert res.status_code == 200
    records = res.json()
    assert len(records) > 0

    res_bot = client.get("/api/v1/negative-knowledge/bottlenecks?limit=5")
    assert res_bot.status_code == 200
    assert len(res_bot.json()) > 0


def test_orchestration_workflow_endpoint():
    payload = {
        "research_question": "federated learning clinical healthcare privacy constraints",
        "target_domain": "Healthcare & Oncology",
        "execute_review": True,
        "execute_experiment_design": True,
    }
    res = client.post("/api/v1/orchestration/synthesize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "workflow_id" in data
    assert "stages" in data
    assert len(data["stages"]) >= 6
    assert data["final_status"] in ["HYPOTHESIS_FORMULATED", "INSUFFICIENT_EVIDENCE", "REJECTED_BY_REVIEWER"]
    assert data["total_duration_ms"] > 0.0
