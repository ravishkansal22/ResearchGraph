# ResearchGraph Scientific Information Extraction: Human Annotation Guidelines (v0.4.0)

## 1. Overview and Objective
The goal of this benchmark is to establish verified, reproducible human ground-truth labels for scientific information extraction across research publications.

Reviewers evaluate machine-extracted scientific entities, statements, and relationships against the source text of each chunk.

**CRITICAL INTEGRITY PROTOCOL**:
- All human assessment columns in `scientific_extraction_v0.4.0_annotation_template.csv` are initially blank.
- Reviewers must not fabricate annotations or assume automated extractions are correct.
- An extracted author claim is **NOT** automatically a verified universal fact.

---

## 2. Allowed Annotation Categories

### A. Scientific Entities & Concepts
- `METHOD`: Specific algorithms, models, architectures, techniques, or interventions (e.g. *CNN*, *BERT*, *SVM*, *adaptive intrusion detection system*).
- `PROBLEM`: Scientific or engineering problems being tackled (e.g. *intrusion detection*, *concept drift*, *adversarial attacks*).
- `BOTTLENECK`: Fundamental limitations or resource constraints (e.g. *latency overhead*, *data imbalance*, *black-box nature*, *high computational cost*).
- `METRIC`: Quantitative performance metrics or evaluation criteria (e.g. *accuracy*, *F1-score*, *latency*, *precision*, *throughput*).
- `DATASET`: Benchmark datasets, corpora, or data collections (e.g. *NSL-KDD*, *CICIDS2017*, *MIMIC-III*, *ImageNet*).
- `TASK`: Specific operational objectives (e.g. *threat detection*, *anomaly classification*, *packet inspection*).
- `ASSUMPTION`: Stated conditions assumed by the authors (e.g. *assuming independent identically distributed observations*).
- `DOMAIN`: Scientific or technical application domain (e.g. *cybersecurity*, *healthcare*, *aviation*).

### B. Scientific Statements
- `CLAIM`: Core proposition, thesis, or proposed hypothesis made by the authors (e.g. *"This paper examines how deep learning strengthens intrusion detection"*).
- `RESULT`: Reported experimental or analytical finding (e.g. *"The model achieved 98.4% detection accuracy on NSL-KDD"*).
- `LIMITATION`: Explicitly stated weakness, constraint, or caveat (e.g. *"A limitation of this study is the susceptibility to adversarial evasion"*).
- `FUTURE_DIRECTION`: Research directions proposed by the authors (e.g. *"Future work should explore federated privacy-preserving protocols"*).
- `FAILURE_MODE`: Conditions under which methods break down or fail (e.g. *"Traditional rule-based systems struggle to detect zero-day attacks"*).

### C. Scientific Relationships
- `ADDRESSES`: Method -> Problem
- `USES`: Method -> Dataset / Metric / Component
- `IMPROVES`: Method -> Metric / Outcome
- `OUTPERFORMS`: Method -> Baseline Method
- `LIMITED_BY`: Method -> Bottleneck
- `EVALUATED_ON`: Method -> Dataset / Task
- `ASSUMES`: Method / Claim -> Assumption
- `REPORTS`: Paper -> Result / Claim
- `SUGGESTS`: Authors -> Future Direction
- `CONTRADICTS`: Statement conflicts with another statement

---

## 3. Epistemological Attribution: AUTHOR_STATED vs. SYSTEM_INFERRED
- `AUTHOR_STATED`: The text explicitly and directly asserts the concept, statement, or relationship.
- `SYSTEM_INFERRED`: The relationship or concept is logically deduced or inferred by the system without explicit author phrasing. System inferences must never be recorded as direct author statements.

---

## 4. Verdict Options
For each system prediction, assign one of:
1. `CORRECT`: Both the category and the exact evidence span are accurate and fully supported by text.
2. `PARTIALLY_CORRECT`: Category is correct but the span is imprecise (e.g., clipped words or over-extended span), or concept is valid but miscategorized.
3. `UNSUPPORTED`: Hallucinated, factually inverted, or not backed by the quoted text.
4. `MISSING`: A vital scientific concept or statement in the chunk that the system completely failed to extract.
