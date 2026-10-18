"""Idempotent, Reproducible Knowledge Ingestion Pipeline.

Orchestrates the 9-stage ingestion workflow:
1. Load selected upstream Phase 1, Phase 2, and Phase 3 artifacts.
2. Validate input schemas and required fields.
3. Validate source references and evidence provenance.
4. Normalize entities and statements conservatively.
5. Generate stable cryptographic identifiers and consolidate CanonicalEntityNodes.
6. Resolve confirmed aliases and handle duplicate records.
7. Validate relationship endpoints and predicates, quarantining dangling edges.
8. Persist canonical records to JSONL, Parquet, and embedded SQLite.
9. Produce build manifest and quality report.
Schema Version: 0.5.0
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from dataset.schemas.canonical_paper import Author, Topic, Venue
from dataset.schemas.scientific_knowledge import (
    ScientificEntityType,
    ScientificRelationType,
    ScientificStatementType,
    ValidationStatus,
)
from dataset.schemas.scientific_knowledge_base import (
    AliasMapping,
    AliasResolutionStatus,
    CanonicalEntityNode,
    CanonicalPaperNode,
    CanonicalRelationshipNode,
    CanonicalStatementNode,
    EntityMention,
    KnowledgeBaseManifest,
    QuarantineReason,
    QuarantinedRecord,
)
from pipelines.knowledge_base.alias_registry import (
    CONFIRMED_ALIASES,
    SEPARATE_CONCEPTS,
)
from pipelines.knowledge_base.config import KnowledgeBaseConfig
from pipelines.knowledge_base.normalizer import (
    generate_canonical_entity_id,
    normalize_text,
    resolve_canonical_entity,
)
from pipelines.knowledge_base.reporter import KnowledgeBaseReporter
from pipelines.knowledge_base.storage import KnowledgeBaseStorage, read_jsonl
from pipelines.knowledge_base.validator import (
    VALID_ENTITY_TYPES,
    VALID_STATEMENT_TYPES,
    validate_entity_mention_record,
    validate_relationship_record,
    validate_statement_record,
)

logger = logging.getLogger(__name__)


class ScientificKnowledgeBasePipeline:
    """End-to-end scientific knowledge base builder and ingestion pipeline."""

    def __init__(self, config: Optional[KnowledgeBaseConfig] = None):
        self.config = config or KnowledgeBaseConfig()
        self.storage = KnowledgeBaseStorage(self.config.output_dir)
        self.reporter = KnowledgeBaseReporter(self.config.manifest_dir)

    def run(self) -> KnowledgeBaseManifest:
        """Execute the full 9-stage knowledge base build."""
        logger.info("Starting Scientific Knowledge Base build %s...", self.config.kb_version)

        # ---------------------------------------------------------------------
        # Stage 1: Load selected versioned upstream outputs
        # ---------------------------------------------------------------------
        logger.info("Stage 1: Loading upstream artifacts...")
        upstream_sources: Dict[str, str] = {}

        # 1.1 Papers
        raw_papers = read_jsonl(self.config.papers_path)
        upstream_sources["phase1_canonical_papers"] = str(self.config.papers_path)
        logger.info("Loaded %d raw canonical papers", len(raw_papers))

        # 1.2 Chunks (for provenance boundary checks)
        raw_chunks = read_jsonl(self.config.chunks_path)
        valid_chunk_ids: Set[str] = {c.get("chunk_id") for c in raw_chunks if c.get("chunk_id")}
        upstream_sources["phase2_processed_chunks"] = str(self.config.chunks_path)
        logger.info("Loaded %d processed chunks for reference validation", len(valid_chunk_ids))

        # 1.3 Extractions
        raw_v040_records: List[Dict[str, Any]] = []
        if self.config.ingest_v040_records and self.config.extractions_v040_records_path.exists():
            raw_v040_records = read_jsonl(self.config.extractions_v040_records_path)
            upstream_sources["phase3_v040_extractions"] = str(self.config.extractions_v040_records_path)
            logger.info("Loaded %d raw v0.4.0 extraction records", len(raw_v040_records))

        raw_v041_records: List[Dict[str, Any]] = []
        if self.config.ingest_v041_records and self.config.extractions_v041_records_path.exists():
            raw_v041_records = read_jsonl(self.config.extractions_v041_records_path)
            upstream_sources["phase3_v041_extractions"] = str(self.config.extractions_v041_records_path)
            logger.info("Loaded %d raw v0.4.1 extraction records", len(raw_v041_records))

        # 1.4 Relationships
        raw_relationships: List[Dict[str, Any]] = []
        if self.config.ingest_v040_relationships and self.config.extractions_v040_relationships_path.exists():
            raw_relationships = read_jsonl(self.config.extractions_v040_relationships_path)
            upstream_sources["phase3_v040_relationships"] = str(self.config.extractions_v040_relationships_path)
            logger.info("Loaded %d raw v0.4.0 relationship records", len(raw_relationships))

        # Initialize paper nodes
        papers_dict: Dict[str, CanonicalPaperNode] = {}
        for p in raw_papers:
            pid = p.get("canonical_id")
            if not pid:
                continue
            authors = [Author(**a) for a in p.get("authors", []) if isinstance(a, dict)]
            topics = [Topic(**t) for t in p.get("topics", []) if isinstance(t, dict)]
            venue = Venue(**p["venue"]) if p.get("venue") and isinstance(p["venue"], dict) else None
            oa_url = p.get("open_access", {}).get("oa_url") if isinstance(p.get("open_access"), dict) else None

            node = CanonicalPaperNode(
                paper_id=pid,
                schema_version=self.config.schema_version,
                doi=p.get("doi"),
                arxiv_id=p.get("arxiv_id"),
                title=p.get("title", "Untitled"),
                abstract=p.get("abstract"),
                publication_year=p.get("publication_year"),
                venue=venue,
                authors=authors,
                topics=topics,
                open_access_url=oa_url,
                file_hash=p.get("file_hash"),
            )
            papers_dict[pid] = node

        # ---------------------------------------------------------------------
        # Stages 2 & 3: Validate input schemas, required fields, and provenance
        # ---------------------------------------------------------------------
        logger.info("Stages 2 & 3: Validating extraction records and provenance...")
        quarantined_records: List[QuarantinedRecord] = []
        validated_mentions: List[EntityMention] = []
        validated_statements: Dict[str, CanonicalStatementNode] = {}
        upstream_to_kb: Dict[str, str] = {}

        # Track mentions by deterministic mention_id to enforce idempotency
        seen_mention_ids: Set[str] = set()

        # Ingest extraction records: prioritize v0.4.1, supplemented by v0.4.0
        all_record_inputs: List[Tuple[Dict[str, Any], str]] = []
        if self.config.ingest_v040_records:
            all_record_inputs.extend([(r, "v0.4.0") for r in raw_v040_records])
        if self.config.ingest_v041_records:
            all_record_inputs.extend([(r, "v0.4.1") for r in raw_v041_records])

        for raw_rec, source_ver in all_record_inputs:
            category_str = raw_rec.get("category", "")
            upstream_id = raw_rec.get("record_id", "")

            # Check if this record is a Scientific Statement
            if category_str in VALID_STATEMENT_TYPES:
                stmt, quar = validate_statement_record(raw_rec, source_version=source_ver)
                if quar:
                    quarantined_records.append(quar)
                elif stmt:
                    # Deduplicate statements deterministically
                    if stmt.statement_id not in validated_statements:
                        validated_statements[stmt.statement_id] = stmt
                    if upstream_id:
                        upstream_to_kb[upstream_id] = stmt.statement_id

            # Check if this record is a Scientific Entity
            elif category_str in VALID_ENTITY_TYPES:
                mention, quar = validate_entity_mention_record(raw_rec, source_version=source_ver)
                if quar:
                    quarantined_records.append(quar)
                elif mention:
                    # Enforce mention idempotency
                    if mention.mention_id not in seen_mention_ids:
                        seen_mention_ids.add(mention.mention_id)
                        validated_mentions.append(mention)
                    # Track upstream ID mapping for relationship resolution
                    if upstream_id:
                        # Will be updated to entity_id during consolidation
                        upstream_to_kb[upstream_id] = mention.mention_id

            else:
                # Unknown category
                from pipelines.knowledge_base.validator import create_quarantine_record
                quarantined_records.append(
                    create_quarantine_record(
                        "UNKNOWN",
                        QuarantineReason.SCHEMA_VALIDATION_ERROR,
                        f"Unrecognized scientific category: {category_str}",
                        raw_rec,
                        source_ver,
                        upstream_id,
                    )
                )

        logger.info(
            "Validated %d unique entity mentions, %d statements, %d quarantined",
            len(validated_mentions),
            len(validated_statements),
            len(quarantined_records),
        )

        # ---------------------------------------------------------------------
        # Stages 4, 5, 6: Normalization, Canonical Entity Consolidation & Alias Resolution
        # ---------------------------------------------------------------------
        logger.info("Stages 4, 5, 6: Normalizing entities and consolidating canonical nodes...")
        
        # Group mentions by (category, canonical_name)
        entity_groups: Dict[Tuple[str, str], List[EntityMention]] = defaultdict(list)
        entity_alias_status: Dict[Tuple[str, str], AliasResolutionStatus] = {}
        entity_aliases: Dict[Tuple[str, str], Set[str]] = defaultdict(set)

        for mention in validated_mentions:
            canon_name, observed_aliases, status = resolve_canonical_entity(
                mention.surface_text,
                mention.category,
            )
            key = (mention.category.value, canon_name)
            entity_groups[key].append(mention)
            entity_aliases[key].add(mention.surface_text)
            for a in observed_aliases:
                entity_aliases[key].add(a)

            # Preserve highest confidence alias status
            if key not in entity_alias_status or status == AliasResolutionStatus.CONFIRMED:
                entity_alias_status[key] = status

        # Construct CanonicalEntityNodes and update mention foreign keys
        canonical_entities: Dict[str, CanonicalEntityNode] = {}
        mention_id_to_entity_id: Dict[str, str] = {}

        for (cat_str, canon_name), mentions_list in entity_groups.items():
            category = ScientificEntityType(cat_str)
            entity_id = generate_canonical_entity_id(category, canon_name)

            paper_ids = sorted(list({m.paper_id for m in mentions_list}))
            chunk_ids = sorted(list({m.chunk_id for m in mentions_list}))
            mention_ids = [m.mention_id for m in mentions_list]
            earliest_ver = min(m.extraction_version for m in mentions_list)

            # Link mentions to this canonical entity
            for m in mentions_list:
                m.entity_id = entity_id
                mention_id_to_entity_id[m.mention_id] = entity_id

            node = CanonicalEntityNode(
                entity_id=entity_id,
                schema_version=self.config.schema_version,
                category=category,
                canonical_name=canon_name,
                aliases=sorted(list(entity_aliases[(cat_str, canon_name)])),
                mentions_count=len(mentions_list),
                paper_ids=paper_ids,
                chunk_ids=chunk_ids,
                mention_ids=mention_ids,
                validation_status=ValidationStatus.VALIDATED,
                alias_resolution_status=entity_alias_status[(cat_str, canon_name)],
                first_seen_version=earliest_ver,
            )
            canonical_entities[entity_id] = node

        # Update upstream_to_kb mapping: point upstream record IDs directly to canonical entity_id
        for upstream_id, target in list(upstream_to_kb.items()):
            if target in mention_id_to_entity_id:
                upstream_to_kb[upstream_id] = mention_id_to_entity_id[target]

        logger.info("Consolidated into %d canonical entity nodes", len(canonical_entities))

        # ---------------------------------------------------------------------
        # Stage 7: Validate relationship endpoints and predicates
        # ---------------------------------------------------------------------
        logger.info("Stage 7: Validating relationship endpoints and predicates...")
        canonical_relationships: Dict[str, CanonicalRelationshipNode] = {}
        valid_entity_ids = set(canonical_entities.keys())
        valid_statement_ids = set(validated_statements.keys())

        for raw_rel in raw_relationships:
            rel_node, rel_quar = validate_relationship_record(
                raw_rel,
                valid_entity_ids=valid_entity_ids,
                valid_statement_ids=valid_statement_ids,
                upstream_to_kb=upstream_to_kb,
                source_version="v0.4.0",
            )
            if rel_quar:
                quarantined_records.append(rel_quar)
            elif rel_node:
                # Deduplicate relationships idempotently
                if rel_node.relationship_id not in canonical_relationships:
                    canonical_relationships[rel_node.relationship_id] = rel_node

        logger.info(
            "Validated %d canonical relationships, total quarantined records: %d",
            len(canonical_relationships),
            len(quarantined_records),
        )

        # ---------------------------------------------------------------------
        # Link Paper Node Entity, Statement, and Relationship Counts
        # ---------------------------------------------------------------------
        paper_entities_count: Dict[str, Set[str]] = defaultdict(set)
        for m in validated_mentions:
            paper_entities_count[m.paper_id].add(m.entity_id)

        paper_stmts_count: Dict[str, int] = defaultdict(int)
        for s in validated_statements.values():
            paper_stmts_count[s.paper_id] += 1

        paper_rels_count: Dict[str, int] = defaultdict(int)
        for r in canonical_relationships.values():
            paper_rels_count[r.paper_id] += 1

        for pid, paper_node in papers_dict.items():
            paper_node.total_entities_count = len(paper_entities_count.get(pid, set()))
            paper_node.total_statements_count = paper_stmts_count.get(pid, 0)
            paper_node.total_relationships_count = paper_rels_count.get(pid, 0)

        # Build alias mappings audit list
        alias_mappings_list: List[AliasMapping] = []
        for (cat_str, surf), canon in CONFIRMED_ALIASES.items():
            alias_mappings_list.append(
                AliasMapping(
                    surface_form=surf,
                    canonical_name=canon,
                    category=ScientificEntityType(cat_str),
                    status=AliasResolutionStatus.CONFIRMED,
                    rationale="Formally curated acronym/lexical variant expansion",
                )
            )

        # ---------------------------------------------------------------------
        # Stage 8: Persist canonical records to JSONL, Parquet, and SQLite
        # ---------------------------------------------------------------------
        logger.info("Stage 8: Persisting canonical records to %s...", self.config.output_dir)
        papers_list = list(papers_dict.values())
        entities_list = sorted(canonical_entities.values(), key=lambda e: e.entity_id)
        statements_list = sorted(validated_statements.values(), key=lambda s: s.statement_id)
        relationships_list = sorted(canonical_relationships.values(), key=lambda r: r.relationship_id)

        snapshot_counts = self.storage.save_snapshots_jsonl(
            papers=papers_list,
            entities=entities_list,
            mentions=validated_mentions,
            statements=statements_list,
            relationships=relationships_list,
            quarantine=quarantined_records,
            aliases=alias_mappings_list,
        )

        parquet_files: Optional[Dict[str, str]] = None
        if self.config.save_parquet:
            parquet_files = self.storage.save_parquet(
                papers=papers_list,
                entities=entities_list,
                mentions=validated_mentions,
                statements=statements_list,
                relationships=relationships_list,
            )

        sqlite_path: Optional[str] = None
        if self.config.save_sqlite:
            sqlite_path = self.storage.save_sqlite(
                papers=papers_list,
                entities=entities_list,
                mentions=validated_mentions,
                statements=statements_list,
                relationships=relationships_list,
                quarantine=quarantined_records,
                aliases=alias_mappings_list,
            )

        # ---------------------------------------------------------------------
        # Stage 9: Produce manifest and quality report
        # ---------------------------------------------------------------------
        logger.info("Stage 9: Generating build manifest and quality report...")
        manifest = self.reporter.generate_manifest(
            kb_version=self.config.kb_version,
            schema_version=self.config.schema_version,
            upstream_sources=upstream_sources,
            papers=papers_list,
            entities=entities_list,
            mentions=validated_mentions,
            statements=statements_list,
            relationships=relationships_list,
            quarantine=quarantined_records,
            aliases=alias_mappings_list,
        )

        self.reporter.save_manifest(manifest)
        self.reporter.save_quality_report(
            manifest=manifest,
            output_snapshots=snapshot_counts,
            sqlite_path=sqlite_path,
            parquet_files=parquet_files,
        )

        logger.info("Phase 4 Knowledge Base build completed successfully.")
        return manifest
