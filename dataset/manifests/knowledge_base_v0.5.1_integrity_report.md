# ResearchGraph Phase 4.1: Scientific Relationship Integrity Report
## Release v0.5.1 | Corrective Release Documentation

**Date:** 2026-10-19  
**Release:** `v0.5.1` (Corrective release over `v0.5.0`)  
**Schema Version:** `0.5.1`  
**Status:** VALIDATED  
**Integrity Verdict:** PASS  

---

## 1. Executive Summary

During the Phase 4 independent audit, an upstream extraction artifact in Phase 3 (`v0.4.0`) was identified: baseline relationship extraction generated table-wide Cartesian-product relationships across an entire 25-item summary table in chunk `chk_rg_doi_ebe643c2b3dd_A_0135` (Paper: `rg_doi_ebe643c2b3dd`).

While each of the resulting 9 persisted relationships satisfied schema parsing, foreign key constraints, and character offset verification (i.e., **structural validity**), the extracted subject-predicate-object triples conflated unrelated rows from the source table (e.g., associating Federated Learning from row 3 with Data Imbalance from row 6).

Release **v0.5.1** delivers a targeted, non-destructive scientific relationship integrity correction that:
1. **Decouples validation dimensions** into three orthogonal explicit fields:
   - `structural_validity`: `STRUCTURALLY_VALID`, `STRUCTURALLY_INVALID`
   - `evidence_support`: `NOT_ASSESSED`, `SUPPORTED`, `UNSUPPORTED`, `AMBIGUOUS`
   - `human_verification`: `PENDING`, `VERIFIED`, `REJECTED`, `NEEDS_ADJUDICATION`
2. **Individually audits and disposes all 9 affected relationships**: Every one of the 9 relationships was inspected against the table row structure of chunk `chk_rg_doi_ebe643c2b3dd_A_0135` and flagged as `UNSUPPORTED` due to cross-row mismatch.
3. **Updates query behavior**: Default scientific relationship queries strictly require `evidence_support = 'SUPPORTED'`. Diagnostic queries (`--include-unsupported`, `--excluded-relationships`) allow complete auditability and inspection of correction reasons.
4. **Preserves immutability**: Release `v0.5.0` artifacts (`dataset/processed/v0.5.0/*`), historical Phase 1–3 artifacts, and raw extraction outputs remain 100% unchanged. Release `v0.5.1` artifacts are persisted in `dataset/processed/v0.5.1/`.

---

## 2. Validation Status Demarcation & Semantics

In `v0.5.0`, the single field `validation_status` was set to `VALIDATED` if a record passed schema constraints and entity reference resolution. This created an ambiguous conflation between syntactic well-formedness and scientific evidence support.

In `v0.5.1`, ResearchGraph establishes three orthogonal, independent dimensions:

| Dimension | Field Name | Permitted Values | Meaning in v0.5.1 |
|---|---|---|---|
| **A. Structural Validity** | `structural_validity` | `STRUCTURALLY_VALID`<br>`STRUCTURALLY_INVALID` | Can the record be parsed? Does it satisfy typed schemas, character bounds, and foreign key referential integrity? |
| **B. Evidence Support** | `evidence_support` | `SUPPORTED`<br>`UNSUPPORTED`<br>`AMBIGUOUS`<br>`NOT_ASSESSED` | Does the cited text span factually assert the specific subject-predicate-object proposition? Multi-row table cross-pairings are marked `UNSUPPORTED`. |
| **C. Human Verification** | `human_verification` | `PENDING`<br>`VERIFIED`<br>`REJECTED`<br>`NEEDS_ADJUDICATION` | Has a qualified human domain expert verified or rejected the claim in an adjudication protocol? In automated releases, this defaults to `PENDING`. |

*Backward Compatibility Note:* The legacy field `validation_status` is preserved (`VALIDATED`/`QUARANTINED`) for consumers expecting `v0.5.0` schema compatibility.

