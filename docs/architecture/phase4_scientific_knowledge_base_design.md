# ResearchGraph Phase 4: Scientific Knowledge Base Architecture & Design Document (v0.5.0)

**Document Version:** 1.0.0  
**Phase:** Phase 4 — Scientific Knowledge Base  
**Target Release:** `v0.5.0`  
**Schema Version:** `0.5.0`  
**Status:** APPROVED FOR IMPLEMENTATION  
**Date:** 2026-10-18  
**Author:** Senior Research Engineer & Scientific Knowledge Representation Architect  

---

## 1. Executive Summary & Epistemological Stance

Phase 4 of ResearchGraph transitions extracted scientific literature items from isolated per-chunk records into a unified, normalized, persistent, and queryable **Scientific Knowledge Base (SKB)**.

ResearchGraph is an epistemological discovery engine designed to uncover non-obvious cross-domain scientific linkages and formulate testable research hypotheses. It is strictly **NOT** a generic RAG chatbot, PDF summarizer, or citation-network visualizer.

### Core Architectural Principles
1. **Evidence-Grounded Lineage**: Every canonical entity, statement, and relationship in the knowledge base must preserve full character-level evidence spans and cryptographic provenance back to its originating chunk, paper, and PDF hash.
2. **Conservative Normalization & Explicit Alias Boundaries**: Entities are canonicalized using deterministic lexical rules and explicit alias dictionaries. Concepts are never merged on superficial string similarity. Candidate aliases are explicitly distinguished from confirmed mappings.
3. **Preservation of Epistemological Status**: Author claims (`CLAIM`), empirical findings (`RESULT`), stated constraints (`LIMITATION`), and prospective research (`FUTURE_DIRECTION`) remain strictly typed with their author attribution (`AUTHOR_STATED` vs `CITED_PRIOR_WORK`). An author claim is never promoted to an established universal fact.
4. **Referential Integrity & Quarantine Safety**: Relationships must connect strictly valid, existing endpoint nodes. Dangling edges or corrupt inputs are quarantined with diagnostic explanations, never silently dropped or accepted without valid endpoints.
5. **Reproducibility & Complete Rebuildability**: The knowledge base is fully rebuildable from upstream Phase 1 (`v0.1.0`), Phase 2 (`v0.3.0`), and Phase 3 (`v0.4.0`/`v0.4.1`) artifacts. Repeated builds produce bit-for-bit identical canonical identifiers and record structures.
6. **Strict Phase Boundary Adherence**: Embeddings, vector indices, Neo4j/graph databases, cross-domain discovery algorithms, and hypothesis generation are deferred to Phases 5+. Phase 4 delivers the foundational scientific knowledge representation layer.

---

## 2. Canonical Knowledge Base Data Model (`Schema Version 0.5.0`)

The canonical schema is defined in [`dataset/schemas/scientific_knowledge_base.py`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/dataset/schemas/scientific_knowledge_base.py), building on established Phase 1–3 models.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CanonicalPaperNode                            │
│  paper_id, doi, title, abstract, venue, authors, publication_year      │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │ 1..*                           │ 1..*
                    ▼                                ▼
┌──────────────────────────────────────┐   ┌─────────────────────────────────────┐
│       CanonicalStatementNode         │   │            EntityMention            │
│  statement_id, category (CLAIM,      │   │  mention_id, surface_text, offsets  │
│  RESULT, LIMITATION, FUTURE_DIR),    │   │  evidence, provenance, chunk_id     │
│  evidence, provenance, attribution   │   └──────────────────┬──────────────────┘
└───────────────────┬──────────────────┘                      │ *..1
                    │                                         ▼
                    │                              ┌─────────────────────────────┐
                    │                              │    CanonicalEntityNode      │
                    │                              │  entity_id, category,       │
                    │                              │  canonical_name, aliases    │
                    │                              │  mentions_count, papers     │
                    │                              └──────────────┬──────────────┘
                    ▼                                             │
