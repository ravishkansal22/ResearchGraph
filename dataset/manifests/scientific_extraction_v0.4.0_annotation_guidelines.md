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

## 4. Verdict Options & Evaluation Protocol

For each system prediction, assign one of:
1. `CORRECT`: Both the category and the exact evidence span are accurate and fully supported by text. When marked `CORRECT`, the reviewer may leave the ground-truth category and evidence columns blank to inherit the validated system values, or re-type them for affirmation.
2. `PARTIALLY_CORRECT`: The underlying concept or finding is valid, but either the category is imprecise (e.g. `TASK` miscategorized as `METHOD`) or the character span is clipped or over-extended. Specify the corrected category and exact evidence span in the human fields.
3. `UNSUPPORTED`: Hallucinated, factually inverted, contextually inapplicable, or not backed by the quoted text. These represent system false positives.
4. `MISSING`: A vital scientific entity, statement, or relationship present in the chunk that the system failed to extract.

---

## 5. Review Workflow for 25-Chunk Audit Packet

### A. Chunks with Predictions (Chunks 01–15)
- **Part A (Assess Existing Predictions)**: Review every machine-extracted candidate record. Assign verdict `CORRECT`, `PARTIALLY_CORRECT`, or `UNSUPPORTED`.
- **Part B (Discover Missed Knowledge)**: Scan the chunk text for any missed entities, contribution claims, empirical results, limitations, datasets, or relationships. Record them in the provided candidate rows with verdict `MISSING`, verbatim evidence span, and attribution.

### B. Chunks without Predictions (Chunks 16–25)
- Perform a thorough recall audit of the chunk text.
- If valid scientific concepts, methods (e.g. bibliometric analysis, VOSviewer), limitations, datasets, or claims are present, record them in the structured discovery rows with verdict `MISSING`.
- If the chunk is genuinely devoid of scientific content (e.g. front matter, author preface, table fragments), leave human fields blank or add a clarifying comment.

---

## 6. Audit Trail and Data Integrity
- Keep all human ground-truth columns initially blank until reviewed by a qualified human annotator.
- Do not auto-fill, simulate, or synthesize ground-truth labels in production benchmark files.
- The evaluation engine ingests completed annotations and calculates strict and relaxed precision, recall, F1, category-wise metrics, evidence-span correctness, relation metrics, and detailed false positive/negative listings.

