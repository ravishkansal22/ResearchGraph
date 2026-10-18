# ResearchGraph Scientific Information Extraction: Human Annotation Guidelines (v0.4.0)

## 1. Overview and Objective
The goal of this benchmark is to establish verified, reproducible human ground-truth labels for scientific information extraction across research publications.

Reviewers evaluate machine-extracted scientific entities, statements, and relationships against the source text of each chunk, and discover missed scientific knowledge.

**CRITICAL INTEGRITY PROTOCOL**:
- All human assessment columns in `scientific_extraction_v0.4.0_audit_packet_25.csv`, `scientific_extraction_v0.4.0_audit_packet_reviewer1.csv`, and `scientific_extraction_v0.4.0_audit_packet_reviewer2.csv` are initially strictly blank.
- Reviewers must not fabricate annotations or assume automated extractions are correct.
- An extracted author claim is **NOT** automatically a verified universal fact.
- Candidate yield, extraction counts, and lower empty-chunk rates reflect engineering sensitivity, **not verified scientific accuracy**. Scientific precision, recall, and F1 remain unverified until completed human annotations are evaluated.

---

## 2. Allowed Annotation Categories

### A. Scientific Entities & Concepts
- `METHOD`: Specific algorithms, models, architectures, techniques, or interventions (e.g. *CNN*, *BERT*, *SVM*, *co-occurrence mapping*, *cluster analysis*, *VOSviewer*, *intelligent tutoring systems*).
- `TASK`: Specific operational objectives or applications (e.g. *automated assessment*, *image captioning*, *threat detection*, *anomaly classification*, *materials discovery*).
- `DATASET`: Benchmark datasets, databases, corpora, or data collections, whether named or descriptive (e.g. *Web of Science*, *Scopus*, *PubMed*, *NSL-KDD*, *dataset of mental health-related information*).
- `METRIC`: Quantitative performance metrics or evaluation criteria (e.g. *accuracy*, *F1-score*, *latency*, *precision*, *throughput*). Note: Colloquial, non-measurement mentions (e.g. "accuracy of our understanding") must NOT be labeled as METRIC.
- `DOMAIN`: Scientific or technical application domain (e.g. *cybersecurity*, *mental health*, *healthcare*, *educational technology*).
- `PROBLEM`: Scientific, technical, or systemic challenges being tackled (e.g. *data quality*, *patient privacy*, *intrusion detection*, *supply chain resilience*).
- `BOTTLENECK`: Fundamental constraints or trade-offs (e.g. *computational cost*, *ethical concerns*, *lack of explainability*, *data imbalance*).
- `ASSUMPTION`: Stated conditions assumed by the authors (e.g. *assuming independent identically distributed observations*).

### B. Scientific Statements
- `CLAIM`: Core proposition, thesis, or explicit contribution statement made by the authors (e.g. *"Contributions of this study: (1) We conduct comprehensive co-occurrence mapping..."*, *"We propose a novel framework for..."*).
- `RESULT`: Reported experimental, numerical, or analytical finding (e.g. *"Initial testing of the AI robot demonstrates promising results in its ability to accurately recognize emotional cues"*, *"The model achieved 98.4% detection accuracy"*).
- `LIMITATION`: Explicitly stated weakness, constraint, hurdle, or caveat, whether expressed with verbs or descriptive noun phrases (e.g. *"Key challenges in integrating clinical AI systems include concerns regarding data quality..."*, *"A limitation of this study is the sample size"*).
- `FUTURE_DIRECTION`: Prospective research directions proposed by the authors (e.g. *"Future work should explore federated privacy-preserving protocols"*).
- `FAILURE_MODE`: Specific failure conditions under which methods break down (e.g. *"Traditional rule-based systems fail to detect zero-day polymorphic payloads"*).

### C. Scientific Relationships
- `ADDRESSES`: Method -> Problem (e.g. *Federated Learning addresses Data Privacy Concerns*)
- `USES`: Method -> Dataset / Tool / Component (e.g. *Analysis uses VOSviewer*, *Model uses Web of Science*)
- `IMPROVES`: Method -> Metric / Outcome (e.g. *Optimization improves Throughput*)
- `OUTPERFORMS`: Method -> Baseline Method (e.g. *Transformer outperforms LSTM*)
- `LIMITED_BY`: Method -> Bottleneck (e.g. *Ensemble learning is limited by Computational Cost*)
- `EVALUATED_ON`: Method -> Dataset / Benchmark (e.g. *Model was evaluated on NSL-KDD*)
- `ASSUMES`: Method / Claim -> Assumption
- `REPORTS`: Paper -> Result / Claim
- `SUGGESTS`: Authors -> Future Direction
- `CONTRADICTS`: Statement conflicts with another statement

---

## 3. Epistemological Attribution: AUTHOR_STATED vs. CITED_PRIOR_WORK vs. SYSTEM_INFERRED

For every human-annotated record, specify the attribution:
- `AUTHOR_STATED`: The authors of the current paper explicitly claim, discover, or propose the entity, finding, or statement.
- `CITED_PRIOR_WORK`: The concept, method, or finding is attributed to prior literature (e.g. *"Smith et al. [14] developed an algorithm for..."*).
- `SYSTEM_INFERRED`: The relationship or concept is logically deduced by the reviewer/system without explicit author phrasing. System inferences must never be recorded as direct author assertions.

