.PHONY: help setup up down logs clean lint format test verify-dataset export-schema quality-report ingest-pilot

PYTHON ?= python
PIP ?= pip

help:
	@echo "ResearchGraph Development Commands:"
	@echo "  make setup          - Install backend and frontend dependencies"
	@echo "  make up             - Start core development infrastructure (Docker)"
	@echo "  make down           - Stop development infrastructure"
	@echo "  make logs           - Tail infrastructure container logs"
	@echo "  make lint           - Run linting and static analysis across codebase"
	@echo "  make format         - Auto-format codebases"
	@echo "  make test           - Run test suite"
	@echo "  make verify-dataset - Verify integrity of processed dataset"
	@echo "  make export-schema  - Export canonical paper JSON schema"
	@echo "  make quality-report - Generate quality report for processed dataset"
	@echo "  make ingest-pilot   - Run pilot literature ingestion workflow"
	@echo "  make clean          - Remove cached build/bytecode artifacts"

setup:
	@echo "Setting up Python backend environment..."
	cd backend && $(PIP) install -e ".[dev]"
	@echo "Setting up Frontend environment..."
	cd frontend && npm install

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

lint:
	cd backend && ruff check . && mypy .
	cd frontend && npm run lint

format:
	cd backend && ruff format .
	cd frontend && npm run format

test:
	pytest tests/

verify-dataset:
	$(PYTHON) scripts/verify_dataset.py --version v0.1.0

export-schema:
	$(PYTHON) scripts/export_schema.py

quality-report:
	$(PYTHON) scripts/generate_quality_report.py --version v0.1.0

ingest-pilot:
	$(PYTHON) scripts/run_ingestion.py --preset pilot --limit 350 --version v0.1.0

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
