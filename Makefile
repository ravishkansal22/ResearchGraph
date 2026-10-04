.PHONY: help setup up down logs clean lint format test

PYTHON ?= python
PIP ?= pip

help:
	@echo "ResearchGraph Development Commands:"
	@echo "  make setup       - Install backend and frontend dependencies"
	@echo "  make up          - Start core development infrastructure (Docker)"
	@echo "  make down        - Stop development infrastructure"
	@echo "  make logs        - Tail infrastructure container logs"
	@echo "  make lint        - Run linting and static analysis across codebase"
	@echo "  make format      - Auto-format codebases"
	@echo "  make test        - Run test suite"
	@echo "  make clean       - Remove cached build/bytecode artifacts"

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
	cd backend && pytest
	pytest tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
