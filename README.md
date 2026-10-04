# ResearchGraph

> A research discovery and scientific literature intelligence platform designed to uncover non-obvious connections across research domains and transform them into evidence-grounded, falsifiable research hypotheses.

---

## Overview

Modern scientific research is expanding exponentially, yet it remains heavily siloed. Specialized terminology, fragmented sub-disciplines, and dense publication volumes create artificial boundaries where researchers rarely observe relevant advances outside their immediate niches. Consequently, complementary breakthroughs often develop in parallel for years without convergence, while solutions, mathematical formalisms, and mechanistic mitigations established in one field remain invisible to adjacent domains facing identical bottlenecks.

**ResearchGraph** is built to bridge these epistemological divides. By modeling scientific literature as a structured, mechanistic knowledge graph rather than flat text embeddings or unstructured citation networks, ResearchGraph systematically traverses cross-domain topologies to discover latent connections, verify authentic research gaps, identify historically documented dead ends, and formulate testable hypotheses.

### What ResearchGraph Is NOT

To maintain technical clarity and rigorous scope, ResearchGraph is explicitly differentiated from existing superficial literature tools:

* **NOT a generic RAG chatbot**: It does not retrieve top-$k$ text chunks to prompt an LLM for conversational summaries without causal grounding.
* **NOT a PDF summarizer**: It does not merely condense document abstracts or generate high-level paper takeaways.
* **NOT a simple citation-network visualizer**: It does not treat papers as opaque nodes connected solely by bibliographic references.
* **NOT a conventional semantic search engine**: It does not rely purely on keyword indexing or vector similarity over surface text.

ResearchGraph’s long-term objective is to operate as an epistemological discovery engine: a **Serendipity Engine + Epistemological Discovery Platform** designed to accelerate scientific inquiry through structured causal reasoning and adversarial validation.

---

## Problem

1. **Terminology Silos & Disciplinary Tunnel Vision**: The same conceptual mechanism or mathematical technique is often described using entirely disparate nomenclature across subfields (e.g., control theory vs. reinforcement learning vs. optimization).
2. **Superficial Literature Retrieval**: Traditional keyword and dense retrieval methods surface papers within the same citation cluster or semantic neighborhood, failing to bridge distant conceptual domains.
3. **Buried Negative Knowledge**: Failed methodologies, negative results, ablation regressions, and operational constraints are routinely buried in appendices or left unpublished, leading subsequent researchers to repeat failed approaches.
4. **Lack of Falsifiability in Automated Synthesis**: Generative AI tools frequently produce plausible-sounding research directions that lack operationalized variables, concrete failure criteria, or grounded experimental protocols.

---

## Vision

The overarching goal of ResearchGraph is to transition computational literature analysis from **passive document search** to **active scientific discovery**:

```text
Scientific Literature Corpus (Unstructured Text & Data)
                       │
                       ▼
         Mechanistic Knowledge Extraction
                       │
                       ▼
      Topological & Literature-Based Discovery (LBD)
                       │
                       ▼
         Negative Knowledge & Constraint Check
                       │
                       ▼
   Adversarial Hypothesis Validation ("Reviewer #2")
                       │
                       ▼
      Evidence-Grounded, Falsifiable Hypothesis Dossier
```

---

## Core Research Ideas

ResearchGraph investigates several novel paradigms at the intersection of knowledge graphs, literature-based discovery, and formal hypothesis formulation.

> **Note**: The concepts outlined below represent core architectural and research directions. Specific sub-systems will be implemented progressively according to the project roadmap.

### 1. Mechanistic Knowledge Graph

Rather than representing papers as atomic nodes in a citation graph, literature is parsed into granular scientific entities:

* **Entities**: `Method`, `Bottleneck`, `Mechanism`, `Constraint`, `Metric`, `Claim`, `Assumption`, `Dataset/Domain`.
* **Causal & Operational Relations**:
  * `[Method A]` *mitigates* `[Bottleneck B]`
  * `[Method A]` *causes failure under* `[Constraint C]`
  * `[Metric M]` *measures* `[Bottleneck B]`
  * `[Method A]` *depends on* `[Assumption K]`
  * `[Claim X]` *contradicts* `[Claim Y]`
  * `[Method A]` *improves* `[Metric M]` *over* `[Method B]`

