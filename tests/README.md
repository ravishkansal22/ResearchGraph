# ResearchGraph Test Suite

This directory contains cross-boundary integration tests, end-to-end tests, and shared test fixtures.

## Test Boundaries

```text
tests/
├── integration/  # Multi-component integration tests (pipeline-to-db, API-to-storage)
├── e2e/          # End-to-end user journeys and full pipeline validation
└── fixtures/     # Shared mock configurations and static test assets
```

> **Note**: Unit tests reside within their respective sub-projects (e.g. `backend/tests/`).
