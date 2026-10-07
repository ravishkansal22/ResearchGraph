# Changelog

All notable changes to the **ResearchGraph** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
