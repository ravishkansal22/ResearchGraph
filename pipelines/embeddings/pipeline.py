"""ResearchGraph Phase 5: Versioned Scientific Embedding Pipeline.

Generates and tracks reproducible vector representations across distinct representation types:
1. Document Chunks (Phase 2 chunks.parquet)
2. Scientific Statements (Phase 4 knowledge_base statements)
3. Canonical Entities (Phase 4 knowledge_base entities)
4. Research Problems & Bottlenecks

Preserves complete reproducibility metadata including SHA-256 source hashes, exact model revisions,
dimensions, pipeline versions, and creation timestamps.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, Field

from pipelines.embeddings.models import (
    BaseEmbeddingEncoder,
    compute_text_hash,
    get_encoder,
)


class RepresentationType(str, Enum):
    """Explicit scientific representation categories to avoid category conflation."""
    CHUNK = "CHUNK"
    STATEMENT = "STATEMENT"
    ENTITY = "ENTITY"
    PROBLEM_BOTTLENECK = "PROBLEM_BOTTLENECK"
    QUERY = "QUERY"


class EmbeddingRecord(BaseModel):
    """Reproducible embedding record with full source provenance and model metadata."""
    record_id: str = Field(..., description="Unique source record identifier (chunk_id, statement_id, entity_id)")
    representation_type: RepresentationType = Field(..., description="Categorical type of scientific representation")
    source_text: str = Field(..., description="Exact textual content encoded")
    source_text_hash: str = Field(..., description="Deterministic SHA-256 hash of source_text")
    model_name: str = Field(..., description="Model identifier used for inference")
    model_revision: str = Field(..., description="Exact model commit hash or version")
    dimension: int = Field(..., description="Dimensionality of embedding vector")
    preprocessing_config: Dict[str, Any] = Field(default_factory=dict, description="Normalization parameters")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    pipeline_version: str = Field(default="v0.6.0", description="Embedding pipeline release version")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Domain and provenance metadata")
    embedding: List[float] = Field(..., description="Normalized dense embedding vector")


class EmbeddingPipeline:
    """End-to-end embedding pipeline for scientific literature knowledge representations."""

    def __init__(
        self,
        encoder: Optional[BaseEmbeddingEncoder] = None,
        model_key: str = "tfidf-lsa-384",
        pipeline_version: str = "v0.6.0",
        device: str = "cpu",
    ):
        self.pipeline_version = pipeline_version
        self.model_key = model_key
        self.encoder = encoder or get_encoder(model_name_or_key=model_key, device=device)

    def generate_chunk_embeddings(
        self,
        chunks_parquet_path: Path | str,
        limit: Optional[int] = None,
        batch_size: int = 128,
    ) -> List[EmbeddingRecord]:
        """Generate versioned embeddings for document chunks from Phase 2 parquet."""
        path = Path(chunks_parquet_path)
        if not path.exists():
            raise FileNotFoundError(f"Chunks parquet file not found at {path}")

        table = pq.read_table(str(path))
        num_rows = table.num_rows if limit is None else min(limit, table.num_rows)
        chunk_ids = table["chunk_id"].to_pylist()[:num_rows]
        texts = table["text"].to_pylist()[:num_rows]
        canonical_ids = table["canonical_id"].to_pylist()[:num_rows]
        section_titles = table["section_title"].to_pylist()[:num_rows]

        # Fit encoder if LSA baseline
        if hasattr(self.encoder, "fit") and not getattr(self.encoder, "_fitted", False):
            self.encoder.fit(texts)

        records: List[EmbeddingRecord] = []
        spec = self.encoder.spec

        for i in range(0, num_rows, batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_ids = chunk_ids[i : i + batch_size]
            batch_can_ids = canonical_ids[i : i + batch_size]
            batch_sections = section_titles[i : i + batch_size]

            embeddings = self.encoder.encode(batch_texts, is_query=False)

            for j in range(len(batch_texts)):
                rec = EmbeddingRecord(
                    record_id=batch_ids[j],
                    representation_type=RepresentationType.CHUNK,
                    source_text=batch_texts[j],
                    source_text_hash=compute_text_hash(batch_texts[j]),
                    model_name=spec.model_name,
                    model_revision=spec.revision,
                    dimension=spec.dimension,
                    preprocessing_config={"lowercase": True, "strip_accents": True},
                    pipeline_version=self.pipeline_version,
                    metadata={
                        "paper_id": batch_can_ids[j],
                        "section_title": batch_sections[j],
                    },
                    embedding=embeddings[j].tolist(),
                )
                records.append(rec)

        return records

    def generate_statement_embeddings(
        self,
        statements: List[Dict[str, Any]],
    ) -> List[EmbeddingRecord]:
        """Generate embeddings for scientific claims, results, limitations, and future directions."""
        if not statements:
            return []

        texts = [s.get("normalized_statement") or s.get("surface_text", "") for s in statements]
        if hasattr(self.encoder, "fit") and not getattr(self.encoder, "_fitted", False):
            self.encoder.fit(texts)

        embeddings = self.encoder.encode(texts, is_query=False)
        spec = self.encoder.spec
        records: List[EmbeddingRecord] = []

        for idx, s in enumerate(statements):
            text = texts[idx]
            rec = EmbeddingRecord(
                record_id=s["statement_id"],
                representation_type=RepresentationType.STATEMENT,
                source_text=text,
                source_text_hash=compute_text_hash(text),
                model_name=spec.model_name,
                model_revision=spec.revision,
                dimension=spec.dimension,
                preprocessing_config={"source_field": "normalized_statement"},
                pipeline_version=self.pipeline_version,
                metadata={
                    "category": s.get("category"),
                    "paper_id": s.get("paper_id"),
                    "chunk_id": s.get("chunk_id"),
                },
                embedding=embeddings[idx].tolist(),
            )
            records.append(rec)

        return records

    def generate_entity_embeddings(
        self,
        entities: List[Dict[str, Any]],
    ) -> List[EmbeddingRecord]:
        """Generate embeddings for canonical scientific concepts (methods, problems, bottlenecks)."""
        if not entities:
            return []

        texts = []
        for e in entities:
            desc = e.get("description") or ""
            aliases = ", ".join(e.get("aliases") or [])
            combined = f"{e['canonical_name']} ({e.get('category')}). {desc} Aliases: {aliases}".strip()
            texts.append(combined)

        if hasattr(self.encoder, "fit") and not getattr(self.encoder, "_fitted", False):
            self.encoder.fit(texts)

        embeddings = self.encoder.encode(texts, is_query=False)
        spec = self.encoder.spec
        records: List[EmbeddingRecord] = []

        for idx, e in enumerate(entities):
            text = texts[idx]
            rep_type = (
                RepresentationType.PROBLEM_BOTTLENECK
                if e.get("category") in {"PROBLEM", "BOTTLENECK"}
                else RepresentationType.ENTITY
            )
            rec = EmbeddingRecord(
                record_id=e["entity_id"],
                representation_type=rep_type,
                source_text=text,
                source_text_hash=compute_text_hash(text),
                model_name=spec.model_name,
                model_revision=spec.revision,
                dimension=spec.dimension,
                preprocessing_config={"format": "name_category_description_aliases"},
                pipeline_version=self.pipeline_version,
                metadata={
                    "canonical_name": e.get("canonical_name"),
                    "category": e.get("category"),
                    "mentions_count": e.get("mentions_count", 1),
                },
                embedding=embeddings[idx].tolist(),
            )
            records.append(rec)

        return records

    def save_records(
        self,
        records: List[EmbeddingRecord],
        output_dir: Path | str,
        name_prefix: str = "embeddings",
    ) -> Dict[str, str]:
        """Persist embedding records to Parquet and JSONL with a release manifest."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        parquet_file = out_path / f"{name_prefix}.parquet"
        jsonl_file = out_path / f"{name_prefix}.jsonl"
        manifest_file = out_path / f"{name_prefix}_manifest.json"

        # 1. JSONL
        with open(jsonl_file, "w", encoding="utf-8") as f:
            for r in records:
                f.write(r.model_dump_json() + "\n")

        # 2. Parquet
        data_dict = {
            "record_id": [r.record_id for r in records],
            "representation_type": [r.representation_type.value for r in records],
            "source_text_hash": [r.source_text_hash for r in records],
            "model_name": [r.model_name for r in records],
            "model_revision": [r.model_revision for r in records],
            "dimension": [r.dimension for r in records],
            "created_at": [r.created_at for r in records],
            "pipeline_version": [r.pipeline_version for r in records],
            "metadata_json": [json.dumps(r.metadata) for r in records],
            "embedding": [r.embedding for r in records],
        }
        table = pa.Table.from_pydict(data_dict)
        pq.write_table(table, str(parquet_file), compression="snappy")

        # 3. Manifest
        manifest = {
            "pipeline_version": self.pipeline_version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "total_records": len(records),
            "model_name": records[0].model_name if records else "",
            "dimension": records[0].dimension if records else 0,
            "representation_types_breakdown": {
                t.value: sum(1 for r in records if r.representation_type == t)
                for t in RepresentationType
                if any(r.representation_type == t for r in records)
            },
            "parquet_file": str(parquet_file.name),
            "jsonl_file": str(jsonl_file.name),
        }
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return {
            "parquet": str(parquet_file),
            "jsonl": str(jsonl_file),
            "manifest": str(manifest_file),
        }
