# ResearchGraph Data Processing Pipelines

This directory contains standalone, reproducible data-processing and graph-construction workflows.

## Pipeline vs. Application Services

Pipelines are decoupled from interactive web backend requests:
- **Batch Processing**: Run as deterministic CLI commands, cron tasks, or orchestration steps.
- **Reproducibility**: Parameterized by configuration files or manifests with explicit input/output lineage.

## Pipeline Stages

```text
pipelines/
├── ingestion/   # Literature collection from scholarly APIs (OpenAlex, S2, arXiv)
├── processing/  # Normalization, deduplication, field standardization, full-text parsing
├── graph/       # Batch entity resolution, relation extraction, graph construction
└── evaluation/  # Automated benchmark suites, discovery evaluation, validation pipelines
```