┌─────────────────────────────────────────────────────────────────┴──────────────┐
│                          CanonicalRelationshipNode                             │
│  relationship_id, relation_type (ADDRESSES, USES, IMPROVES, LIMITED_BY, etc.)  │
│  source_id (Entity/Statement), target_id (Entity/Statement)                    │
│  evidence, provenance, attribution, extraction_version                         │
└────────────────────────────────────────────────────────────────────────────────┘
```

### A. CanonicalPaperNode
Represents the scholarly publication context:
- `paper_id`: Stable canonical paper ID (`rg_doi_...`).
- `doi`: External digital object identifier.
- `arxiv_id`: External preprint identifier (if present).
- `title`: Normalized publication title.
- `abstract`: Abstract text.
- `publication_year`: Integer year.
- `venue`: Publication venue name.
- `authors`: List of author names.
- `topics`: Domain concepts/topics from ingestion metadata.
- `open_access`: Open access license/status.
- `source_schema_version`: Provenance schema version (`0.2.0`).

### B. CanonicalEntityNode & EntityMention
Distinguishes universal scientific concepts from individual textual occurrences:
1. **EntityMention**:
   - `mention_id`: Deterministic ID linking mention to extraction (`ent_men_{hash[:12]}`).
   - `entity_id`: Foreign key to canonical entity.
   - `surface_text`: Exact surface text in chunk.
   - `category`: `ScientificEntityType` (METHOD, PROBLEM, BOTTLENECK, TASK, DATASET, METRIC, DOMAIN, ASSUMPTION).
   - `evidence`: Character-level `EvidenceSpan`.
   - `provenance`: Full `ExtractionProvenance` (paper_id, chunk_id, section, file_hash).
   - `extraction_version`: Originating extractor version (`v0.4.0` or `v0.4.1`).
   - `validation_status`: `VALIDATED`, `NEEDS_REVIEW`, `REJECTED`.
   - `upstream_record_id`: Originating extraction `record_id`.
2. **CanonicalEntityNode**:
   - `entity_id`: Deterministic hash ID based on `(category, canonical_name)`: `kb_ent_{category.lower()}_{hash[:12]}`.
   - `category`: `ScientificEntityType`.
   - `canonical_name`: Cleaned, normalized representative name.
   - `aliases`: Set of observed surface variants confirmed as aliases.
   - `mentions_count`: Frequency count across corpus.
   - `paper_ids`: Set of distinct canonical paper IDs where entity appears.
   - `chunk_ids`: Set of distinct chunk IDs containing mentions.
   - `validation_status`: Aggregated validation status.
   - `alias_resolution_status`: `CONFIRMED` or `CANDIDATE`.

### C. CanonicalStatementNode
Captures propositions, claims, and empirical findings without distorting meaning:
- `statement_id`: Stable ID `kb_stmt_{hash[:12]}` based on `(paper_id, chunk_id, normalized_statement)`.
- `category`: `ScientificStatementType` (CLAIM, RESULT, LIMITATION, FUTURE_DIRECTION, FAILURE_MODE).
- `surface_text`: Verbatim sentence or clause.
- `normalized_statement`: Normalized statement string.
- `paper_id`: Originating paper ID.
- `chunk_id`: Containing chunk ID.
- `evidence`: `EvidenceSpan` with character offsets.
- `provenance`: `ExtractionProvenance`.
- `attribution`: `AttributionType` (`AUTHOR_STATED`, `CITED_PRIOR_WORK`, `SYSTEM_INFERRED`).
- `confidence_score`: Float score.
- `extraction_version`: Pipeline execution version (`v0.4.0` or `v0.4.1`).
- `validation_status`: `VALIDATED`, `NEEDS_REVIEW`, `REJECTED`.
- `related_entity_ids`: Canonical entity IDs mentioned in the statement.
- `upstream_record_id`: Originating extraction `record_id`.

### D. CanonicalRelationshipNode
Represents verified directional relational assertions:
- `relationship_id`: Stable ID `kb_rel_{hash[:12]}` based on `(source_id, relation_type, target_id, chunk_id)`.
- `relation_type`: `ScientificRelationType` (ADDRESSES, USES, IMPROVES, OUTPERFORMS, LIMITED_BY, EVALUATED_ON, ASSUMES, REPORTS, SUGGESTS, CONTRADICTS).
- `source_id`: Canonical ID of subject (must exist in entities or statements).
- `target_id`: Canonical ID of object (must exist in entities or statements).
- `source_type`: `"ENTITY"` or `"STATEMENT"`.
- `target_type`: `"ENTITY"` or `"STATEMENT"`.
- `paper_id`: Canonical paper ID.
- `chunk_id`: Containing chunk ID.
- `surface_text`: Connecting predicate phrase or sentence excerpt.
- `evidence`: Supporting `EvidenceSpan`.
- `provenance`: Full `ExtractionProvenance`.
- `attribution`: `AttributionType`.
- `extraction_version`: Extractor version (`v0.4.0` or `v0.4.1`).
- `validation_status`: `VALIDATED`, `NEEDS_REVIEW`, `REJECTED`.
- `upstream_relation_id`: Originating extraction `relation_id`.

### E. QuarantinedRecord
Captures any record that fails validation, preventing silent data loss:
- `quarantine_id`: Stable ID `kb_quar_{hash[:12]}`.
- `record_type`: `"ENTITY"`, `"STATEMENT"`, `"RELATIONSHIP"`, or `"PAPER"`.
- `raw_payload`: Complete original JSON record.
- `quarantine_reason`: Explicit diagnostic code (e.g. `DANGLING_RELATION_ENDPOINT`, `MISSING_PROVENANCE_FIELD`, `INVALID_SPAN_BOUNDS`).
- `source_version`: Upstream pipeline version.
- `timestamp`: UTC ingestion timestamp.

---

## 3. Identity Resolution, Normalization, and Alias Strategy

### Normalization Pipeline
1. **Unicode & Whitespace Normalization**: NFKC normalization, strip leading/trailing whitespace, collapse internal consecutive spaces.
2. **Case & Punctuation Regularization**: Retain surface casing for display; lowercase for matching; strip trailing punctuation (periods, commas, colons) that attach to token boundaries during extraction.
3. **Plural & Formatting Suffixes**: Standardize morphological plurals for count nouns without truncating acronyms or proper nouns.

### Conservative Alias Disambiguation
An explicit, auditable alias registry ([`pipelines/knowledge_base/alias_registry.py`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/pipelines/knowledge_base/alias_registry.py)) partitions mappings into two strict tiers:
1. **Confirmed Aliases (`CONFIRMED`)**:
   - Acronym / Full Name pairs established in scholarly consensus:
     - `cnn` $\leftrightarrow$ `convolutional neural network`
     - `svm` $\leftrightarrow$ `support vector machine`
     - `lstm` $\leftrightarrow$ `long short-term memory`
     - `nlp` $\leftrightarrow$ `natural language processing`
     - `vosviewer` $\leftrightarrow$ `vosviewer software`
     - `scopus` $\leftrightarrow$ `scopus database`
     - `web of science` $\leftrightarrow$ `web of science database`
2. **Candidate Aliases (`CANDIDATE`)**:
   - High lexical similarity or shared head nouns (e.g. `cluster analysis` vs `hierarchical clustering`) that are tracked as candidate aliases but **NOT automatically merged** without explicit verification.
3. **Explicit Non-Merges (`SEPARATE`)**:
   - Guard against conflating distinct concepts (e.g. `machine learning` $\neq$ `deep learning`; `accuracy` $\neq$ `balanced accuracy`).

### Deterministic Stable Identifier Generation
All identifiers are computed via deterministic SHA-256 hashes over canonical composite keys:
- Canonical Entity ID: `kb_ent_{category.lower()}_{sha256(category + ":" + canonical_name)[:12]}`
- Canonical Statement ID: `kb_stmt_{sha256(paper_id + ":" + chunk_id + ":" + category + ":" + normalized_statement)[:12]}`
- Canonical Relationship ID: `kb_rel_{sha256(source_id + ":" + relation_type + ":" + target_id + ":" + chunk_id)[:12]}`
- Entity Mention ID: `ent_men_{sha256(chunk_id + ":" + category + ":" + start_char + ":" + end_char)[:12]}`

---

## 4. Persistence Architecture: Snapshot Files + Embedded SQLite

We implement a simple, zero-external-dependency persistence architecture:

### 1. Versioned Artifact Snapshot Directory (`dataset/processed/v0.5.0/`)
- `papers.jsonl` / `papers.parquet`
- `entities.jsonl` / `entities.parquet`
- `entity_mentions.jsonl` / `entity_mentions.parquet`
- `statements.jsonl` / `statements.parquet`
- `relationships.jsonl` / `relationships.parquet`
- `quarantined_records.jsonl`
- `alias_mappings.json`

### 2. Embedded Relational Knowledge Base Engine (`knowledge_base.db`)
- Stored at `dataset/processed/v0.5.0/knowledge_base.db`.
- Managed using standard Python `sqlite3` (built into standard library, zero external server processes).
- Indexed schemas with `PRAGMA foreign_keys = ON;`.
- Indexes on `canonical_name`, `category`, `paper_id`, `chunk_id`, `source_id`, `target_id`, `relation_type`.
- Supports atomic rebuilds: can be regenerated deterministically from the snapshot JSONL files in seconds.

---

## 5. Knowledge Ingestion Pipeline Architecture

The ingestion pipeline is implemented in [`pipelines/knowledge_base/pipeline.py`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/pipelines/knowledge_base/pipeline.py):

```text
[Phase 1 Papers (v0.1.0)] ──┐
[Phase 2 Chunks (v0.3.0)] ──┼──> [Stage 1: Load Upstream Inputs]
[Phase 3 Extractions (v0.4.1)] ┘              │
                                              ▼
                             [Stage 2: Schema & Type Validation] ──(fail)──> [Quarantine]
                                              │
                                              ▼
                             [Stage 3: Provenance Verification]  ──(fail)──> [Quarantine]
                                              │
                                              ▼
                             [Stage 4: Normalization & ID Gen]
                                              │
                                              ▼
                             [Stage 5: Alias Disambiguation]
                                              │
                                              ▼
                             [Stage 6: Relationship Validation]  ──(fail)──> [Quarantine]
                                              │
                                              ▼
                             [Stage 7: Snapshot & DB Persistence]
                                              │
                                              ▼
                             [Stage 8: Manifest & Quality Report]
