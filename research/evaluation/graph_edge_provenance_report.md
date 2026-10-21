# ResearchGraph: Graph Edge Provenance Reconciliation Report
**Independent Audit Deliverable: Audit 2**

- **Date:** `2026-10-21T15:53:00Z`
- **Auditor:** Independent Principal Research Engineer
- **Knowledge Base Version:** `v0.5.1` (`dataset/processed/v0.5.1/knowledge_base.db`)
- **Graph Builder:** `pipelines/graph/builder.py` (`ResearchGraphBuilder`)

---

## 1. Executive Summary

The previous backend implementation report claimed that the ResearchGraph contains **618 nodes, 31 graph edges, and 22 trusted edges**, with 9 Cartesian-product relationships isolated as unsupported.

This audit conducted an exhaustive record-by-record trace of all 31 edges in the constructed graph. The audit revealed a **critical epistemic conflation**:

1. **The 22 "trusted edges" are NOT scientific concept-to-concept relationships.** They are **document-structural containment edges** (`Paper -CONTAINS-> Statement`) linking canonical paper identifiers to canonical statement nodes.
2. **The 9 concept-to-concept semantic edges are the exact 9 Cartesian-product relationships** from chunk `chk_rg_doi_ebe643c2b3dd_A_0135`, all of which are explicitly marked `evidence_support = UNSUPPORTED` in `v0.5.1`.
3. **There are currently ZERO trusted scientific relationships between concepts in the graph.**
4. All 22 statements in `v0.5.1` have empty related entity lists (`related_entity_ids_json = '[]'`), meaning zero `Statement -REPORTS-> Entity` edges could be instantiated.

---

## 2. Complete Inventory of Graph Edges

### Group A: The 22 "Trusted" Edges (Document Containment Edges)

All 22 edges below were generated dynamically in `ResearchGraphBuilder.build_graph()` (lines 226–244) during statement ingestion. They possess predicate `CONTAINS`, linking a paper node to a statement node. None of them link scientific concepts.

