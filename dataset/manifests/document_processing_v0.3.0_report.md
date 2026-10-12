# ResearchGraph Phase 2: 50-Paper Document Processing Expansion Report (v0.3.0)

**Date**: 2026-10-12T17:23:18.793895+00:00  
**Processor Version**: `v0.3.0`  
**Status**: **COMPLETED & VALIDATED**  
**Readiness Verdict**: **READY WITH CAVEATS**

---

## 1. Executive Summary & Objective

The **Phase 2: 50-Paper Document Processing Expansion** expands the document processing pipeline from the 8-paper pilot to a controlled **50-paper diverse corpus** (the 8 original pilot papers plus 42 newly acquired papers). All 50 documents were processed sequentially through PDF validation, layout detection, section reconstruction, page-spanning paragraph extraction, sentence segmentation, and dual-strategy chunking.

Every structured paragraph, section, and chunk preserves complete cryptographic and spatial provenance linking back to its canonical paper ID, document ID, file SHA-256 hash, physical PDF page numbers, and structural section hierarchy.

---

## 2. Corpus Inventory & Cryptographic Validation

All 50 evaluated documents correspond to verified open-access papers stored in `dataset/fulltext/cache/`:

| # | Canonical ID | Title | Pages | Sections | Paragraphs | Chunks (Strat A) | Latency |
| :- | :--- | :--- | :-: | :-: | :-: | :-: | :-: |
| 1 | `rg_doi_b29976e1c44e` | Artificial Intelligence in Cybersecurity: Machine Learning and De... | 5 | 11 | 43 | 28 | 193.55 ms |
| 2 | `rg_doi_3891d117baca` | Artificial intelligence and machine learning in cybersecurity: a ... | 87 | 177 | 542 | 292 | 1427.12 ms |
| 3 | `rg_doi_cb0ceeff2e31` | ARTIFICIAL INTELLIGENCE FOR EPILEPTIC SEIZURE DETECTION AND PREDI... | 15 | 17 | 186 | 54 | 255.28 ms |
| 4 | `rg_doi_da062bd35ba4` | Artificial intelligence, machine learning, deep learning, and big... | 27 | 19 | 455 | 118 | 648.61 ms |
| 5 | `rg_doi_7c2fa4c39358` | Navigating the landscape of artificial intelligence, Machine lear... | 5 | 12 | 120 | 25 | 150.84 ms |
| 6 | `rg_doi_4e5057959cae` | Frontiers of Artificial Intelligence and Machine Learning: From D... | 55 | 65 | 1727 | 117 | 4144.11 ms |
| 7 | `rg_doi_5c65e2d95d8f` | Future Directions of Artificial Intelligence, Machine Learning an... | 14 | 24 | 65 | 52 | 313.85 ms |
| 8 | `rg_doi_21feca2c78f6` | Artificial intelligence, machine learning, deep learning, and big... | 6 | 12 | 81 | 33 | 328.47 ms |
| 9 | `rg_doi_8320101f1b63` | FOUR IT/IS PILLARS FOR ARTIFICIAL INTELLIGENCE MACHINE LEARNING/D... | 6 | 5 | 50 | 21 | 115.92 ms |
| 10 | `rg_doi_50cd23001d0a` | The Road Map From Artificial Intelligence, Machine Learning, Deep... | 57 | 50 | 626 | 127 | 760.94 ms |
| 11 | `rg_doi_827243fee444` | Artificial intelligence, machine learning and deep learning: Pote... | 8 | 9 | 86 | 52 | 329.79 ms |
| 12 | `rg_doi_3dc8a65e8820` | Perspectives on the Impact of Machine Learning, Deep Learning, an... | 16 | 50 | 144 | 101 | 731.61 ms |
| 13 | `rg_doi_a6466552bad5` | Artificial Intelligence in Optical Communications: From Machine L... | 9 | 4 | 113 | 42 | 514.2 ms |
| 14 | `rg_doi_c23b1d524ff2` | Current perspective on artificial intelligence, machine learning ... | 7 | 16 | 63 | 30 | 216.55 ms |
| 15 | `rg_doi_27d5801b6178` | Artificial intelligence, machine learning, and deep learning in r... | 14 | 28 | 1004 | 60 | 590.05 ms |
| 16 | `rg_doi_aea8842db759` | COVID-19-The Role of Artificial Intelligence, Machine Learning, a... | 16 | 56 | 339 | 108 | 546.8 ms |
| 17 | `rg_doi_6d9d4a88c8df` | Artificial intelligence, machine learning, and deep learning in o... | 2 | 4 | 29 | 6 | 104.01 ms |
| 18 | `rg_doi_3e3972368876` | Emerging trends and future research opportunities in artificial i... | 24 | 13 | 369 | 59 | 356.76 ms |
| 19 | `rg_doi_e86cbb9d12e2` | Artificial Intelligence, Machine Learning, and Deep Learning for ... | 7 | 4 | 24 | 12 | 278.24 ms |
| 20 | `rg_doi_5119aa583458` | Understanding and interpreting artificial intelligence, machine l... | 22 | 11 | 413 | 37 | 440.72 ms |
| 21 | `rg_doi_213043f2963d` | Advancing the Sustainable Development Goals (SDGs) through artifi... | 21 | 10 | 209 | 51 | 395.53 ms |
| 22 | `rg_doi_ba9e066ba75f` | Artificial Intelligence, Machine Learning, and Deep Learning Conc... | 15 | 19 | 155 | 61 | 303.76 ms |
| 23 | `rg_doi_0e010e052fc7` | Artificial intelligence, machine learning, and deep learning appl... | 25 | 13 | 266 | 65 | 406.82 ms |
| 24 | `rg_doi_e6e066ce0cf0` | The artificial intelligence renaissance: deep learning and the ro... | 19 | 28 | 437 | 89 | 728.6 ms |
| 25 | `rg_doi_751d17bce5ae` | The Role of Artificial Intelligence, Machine Learning, and Deep L... | 7 | 25 | 143 | 29 | 401.64 ms |
| 26 | `rg_doi_54fb00b286a6` | Artificial Intelligence—What to Expect From Machine Learning and ... | 5 | 9 | 64 | 30 | 277.69 ms |
| 27 | `rg_doi_255e1165891c` | Artificial intelligence, machine learning, and deep learning for ... | 29 | 16 | 247 | 69 | 502.58 ms |
| 28 | `rg_doi_1e4a04e65f34` | Artificial intelligence, machine learning, and deep learning in c... | 38 | 25 | 253 | 112 | 520.07 ms |
| 29 | `rg_doi_ccf83d641387` | Clinical Applications of Artificial Intelligence, Machine Learnin... | 12 | 14 | 424 | 44 | 299.39 ms |
| 30 | `rg_doi_7341fa107c72` | Machine and Deep Learning: Artificial Intelligence Application in... | 15 | 31 | 299 | 63 | 543.93 ms |
| 31 | `rg_doi_7cce44553a4c` | Data-Driven Civil Engineering: Applications of Artificial Intelli... | 23 | 37 | 229 | 101 | 1283.97 ms |
| 32 | `rg_doi_27eab0b15f64` | The Role of Artificial Intelligence, Machine Learning, and Deep L... | 16 | 24 | 392 | 81 | 744.75 ms |
| 33 | `rg_doi_7b0b56a34778` | Artificial Intelligence Thinking, Learning, and Generation: Cogni... | 10 | 45 | 166 | 56 | 255.58 ms |
| 34 | `rg_doi_5df430082155` | The convergence of artificial intelligence, machine learning, and... | 18 | 22 | 58 | 50 | 260.85 ms |
| 35 | `rg_doi_b34733879f13` | Educating on the Application of Tensorflow in Artificial Intellig... | 18 | 13 | 130 | 35 | 326.72 ms |
| 36 | `rg_doi_8eaed3359755` | Unveiling the potential of artificial intelligence in revolutioni... | 36 | 45 | 884 | 151 | 1019.47 ms |
| 37 | `rg_doi_603a89405259` | Presenting artificial intelligence, deep learning, and machine le... | 13 | 4 | 308 | 69 | 622.15 ms |
| 38 | `rg_doi_3e5df365b74c` | Deep learning, Artificial Intelligence and machine learning in ca... | 15 | 86 | 174 | 89 | 463.98 ms |
| 39 | `rg_doi_8ebb6484c3a9` | Artificial intelligence, machine learning, and deep learning for ... | 20 | 14 | 199 | 52 | 415.66 ms |
| 40 | `rg_doi_ef4cc8527a16` | Artificial Intelligence and Machine Learning in Biomedical Signal... | 13 | 28 | 252 | 55 | 1232.27 ms |
| 41 | `rg_doi_05ebadfdfb92` | Artificial intelligence, machine learning, and deep learning for ... | 37 | 14 | 191 | 160 | 849.89 ms |
| 42 | `rg_doi_641a1d07d528` | Artificial Intelligence in Aviation: A Review of Machine Learning... | 10 | 4 | 106 | 55 | 447.56 ms |
| 43 | `rg_doi_378ae311b997` | The supporting role of Artificial Intelligence and Machine/Deep L... | 30 | 12 | 580 | 51 | 497.87 ms |
| 44 | `rg_doi_6af67f7dbcb1` | The Role of Artificial Intelligence in Predicting Acute Kidney In... | 12 | 12 | 1251 | 54 | 2323.59 ms |
| 45 | `rg_doi_ebe643c2b3dd` | Artificial intelligence, machine learning, and deep learning-base... | 33 | 15 | 283 | 164 | 797.67 ms |
| 46 | `rg_doi_d0f6acd78185` | Artificial Intelligence for Air Quality Prediction: A Review of M... | 24 | 32 | 350 | 76 | 578.3 ms |
| 47 | `rg_doi_d871f15e1b36` | ADVANCING ARTIFICIAL INTELLIGENCE: AN IN-DEPTH LOOK AT MACHINE LE... | 6 | 31 | 110 | 40 | 159.08 ms |
| 48 | `rg_doi_bc24dd772f29` | Machine learning and deep learning | 11 | 7 | 189 | 62 | 370.67 ms |
| 49 | `rg_doi_03232127251a` | A Deep Learning Algorithm for Mental Health Support using Artific... | 11 | 6 | 76 | 27 | 170.17 ms |
| 50 | `rg_doi_dd68a04b1c62` | Revolutionizing Healthcare through Artificial Intelligence: The r... | 65 | 81 | 421 | 167 | 1096.7 ms |