```

### 9 Ingestion Pipeline Stages:
1. **Load Upstream Artifacts**: Load Phase 1 canonical papers, Phase 2 chunks, and Phase 3 extracted records and relationships.
2. **Schema & Field Conformance**: Validate all incoming records against Pydantic models.
3. **Evidence & Provenance Verification**: Verify `EvidenceSpan` and `ExtractionProvenance` (`canonical_id`, `chunk_id`, character offsets).
4. **Conservative Normalization**: Clean strings, resolve canonical forms.
5. **Entity Canonicalization & Alias Resolution**: Group mentions into canonical entities, update mention counts, resolve confirmed aliases.
6. **Relationship Endpoint Verification**: Verify that both `source_id` and `target_id` exist. Flag dangling edges to quarantine.
7. **Quarantine Routing**: Write invalid or ungrounded records to `quarantined_records.jsonl`.
8. **Persistence**: Export JSONL, Parquet, and SQLite database `knowledge_base.db`.
9. **Quality Reporting**: Calculate engineering statistics, referential integrity rates, and emit `knowledge_base_v0.5.0_manifest.json`.

---

## 6. Python Query Interface (`KnowledgeBaseQueryEngine`)

Implemented in [`pipelines/knowledge_base/query.py`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/pipelines/knowledge_base/query.py):
- `get_paper(paper_id: str) -> Optional[CanonicalPaperNode]`
- `list_entities(category: Optional[ScientificEntityType] = None, limit: int = 100, min_mentions: int = 1) -> List[CanonicalEntityNode]`
- `get_statements_by_paper(paper_id: str, statement_type: Optional[ScientificStatementType] = None) -> List[CanonicalStatementNode]`
- `get_records_by_chunk(chunk_id: str) -> Dict[str, Any]`
- `find_methods_for_problem(problem_name_or_id: str) -> List[Dict[str, Any]]`
- `get_relationships_for_entity(entity_id: str, relation_type: Optional[ScientificRelationType] = None, direction: str = "both") -> List[CanonicalRelationshipNode]`
- `trace_entity_mentions(entity_id: str) -> List[EntityMention]`
- `filter_by_extractor_version(version: str) -> Dict[str, Any]`
- `filter_by_validation_status(status: ValidationStatus) -> Dict[str, Any]`
- `get_unresolved_aliases() -> List[Dict[str, Any]]`
- `get_quarantined_records(reason: Optional[str] = None) -> List[QuarantinedRecord]`

---

## 7. Quality and Verification Plan

1. **Automated Schema & Integrity Checks**:
   - Unique ID constraint check (no duplicate entity, statement, or relation IDs).
   - Referential integrity (100% of relationship endpoints exist).
   - Provenance completeness (100% of records link to canonical paper and chunk).
   - Idempotency test (two successive ingestion runs yield bit-for-bit identical tables and record counts).
2. **Test Suite Coverage**:
   - `tests/unit/test_knowledge_base_schema.py`: Schema validation, bounds, and defaults.
   - `tests/unit/test_knowledge_base_normalizer.py`: Normalization, acronym expansion, candidate aliases.
   - `tests/unit/test_knowledge_base_validator.py`: Referential integrity, endpoint validation, quarantine routing.
   - `tests/unit/test_knowledge_base_query.py`: Query engine API across all required query patterns.
   - `tests/integration/test_knowledge_base_pipeline.py`: End-to-end ingestion pipeline, snapshot generation, SQLite export, and idempotency.
3. **Preservation of Existing Tests**:
   - The 126 existing tests across `tests/unit/`, `tests/integration/`, and `backend/tests/` must remain 100% passing.
