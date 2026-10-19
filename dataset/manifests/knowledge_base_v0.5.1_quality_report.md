# ResearchGraph Phase 4.1 Quality & Integrity Report
**Release Version:** `v0.5.1`  
**Schema Version:** `0.5.1`  
**Build Timestamp:** `2026-10-19T06:19:28.142355+00:00`  

## 1. Upstream Source Artifacts
| Source | Path |
|---|---|
| `phase1_canonical_papers` | `dataset\processed\v0.1.0\canonical_papers.jsonl` |
| `phase2_processed_chunks` | `dataset\processed\v0.3.0\chunks.jsonl` |
| `phase3_v040_extractions` | `dataset\processed\v0.4.0\extracted_records.jsonl` |
| `phase3_v041_extractions` | `dataset\processed\v0.4.1\extracted_records.jsonl` |
| `phase3_v040_relationships` | `dataset\processed\v0.4.0\extracted_relationships.jsonl` |

## 2. Ingestion & Persistence Summary
| Metric | Value |
|---|---|
| Total Canonical Papers Ingested | **528** |
| Total Canonical Entities | **68** |
| Total Entity Mentions Grounded | **267** |
| Total Scientific Statements | **22** |
| Total Persisted Relationships | **9** |
| Trusted Relationships (Supported) | **0** |
| Unsupported Relationships Flagged | **9** |
| Total Quarantined Records | **0** |
| Confirmed Aliases Applied | **66** |
| Referential Integrity Pass Rate | **100.00%** |
| Provenance Completeness Rate | **100.00%** |

## 3. Canonical Entities by Category
| Category | Count |
|---|---|
| `BOTTLENECK` | 5 |
| `DATASET` | 5 |
| `DOMAIN` | 8 |
| `METHOD` | 32 |
| `METRIC` | 4 |
| `PROBLEM` | 9 |
| `TASK` | 5 |

## 4. Scientific Statements by Category
| Statement Type | Count |
|---|---|
| `CLAIM` | 12 |
| `FUTURE_DIRECTION` | 4 |
| `LIMITATION` | 4 |
| `RESULT` | 2 |

## 5. Scientific Relationships by Relation Type
| Relation Type | Count |
|---|---|
| `ADDRESSES` | 6 |
| `LIMITED_BY` | 3 |

## 6. Diagnostic Quarantine Breakdown
| Reason | Count |
|---|---|
| *None (Zero quarantined records)* | 0 |

## 7. Storage Artifacts
- **JSONL Snapshots:** {"papers": 528, "entities": 68, "mentions": 267, "statements": 22, "relationships": 9, "quarantine": 0, "aliases": 66}
- **Relational SQLite DB:** `dataset\processed\v0.5.1\knowledge_base.db`
- **Parquet Columnar Snapshots:** `{'papers': 'dataset\\processed\\v0.5.1\\canonical_papers.parquet', 'entities': 'dataset\\processed\\v0.5.1\\canonical_entities.parquet', 'mentions': 'dataset\\processed\\v0.5.1\\entity_mentions.parquet', 'statements': 'dataset\\processed\\v0.5.1\\canonical_statements.parquet', 'relationships': 'dataset\\processed\\v0.5.1\\canonical_relationships.parquet'}`

## 8. Integrity & Scientific Caveats
1. **Engineering Correctness:** 100% of stored records conform strictly to schema `0.5.0` with verifiable SHA-256 stable IDs and foreign key integrity.
2. **Provenance Preservation:** Every entity mention, statement, and relationship links back to its canonical paper ID, document ID, chunk ID, character offsets, and extraction version.
3. **Validation Status:** Phase 3 human annotation remains pending. Ingested records retain their original validation status (`VALIDATED` or unverified); no record is represented as scientifically ground-truth verified without human sign-off.
