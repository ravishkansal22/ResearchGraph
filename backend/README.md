# ResearchGraph Backend

Production backend service for the ResearchGraph discovery platform.

## Architecture

The internal backend structure follows clean architecture boundaries:

```text
backend/
├── app/
│   ├── api/            # Route handlers, endpoint definitions, dependency injection
│   ├── core/           # Configuration, security, logging, global singletons
│   ├── models/         # SQLAlchemy 2.x ORM database models
│   ├── schemas/        # Pydantic v2 validation and serialization schemas
│   ├── services/       # Domain business logic and orchestrations
│   ├── repositories/   # Data access layer and database queries
│   ├── infrastructure/ # External clients, storage adapters, messaging
│   └── workers/        # Asynchronous background tasks and queue consumers
├── alembic/            # Database schema migration scripts
├── tests/              # Unit and backend module tests
└── pyproject.toml      # Dependency specifications and linter configurations
```

> **Note**: Application features and logic will be implemented in their respective milestone phases following schema design.