### 2. Swanson-Style Literature-Based Discovery (LBD)

Drawing on Don R. Swanson’s seminal formulation of undiscovered public knowledge (e.g., $A \rightarrow B$ and $B \rightarrow C \implies A \rightarrow C$ where $A$ and $C$ share no direct co-citations), ResearchGraph generalizes open and closed discovery models to multi-hop graph traversal, cross-domain analogy matching, and latent structural link prediction.

### 3. Dead End Graveyard (Negative Knowledge Mining)

A dedicated negative knowledge repository designed to catalog:
* Documented empirical limitations and negative findings.
* Buried ablation regressions where proposed methods failed to outperform baselines.
* Theoretical and physical/computational constraints (e.g., memory bottlenecks, sample complexity lower bounds).
* Historical dead ends to prevent researchers from pursuing well-documented dead pathways.

### 4. Reviewer #2 (Adversarial Validation Layer)

An adversarial reasoning component that actively challenges every synthesized connection and hypothesis:
* Identifies unstated or invalid assumptions.
* Flags missing experimental controls, confounders, and conflicting literature evidence.
* Evaluates whether a proposed link is trivially obvious, already explored, or physically unviable.

### 5. Falsifiable Hypothesis Dossier

Discovered gaps and cross-domain connections are compiled into structured, actionable research dossiers containing:
* **Proposed Mechanism**: Precise causal mechanism hypothesized to bridge the gap.
* **Underlying Assumptions**: Explicit conditions required for the mechanism to hold.
* **Operational Variables**: Defined Independent Variables ($IV$) and Dependent Variables ($DV$).
* **Quantitative Metrics**: Specific evaluation benchmarks and objective criteria.
* **Falsification Criteria**: Precise empirical thresholds that would disprove the hypothesis.
* **Evidence Provenance**: Direct citation lineages and extracted excerpts substantiating the claim.

---

## System Architecture

ResearchGraph is organized around clean architectural boundaries separating data pipelines, research experimentation, production services, and user interfaces:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                               dataset/                                 │
│      Corpus Storage Tiers: Raw → Interim → Processed → Full Text       │
└──────────────┬──────────────────────────────────────────┬──────────────┘
               │                                          │
               ▼                                          ▼
┌──────────────────────────────┐          ┌──────────────────────────────┐
│          pipelines/          │          │          research/           │
│ Deterministic Workflows      │          │ Exploratory Algorithms       │
│ • Literature Ingestion       │          │ • LBD Traversal Experiments  │
│ • Normalization & Dedup      │          │ • Extraction Prototypes      │
│ • Graph Construction         │          │ • Novelty & Gap Metrics      │
└──────────────┬───────────────┘          └──────────────┬───────────────┘
               │                                         │
               │ (validated graph & datasets)            │ (validated logic)
               ▼                                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│                               backend/                                 │
│  FastAPI Application Layer • Domain Models • Repositories • Services   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (Typed API Contracts)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                               frontend/                                │
│       ResearchGraph Three-Pane Workbench (Next.js / TypeScript)        │
│   [ Research Graph ]   |   [ Hypothesis Dossier ]   |   [ Evidence ]   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Development Roadmap

ResearchGraph is structured into 15 sequential development phases. Evaluation is conducted continuously across each milestone rather than solely at project completion.

```text
 1. Dataset / Literature Collection          ◄── (CURRENT PHASE)
 2. Document Processing & Normalization
 3. Scientific Information Extraction
 4. Research Knowledge Base
 5. Semantic Representation / Embeddings
 6. Research Graph Construction
 7. Discovery Algorithms (Swanson LBD & Graph Mining)
 8. Gap / Novelty Verification
 9. Negative Knowledge / Dead-End Detection
10. Hypothesis Engine
11. Reviewer #2 / Adversarial Validation
12. Experiment Designer & Protocol Formulation
13. Production Backend APIs
14. Interactive Frontend Workbench
15. End-to-End System Evaluation & Benchmarking
```

---

## Current Phase

### **Phase 1 — Dataset / Literature Collection**

