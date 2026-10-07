# ResearchGraph — Query-Driven Full-Text Pilot Report (v0.1.2)

**Generated**: 2026-10-07T14:24:35.087205+00:00  
**Pilot Objective**: Evaluate empirical feasibility, storage footprint, and PDF extractability of query-driven on-demand full-text acquisition.

---

## 1. Executive Summary

| Metric | Measured Value |
|---|---|
| **Papers Evaluated in Pilot** | **25** |
| **Successfully Downloaded** | **8** (32.0%) |
| **Valid & Verified PDFs** | **8** (32.0%) |
| **Parseable Documents (Text Extracted)** | **8** (100.0% of valid PDFs) |
| **Confirmed Unavailable / Paywalled** | **7** (28.0%) |
| **Network / Validation Failures** | **10** (40.0%) |
| **Total Pilot Storage Added** | **9.19 MB** (9,638,234 bytes) |
| **Average Valid PDF Size** | **1.08 MB** (1108.8 KB) |
| **Median Valid PDF Size** | **991.3 KB** |
| **Idempotency / Caching** | **PASSED** (Zero redundant network transfers) |

---

## 2. Source Breakdown & Acquisition Outcomes

| Source Type | Attempted | Downloaded | Valid PDF |
|---|---|---|---|
| `direct_pdf` | 10 | 5 | 5 |
| `none` | 7 | 0 | 0 |
| `open_access` | 7 | 3 | 3 |
| `repository` | 1 | 0 | 0 |

---

## 3. PDF Validation & Failure Classification

| Validation Status | Count | Percentage | Description |
|---|---|---|---|
| `SUCCESS_PDF` | 8 | 32.0% | SUCCESS_PDF |
| `UNAVAILABLE` | 7 | 28.0% | UNAVAILABLE |
| `HTML_NOT_PDF` | 7 | 28.0% | HTML_NOT_PDF |
| `PAYWALL` | 3 | 12.0% | PAYWALL |

---

## 4. Empirical Storage Projections

Based on the empirical PDF size distribution (average = **1.08 MB**, median = **0.97 MB**), the projected storage requirements for full-text retention are:

| Corpus Size | Storage (Average Size Basis) | Storage (Median Size Basis) |
|---|---|---|
| **500 Papers** | **0.53 GB** (~541 MB) | **0.47 GB** (~484 MB) |
| **5,000 Papers** | **5.29 GB** | **4.73 GB** |
| **10,000 Papers** | **10.57 GB** | **9.45 GB** |

---

## 5. Architectural Recommendations

1. **Query-Driven On-Demand Acquisition (RECOMMENDED)**:
   - Metadata-first candidate retrieval limits full-text downloads strictly to papers relevant to the active research query (typically 10–30 papers per query rather than 5,000+ PDFs).
2. **Hybrid Storage with Ephemeral PDF Cache**:
   - Downloaded PDFs should be stored in a bounded local LRU cache (`dataset/fulltext/cache/`).
   - Downstream extracted representations (structured JSON / markdown / sections) should be persisted permanently in lightweight form, allowing the heavy raw PDF binaries to be evicted when cache limits are reached.
3. **Robust Quality Validation**:
   - HTML detection and magic byte verification are essential: scholarly APIs often return HTML paywalls or cookie gates under 200 OK statuses when resolving DOI links.