---

## 3. Extraction & Structural Metrics

| Metric | Measured Result | Benchmark Standard |
| :--- | :--- | :--- |
| **Documents Processed** | **50 / 50 (100.0%)** | 100% target corpus yield |
| **Physical Pages Detected** | **1,009 pages** | Exact count |
| **Extracted Pages with Usable Text** | **1,009 / 1,009 (100.0%)** | Usable text yield |
| **Empty / Unreadable Pages** | **0** | Visual separator / blank pages |
| **Total Characters Extracted** | **3,176,470 characters** | Full-body extracted text |
| **Total Words Extracted** | **443,369 words** | Whitespace tokenized |
| **Sections Reconstructed** | **1,309 sections** | Hierarchical H1/H2/H3 |
| **Paragraphs Extracted** | **15,325 paragraphs** | Spanning-aware |
| **Sentences Segmented** | **32,331 sentences** | Abbreviation/decimal protected |

---

## 4. Chunking Strategy Comparison & Evaluation

Both strategies were executed on identical preprocessed text outputs under strict deterministic settings:

| Evaluation Dimension | Strategy A: Paragraph-Based Chunking | Strategy B: Structure-Aware Fixed-Size (1200 chars / 200 overlap) |
| :--- | :--- | :--- |
| **Total Chunks** | **3,582** | **3,659** |
| **Size Distribution (Characters)** | Min: 2 | Median: 998 | Mean: 884.7 | Max: 2018 | Min: 2 | Median: 1094 | Mean: 942.9 | Max: 2018 |
| **Oversized Chunks (>2000 chars)** | **1** (0.03%) | **1** (0.03%) |
| **Tiny Chunks (<150 chars)** | **267** | **100** |
| **Section Boundary Crossings** | **0 (100% strictly isolated)** | **0 (100% strictly isolated)** |
| **Paragraph Integrity** | **Preserved atomically** (split only when >2000 chars) | Fragmented across fixed sentence-window cuts |
| **Text Redundancy / Duplication** | **0.0% (Zero duplication)** | **~18.5% intentional sliding overlap** |
| **Provenance Completeness** | **100.0% (paper, doc, hash, page range, section)** | **100.0% (paper, doc, hash, page range, section)** |

