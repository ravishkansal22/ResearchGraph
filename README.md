# ResearchGraph

> An open, mechanistic research discovery platform to systematically analyze scientific literature, construct cross-domain knowledge graphs, verify research gaps, detect previously failed approaches, and generate evidence-grounded, falsifiable hypotheses.

---

## 1. Project Overview

**ResearchGraph** is a research discovery platform and scientific hypothesis generation system. By indexing literature, extracting semantic entities and causal mechanisms, mapping negative results (what failed and why), and linking cross-domain findings, ResearchGraph helps researchers uncover non-obvious gaps and formulate novel, testable directions.

### Core Objectives
- **Mechanistic Literature Representation**: Parse and represent scientific papers as structured entities, relationships, and experimental conditions rather than unstructured text chunks.
- **Cross-Domain Connection Discovery**: Identify analogous mechanisms across distant sub-fields of Artificial Intelligence (and broader disciplines).
- **Negative Knowledge & Prior Failures**: Surface documented dead-ends, failure modes, and boundary constraints to prevent redundant efforts.
- **Falsifiable Hypothesis Generation**: Synthesize grounded hypotheses with supporting literature traces, suggested experimental protocols, and critical evaluation ("Reviewer #2" adversarial check).

---

## 2. Repository Structure

```text
ResearchGraph/
├── backend/            # Production API, domain models, services, and workers (FastAPI, SQLAlchemy)
├── frontend/           # ResearchGraph interactive workbench (Next.js, TypeScript, Tailwind)
├── dataset/            # Multi-tier scientific literature corpus storage & manifest schemas
├── research/           # Isolated experimental explorations (LBD algorithms, extraction, discovery)
├── pipelines/          # Reproducible, standalone workflows (ingestion, graph construction, evaluation)
├── docs/               # Architectural designs, ADRs, research notes, and API documentation
├── infrastructure/     # Container configurations, database migrations, and deployment specs
├── tests/              # Cross-boundary integration, e2e tests, and shared test fixtures
├── scripts/            # Developer automation and repository maintenance utilities
├── .github/            # GitHub Actions CI/CD workflows
├── .env.example        # Environment variable configuration template
├── docker-compose.yml  # Local development infrastructure (PostgreSQL, Redis)
├── Makefile            # Standard developer commands
├── LICENSE             # Project license
└── README.md           # Repository documentation
```

---

## 3. Engineering & Architecture Separation

To ensure scientific rigor and long-term maintainability:

| Directory | Responsibility | Separation Principle |
|---|---|---|
| `backend/` | Production application services, persistent API endpoints, schemas, database access, background workers. | High availability, strict typing, zero untested experimental scripts. |
| `research/` | Experimental explorations, algorithmic prototypes (e.g., Swanson LBD variations, embedding benchmarks). | Fast experimentation, benchmark scripts; only promoted to `backend/` or `pipelines/` once validated. |
| `dataset/` | Corpus tiers (`raw/`, `interim/`, `processed/`, `fulltext/`), schemas, and versioned manifests. | Datasets are strictly externalized from Git history; schema definitions enforce integrity. |
| `pipelines/` | Standalone, deterministic, reproducible processing workflows (ingestion, graph building, evaluation). | Can run as independent batch jobs or scheduled tasks outside the API server. |

---

## 4. Current Development Status

**Active Stage: Phase 1 — Dataset / Literature Collection**

The initial focus is establishing the literature collection, normalization, and deduplication pipeline for the AI domain:
- **Sources under investigation**: OpenAlex, Semantic Scholar, arXiv.
- **Target taxonomy**: Machine Learning, NLP, LLMs, Computer Vision, Agentic Systems, AI Efficiency, Alignment, and related subfields.

---

## 5. Development Setup

### Prerequisites
- Python 3.11+
- Node.js 20+ & npm
- Docker & Docker Compose

### Quick Start
1. **Clone & Configure Environment**:
   ```bash
   cp .env.example .env
   ```
2. **Start Local Infrastructure**:
   ```bash
   make up
   ```
3. **Install Dependencies**:
   ```bash
   make setup
   ```
