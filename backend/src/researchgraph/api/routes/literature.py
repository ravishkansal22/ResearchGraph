"""Scientific Literature and Knowledge Base Entities Endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
import pyarrow.parquet as pq

from researchgraph.core.config import settings
from pipelines.knowledge_base.query import KnowledgeBaseQueryEngine

router = APIRouter(prefix="/literature", tags=["Literature & Knowledge Base"])

_query_engine: Optional[KnowledgeBaseQueryEngine] = None


def get_query_engine() -> KnowledgeBaseQueryEngine:
    global _query_engine
    if _query_engine is None:
        _query_engine = KnowledgeBaseQueryEngine(db_path=settings.sqlite_db_path)
    return _query_engine


@router.get("/papers")
def list_papers(limit: int = Query(default=20, ge=1, le=100)) -> List[Dict[str, Any]]:
    """Retrieve list of canonical papers from the knowledge base."""
    engine = get_query_engine()
    with engine._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT paper_id, title, publication_year, doi FROM papers LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]


@router.get("/papers/{paper_id}")
def get_paper_details(paper_id: str) -> Dict[str, Any]:
    """Retrieve canonical paper metadata by ID."""
    engine = get_query_engine()
    paper = engine.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found.")
    return paper


@router.get("/entities")
def list_entities(
    category: str = Query(default="METHOD", description="Entity category e.g. METHOD, PROBLEM, BOTTLENECK"),
    limit: int = Query(default=50, ge=1, le=200),
) -> List[Dict[str, Any]]:
    """List canonical entities of a specified scientific type."""
    engine = get_query_engine()
    return engine.list_entities_by_type(category=category, limit=limit)


@router.get("/statements")
def list_statements(
    paper_id: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
) -> List[Dict[str, Any]]:
    """List evidence-backed scientific statements."""
    engine = get_query_engine()
    with engine._get_connection() as conn:
        cur = conn.cursor()
        clauses = []
        params = []
        if paper_id:
            clauses.append("paper_id = ?")
            params.append(paper_id)
        if category:
            clauses.append("category = ?")
            params.append(category.strip().upper())
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        cur.execute(f"SELECT * FROM statements {where_sql} LIMIT 100", params)
        results = []
        for r in cur.fetchall():
            d = dict(r)
            if "provenance_json" in d:
                d["provenance"] = json.loads(d.pop("provenance_json"))
            if "validation_notes_json" in d:
                d["validation_notes"] = json.loads(d.pop("validation_notes_json"))
            if "related_entity_ids_json" in d:
                d["related_entity_ids"] = json.loads(d.pop("related_entity_ids_json"))
            results.append(d)
        return results


@router.get("/chunks/{chunk_id}")
def get_chunk(chunk_id: str) -> Dict[str, Any]:
    """Retrieve text and metadata of a specific document chunk."""
    chunks_path = Path(settings.chunks_parquet_path)
    if not chunks_path.exists():
        raise HTTPException(status_code=500, detail="Chunks parquet artifact missing.")

    table = pq.read_table(str(chunks_path))
    c_ids = table["chunk_id"].to_pylist()
    if chunk_id not in c_ids:
        raise HTTPException(status_code=404, detail=f"Chunk {chunk_id} not found.")

    idx = c_ids.index(chunk_id)
    return {
        "chunk_id": chunk_id,
        "canonical_id": table["canonical_id"][idx].as_py(),
        "section_title": table["section_title"][idx].as_py(),
        "page_start": table["page_start"][idx].as_py(),
        "page_end": table["page_end"][idx].as_py(),
        "text": table["text"][idx].as_py(),
        "word_count": table["word_count"][idx].as_py(),
    }