We are currently establishing the foundational data ingestion pipelines, storage tiers, and canonical schema definitions.

* **Target Research Universe**: Artificial Intelligence (AI), covering sub-domains including:
  * Machine Learning & Statistical Learning
  * Deep Learning Architectures
  * Natural Language Processing (NLP) & Large Language Models (LLMs)
  * Retrieval-Augmented Generation (RAG) & Vector Retrieval
  * AI Agents & Multi-Agent Systems
  * Reinforcement Learning (RL)
  * Computer Vision & Multimodal Perception
  * Speech & Audio Processing
  * Generative AI & Diffusion Models
  * AI Systems, Hardware Efficiency & Optimization
  * AI Safety, Alignment & Interpretability
  * Emerging AI Paradigms

> *Note*: This initial taxonomy is provisional and will be iteratively derived and refined directly from the corpus during Phase 1 processing.

* **Literature Sources Under Active Investigation**:
  * **OpenAlex**: Metadata, citation graphs, institutional affiliations, and thematic concepts.
  * **Semantic Scholar**: Enriched citation contexts, influential citation flags, and corpus mappings.
  * **arXiv API / Bulk Data**: High-velocity preprints, full-text source bundles, and category classifications.
  * *Additional scholarly data sources will be integrated as justified by domain requirements.*

---

## Repository Structure

```text
ResearchGraph/
├── backend/            # Production API, domain models, services, and workers (FastAPI, SQLAlchemy)
├── frontend/           # ResearchGraph interactive workbench (Next.js, TypeScript, Tailwind)
├── dataset/            # Multi-tier scientific literature corpus storage & manifest schemas
├── research/           # Isolated experimental explorations (LBD algorithms, extraction, discovery)
├── pipelines/          # Reproducible, standalone workflows (ingestion, graph building, evaluation)
├── docs/               # Architectural designs, ADRs, research notes, and API documentation
├── infrastructure/     # Container configurations, database migrations, and deployment specs
├── tests/              # Cross-boundary integration, e2e tests, and shared test fixtures
├── scripts/            # Developer automation and repository maintenance utilities
├── .github/            # GitHub Actions CI/CD workflows
├── .env.example        # Environment variable configuration template
├── docker-compose.yml  # Local development infrastructure (PostgreSQL, Redis)
├── Makefile            # Standard developer commands
├── README.md           # Project documentation
├── requirements.txt    # Python dependencies for the core data and backend foundation
└── LICENSE             # MIT License
```

### Architectural Boundary Distinctions

* **`backend/` (Production Services)**: High-availability, strictly-typed services, database access layers, and API endpoints. No unvalidated research scripts exist here.
* **`research/` (Scientific Exploration)**: Fast-iteration algorithmic prototypes, graph traversal benchmarks, and experimental scoring heuristics. Once an algorithm is proven, it is promoted to `backend/` or `pipelines/`.
* **`dataset/` (Corpus & Manifests)**: Multi-tier storage boundary. Raw binaries and bulk paper files are excluded from Git, while schemas, manifests, and lineage logs are strictly tracked.
* **`pipelines/` (Reproducible Data Workflows)**: Deterministic, parameter-driven batch jobs for ingestion, normalization, and graph building that run independently of client-facing web requests.

---

## Technology Stack

### Current Foundation & Selected Technologies

* **Backend & Data Core**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, Polars, PyArrow, httpx
* **Database & Storage**: PostgreSQL (with pgvector under evaluation), Supabase-compatible relational models
* **Testing & Quality Assurance**: pytest, pytest-asyncio, Ruff (linting and formatting), Mypy (strict type checking)
* **Infrastructure**: Docker, Docker Compose, GitHub Actions CI
* **Frontend (Planned)**: Next.js 14, React 18, TypeScript, Tailwind CSS

### Technologies Under Evaluation (Phase-Gated)

The following technologies are actively being researched but are **intentionally excluded** from current dependencies until formal Architectural Decision Records (ADRs) are completed:
* **Graph Databases**: Neo4j, Kuzu, Memgraph (evaluating query expressiveness vs. embedded performance).
* **Vector Databases**: Qdrant, Milvus, pgvector (benchmarking filtering efficiency and hybrid search).
* **Distributed Task Processing**: Redis, Celery, Temporal (assessing workflow orchestration needs).
* **LLM Orchestration**: Direct API adapters vs. specialized agent frameworks.

