# ResearchGraph Dataset Management

This directory manages the scientific literature corpus used by ResearchGraph across its lifecycle stages.

## Data Storage Tiers

| Tier | Directory | Description | Git Policy |
|---|---|---|---|
| **Raw** | `raw/` | Unmodified API responses and raw dumps directly from scholarly sources (OpenAlex, Semantic Scholar, arXiv). | **Ignored** (External Storage / S3) |
| **Interim** | `interim/` | Normalized, deduplicated, and domain-filtered intermediate representations. | **Ignored** |
| **Processed** | `processed/` | Canonical structured papers, extracted entities, causal assertions, and graph-ready records. | **Ignored** |
| **Fulltext** | `fulltext/` | Downloaded or extracted full-text PDFs, TEI XMLs, and markdown parses. | **Ignored** |
| **Manifests** | `manifests/` | Versioned collection manifests, checksum records, query criteria, and dataset release logs. | **Committed / Tracked** |
| **Schemas** | `schemas/` | Formal data schemas (JSON Schema / Pydantic models) defining corpus record specifications. | **Committed / Tracked** |

## Dataset Lifecycle (Phase 1 Target)

```text
Scholarly APIs (OpenAlex / S2 / arXiv)
         │
         ▼
    dataset/raw/
         │
         ▼ (Normalization & Deduplication)
   dataset/interim/
         │
         ▼ (Domain Filtering & Feature Enrichment)
  dataset/processed/
         │
         ▼ (Full-text Parsing)
   dataset/fulltext/
```

> **Note**: Actual dataset acquisition will be conducted via reproducible pipelines during Phase 1.