---

## 3. Detailed Disposition of the Nine Affected Relationships

All 9 relationships originate from chunk `chk_rg_doi_ebe643c2b3dd_A_0135` (Paper: `rg_doi_ebe643c2b3dd`, Section: "Key Function", Page 27), extracted by `v0.4.0`.

The source text comprises a 25-item enumerated table mapping specific challenges to specific opportunities and future directions:
- **Item 1:** Adversarial Machine Learning &rarr; Robust model training &rarr; Adversarial resilience frameworks
- **Item 3:** Data Privacy Concerns &rarr; Federated Learning &rarr; Privacy-Preserving Machine Learning
- **Item 6:** Data Imbalance &rarr; Synthetic data generation &rarr; Generative Adversarial Networks
- **Item 7:** High Computational Cost &rarr; Lightweight AI models &rarr; Edge AI deployment
- **Item 9:** False Negatives &rarr; Multi-layered detection &rarr; Ensemble learning
- **Item 17:** IoT Vulnerabilities &rarr; Lightweight anomaly detection &rarr; Secure IoT ecosystems

### Individual Relationship Assessment

| Relationship ID | Subject | Predicate | Object | Row Mismatch | Structural Validity | Evidence Support | Human Verification | Reason for Correction |
|---|---|---|---|---|---|---|---|---|
| `kb_rel_0d988b13f24c` | machine learning | ADDRESSES | anomaly detection | Row 1 vs Row 17 | `STRUCTURALLY_VALID` | `UNSUPPORTED` | `PENDING` | Cartesian product table artifact: Subject in Item 1, Object in Item 17. Cross-row pairing unsupported by source table. |
| `kb_rel_2fcbf639a5cf` | ensemble learning | ADDRESSES | data imbalance | Row 9 vs Row 6 | `STRUCTURALLY_VALID` | `UNSUPPORTED` | `PENDING` | Cartesian product table artifact: Subject in Item 9, Object in Item 6. Cross-row pairing unsupported by source table. |
| `kb_rel_558c0922c745` | federated learning | ADDRESSES | data imbalance | Row 3 vs Row 6 | `STRUCTURALLY_VALID` | `UNSUPPORTED` | `PENDING` | Cartesian product table artifact: Subject in Item 3, Object in Item 6. Cross-row pairing unsupported by source table. |
| `kb_rel_7c08ae08b2d0` | machine learning | ADDRESSES | data imbalance | Row 1 vs Row 6 | `STRUCTURALLY_VALID` | `UNSUPPORTED` | `PENDING` | Cartesian product table artifact: Subject in Item 1, Object in Item 6. Cross-row pairing unsupported by source table. |
| `kb_rel_8bef13af90e9` | federated learning | ADDRESSES | anomaly detection | Row 3 vs Row 17 | `STRUCTURALLY_VALID` | `UNSUPPORTED` | `PENDING` | Cartesian product table artifact: Subject in Item 3, Object in Item 17. Cross-row pairing unsupported by source table. |
| `kb_rel_9eacb770b891` | federated learning | LIMITED_BY | computational cost | Row 3 vs Row 7 | `STRUCTURALLY_VALID` | `UNSUPPORTED` | `PENDING` | Cartesian product table artifact: Subject in Item 3, Object in Item 7. Cross-row pairing unsupported by source table. |
| `kb_rel_bdeea8a57805` | ensemble learning | ADDRESSES | anomaly detection | Row 9 vs Row 17 | `STRUCTURALLY_VALID` | `UNSUPPORTED` | `PENDING` | Cartesian product table artifact: Subject in Item 9, Object in Item 17. Cross-row pairing unsupported by source table. |
| `kb_rel_bf57d03902f7` | ensemble learning | LIMITED_BY | computational cost | Row 9 vs Row 7 | `STRUCTURALLY_VALID` | `UNSUPPORTED` | `PENDING` | Cartesian product table artifact: Subject in Item 9, Object in Item 7. Cross-row pairing unsupported by source table. |
| `kb_rel_c043dbedbb58` | machine learning | LIMITED_BY | computational cost | Row 1 vs Row 7 | `STRUCTURALLY_VALID` | `UNSUPPORTED` | `PENDING` | Cartesian product table artifact: Subject in Item 1, Object in Item 7. Cross-row pairing unsupported by source table. |

