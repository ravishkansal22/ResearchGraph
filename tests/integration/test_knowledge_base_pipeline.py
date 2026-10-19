"""Integration Tests for Phase 4 Scientific Knowledge Base Pipeline.

Tests end-to-end ingestion, schema validation, persistent snapshot creation,
relational SQLite population, idempotency, and referential integrity across rebuilds.
Schema Version: 0.5.0
"""

from pathlib import Path
import pytest
from pipelines.knowledge_base.config import KnowledgeBaseConfig
from pipelines.knowledge_base.pipeline import ScientificKnowledgeBasePipeline
from pipelines.knowledge_base.query import KnowledgeBaseQueryEngine
from pipelines.knowledge_base.storage import read_jsonl


def test_knowledge_base_pipeline_end_to_end(tmp_path: Path) -> None:
    output_dir = tmp_path / "processed_v050"
    manifest_dir = tmp_path / "manifests"

    config = KnowledgeBaseConfig(
        output_dir=output_dir,
        manifest_dir=manifest_dir,
        save_parquet=True,
        save_sqlite=True,
    )

    pipeline = ScientificKnowledgeBasePipeline(config=config)
    manifest = pipeline.run()

    # Verify manifest properties
    assert manifest.kb_version == config.kb_version
    assert manifest.schema_version == config.schema_version
    assert manifest.total_papers_count > 0
    assert manifest.total_canonical_entities_count > 0
    assert manifest.total_entity_mentions_count > 0
    assert manifest.total_statements_count > 0
    assert manifest.total_relationships_count > 0
    assert manifest.referential_integrity_pass_rate == 1.0
    assert manifest.provenance_completeness_rate == 1.0

    # Verify generated JSONL files
    papers = read_jsonl(output_dir / "canonical_papers.jsonl")
    entities = read_jsonl(output_dir / "canonical_entities.jsonl")
    mentions = read_jsonl(output_dir / "entity_mentions.jsonl")
    statements = read_jsonl(output_dir / "canonical_statements.jsonl")
    relationships = read_jsonl(output_dir / "canonical_relationships.jsonl")
    quarantine = read_jsonl(output_dir / "quarantined_records.jsonl")
    aliases = read_jsonl(output_dir / "alias_mappings.jsonl")

    assert len(papers) == manifest.total_papers_count
    assert len(entities) == manifest.total_canonical_entities_count
    assert len(mentions) == manifest.total_entity_mentions_count
    assert len(statements) == manifest.total_statements_count
    assert len(relationships) == manifest.total_relationships_count
    assert len(quarantine) == manifest.total_quarantined_records_count
    assert len(aliases) > 0

    # Verify Parquet files
    assert (output_dir / "canonical_papers.parquet").exists()
    assert (output_dir / "canonical_entities.parquet").exists()
    assert (output_dir / "entity_mentions.parquet").exists()
    assert (output_dir / "canonical_statements.parquet").exists()
    assert (output_dir / "canonical_relationships.parquet").exists()

    # Verify SQLite database and Query Engine
    db_path = output_dir / "knowledge_base.db"
    assert db_path.exists()
    engine = KnowledgeBaseQueryEngine(db_path=db_path)
    queried_paper = engine.get_paper(papers[0]["paper_id"])
    assert queried_paper is not None
    assert queried_paper["paper_id"] == papers[0]["paper_id"]


def test_pipeline_reproducibility_and_idempotency(tmp_path: Path) -> None:
    output_dir_1 = tmp_path / "run_1"
    output_dir_2 = tmp_path / "run_2"
    manifest_dir = tmp_path / "manifests"

    config_1 = KnowledgeBaseConfig(
        output_dir=output_dir_1,
        manifest_dir=manifest_dir,
        save_parquet=False,
        save_sqlite=True,
    )
    config_2 = KnowledgeBaseConfig(
        output_dir=output_dir_2,
        manifest_dir=manifest_dir,
        save_parquet=False,
        save_sqlite=True,
    )

    manifest_1 = ScientificKnowledgeBasePipeline(config=config_1).run()
    manifest_2 = ScientificKnowledgeBasePipeline(config=config_2).run()

    # Exact equality of counts
    assert manifest_1.total_papers_count == manifest_2.total_papers_count
    assert manifest_1.total_canonical_entities_count == manifest_2.total_canonical_entities_count
    assert manifest_1.total_entity_mentions_count == manifest_2.total_entity_mentions_count
    assert manifest_1.total_statements_count == manifest_2.total_statements_count
    assert manifest_1.total_relationships_count == manifest_2.total_relationships_count
    assert manifest_1.total_quarantined_records_count == manifest_2.total_quarantined_records_count

    # Exact equality of entity IDs and relationship IDs
    entities_1 = read_jsonl(output_dir_1 / "canonical_entities.jsonl")
    entities_2 = read_jsonl(output_dir_2 / "canonical_entities.jsonl")
    ids_1 = [e["entity_id"] for e in entities_1]
    ids_2 = [e["entity_id"] for e in entities_2]
    assert ids_1 == ids_2

    rels_1 = read_jsonl(output_dir_1 / "canonical_relationships.jsonl")
    rels_2 = read_jsonl(output_dir_2 / "canonical_relationships.jsonl")
    rel_ids_1 = [r["relationship_id"] for r in rels_1]
    rel_ids_2 = [r["relationship_id"] for r in rels_2]
    assert rel_ids_1 == rel_ids_2
