"""End-to-End Scientific Information Extraction Pipeline (Phase 3).

Orchestrates deterministic chunk sampling, scientific entity and statement extraction,
evidence grounding and provenance validation, relationship link verification,
versioned dataset output persistence, and quality reporting.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dataset.schemas.document_processing import ProcessedChunk
from dataset.schemas.scientific_knowledge import (
    ExtractionBatchResult,
    ScientificEntityRecord,
    ScientificRelationRecord,
    ScientificStatementRecord,
    ValidationStatus,
)
from pipelines.extraction.config import ExtractionConfig, config as default_config
from pipelines.extraction.evaluator import ExtractionEvaluationReport, ExtractionEvaluator
from pipelines.extraction.extractor import (
    BaseScientificExtractor,
    LLMScientificExtractor,
    RuleBasedScientificExtractor,
)
from pipelines.extraction.reporter import ExtractionReporter
from pipelines.extraction.selection import ChunkSampler, SampledChunkRecord
from pipelines.extraction.validator import EvidenceGroundingValidator

logger = logging.getLogger(__name__)


class ScientificExtractionPipeline:
    """Orchestrates Phase 3 scientific information extraction across validated chunks."""

    def __init__(
        self,
        config: Optional[ExtractionConfig] = None,
        extractor: Optional[BaseScientificExtractor] = None,
    ):
        self.config = config or default_config
        if extractor is not None:
            self.extractor = extractor
        elif self.config.EXTRACTION_PIPELINE_VERSION == "v0.4.1":
            from pipelines.extraction.extractor_v041 import ExperimentalScientificExtractor
            self.extractor = ExperimentalScientificExtractor(
                schema_version=self.config.EXTRACTION_SCHEMA_VERSION,
                pipeline_version=self.config.EXTRACTION_PIPELINE_VERSION,
            )
        else:
            self.extractor = RuleBasedScientificExtractor(
                schema_version=self.config.EXTRACTION_SCHEMA_VERSION,
                pipeline_version=self.config.EXTRACTION_PIPELINE_VERSION,
            )
        self.validator = EvidenceGroundingValidator(
            min_evidence_chars=self.config.MIN_EVIDENCE_CHARS,
            strict_offset_matching=self.config.REQUIRE_EXACT_SPANS,
        )
        self.sampler = ChunkSampler(
            seed=self.config.DEFAULT_RANDOM_SEED,
            target_size=self.config.DEFAULT_SAMPLE_SIZE,
        )
        self.evaluator = ExtractionEvaluator()
        self.reporter = ExtractionReporter()

    def run_pilot(
        self,
        target_size: Optional[int] = None,
        seed: Optional[int] = None,
        chunks_jsonl_path: Optional[Path] = None,
    ) -> Tuple[ExtractionBatchResult, ExtractionEvaluationReport]:
        """Execute complete extraction pilot workflow on Stratified Strategy A chunks."""
        t_start = time.perf_counter()
        timestamp = datetime.now(timezone.utc).isoformat()

        # 1. Ensure output and manifest directories exist
        self.config.ensure_directories()

        # 2. Load input chunks
        input_path = chunks_jsonl_path or self.config.v030_chunks_path
        if not input_path.exists():
            raise FileNotFoundError(f"Upstream chunks file not found at {input_path}")

        logger.info(f"Loading Strategy A chunks from {input_path}...")
        all_chunks = self.sampler.load_chunks_from_jsonl(input_path)
        logger.info(f"Loaded {len(all_chunks)} chunks from upstream dataset.")

        # 3. Deterministic Stratified Sampling
        if target_size:
            self.sampler.target_size = target_size
        if seed is not None:
            self.sampler.seed = seed

        sampled_chunks, sample_manifest_records = self.sampler.select_pilot_chunks(all_chunks)
        chunk_map: Dict[str, ProcessedChunk] = {c.chunk_id: c for c in sampled_chunks}

        # Save sample manifest immediately for auditability
        sample_manifest_path = self.config.manifests_dir / f"scientific_extraction_{self.config.EXTRACTION_PIPELINE_VERSION}_sample_manifest.json"
        with open(sample_manifest_path, "w", encoding="utf-8") as f:
            json.dump([s.__dict__ for s in sample_manifest_records], f, indent=2)

        # 4. Execute extraction across sampled chunks
        logger.info(f"Extracting scientific knowledge from {len(sampled_chunks)} chunks...")
        raw_entities: List[ScientificEntityRecord] = []
        raw_statements: List[ScientificStatementRecord] = []
        raw_relations: List[ScientificRelationRecord] = []

        for chk in sampled_chunks:
            ents, stmts, rels = self.extractor.extract(chk)
            raw_entities.extend(ents)
            raw_statements.extend(stmts)
            raw_relations.extend(rels)

        # 5. Evidence grounding and provenance validation
        logger.info("Executing strict evidence grounding and provenance validation...")
        validated_entities: List[ScientificEntityRecord] = []
        validated_statements: List[ScientificStatementRecord] = []
        validated_relations: List[ScientificRelationRecord] = []
        rejected_records: List[Dict[str, Any]] = []

        for ent in raw_entities:
            chk = chunk_map.get(ent.provenance.chunk_id)
            val_ent = self.validator.validate_entity(ent, chk)
            if val_ent.validation_status == ValidationStatus.REJECTED:
                rejected_records.append({
                    "record_id": val_ent.record_id,
                    "record_type": "ENTITY",
                    "category": val_ent.category.value,
                    "surface_text": val_ent.surface_text,
                    "chunk_id": val_ent.provenance.chunk_id,
                    "validation_notes": val_ent.validation_notes,
                })
            else:
                validated_entities.append(val_ent)

        for stmt in raw_statements:
            chk = chunk_map.get(stmt.provenance.chunk_id)
            val_stmt = self.validator.validate_statement(stmt, chk)
            if val_stmt.validation_status == ValidationStatus.REJECTED:
                rejected_records.append({
                    "record_id": val_stmt.record_id,
                    "record_type": "STATEMENT",
                    "category": val_stmt.category.value,
                    "surface_text": val_stmt.surface_text,
                    "chunk_id": val_stmt.provenance.chunk_id,
                    "validation_notes": val_stmt.validation_notes,
                })
            else:
                validated_statements.append(val_stmt)

        known_record_ids = {e.record_id for e in validated_entities}.union(
            {s.record_id for s in validated_statements}
        )

        for rel in raw_relations:
            chk = chunk_map.get(rel.provenance.chunk_id)
            val_rel = self.validator.validate_relation(rel, chk, known_record_ids)
            if val_rel.validation_status == ValidationStatus.REJECTED:
                rejected_records.append({
                    "record_id": val_rel.relation_id,
                    "record_type": "RELATION",
                    "category": val_rel.relation_type.value,
                    "surface_text": val_rel.surface_text or "",
                    "chunk_id": val_rel.provenance.chunk_id,
                    "validation_notes": val_rel.validation_notes,
                })
            else:
                validated_relations.append(val_rel)

        duration_ms = (time.perf_counter() - t_start) * 1000.0

        # 6. Evaluation metrics computation
        eval_report = self.evaluator.evaluate_batch(
            chunks_count=len(sampled_chunks),
            entities=validated_entities,
            statements=validated_statements,
            relations=validated_relations,
            rejected_records=rejected_records,
            duration_ms=duration_ms,
            pipeline_version=self.config.EXTRACTION_PIPELINE_VERSION,
            schema_version=self.config.EXTRACTION_SCHEMA_VERSION,
            timestamp=timestamp,
        )

        # 7. Persist versioned extraction outputs in dataset/processed/v0.4.0/
        self._persist_versioned_outputs(
            validated_entities,
            validated_statements,
            validated_relations,
            rejected_records,
        )

        # 8. Generate reports and human annotation benchmarks
        self._generate_reports_and_benchmarks(
            sampled_chunks,
            sample_manifest_records,
            validated_entities,
            validated_statements,
            validated_relations,
            eval_report,
        )

        batch_result = ExtractionBatchResult(
            batch_id=f"batch_ext_{self.config.EXTRACTION_PIPELINE_VERSION}_{int(time.time())}",
            pipeline_version=self.config.EXTRACTION_PIPELINE_VERSION,
            timestamp=timestamp,
            total_chunks_processed=len(sampled_chunks),
            entities=validated_entities,
            statements=validated_statements,
            relations=validated_relations,
            rejected_count=len(rejected_records),
            validation_summary={
                "VALIDATED": eval_report.total_validated_records,
                "NEEDS_REVIEW": eval_report.total_needs_review_records,
                "REJECTED": eval_report.total_rejected_records,
            },
        )

        logger.info(
            f"Phase 3 Extraction complete: {len(validated_entities)} entities, "
            f"{len(validated_statements)} statements, {len(validated_relations)} relations "
            f"across {len(sampled_chunks)} chunks ({duration_ms:.1f} ms)."
        )

        return batch_result, eval_report

    def _persist_versioned_outputs(
        self,
        entities: List[ScientificEntityRecord],
        statements: List[ScientificStatementRecord],
        relations: List[ScientificRelationRecord],
        rejected: List[Dict[str, Any]],
    ) -> None:
        """Write structured JSONL files to versioned dataset directory."""
        out_dir = self.config.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        # A. Extracted records (Entities and Statements)
        records_path = out_dir / "extracted_records.jsonl"
        with open(records_path, "w", encoding="utf-8") as f:
            for ent in entities:
                f.write(json.dumps(ent.model_dump()) + "\n")
            for stmt in statements:
                f.write(json.dumps(stmt.model_dump()) + "\n")

        # B. Extracted relationships
        rels_path = out_dir / "extracted_relationships.jsonl"
        with open(rels_path, "w", encoding="utf-8") as f:
            for rel in relations:
                f.write(json.dumps(rel.model_dump()) + "\n")

        # C. Rejected records audit
        rej_path = out_dir / "rejected_records.jsonl"
        with open(rej_path, "w", encoding="utf-8") as f:
            for rej in rejected:
                f.write(json.dumps(rej) + "\n")

        logger.info(f"Persisted versioned extraction outputs to {out_dir}")

    def _generate_reports_and_benchmarks(
        self,
        chunks: List[ProcessedChunk],
        sample_records: List[SampledChunkRecord],
        entities: List[ScientificEntityRecord],
        statements: List[ScientificStatementRecord],
        relations: List[ScientificRelationRecord],
        eval_report: ExtractionEvaluationReport,
    ) -> None:
        """Generate manifest, quality reports, annotation template, and guidelines."""
        m_dir = self.config.manifests_dir
        v = self.config.EXTRACTION_PIPELINE_VERSION

        # 1. Manifest
        manifest_path = m_dir / f"scientific_extraction_pilot_{v}_manifest.json"
        self.reporter.export_experiment_manifest_json(eval_report, sample_records, manifest_path)

        # 2. Quality Report JSON
        q_json_path = m_dir / f"scientific_extraction_pilot_{v}_quality_report.json"
        self.reporter.export_quality_report_json(eval_report, q_json_path)

        # 3. Quality Report Markdown
        q_md_path = m_dir / f"scientific_extraction_pilot_{v}_report.md"
        self.reporter.export_quality_report_md(eval_report, sample_records, q_md_path)

        # 4. Human Annotation Template CSV
        template_csv_path = m_dir / f"scientific_extraction_{v}_annotation_template.csv"
        self.reporter.export_human_annotation_template_csv(
            chunks, sample_records, entities, statements, relations, template_csv_path
        )

        # 5. Human Annotation Guidelines Markdown
        guidelines_path = m_dir / f"scientific_extraction_{v}_annotation_guidelines.md"
        self.reporter.export_annotation_guidelines_md(guidelines_path)