---

## 4. Verdict Options & Evaluation Protocol

For each prediction row, assign one of:
1. `CORRECT`: Both the category and the exact evidence span are accurate and fully supported by text. When marked `CORRECT`, the reviewer may leave the ground-truth category and evidence columns blank to inherit the validated system values.
2. `PARTIALLY_CORRECT`: The underlying concept or finding is valid, but either the category is imprecise (e.g. `TASK` miscategorized as `METHOD`) or the character span is clipped or over-extended. Specify the corrected category and exact evidence span in the human fields.
3. `UNSUPPORTED`: Hallucinated, factually inverted, contextually inapplicable, or not backed by the quoted text. These represent system false positives.
4. `MISSING`: A valid scientific entity, statement, or relationship present in the chunk that the system failed to extract.

---

## 5. Review Workflow for 25-Chunk Audit Packet

### A. Chunks with Predictions (Chunks 01–15)
- **Part A (Assess Existing Predictions)**: Review every machine-extracted candidate record. Assign verdict `CORRECT`, `PARTIALLY_CORRECT`, or `UNSUPPORTED`.
- **Part B (Discover Missed Knowledge)**: Scan the chunk text for any missed entities, contribution claims, empirical results, limitations, datasets, or relationships. Record them in the provided candidate rows (`ADD_MISSING`) with verdict `MISSING`, verbatim evidence span, and attribution.

### B. Chunks without Predictions (Chunks 16–25)
- Perform a thorough recall audit of the chunk text.
- If valid scientific concepts, methods (e.g. bibliometric analysis, VOSviewer), limitations, datasets, or claims are present, record them in the structured discovery rows with verdict `MISSING`.
- If the chunk is genuinely devoid of scientific content (e.g. front matter, author preface, table formatting fragments), leave human fields blank or add comment `NO_VALID_SCIENTIFIC_CONTENT`.

---

## 6. Independent Dual-Reviewer & Consensus Procedure

To ensure scientific defensibility, annotations are conducted independently by two reviewers, followed by formal reconciliation:

```
[Reviewer 1 Packet] ---> (Independent Blind Review) ---+
                                                       |---> [Reconciliation Script] ---> [Adjudication Report]
[Reviewer 2 Packet] ---> (Independent Blind Review) ---+           |
                                                                   v
                                                    [Consensus CSV Template]
                                                                   |
                                                  (Lead Adjudicator Resolves Disputes)
                                                                   v
                                                  [Final Consensus Ground Truth]
                                                                   |
                                                      [Benchmark Evaluator]
```

### Step 1: Independent Blind Review
- Reviewer 1 receives [`scientific_extraction_v0.4.0_audit_packet_reviewer1.csv`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/dataset/manifests/scientific_extraction_v0.4.0_audit_packet_reviewer1.csv).
- Reviewer 2 receives [`scientific_extraction_v0.4.0_audit_packet_reviewer2.csv`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/dataset/manifests/scientific_extraction_v0.4.0_audit_packet_reviewer2.csv).
- Neither reviewer inspects the other's annotations during the review phase.

### Step 2: Automated Concordance and Agreement Calculation
Execute the reconciliation tool:
```bash
python scripts/reconcile_human_annotations.py \
    --reviewer1 dataset/manifests/scientific_extraction_v0.4.0_audit_packet_reviewer1.csv \
    --reviewer2 dataset/manifests/scientific_extraction_v0.4.0_audit_packet_reviewer2.csv \
    --output-consensus dataset/manifests/scientific_extraction_benchmark_consensus_25.csv \
    --output-report dataset/manifests/scientific_extraction_adjudication_report.md
```
The script computes:
- Completion rates for both annotators.
- Observed verdict agreement rate ($P_o$).
- Cohen's Kappa score ($\kappa = \frac{P_o - P_e}{1 - P_e}$) assessing agreement beyond chance.
- Concordance on categories and evidence spans.

### Step 3: Formal Adjudication Phase
- Where both reviewers agree (`CORRECT`, `UNSUPPORTED`, or matching `PARTIALLY_CORRECT`/`MISSING`), the consensus file pre-accepts the verdict.
- Where reviewers disagree, the row is flagged with `human_verdict="NEEDS_ADJUDICATION"`.
- A third senior researcher (Lead Adjudicator) reviews the discrepancy in [`scientific_extraction_adjudication_report.md`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/dataset/manifests/scientific_extraction_adjudication_report.md) and assigns the binding final ground-truth label in `scientific_extraction_benchmark_consensus_25.csv`.

### Step 4: Benchmark Evaluation Execution
Once the consensus CSV is completed and signed off, execute the benchmark evaluation:
```bash
python scripts/evaluate_human_benchmark.py \
    --annotations dataset/manifests/scientific_extraction_benchmark_consensus_25.csv \
    --v040-dir dataset/processed/v0.4.0 \
    --v041-dir dataset/processed/v0.4.1 \
    --output-dir dataset/manifests
```
This produces verified comparative strict/relaxed Precision, Recall, F1, category breakdowns, and error listings for both models.
