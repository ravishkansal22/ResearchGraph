# ResearchGraph Backend

Production backend service for the ResearchGraph discovery platform.

## Architecture

The internal backend structure follows a standard `src-layout` with clean architecture boundaries:

```text
backend/
├── src/
│   └── researchgraph/
│       ├── __init__.py
│       ├── api/            # Route handlers, endpoint definitions, dependency injection
│       ├── core/           # Configuration, security, logging, global singletons
│       ├── models/         # SQLAlchemy 2.x ORM database models
│       ├── schemas/        # Pydantic v2 validation and serialization schemas
│       ├── services/       # Domain business logic and orchestrations
│       ├── repositories/   # Data access layer and database queries
│       ├── infrastructure/ # External clients, storage adapters, messaging
│       └── workers/        # Asynchronous background tasks and queue consumers
├── alembic/                # Database schema migration scripts & environment
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── alembic.ini             # Alembic configuration
├── tests/                  # Unit and backend module tests
├── pyproject.toml          # Package metadata, src-layout discovery, and linter configurations
└── requirements.txt        # Backend dependencies
```