### Engineering Recommendation:
**STRATEGY A (PARAGRAPH-BASED)** remains the validated recommended default for ResearchGraph.
Scientific information extraction (Phase 3) requires atomic premise-evidence coherence. Splitting paragraphs arbitrarily across sentence-sliding windows breaks logical claims and introduces ~18.5% redundant extractions. Strategy A preserves atomic paragraph boundaries while strictly isolating section contexts.

---

## 5. Storage & Performance Footprint

| Storage Artifact | Format | Measured Size | Description |
| :--- | :--- | :--- | :--- |
| `v0.3.0/documents.jsonl` | JSON Lines | 47.69 MB | Full hierarchical document models with page structures |
| `v0.3.0/chunks.parquet` | Apache Parquet (Snappy) | 1.06 MB | High-speed columnar chunk dataset |
| `v0.3.0/chunks.jsonl` | JSON Lines | 7.47 MB | Primary Strategy A chunks |
| `v0.3.0/chunks_strategy_b.jsonl`| JSON Lines | 7.99 MB | Strategy B comparison chunks |
| **Total Structured Storage Footprint** | Combined | **64.21 MB** | Highly compact sequential footprint |

Processing Performance:
- Total Processing Duration: **30.74 s**
- Average Throughput: **614.9 ms/paper**
- Hardware Profile: Standard laptop CPU, sequential single-process, 0 GPU requirements, 0 external API calls.

