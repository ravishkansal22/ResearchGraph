# Changelog

All notable changes to the **ResearchGraph** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.2] - 2026-10-07

### Added
- **Query-Driven On-Demand Full-Text Acquisition Strategy**:
  - `MetadataCandidateRetriever` (`pipelines/ingestion/fulltext/retrieval.py`): Metadata-first lexical and token-overlap retrieval engine that ranks candidate papers dynamically without downloading the corpus. Gracefully handles missing abstracts via dynamic weight rebalancing.
  - `PDFValidator` (`pipelines/ingestion/fulltext/validator.py`): Structural validator that checks magic bytes (`%PDF-`), flags HTML landing/error pages masquerading as PDFs, calculates SHA-256 checksums, and verifies basic text extraction feasibility using `pypdf`/`fitz`.
  - `OnDemandFullTextAcquirer` (`pipelines/ingestion/fulltext/acquirer.py`): On-demand acquirer with multi-tier source priority (direct OA PDF -> arXiv -> institutional repository -> general OA), local cache checking, and idempotency.
- **Explicit Full-Text Lifecycle States**:
  - `FullTextAcquisitionStatus`: `NOT_CHECKED`, `DISCOVERABLE`, `QUEUED`, `DOWNLOADING`, `DOWNLOADED`, `FAILED`, `UNAVAILABLE`.
  - `DocumentProcessingStatus`: `NOT_PROCESSED`, `PARSED`, `PARSE_FAILED`.
  - `PDFValidationStatus`: `SUCCESS_PDF`, `HTML_NOT_PDF`, `PAYWALL`, `BROKEN_LINK`, `TIMEOUT`, `HTTP_ERROR`, `EMPTY_FILE`, `INVALID_PDF`, `UNAVAILABLE`, `UNKNOWN`.
  - `AcquisitionResult` model for complete diagnostic metadata.
- **Pilot Full-Text Experiment & Artifacts (25-paper benchmark)**:
  - `dataset/manifests/fulltext_pilot_v0.1.2_results.csv`: Complete per-paper diagnostic audit across queries and document types.
  - `dataset/manifests/fulltext_pilot_v0.1.2_manifest.json`: Experiment summary with measured storage and download metrics.
  - `dataset/manifests/fulltext_pilot_v0.1.2_report.md`: Comprehensive empirical report and architectural recommendations.
- **Comprehensive Full-Text Test Suite**:
  - Added unit tests in `test_candidate_retrieval.py`, `test_pdf_validator.py`, and `test_fulltext_acquirer.py`, expanding test suite to 46 passing tests.

---

## [0.1.1] - 2026-10-07

### Added
- **Document Type Classification**:
  - Standardized `DocumentType` enum (`RESEARCH_ARTICLE`, `CONFERENCE_PAPER`, `REVIEW`, `SURVEY`, `BOOK_CHAPTER`, `EDITORIAL`, `FRONT_MATTER`, `OTHER`, `UNKNOWN`).
  - Added document type normalizer (`pipelines/ingestion/normalizers/document_type.py`) mapping heterogeneous source types and applying title heuristic cues.
- **Granular Publication Date Model**:
  - Added structured date fields (`online_publication_date`, `print_publication_date`, `issued_date`, `published_date`, `publication_year`) in `CanonicalPaper` schema.
  - Added publication date normalizer (`pipelines/ingestion/normalizers/dates.py`) supporting Crossref date-parts and preserving advance print dates (e.g. 2027 book chapters) without confusing historical research availability.
- **Full-Text Status Clarification**:
  - Explicit distinction between `DISCOVERABLE` (OA link available in metadata) and `DOWNLOADED` (physical artifact stored locally), resolving ambiguous `FULLTEXT_AVAILABLE` nomenclature.
- **Reproducible Dataset Audit Benchmarks**:
  - `dataset/manifests/v0.1.1_relevance_audit.csv`: Deterministic 100-paper evaluation sample (seed 42) with pending human review labels (`CORE_AI`, `AI_ADJACENT`, `NOT_RELEVANT`).
  - `dataset/manifests/v0.1.1_dedup_audit.csv`: Deterministic 30-case deduplication audit sample analyzing multi-signal matches and resolving ambiguous candidate pairs.
- **Dedicated Test Coverage**:
  - Added test suites for document type classification (`test_document_type.py`), granular date models (`test_dates.py`), and full-text status distinctions (`test_fulltext_status.py`), bringing total passing tests to 35.

### Changed
- Upgraded `schema_version` to `0.2.0`.
- Regenerated dataset release artifacts in `dataset/processed/v0.1.1/` (Parquet and JSONL), leaving `v0.1.0` immutable.
- Updated `QualityReporter` with exact metadata completeness percentages, document type breakdown, and separated discovery/download metrics.

