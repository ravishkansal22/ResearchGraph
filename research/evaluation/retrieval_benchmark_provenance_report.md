# ResearchGraph: Retrieval Benchmark Provenance & Validity Report
**Independent Audit Deliverable: Audit 3**

- **Date:** `2026-10-21T15:54:00Z`
- **Auditor:** Independent Principal Research Engineer
- **Harness Evaluated:** `research/embeddings/eval_retrieval.py`
- **Report Evaluated:** `research/embeddings/retrieval_evaluation_report.json` / `.md`
- **Corpus Evaluated:** 500-chunk stratified subset of `dataset/processed/v0.3.0/chunks.parquet`

---

## 1. Executive Summary

This audit evaluated the methodology, provenance, ground-truth label generation, and metric validity of the Phase 5 retrieval benchmark.

### Core Findings
1. **Relevance judgments are NOT human-annotated.** Ground-truth labels are generated dynamically by a **rule-based term-matching heuristic** (`is_relevant` in `eval_retrieval.py`).
2. **Structural Lexical Bias:** Because a chunk is labeled "relevant" if it contains the target concept string or $\ge 2$ query keywords, the lexical baseline (BM25) possesses an inherent structural advantage in finding chunks satisfying that exact lexical definition.
3. **Execution Reproducibility is 100% Verified:** The benchmark script executes deterministically, takes identical corpus subsets across all 3 methods (BM25, Dense Vector, Hybrid RRF), and computes standard IR metrics accurately.
4. **Model Revisions Recorded:** The model specification metadata correctly records `tfidf-lsa-384`, revision `v1.0`, dimension `384`.

---

## 2. Benchmark Query & Ground-Truth Provenance

The evaluation suite defines 8 curated scientific queries in `BENCHMARK_QUERIES`:

| Query ID | Query Text | Target Concept | Relevant Keyword Terms |
| :--- | :--- | :--- | :--- |
| `q01` | `federated learning privacy data concerns distributed networks` | `federated learning` | `federated`, `privacy`, `confidentiality`, `distributed` |
| `q02` | `convolutional neural network image classification oncology healthcare` | `convolutional neural network` | `convolutional`, `cnn`, `oncology`, `cancer`, `imaging`, `healthcare` |
| `q03` | `prompt injection vulnerabilities in large language models` | `prompt injection` | `prompt`, `injection`, `vulnerability`, `llm`, `language` |
| `q04` | `mitigating data imbalance using synthetic data generation generative models` | `data imbalance` | `imbalance`, `synthetic`, `oversampling`, `generative` |
| `q05` | `computational cost constraints and memory bottlenecks edge AI deployment` | `computational cost` | `computational`, `cost`, `memory`, `latency`, `edge`, `resource` |
| `q06` | `mental health automated assessment using natural language processing` | `mental health` | `mental`, `depression`, `psychological`, `nlp`, `assessment` |
| `q07` | `adversarial robustness and attack resilience in deep learning models` | `adversarial robustness` | `adversarial`, `robustness`, `perturbation`, `resilience` |
| `q08` | `clinical decision support systems predictive analytics patient outcomes` | `decision support systems` | `decision`, `support`, `clinical`, `diagnostic`, `predictive` |

### Ground-Truth Labeling Function
In `eval_retrieval.py` (lines 105–111):
```python
def is_relevant(text: str, query: BenchmarkQuery) -> bool:
    lower = text.lower()
    if query.target_concept.lower() in lower:
        return True
    overlap = sum(1 for term in query.relevant_terms if term.lower() in lower)
    return overlap >= 2
```

### Critical Epistemic Implications
- **Absence of Expert Human Judgments:** No domain expert adjudicated whether a retrieved passage genuinely answers the scientific query, discusses a relevant solution, or merely mentions the phrase in passing (e.g. in a related work citation).
- **Severe Recall Underestimation:** A passage expressing the concept via semantic paraphrase (e.g., *"decentralized multi-institutional gradient aggregation without sharing raw clinical records"*) is labeled **irrelevant** by `is_relevant` if it does not explicitly contain the exact string *"federated learning"* or two keyword tokens.
- **Dense Vector Penalization:** Dense vector retrieval often retrieves conceptually identical passages that do not use the exact surface tokens. Under this labeling rule, those semantic matches are penalized as false positives.

---

## 3. Metric Computation Verification

The metric calculations were mathematically inspected:
- **Precision@k:** $\frac{\sum_{i=1}^k \text{rel}_i}{k}$ (Correctly implemented).
- **Recall@k:** $\frac{\sum_{i=1}^k \text{rel}_i}{\text{Total Relevant in Corpus Sample}}$ (Correctly implemented).
- **MRR (Mean Reciprocal Rank):** $\frac{1}{\text{rank of first relevant item}}$ (Correctly implemented).
- **nDCG@k:** Normalized discounted cumulative gain with binary gains $2^{\text{rel}} - 1 = \text{rel}$ and logarithmic discounting $\log_2(i + 1)$ (Correctly implemented).

---

## 4. Auditor Verdict & Recommendations

### Verdict: `PASS WITH CAVEATS`
The software implementation of the retrieval benchmark is robust, deterministic, and reproducible. However, **its results must be reported as a rule-based pseudo-relevance benchmark, not a human-validated scientific retrieval benchmark**.

### Corrective Recommendations for Phase 14 / Next Release
1. **Adjudicated Benchmark Creation:** Sample 20 passages retrieved by Dense Vector that were marked "irrelevant" by the rule; have a human researcher label their semantic relevance.
2. **Reporting Transparency:** In all public documentation, label these metrics: *"Heuristic Term-Overlap Pseudo-Relevance Benchmark (Automated Baseline)"*.
3. **Dual-Evaluation Protocol:** Evaluate dense embeddings against a dataset where ground truth is established by document-level bibliographic co-citation or human task judgments, rather than lexical keyword presence.
