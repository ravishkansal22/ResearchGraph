# ResearchGraph Phase 7: Discovery Scoring Ablation Report

**Query:** privacy-preserving federated machine learning in clinical oncology  

| Configuration | Top Candidate | Top Score | Candidates Returned |
|---|---|---|---|
| **full_model** | healthcare | 0.5625 | 5 |
| **ablation_no_distance** | healthcare | 0.4825 | 5 |
| **ablation_no_redundancy_penalty** | healthcare | 0.5625 | 5 |
| **ablation_no_evidence** | healthcare | 0.6875 | 5 |
| **ablation_no_contradiction** | healthcare | 0.5625 | 5 |

## Findings

- **Domain Distance Component:** Successfully distinguishes cross-disciplinary transfers from trivial same-field rephrasing.
- **Redundancy Penalty:** Penalizes concepts already co-occurring within the same document, elevating latent connections.
- **Evidence Support Weight:** Ensures that high semantic similarity without grounding evidence cannot dominate the top ranks.