---

## [0.1.0] - 2026-10-04

### Added
- **Canonical Paper Representation**:
  - Implemented source-independent `CanonicalPaper` schema in `dataset/schemas/canonical_paper.py`.
  - Added structured representations for `Author`, `Institution`, `Venue`, `Topic`, `ProvenanceRecord`, `SourceRecords`, `OpenAccessInfo`, `ConfidenceLevel`, and `FulltextStatus`.
  - Added formal JSON schema generation for external tools in `dataset/schemas/canonical_paper.json`.
- **Modular Scholarly Source Adapters**:
  - `BaseSourceAdapter` (`pipelines/ingestion/sources/base.py`): Abstract base class with exponential backoff retries, polite pool rate limiting, failure logging, and checkpointing.
  - `OpenAlexAdapter` (`pipelines/ingestion/sources/openalex.py`): OpenAlex Works API client supporting polite pool `mailto`, cursor pagination, concept mapping, and inverted index abstract reconstruction.
  - `SemanticScholarAdapter` (`pipelines/ingestion/sources/semantic_scholar.py`): Semantic Scholar Academic Graph client with field selection, external ID extraction, and rate limit handling.
  - `ArxivAdapter` (`pipelines/ingestion/sources/arxiv.py`): arXiv Export API client with Atom XML feed parsing, category classification, and PDF link discovery.
  - `CrossrefAdapter` (`pipelines/ingestion/sources/crossref.py`): Crossref REST API client with polite headers, JATS XML abstract cleaning, and container venue extraction.
- **Normalization & Field Standardizers**:
  - `identifiers.py`: Strict validation and normalization for DOIs, arXiv IDs, and ORCIDs.
  - `text.py`: Unicode NFKD normalization, punctuation stripping, title fingerprinting, author name parsing (`First Last` / `Last, First`), and OpenAlex inverted index abstract reconstruction.
- **Identity Resolution & Deduplication**:
  - `IdentityResolver` (`pipelines/ingestion/resolution/identity.py`): Multi-signal matching across DOIs, arXiv IDs, title similarity, author overlap, and publication year compatibility with four confidence tiers (`EXACT`, `HIGH_CONFIDENCE`, `POSSIBLE`, `UNRESOLVED`).
  - Deterministic canonical ID generation (`rg_doi_*`, `rg_arx_*`, `rg_tit_*`).
  - `Deduplicator` (`pipelines/ingestion/resolution/deduplicator.py`): Multi-source metadata consolidation with full provenance preservation and conflict resolution.
- **Configurable AI Domain Relevance Filter**:
  - `AIRelevanceFilter` (`pipelines/ingestion/filters/relevance.py`): Multi-mode relevance evaluation (`strict_ai`, `broad_ai`, `all`) accommodating core AI, adjacent, and interdisciplinary fields.
- **Full-Text Acquisition & Artifact Storage**:
  - `FullTextCollector` (`pipelines/ingestion/fulltext/collector.py`): Legitimate open-access artifact discovery, polite download throttling, and canonical linkage.
- **Multi-Tier Dataset Storage Architecture**:
  - `DatasetStorageManager` (`pipelines/ingestion/storage/manager.py`): Structured file persistence across `raw/`, `interim/`, `processed/` (Parquet and JSONL via Polars/PyArrow), `manifests/`, and `schemas/`.
- **Quality Reporting & Release Manifests**:
  - `QualityReporter` (`pipelines/ingestion/quality/reporter.py`): Generates dataset release manifests (`{version}_manifest.json`) and quality reports (`{version}_quality_report.md` / `{version}_quality_report.json`) with metadata completeness, deduplication metrics, source overlap matrices, and temporal distributions.
- **Ingestion CLI & Pipeline Runner**:
  - `LiteratureIngestionPipeline` (`pipelines/ingestion/pipeline.py`): End-to-end orchestration runner.
  - `collect.py` (`pipelines/ingestion/collect.py`): Command-line interface supporting `--sources`, `--limit`, `--query`, `--version`, `--filter-mode`, `--fulltext`, and `--dry-run`.
- **Comprehensive Test Suite**:
  - 24 unit and integration tests covering normalizers, source adapters, identity resolution, deduplication, relevance filtering, quality reporting, and end-to-end pipeline execution.
- **Initial Dataset Release (v0.1.0)**:
  - 700 raw records ingested from OpenAlex and Crossref.
  - 528 unique canonical papers consolidated.
  - 141 duplicates merged (21.08% deduplication rate).
  - Parquet and JSONL artifacts created under `dataset/processed/v0.1.0/`.
