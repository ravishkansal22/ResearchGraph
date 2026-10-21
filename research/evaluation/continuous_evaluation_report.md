# ResearchGraph Phase 15: Continuous Evaluation Report

- **Generated:** `2026-10-21T15:20:16.109451+00:00`
- **Evaluation Version:** `v1.0.0`
- **Execution Latency:** `11.06 seconds`
- **Corpus Scope:** 50 canonical papers, 3,582 chunks (`v0.2.0`), KB `v0.5.1`

## 1. Multi-Modal Retrieval Performance

| Metric | BM25 Lexical | Dense Vector (TF-IDF/LSA 384d) | Hybrid RRF |
| :--- | :--- | :--- | :--- |
| **Mean Query Latency** | `1.822 ms` | `6.268 ms` | `8.15 ms` |
| **Indexed Corpus Chunks** | `500` | `500` | `500` |
| **Mean Top-5 Overlap** | - | - | `0.39` |

## 2. Research Graph Quality & Integrity

- **Total Nodes:** `618`
- **Total Edges:** `31`
- **Trusted Edges:** `22`
- **Excluded Cartesian Edges (v0.5.1):** `9` (Strictly isolated from trusted discovery)
- **Referential Integrity Violations:** `0` (0 violations)
- **Trusted Subgraph Export Verified:** `True`

## 3. Cross-Domain Discovery & Scoring Ablations

- **Total Discovery Candidates Generated:** `15`
- **Active Discovery Strategies:** `PROBLEM_TO_METHOD`

### Ablation Study Results

| Scoring Configuration | Mean Score | Delta vs Full |
| :--- | :--- | :--- |
| **Full Discovery Scorer** | `0.825` | `0.0000` |
| **w/o Cross-Domain Distance Bonus** | `0.745` | `+0.0800` |
| **w/o Contradiction Risk Penalty** | `0.825` | `+0.0000` |

## 4. Research-Gap Verification & Epistemic Boundaries

- **False-Novelty Prevention Rate:** `100.0%` (Strict non-inflation invariant)
| Case | Status | Precedents Found | Supporting Evidence | Audit Trail Events |
| :--- | :--- | :--- | :--- | :--- |
| prompt injection defenses in large language models... | `POSSIBLE_GAP` | `0` | `1` | `3` |
| federated learning clinical oncology institutional... | `POSSIBLE_GAP` | `0` | `2` | `3` |
| quantum-gravity unified lattice simulation on neur... | `POSSIBLE_GAP` | `0` | `2` | `3` |

## 5. Negative Knowledge & Dead-End Graveyard

- **Indexed Negative Knowledge Records:** `7`
- **Bottlenecks Cataloged:** `2`
- **FL Method Failure Modes:** `1`
- **FL Contradiction Risk Score:** `0.0`

## 6. Hypotheses, Reviewer #2 & Experiment Design

- **Hypotheses Synthesized:** `3`
- **Adversarial Review Verdict Distribution:** `{'PROMISING_BUT_UNVERIFIED': 3}`

| Hypothesis ID | Independent Vars | Dependent Vars | Reviewer Verdict | Protocol Steps | Rejection Criteria Explicit |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `hyp_923a71c8087d` | `3` | `3` | `PROMISING_BUT_UNVERIFIED` | `8` | `True` |
| `hyp_e2ad78d1a284` | `3` | `3` | `PROMISING_BUT_UNVERIFIED` | `8` | `True` |
| `hyp_3e0391b0b140` | `3` | `3` | `PROMISING_BUT_UNVERIFIED` | `8` | `True` |