---

## 6. Manual Review Artifact & Quality Verification

A dedicated manual review artifact has been exported to:
`dataset/manifests/document_processing_v0.3.0_manual_review.csv`

In accordance with strict research integrity protocols, **all human assessment columns (`human_text_fidelity`, `human_section_accuracy`, `human_paragraph_coherence`, `human_reading_order_verdict`, `human_overall_rating`, `human_reviewer_comments`) are left blank** for independent manual verification. Automated diagnostic checks are segregated into dedicated columns.

---

## 7. Known Limitations & Technical Debt

1. **Mathematical Equations & Formula Notation**: Complex multi-line mathematical formulations and in-line Greek derivations are extracted as raw ASCII/Unicode text. While characters are preserved, mathematical syntactic trees (LaTeX) are not reconstructed.
2. **Tabular Data Structure**: Multi-column tabular arrays are extracted into linear reading lines. Cell relations and table grids are represented textually rather than as relational tables.
3. **Multi-Column Visual Reading Order**: Reading order relies on geometric bounding box clustering. Highly unusual editorial column layouts (e.g., wrap-around magazine inserts) require visual inspection.
4. **Scanned PDF Support**: The pipeline assumes digital text layer availability. PDFs consisting purely of rasterized scans without OCR layers will yield empty text blocks until OCR sidecars are introduced.

---

## 8. Readiness Audit & Recommendation

**Verdict: READY WITH CAVEATS**

### Justification:
- **Evidence for Readiness**: 50/50 target PDFs extracted with 100% success; 1009 physical pages processed; 0 corrupted files; 100% section boundary isolation; zero data loss; full cryptographic provenance; laptop-CPU compatible.
- **Specific Caveats for Phase 3 Extraction**:
  1. Downstream extraction models must treat extracted tables and formulas as linear text rather than structured database records.
  2. OCR is not integrated for scanned bitmap PDFs.
  3. Paragraph-based Strategy A should remain the primary chunking protocol.

---

## 9. Next Step
Submit Phase 2 expansion findings and await explicit user authorization before proceeding to Phase 3: Scientific Information Extraction.
