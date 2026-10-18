"""Unit Tests for KnowledgeBaseQueryEngine.

Verifies structured query operations: paper lookup, entity filtering by type,
chunk records, relational joins, entity mention tracing, and quarantine inspection.
Schema Version: 0.5.0
"""

from pathlib import Path
import pytest
from pipelines.knowledge_base.query import KnowledgeBaseQueryEngine


@pytest.fixture
def query_engine() -> KnowledgeBaseQueryEngine:
    db_path = Path("dataset/processed/v0.5.0/knowledge_base.db")
    if not db_path.exists():
        pytest.skip("Knowledge base database not built yet")
    return KnowledgeBaseQueryEngine(db_path=db_path)


def test_get_paper(query_engine: KnowledgeBaseQueryEngine) -> None:
    paper = query_engine.get_paper("rg_doi_ebe643c2b3dd")
    assert paper is not None
    assert paper["paper_id"] == "rg_doi_ebe643c2b3dd"
    assert "title" in paper
    assert paper["total_entities_count"] > 0


def test_list_entities_by_type(query_engine: KnowledgeBaseQueryEngine) -> None:
    methods = query_engine.list_entities_by_type("METHOD", limit=10)
    assert len(methods) > 0
    assert all(m["category"] == "METHOD" for m in methods)
    # Check that aliases and paper_ids were parsed from JSON
    assert isinstance(methods[0]["aliases"], list)
    assert isinstance(methods[0]["paper_ids"], list)


def test_get_statements_for_paper(query_engine: KnowledgeBaseQueryEngine) -> None:
    stmts = query_engine.get_statements_for_paper("rg_doi_ebe643c2b3dd")
    assert len(stmts) > 0
    for s in stmts:
        assert s["paper_id"] == "rg_doi_ebe643c2b3dd"
        assert "provenance" in s
        assert "evidence_text" in s


def test_get_records_for_chunk(query_engine: KnowledgeBaseQueryEngine) -> None:
    records = query_engine.get_records_for_chunk("chk_rg_doi_ebe643c2b3dd_A_0135")
    assert records["chunk_id"] == "chk_rg_doi_ebe643c2b3dd_A_0135"
    assert len(records["mentions"]) > 0
    assert len(records["statements"]) > 0
    assert len(records["relationships"]) > 0


def test_find_methods_for_problem(query_engine: KnowledgeBaseQueryEngine) -> None:
    results = query_engine.find_methods_for_problem("data imbalance")
    assert len(results) > 0
    assert any("ensemble learning" in r["method_name"].lower() for r in results)
    for r in results:
        assert r["relation_type"] == "ADDRESSES"
        assert r["attribution"] == "AUTHOR_STATED"


def test_trace_entity_mentions(query_engine: KnowledgeBaseQueryEngine) -> None:
    # Retrieve convolutional neural network entity
    methods = query_engine.list_entities_by_type("METHOD", limit=50)
    cnn = next((m for m in methods if "convolutional" in m["canonical_name"]), None)
    assert cnn is not None

    trace = query_engine.trace_entity_mentions(cnn["entity_id"])
    assert trace["mentions_count"] > 0
    assert len(trace["mentions"]) == trace["mentions_count"]
    first_men = trace["mentions"][0]
    assert "start_char" in first_men
    assert "provenance" in first_men
    assert "surface_text" in first_men


def test_filter_records(query_engine: KnowledgeBaseQueryEngine) -> None:
    filtered = query_engine.filter_records(extractor_version="v0.4.1", limit=10)
    assert len(filtered["mentions"]) > 0
    for m in filtered["mentions"]:
        assert m["extraction_version"] == "v0.4.1"


def test_inspect_alias_mappings(query_engine: KnowledgeBaseQueryEngine) -> None:
    aliases = query_engine.inspect_alias_mappings(status="CONFIRMED")
    assert len(aliases) > 0
    cnn_alias = next((a for a in aliases if a["surface_form"] == "cnn"), None)
    assert cnn_alias is not None
    assert cnn_alias["canonical_name"] == "convolutional neural network"