| Edge ID | Source (Paper ID) | Target (Statement ID) | Predicate | Attribution | Structural Validity | Evidence Support | Human Verification | Originating Chunk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `edge_contain_kb_stmt_01d0b20120ea` | `rg_doi_1e4a04e65f34` | `kb_stmt_01d0b20120ea` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0008` |
| `edge_contain_kb_stmt_0776aa2cbac7` | `rg_doi_03232127251a` | `kb_stmt_0776aa2cbac7` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0002` |
| `edge_contain_kb_stmt_0861d7d4ef42` | `rg_doi_0e010e052fc7` | `kb_stmt_0861d7d4ef42` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0011` |
| `edge_contain_kb_stmt_094039105d32` | `rg_doi_1e4a04e65f34` | `kb_stmt_094039105d32` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0008` |
| `edge_contain_kb_stmt_1d8335bc5124` | `rg_doi_3e5df365b74c` | `kb_stmt_1d8335bc5124` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0079` |
| `edge_contain_kb_stmt_21c29f73ecf8` | `rg_doi_0e010e052fc7` | `kb_stmt_21c29f73ecf8` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0011` |
| `edge_contain_kb_stmt_29bd3e1d05c7` | `rg_doi_0e010e052fc7` | `kb_stmt_29bd3e1d05c7` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0011` |
| `edge_contain_kb_stmt_2ef868e225db` | `rg_doi_1e4a04e65f34` | `kb_stmt_2ef868e225db` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0008` |
| `edge_contain_kb_stmt_313d3f98eeee` | `rg_doi_03232127251a` | `kb_stmt_313d3f98eeee` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0002` |
| `edge_contain_kb_stmt_3bfd83f2f7ab` | `rg_doi_03232127251a` | `kb_stmt_3bfd83f2f7ab` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0002` |
| `edge_contain_kb_stmt_526b4ef811c6` | `rg_doi_1e4a04e65f34` | `kb_stmt_526b4ef811c6` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0008` |
| `edge_contain_kb_stmt_6b667f284e34` | `rg_doi_3e5df365b74c` | `kb_stmt_6b667f284e34` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0079` |
| `edge_contain_kb_stmt_6ce7cf524604` | `rg_doi_1e4a04e65f34` | `kb_stmt_6ce7cf524604` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0008` |
| `edge_contain_kb_stmt_70f65075096c` | `rg_doi_1e4a04e65f34` | `kb_stmt_70f65075096c` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0008` |
| `edge_contain_kb_stmt_79785a6d4543` | `rg_doi_1e4a04e65f34` | `kb_stmt_79785a6d4543` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0008` |
| `edge_contain_kb_stmt_7b438dc13399` | `rg_doi_0e010e052fc7` | `kb_stmt_7b438dc13399` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0011` |
| `edge_contain_kb_stmt_99794a2a0e57` | `rg_doi_ebe643c2b3dd` | `kb_stmt_99794a2a0e57` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0135` |
| `edge_contain_kb_stmt_ab02b07ac3f9` | `rg_doi_50cd23001d0a` | `kb_stmt_ab02b07ac3f9` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0017` |
| `edge_contain_kb_stmt_b763b85c6494` | `rg_doi_0e010e052fc7` | `kb_stmt_b763b85c6494` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0011` |
| `edge_contain_kb_stmt_c20b4a12552e` | `rg_doi_1e4a04e65f34` | `kb_stmt_c20b4a12552e` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0008` |
| `edge_contain_kb_stmt_d5521bf900cd` | `rg_doi_255e1165891c` | `kb_stmt_d5521bf900cd` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0001` |
| `edge_contain_kb_stmt_fb06e6ac9279` | `rg_doi_1e4a04e65f34` | `kb_stmt_fb06e6ac9279` | `CONTAINS` | `AUTHOR_STATED` | `VALID` | `SUPPORTED` | `VERIFIED` | `chk_...0008` |

### Group B: The 9 Unsupported Concept-to-Concept Edges (Cartesian Artifacts)

All 9 edges below originate from the SQLite `relationships` table in `v0.5.1`. They are the known table-extraction Cartesian-product relationships generated from chunk `chk_rg_doi_ebe643c2b3dd_A_0135` (Paper `rg_doi_ebe643c2b3dd`). Every single one is marked `UNSUPPORTED`.

| Edge ID | Source Concept | Target Concept | Predicate | Evidence Support | Human Verification | Failure Mechanism |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `kb_rel_0d988b13f24c` | `machine learning` | `privacy concerns` | `ADDRESSES` | `UNSUPPORTED` | `PENDING` | Multi-row table cross-product pairing |
| `kb_rel_2fcbf639a5cf` | `ensemble learning` | `data privacy` | `ADDRESSES` | `UNSUPPORTED` | `PENDING` | Multi-row table cross-product pairing |
| `kb_rel_558c0922c745` | `federated learning` | `data privacy` | `ADDRESSES` | `UNSUPPORTED` | `PENDING` | Multi-row table cross-product pairing |
| `kb_rel_7c08ae08b2d0` | `machine learning` | `data privacy` | `ADDRESSES` | `UNSUPPORTED` | `PENDING` | Multi-row table cross-product pairing |
| `kb_rel_8bef13af90e9` | `federated learning` | `privacy concerns` | `ADDRESSES` | `UNSUPPORTED` | `PENDING` | Multi-row table cross-product pairing |
| `kb_rel_9eacb770b891` | `federated learning` | `computational cost` | `LIMITED_BY` | `UNSUPPORTED` | `PENDING` | Multi-row table cross-product pairing |
| `kb_rel_bdeea8a57805` | `ensemble learning` | `privacy concerns` | `ADDRESSES` | `UNSUPPORTED` | `PENDING` | Multi-row table cross-product pairing |
| `kb_rel_bf57d03902f7` | `ensemble learning` | `computational cost` | `LIMITED_BY` | `UNSUPPORTED` | `PENDING` | Multi-row table cross-product pairing |
| `kb_rel_c043dbedbb58` | `machine learning` | `computational cost` | `LIMITED_BY` | `UNSUPPORTED` | `PENDING` | Multi-row table cross-product pairing |

---

## 3. Provenance Discrepancy Analysis

### 3.1 The Illusion of Trusted Scientific Edges
In the previous implementation summary, the phrase:
> *"Total Nodes: 618, Total Edges: 31, Trusted Edges: 22, Excluded Cartesian: 9"*

created the impression that 22 scientific relationships had survived evidence validation, while 9 were quarantined.
In reality:
- The 22 edges are document-containment structures (`Paper CONTAINS Statement`). They do not bridge entities or scientific concepts.
- The 9 relationships are the *only* semantic relationships in the database, and 100% of them are quarantined.
- When `GraphTraversalEngine` filters with `trusted_only = True`, **no path between two scientific concepts can ever be traversed using graph edges alone**.

### 3.2 Impact on Cross-Domain Discovery (Phase 7)
Because there are zero trusted concept-to-concept graph edges:
- Swanson-style LBD ($A \rightarrow B \rightarrow C$) cannot find intermediate bridging concepts via graph edges alone, because all outgoing edges from concept nodes are marked `UNSUPPORTED`.
- Discovery algorithms fall back to **hybrid retrieval over chunks** (`retrieval.retrieve_hybrid()`) rather than traversing mechanistic graph paths.

---

## 4. Auditor Recommendations

1. **Explicit Schema Segregation:** In `GraphEdge`, distinguish `EdgeCategory.DOCUMENT_STRUCTURE` (containment, authorship, section hierarchy) from `EdgeCategory.SCIENTIFIC_RELATIONSHIP` (mechanistic, causal, evaluation).
2. **Phase 3 Relationship Extraction Expansion:** Expand scientific relationship extraction beyond the single 75-chunk pilot to extract validated, grounded relationships across the 3,582 chunks of `v0.3.0`.
3. **Transparent Reporting:** The system must clearly report that current discovery is **hybrid retrieval-grounded**, not **semantic graph path-grounded**, until genuine concept-to-concept relationships are extracted and verified.
