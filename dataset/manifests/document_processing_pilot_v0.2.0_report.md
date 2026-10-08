# ResearchGraph Phase 2: Document Processing Pilot Report (v0.2.0)

**Date**: 2026-10-08T18:14:08.020016+00:00  
**Status**: **COMPLETED & VALIDATED**  
**Readiness Verdict**: **READY**

---

## Executive Summary

The **Phase 2 Document Processing Pilot** successfully executed end-to-end extraction, structural decomposition, hierarchical section detection, provenance-preserving paragraph parsing, scientific sentence segmentation, and chunking experiments on the **8 validated full-text PDFs** acquired during the v0.1.2 pilot.

Every piece of processed text retains strict, end-to-end lineage back to its source paper, page range, section hierarchy, and paragraph order.

---

## Controlled Pilot Metrics

| Metric | Measured Result | Target / Baseline |
| :--- | :--- | :--- |
| **PDFs Processed** | **8** | 8 controlled candidate PDFs |
| **Success Rate** | **100.0% (8 / 8)** | ≥ 95% |
| **Total Physical Pages** | **214 pages** | 214 pages |
| **Pages with Usable Text** | **214 (100.0%)** | > 98% |
| **Empty / Unreadable Pages**| **0 (0.0%)** | 0 |
| **Total Extracted Text** | **632,474 characters** (~84,757 words) | — |
| **Sections Detected** | **470 sections** | Hierarchical H1/H2/H3 |
| **Paragraphs Extracted** | **2,684 paragraphs** | Full provenance |
| **Sentences Segmented** | **5,792 sentences** | Abbreviation/decimal protected |
| **Total Chunks (Strategy A)**| **663 chunks** | Atomic paragraph grouped |
| **Total Chunks (Strategy B)**| **807 chunks** | Fixed-window with overlap |
| **Total Storage (JSONL+Parquet)**| **10.04 MB** | Highly compact |

---

## Chunking Strategy Comparison

| Feature | Strategy A (Paragraph-Based) | Strategy B (Structure-Aware Fixed) |
| :--- | :--- | :--- |
| **Total Chunks** | **663** | 807 |
| **Average Chunk Size** | **952.0 characters** (~146 words) | 844.7 characters (~130 words) |
| **Min / Max Size** | 3 / 4961 chars | 15 / 1200 chars |
| **Section Boundary Preservation** | **100.0% (Zero bleeding)** | **100.0% (Zero bleeding)** |
| **Paragraph Integrity** | **100.0% preserved** | Broken at sentence window cuts |
| **Overlap Redundancy** | 0% (No duplication) | ~18% token redundancy |
| **Recommendation** | **RECOMMENDED FOR RESEARCHGRAPH** | Optional for standard RAG |

### Rationale for Strategy A:
Unlike generic RAG retrieval chatbots, ResearchGraph builds structured semantic representations. Splitting paragraphs across arbitrary window borders fragments arguments and premises. Strategy A guarantees complete conceptual unity per paragraph while strictly honoring section hierarchies.


---

## Document-by-Document Processing Breakdown

| Canonical ID | Title | Pages | Sections | Paragraphs | Sentences | Chunks (A) | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `rg_doi_b29976e1c44e` | Artificial Intelligence in Cybersecurity: Mac... | 5 | 3 | 13 | 220 | 12 | `SUCCESS` |
| `rg_doi_3891d117baca` | Artificial intelligence and machine learning ... | 87 | 274 | 426 | 1767 | 285 | `SUCCESS` |
| `rg_doi_cb0ceeff2e31` | ARTIFICIAL INTELLIGENCE FOR EPILEPTIC SEIZURE... | 15 | 21 | 227 | 420 | 53 | `SUCCESS` |
| `rg_doi_da062bd35ba4` | Artificial intelligence, machine learning, de... | 27 | 22 | 499 | 1190 | 107 | `SUCCESS` |
| `rg_doi_7c2fa4c39358` | Navigating the landscape of artificial intell... | 5 | 17 | 128 | 232 | 26 | `SUCCESS` |
| `rg_doi_4e5057959cae` | Frontiers of Artificial Intelligence and Mach... | 55 | 92 | 1252 | 1424 | 102 | `SUCCESS` |
| `rg_doi_5c65e2d95d8f` | Future Directions of Artificial Intelligence,... | 14 | 27 | 86 | 334 | 50 | `SUCCESS` |
| `rg_doi_21feca2c78f6` | Artificial intelligence, machine learning, de... | 6 | 14 | 53 | 205 | 28 | `SUCCESS` |

---

## Key Technical Observations

1. **Parser Superiority (PyMuPDF vs pypdf)**:
   - PyMuPDF (`fitz`) parsed all 214 pages in **1.45 seconds** total (sub-millisecond to ~300ms per paper).
   - `pypdf` suffered major stalls and warnings on PDFs with malformed cross-reference objects (e.g. `rg_doi_4e5057959cae.pdf`), requiring over 30 seconds for the same document.
   - **Conclusion**: PyMuPDF is firmly established as the primary parsing engine.

2. **Column Layout Disambiguation**:
   - 4 out of 8 papers utilized two-column formats (`rg_doi_b29976e1c44e`, `rg_doi_cb0ceeff2e31`, `rg_doi_7c2fa4c39358`, `rg_doi_21feca2c78f6`).
   - Coordinate-based column sorting prevented cross-column sentence interleaving.

3. **Section Hierarchy**:
   - Numbered sections (`1.`, `1.1`, `1.1.1`, `Chapter 1`), Roman numerals (`I.`, `II.`), and unnumbered scientific headers (`Abstract`, `References`, `Methodology`) were successfully organized into multi-level hierarchies.

---

## Scaling Readiness Assessment

**Verdict**: **READY**

The document processing foundation is verified, deterministic, and ready for scaling to the next 50-paper benchmark.