---

## Research Direction

ResearchGraph approaches literature discovery through the following core scientific vectors:

1. **Information Extraction**: Developing high-precision prompt pipelines and token-efficient parsers to extract structured mechanistic assertions from research text.
2. **Cross-Domain Topology Mapping**: Measuring semantic overlap across mathematically equivalent formulations that use divergent vocabulary across distinct AI fields.
3. **Graph-Based Hypothesis Synthesis**: Formulating path-finding and constraint-satisfaction algorithms over typed knowledge graphs to generate candidate scientific propositions.
4. **Epistemic Calibration**: Quantifying certainty, empirical support, and contradictory literature evidence to score hypothesis plausibility.

---

## Dataset Philosophy

The literature corpus is organized into clear progressive tiers to ensure data integrity, lineage, and full reproducibility:

```text
  Raw Dumps (OpenAlex / S2 / arXiv)
                 │
                 ▼
  Interim (Normalized, Deduplicated, Filtered)
                 │
                 ▼
  Processed (Canonical Entities, Structured Claims)
                 │
                 ▼
  Full Text (Extracted Sections, Tables, Equations)
                 │
                 ▼
  Versioned Dataset Manifests (SHA-256 Hashes, Query Criteria)
```

* **Reproducibility**: Every processed dataset artifact is accompanied by a manifest detailing query parameters, API timestamps, and source IDs.
* **Deduplication & Canonical Identifiers**: Multi-source resolution matching DOIs, arXiv IDs, PubMed IDs, and normalized title hashes.
* **Git Cleanliness**: Bulk text, JSON dumps, and PDFs are stored externally; only formal schemas and manifests are committed to version control.

---

## Development Philosophy

* **Separation of Concerns**: Strict boundaries between exploratory research code, deterministic data pipelines, and production backend services.
* **Type Safety & Contracts**: Pydantic v2 schemas and strict TypeScript types serve as single sources of truth across API and data boundaries.
* **Minimal Dependencies**: We add external libraries only when they solve an immediate, present architectural need. No speculative dependency bloat.
* **Traceability & Grounding**: Every generated insight must trace back to explicit, verifiable literature provenance.

---

## Evaluation

Evaluation is integrated into every phase of system development:

1. **Historical Rediscovery Backtesting**: Evaluating whether discovery algorithms can rediscover historically validated cross-domain breakthroughs using only papers published prior to the discovery date (e.g., Swanson's Raynaud's-fish oil discovery, early deep learning/attention transfer).
2. **Adversarial Critique Robustness**: Benchmarking the Reviewer #2 subsystem on known flawed or retracted papers to evaluate failure-detection recall.
3. **Extraction Precision & Recall**: Measuring mechanistic entity and relation extraction accuracy against curated expert-annotated scientific benchmarks.

---

## Project Status

* **Status**: **Phase 1 — Early Foundation & Architecture Setup**
* The repository currently establishes the core workspace boundaries, configuration profiles, testing harness, and data storage design.
* Application features, model adapters, and discovery algorithms will be implemented iteratively across subsequent roadmap phases.

---

## Getting Started

### Prerequisites
* Python 3.11+
* Node.js 20+ & npm (for frontend workbench)
* Docker & Docker Compose

### 1. Clone & Configure Environment
```bash
git clone https://github.com/<your-org>/ResearchGraph.git
cd ResearchGraph
cp .env.example .env
```

### 2. Set Up Python Environment
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install core dependencies
pip install -r requirements.txt
```

### 3. Start Development Services
```bash
# Launch PostgreSQL and Redis via Docker Compose
docker compose up -d
```

---

## Contributing / Development

All development follows strict linting, type-checking, and testing standards:

```bash
# Run Ruff linting and formatting checks
ruff check .
ruff format --check .

# Run test suite
pytest
```

---

## License

This project is licensed under the [MIT License](file:///a:/Academics/AIML/Projects/ResearchGapAnalysis/ResearchGraph/LICENSE).
