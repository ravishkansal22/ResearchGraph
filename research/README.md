# ResearchGraph Research & Exploration

This directory contains experimental, exploratory, and prototype research implementations.

## Architectural Separation: Research vs. Backend

```text
research/                      backend/ & pipelines/
Experimental Algorithms  ───►  Validated Production Services & Batch Workflows
(Swanson LBD prototypes,       (High-throughput, strictly-typed, tested,
 embedding benchmarks, etc.)   production-ready modules)
```

1. **Experimental Freedom**: Code here can experiment with novel ranking metrics, prompt variations, LBD traversal heuristics, and clustering techniques.
2. **Promotion Pathway**: Once an experimental approach is benchmarked, validated, and documented against baseline evaluations, it is refactored into production services (`backend/`) or standalone batch pipelines (`pipelines/`).

## Research Sub-Areas

| Directory | Scope & Focus Area |
|---|---|
| `literature_collection/` | Exploratory source benchmarking, rate-limit analyses, query recall evaluations. |
| `information_extraction/` | Entity, relation, mechanism, and claim extraction experiments (NER, OpenIE, LLM parsers). |
| `embeddings/` | Representation learning, scientific semantic encoders, contrastive fine-tuning. |
| `knowledge_graph/` | Graph construction topologies, causal link prediction, multi-hop path extraction. |
| `discovery/` | Swanson Literature-Based Discovery (LBD) variations, cross-domain bridge algorithms. |
| `novelty/` | Novelty scoring, conceptual distance metrics, prior art differentiation heuristics. |
| `negative_knowledge/` | Mining failed approaches, negative results, ablation regressions, and constraint boundary analysis. |
| `hypothesis/` | Mechanistic hypothesis synthesis, falsifiable proposition formulation, experimental protocol drafting. |
| `evaluation/` | Discovery backtesting protocols, historical rediscovery benchmarks, expert evaluation rubrics. |