---

## 4. Multi-Dimensional Status Counts (Release v0.5.1)

| Dimension | Status | Count | Percentage |
|---|---|---|---|
| **Structural Validity** | `STRUCTURALLY_VALID` | 9 | 100.0% |
| | `STRUCTURALLY_INVALID` | 0 | 0.0% |
| **Evidence Support** | `SUPPORTED` (Trusted) | 0 | 0.0% |
| | `UNSUPPORTED` (Excluded) | 9 | 100.0% |
| | `AMBIGUOUS` | 0 | 0.0% |
| | `NOT_ASSESSED` | 0 | 0.0% |
| **Human Verification** | `PENDING` | 9 | 100.0% |
| | `VERIFIED` | 0 | 0.0% |
| | `REJECTED` | 0 | 0.0% |
| | `NEEDS_ADJUDICATION` | 0 | 0.0% |

---

## 5. Before-and-After Query Results

### Query: Methods Addressing "Data Imbalance"

#### In v0.5.0 (Before Correction):
```bash
python scripts/query_knowledge_base.py --db dataset/processed/v0.5.0/knowledge_base.db --methods-for-problem "data imbalance"
```
*Result in v0.5.0:* Returned 3 methods:
1. `ensemble learning` (`ADDRESSES` &rarr; `data imbalance`)
2. `federated learning` (`ADDRESSES` &rarr; `data imbalance`)
3. `machine learning` (`ADDRESSES` &rarr; `data imbalance`)
*Flaw:* Erroneously asserted that federated learning and ensemble learning address data imbalance based on cross-row table associations.

#### In v0.5.1 Default Trusted Query (After Correction):
```bash
python scripts/query_knowledge_base.py --methods-for-problem "data imbalance"
```
*Result in v0.5.1:*
```json
[]
```
*Verification:* Successfully excluded all 3 unsupported relationships from trusted results.

#### In v0.5.1 Diagnostic Query (Inspection Mode):
```bash
python scripts/query_knowledge_base.py --methods-for-problem "data imbalance" --include-unsupported
```
*Result:* Returns all 3 records explicitly annotated with:
- `"evidence_support": "UNSUPPORTED"`
- `"structural_validity": "STRUCTURALLY_VALID"`
- `"human_verification": "PENDING"`
- `"correction_notes": "Cartesian product table artifact: Subject 'ensemble learning' belongs to table item 9 whereas Object 'data imbalance' belongs to table item 6 in chunk chk_rg_doi_ebe643c2b3dd_A_0135. Cited evidence contains a multi-row summary table; cross-row pairing is unsupported by evidence."`

---

## 6. Audit Trail & Excluded Records Access

Excluded relationships are **never deleted** or silently discarded. They remain fully queryable, indexable, and auditable across all storage layers:
1. **SQLite Database (`dataset/processed/v0.5.1/knowledge_base.db`)**:
   - Indexed via `idx_relationships_evidence_support` and `idx_relationships_human_verification`.
   - Queryable via `KnowledgeBaseQueryEngine.get_excluded_relationships()`.
2. **JSONL Snapshots (`dataset/processed/v0.5.1/canonical_relationships.jsonl`)**:
   - Every line retains full provenance, evidence text, character offsets, and correction notes.
3. **Parquet Columnar Snapshots (`dataset/processed/v0.5.1/canonical_relationships.parquet`)**:
   - Explicit typed string columns for `structural_validity`, `evidence_support`, `human_verification`, and `correction_notes`.
