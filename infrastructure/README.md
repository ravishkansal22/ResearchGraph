# ResearchGraph Infrastructure & Deployment

This directory holds infrastructure configuration, database initializations, caching configs, and container definitions.

```text
infrastructure/
├── docker/       # Production and development Dockerfiles & Compose profiles
├── database/     # PostgreSQL init scripts, extension configurations (e.g. pgvector if adopted)
├── redis/        # Redis configuration and cache tuning parameters
└── deployment/   # Cloud deployment templates (Terraform, Kubernetes, or cloud runners)
```
