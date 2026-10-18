# ResearchGraph Phase 3: Human Benchmark Evaluation & Validation Report

**Document Version:** 1.0.0  
**Pipeline Baseline:** `v0.4.0`  
**Experimental Version:** `v0.4.1`  
**Evaluation Status:** `PENDING_HUMAN_ANNOTATION` (Evaluation pipeline fully verified; human annotations pending)  
**Date:** 2026-10-18  

---

## 1. Files Inspected or Modified

| File Path | Status | Key Purpose & Changes |
| :--- | :---: | :--- |
| [`pipelines/extraction/evaluator.py`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/pipelines/extraction/evaluator.py) | **Modified** | Added `VALID_CATEGORIES` and `CATEGORY_ALIASES` to normalize aliases (e.g. `METHODS` -> `METHOD`, `DATASETS` -> `DATASET`). Added relation source/target parsing (`human_relation_source`, `human_relation_target`). Implemented prediction and ground-truth deduplication in both strict set intersection and relaxed token-overlap matching. |
| [`scripts/generate_human_audit_packet.py`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/scripts/generate_human_audit_packet.py) | **Modified** | Extended CSV schema with relation fields and `reviewer_id`. Now generates 3 isolated packets: master template (`scientific_extraction_v0.4.0_audit_packet_25.csv`), Reviewer 1 packet (`scientific_extraction_v0.4.0_audit_packet_reviewer1.csv`), and Reviewer 2 packet (`scientific_extraction_v0.4.0_audit_packet_reviewer2.csv`). |
| [`scripts/reconcile_human_annotations.py`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/scripts/reconcile_human_annotations.py) | **Created** | Reconciles independent dual-reviewer annotations. Computes observed verdict agreement rate, full concordance rate, and Cohen's Kappa ($\kappa$). Produces `scientific_extraction_adjudication_report.md` and an adjudicated consensus CSV template. |
| [`scripts/evaluate_human_benchmark.py`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/scripts/evaluate_human_benchmark.py) | **Created** | End-to-end evaluation runner. Ingests completed human annotations or consensus CSV, evaluates `v0.4.0` and `v0.4.1` on identical chunks, calculates strict/relaxed P, R, F1, category breakdowns, evidence correctness, relationship metrics, and itemized FP/FN errors. When labels are blank, exits cleanly reporting `PENDING_HUMAN_ANNOTATION`. |
| [`tests/unit/test_human_benchmark_evaluation.py`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/tests/unit/test_human_benchmark_evaluation.py) | **Created** | 7 synthetic unit tests validating missing labels, duplicate records, category aliases, empty chunks (true negatives, pure FPs, pure FNs), partial matches (relaxed matching), dual-reviewer reconciliation, and comparative model evaluation. |
| [`dataset/manifests/scientific_extraction_v0.4.0_annotation_guidelines.md`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/dataset/manifests/scientific_extraction_v0.4.0_annotation_guidelines.md) | **Modified** | Documented dual-reviewer independent protocol, detailed category definitions, verbatim evidence span boundaries, attribution rules, relation annotation, and the 4-phase reconciliation and adjudication procedure. |
| [`dataset/manifests/scientific_extraction_v0.4.0_audit_packet_25.csv`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/dataset/manifests/scientific_extraction_v0.4.0_audit_packet_25.csv) | **Regenerated** | Canonical master review packet (25 chunks, 164 rows, 100% text and provenance, 0 non-blank human fields). |
| [`dataset/manifests/scientific_extraction_v0.4.0_audit_packet_reviewer1.csv`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/dataset/manifests/scientific_extraction_v0.4.0_audit_packet_reviewer1.csv) | **Created** | Dedicated Reviewer 1 packet (`reviewer_id="reviewer_1"`). |
| [`dataset/manifests/scientific_extraction_v0.4.0_audit_packet_reviewer2.csv`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/dataset/manifests/scientific_extraction_v0.4.0_audit_packet_reviewer2.csv) | **Created** | Dedicated Reviewer 2 packet (`reviewer_id="reviewer_2"`). |

---

## 2. Annotation Workflow and Consensus Procedure

### Protocol Structure
1. **Independent Blind Review Phase**:
   - Reviewer 1 completes [`scientific_extraction_v0.4.0_audit_packet_reviewer1.csv`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/dataset/manifests/scientific_extraction_v0.4.0_audit_packet_reviewer1.csv).
   - Reviewer 2 completes [`scientific_extraction_v0.4.0_audit_packet_reviewer2.csv`](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/dataset/manifests/scientific_extraction_v0.4.0_audit_packet_reviewer2.csv).
   - Both reviewers work independently without access to each other's notes or verdicts.
   - For predicted rows (Chunks 1–15, Part A), reviewers assess candidates as `CORRECT`, `PARTIALLY_CORRECT`, or `UNSUPPORTED`.
   - For missing knowledge (Chunks 1–15 Part B and Chunks 16–25 Recall Audit), reviewers record missed items in `ADD_MISSING` rows with verdict `MISSING`, verbatim evidence span, and attribution (`AUTHOR_STATED` vs `CITED_PRIOR_WORK`).
   - For relationship annotations, reviewers populate `human_relation_source`, `human_relation_target`, category (`ADDRESSES`, `USES`, `LIMITED_BY`, etc.), and supporting trigger evidence.