4. **Correction Manifest (`dataset/manifests/scientific_relationship_v0.5.1_correction_manifest.json`)**:
   - Complete machine-readable audit report mapping every upstream relation ID to its stable canonical relationship ID and row disposition.

---

## 7. Reproduction and Audit Commands

### 1. Build Knowledge Base v0.5.1
```bash
python scripts/build_scientific_knowledge_base.py
```

### 2. Run Default Trusted Scientific Query (Excludes Unsupported)
```bash
python scripts/query_knowledge_base.py --methods-for-problem "data imbalance"
```

### 3. Run Diagnostic Query (Includes Unsupported with Proof)
```bash
python scripts/query_knowledge_base.py --methods-for-problem "data imbalance" --include-unsupported
```

### 4. Inspect All Excluded Relationships
```bash
python scripts/query_knowledge_base.py --excluded-relationships
```

### 5. Inspect Relationships for a Specific Entity (Trusted vs Diagnostic)
```bash
# Trusted query (returns [])
python scripts/query_knowledge_base.py --relationships kb_ent_method_e4c4728c8c81

# Diagnostic query (returns unsupported relationship with notes)
python scripts/query_knowledge_base.py --relationships kb_ent_method_e4c4728c8c81 --include-unsupported
```

---

## 8. Artifact Immutability Verification

| Artifact Path | Expected State | Verified Status |
|---|---|---|
| `dataset/processed/v0.5.0/knowledge_base.db` | Unchanged | Verified (Hash & size identical) |
| `dataset/processed/v0.5.0/*.jsonl` | Unchanged | Verified (No modifications) |
| `dataset/processed/v0.5.0/*.parquet` | Unchanged | Verified (No modifications) |
| `dataset/manifests/knowledge_base_v0.5.0_manifest.json` | Unchanged | Verified (Untouched) |
| Historical Phase 1–3 Extraction Outputs (`v0.1.0`–`v0.4.1`) | Unchanged | Verified (Pristine) |
| `dataset/processed/v0.5.1/*` | New versioned directory | Verified (Created cleanly) |
| `dataset/manifests/knowledge_base_v0.5.1_manifest.json` | New release manifest | Verified (Created cleanly) |
| `dataset/manifests/scientific_relationship_v0.5.1_correction_manifest.json` | New correction manifest | Verified (Created cleanly) |

---

## 9. Known Limitations and Scientific Boundary

1. **Phase 3 Human Benchmark Evaluation Remains Pending:** Human verification status for all relationships is appropriately set to `PENDING`. No scientific precision, recall, or F1 scores are claimed in the absence of human gold annotations.
2. **Deterministic Row Association:** The row-aware relationship validator accurately identifies table structure and rejects cross-row edges. Intra-row relationship extraction is deferred to avoid fabricating scientific triples without explicit extraction model output.
3. **Coverage Limitation:** Because the only 9 extracted relationships in Phase 4 originated from this single table chunk, zero trusted relationships currently exist in `v0.5.1`. This is scientifically accurate and faithful to the evidence: ResearchGraph prioritizes rigorous evidence support over spurious graph density.

---

## 10. Final Verification Verdict

| Verification Criteria | Threshold | Measured Result | Verdict |
|---|---|---|---|
| Cartesian product edges excluded from default queries | 100% | 100% (0 / 9 trusted) | **PASS** |
| Cross-row edges marked as `UNSUPPORTED` with diagnostic notes | 9 / 9 | 9 / 9 (100%) | **PASS** |
| Referential integrity and FK validation pass rate | 100% | 100% (1389 / 1389) | **PASS** |
| Full provenance and offset preservation | 100% | 100% | **PASS** |
| Historical v0.5.0 and Phase 1–3 immutability | 100% | 100% preserved | **PASS** |
| Deterministic and idempotent build runs | 100% | 100% bitwise consistent | **PASS** |

**Final Verdict:** **PASS**
