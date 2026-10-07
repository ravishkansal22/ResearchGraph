# ResearchGraph Developer & Maintenance Scripts

Standalone CLI utilities, dataset maintenance scripts, environment provisioning, and validation tools.

---

## Available Scripts

### 1. `scripts/verify_dataset.py`
Validates dataset integrity, schema conformance against Pydantic models, parity between JSONL and Parquet files, and manifest alignment.

```bash
# Verify release v0.1.0
python scripts/verify_dataset.py --version v0.1.0

# Strict mode for CI/CD checks
python scripts/verify_dataset.py --version v0.1.0 --strict
```

### 2. `scripts/run_ingestion.py`
Convenience preset runner for literature acquisition pipelines.

```bash
# Run pilot collection (~1,000 papers target)
python scripts/run_ingestion.py --preset pilot --limit 350 --version v0.1.0

# Run focused topic collection
python scripts/run_ingestion.py --preset focused --query "graph neural networks" --limit 100

# Test network requests and normalization without writing to disk
python scripts/run_ingestion.py --preset dry-run
```

### 3. `scripts/generate_quality_report.py`
Recomputes and regenerates JSON and Markdown quality reports for any processed dataset release.

```bash
# Generate report for v0.1.0
python scripts/generate_quality_report.py --version v0.1.0
```

### 4. `scripts/export_schema.py`
Exports formal JSON schemas from Pydantic models to `dataset/schemas/canonical_paper.json`.

```bash
python scripts/export_schema.py
```