2. **Automated Concordance & Kappa Computation**:
   - Run `scripts/reconcile_human_annotations.py`.
   - Automatically identifies unanimous concordant rows and discordances.
   - Computes observed agreement rate and Cohen's Kappa score ($\kappa = \frac{P_o - P_e}{1 - P_e}$).
3. **Formal Adjudication Phase**:
   - The reconciliation tool generates `scientific_extraction_adjudication_report.md` and `scientific_extraction_benchmark_consensus_25.csv`.
   - Agreed rows are marked `[AGREED]`.
   - Discrepant rows are flagged with `human_verdict="NEEDS_ADJUDICATION"` and side-by-side reviewer inputs.
   - A Lead Adjudicator resolves discrepancies and signs off on the consensus ground truth.
4. **Data Integrity Guarantee**:
   - All ground-truth columns in production files remain strictly blank prior to human review. No ground-truth labels are fabricated or inferred.

---

## 3. Evaluator Validation Results

The evaluation pipeline was thoroughly validated through isolated synthetic tests and dry-run execution on real benchmark files:

### Synthetic Unit Test Suite (`tests/unit/test_human_benchmark_evaluation.py`)
All 7 synthetic test suites passed:
1. `test_missing_labels_and_unreviewed_rows`: Confirmed that unreviewed blank rows are skipped without corrupting metrics; only reviewed rows are evaluated.
2. `test_duplicate_records_handling`: Confirmed that duplicate predictions or duplicate human annotations are deduplicated in both strict set intersection and relaxed matching.
3. `test_invalid_categories_resilience`: Confirmed category alias normalization (`METHODS` -> `METHOD`, `DATASETS` -> `DATASET`, `LIMITATIONS` -> `LIMITATION`).
4. `test_empty_chunks_edge_cases`: Confirmed true negative chunks (0 predictions, 0 annotations), pure false positive chunks (predictions marked unsupported), and pure false negative chunks (0 predictions, human annotated missing items).
5. `test_partial_matches_relaxed_evaluation`: Confirmed that relaxed matching grants credit for token overlap $\ge 0.5$ and substring matches where strict matching fails.
6. `test_dual_annotator_reconciliation_synthetic`: Confirmed observed agreement rate, Cohen's Kappa computation, and consensus CSV generation on synthetic dual-reviewer sheets.
7. `test_comparative_evaluator_v040_vs_v041_synthetic`: Confirmed that `evaluate_human_benchmark()` evaluates `v0.4.0` and `v0.4.1` on the same ground truth and calculates strict/relaxed P, R, F1, and deltas.

### Status on Actual Benchmark Files
- Running `scripts/evaluate_human_benchmark.py` against `scientific_extraction_v0.4.0_audit_packet_25.csv` returned:
  - **Status**: `PENDING_HUMAN_ANNOTATION`
  - **Unreviewed Rows**: 164
  - **Completed Annotations**: 0
  - Refused to fabricate scientific precision, recall, or F1.
- Running `scripts/reconcile_human_annotations.py` on blank Reviewer 1 and Reviewer 2 packets confirmed 0 completed reviews and produced clean unreviewed templates.

### Full Test Suite Integrity
- `pytest tests/`: **124 / 124 passed**
- `pytest backend/tests/`: **2 / 2 passed**
- **Total Passing Tests**: **126 / 126 passed** (0 failures, 0 regressions).

---

## 4. Exact Commands for Evaluating Completed Annotations

### Step 1: Reconcile Dual Annotator Packets and Produce Consensus Template
```bash
python scripts/reconcile_human_annotations.py \
    --reviewer1 dataset/manifests/scientific_extraction_v0.4.0_audit_packet_reviewer1.csv \
    --reviewer2 dataset/manifests/scientific_extraction_v0.4.0_audit_packet_reviewer2.csv \
    --output-consensus dataset/manifests/scientific_extraction_benchmark_consensus_25.csv \
    --output-report dataset/manifests/scientific_extraction_adjudication_report.md
```

### Step 2: Evaluate Completed Annotations on Baseline (v0.4.0) and Experimental (v0.4.1)
```bash
python scripts/evaluate_human_benchmark.py \
    --annotations dataset/manifests/scientific_extraction_benchmark_consensus_25.csv \
    --v040-dir dataset/processed/v0.4.0 \
    --v041-dir dataset/processed/v0.4.1 \
    --output-dir dataset/manifests
```
*(If evaluating a single reviewer's completed packet directly, replace `--annotations` with the reviewer's CSV path).*

---

## 5. Remaining Blockers

1. **Human Review Execution**: Real human domain expert annotations have not yet been performed. The 25-chunk review packets are formatted, verified, and ready for annotator distribution.
2. **Phase Boundary Stop Condition**: In accordance with project instructions, Phase 4 components (embeddings, vector database, knowledge graph construction, hypothesis generation) must NOT begin until actual human annotations are completed, adjudicated, and evaluated.
