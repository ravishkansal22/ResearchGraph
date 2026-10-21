"""Generate versioned embeddings release artifacts (v0.6.0) for ResearchGraph.

Encodes:
- Canonical entities from dataset/processed/v0.5.1/knowledge_base.db
- Canonical statements from dataset/processed/v0.5.1/knowledge_base.db
- Sample chunks from dataset/processed/v0.3.0/chunks.parquet
Outputs Parquet, JSONL, and manifest to dataset/processed/v0.6.0/
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.embeddings.models import get_encoder
from pipelines.embeddings.pipeline import EmbeddingPipeline
from pipelines.knowledge_base.query import KnowledgeBaseQueryEngine


def generate_v060_embeddings():
    output_dir = Path("dataset/processed/v0.6.0")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    kb_path = Path("dataset/processed/v0.5.1/knowledge_base.db")
    chunks_path = Path("dataset/processed/v0.3.0/chunks.parquet")

    engine = KnowledgeBaseQueryEngine(db_path=kb_path)
    
    # 1. Fetch Entities
    with engine._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM entities")
        entities = []
        for r in cur.fetchall():
            d = dict(r)
            d["aliases"] = json.loads(d["aliases_json"])
            entities.append(d)

    # 2. Fetch Statements
    with engine._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM statements")
        statements = [dict(r) for r in cur.fetchall()]

    print(f"Loaded {len(entities)} entities and {len(statements)} statements.")

    encoder = get_encoder(model_name_or_key="tfidf-lsa-384")
    pipeline = EmbeddingPipeline(encoder=encoder, pipeline_version="v0.6.0")

    print("Encoding entities...")
    ent_records = pipeline.generate_entity_embeddings(entities)

    print("Encoding statements...")
    stmt_records = pipeline.generate_statement_embeddings(statements)

    print("Encoding chunks subset...")
    chunk_records = pipeline.generate_chunk_embeddings(chunks_path, limit=200)

    all_records = ent_records + stmt_records + chunk_records
    print(f"Total embeddings generated: {len(all_records)}. Persisting to {output_dir}...")
    saved = pipeline.save_records(all_records, output_dir=output_dir, name_prefix="scientific_embeddings")
    print("Done! Artifacts saved:", saved)


if __name__ == "__main__":
    generate_v060_embeddings()
