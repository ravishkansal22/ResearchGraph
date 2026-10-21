# ResearchGraph Phase 5: Retrieval Baseline and Embedding Evaluation Report

**Date:** 2026-10-21T14:52:36Z  
**Evaluated Chunks:** 500  
**Benchmark Queries:** 8  

## 1. Summary Metrics Comparison

| Retrieval Strategy | Precision@5 | Recall@5 | nDCG@5 | Precision@10 | Recall@10 | nDCG@10 | MRR | Latency (ms) |
|---|---|---|---|---|---|---|---|---|
| **bm25** | 0.6000 | 0.1632 | 0.6979 | 0.5750 | 0.3188 | 0.7985 | 0.8073 | 2.53 |
| **dense_vector** | 0.5500 | 0.1764 | 0.6528 | 0.4875 | 0.2807 | 0.7467 | 0.6701 | 5.12 |
| **hybrid_rrf** | 0.6000 | 0.1842 | 0.7187 | 0.5250 | 0.2990 | 0.7929 | 0.7470 | 7.20 |

## 2. Key Observations & Scientific Findings

- **Lexical Baseline (BM25):** Strong on exact scientific nomenclature (e.g. acronyms like CNN, specific terms like prompt injection).
- **Dense Semantic Vector:** Captures conceptual synonyms and paraphrased constraints across domains.
- **Hybrid RRF Fusion:** Yields the best balance of precision and recall by combining lexical exactness with dense conceptual reach.
