#!/usr/bin/env python3
"""CLI Query Interface for ResearchGraph Scientific Knowledge Base.

Usage:
    python scripts/query_knowledge_base.py --paper rg_doi_ebe643c2b3dd
    python scripts/query_knowledge_base.py --entities METHOD --limit 10
    python scripts/query_knowledge_base.py --methods-for-problem "data imbalance"
    python scripts/query_knowledge_base.py --trace kb_ent_method_c98ee4eef050
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.knowledge_base.query import KnowledgeBaseQueryEngine


def print_json(data: object) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query ResearchGraph Scientific Knowledge Base",
    )
    default_db = (
        Path("dataset/processed/v0.5.1/knowledge_base.db")
        if Path("dataset/processed/v0.5.1/knowledge_base.db").exists()
        else Path("dataset/processed/v0.5.0/knowledge_base.db")
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=default_db,
        help="Path to SQLite knowledge base file",
    )
    parser.add_argument("--paper", type=str, help="Retrieve paper by canonical ID")
    parser.add_argument("--entities", type=str, help="List entities by category (e.g. METHOD, PROBLEM)")
    parser.add_argument("--statements", type=str, help="List statements for paper ID")
    parser.add_argument("--chunk", type=str, help="Retrieve all records originating from chunk ID")
    parser.add_argument("--methods-for-problem", type=str, help="Find methods addressing specified problem")
    parser.add_argument("--relationships", type=str, help="Get relationships for entity ID")
    parser.add_argument(
        "--include-unsupported",
        action="store_true",
        help="Include unsupported, ambiguous, or unassessed relationships in queries (default: trusted only)",
    )
    parser.add_argument(
        "--evidence-support",
        type=str,
        default=None,
        help="Filter relationships explicitly by evidence support (SUPPORTED, UNSUPPORTED, AMBIGUOUS, NOT_ASSESSED)",
    )
    parser.add_argument(
        "--excluded-relationships",
        action="store_true",
        help="Inspect relationships excluded from trusted queries along with diagnostic correction notes",
    )
    parser.add_argument("--trace", type=str, help="Trace canonical entity ID back to mentions and papers")
    parser.add_argument("--quarantine", action="store_true", help="Inspect quarantined records")
    parser.add_argument("--reason", type=str, default=None, help="Filter quarantine or excluded records by reason")
    parser.add_argument("--limit", type=int, default=20, help="Limit number of query results")

    args = parser.parse_args()

    try:
        engine = KnowledgeBaseQueryEngine(db_path=args.db)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Please run `python scripts/build_scientific_knowledge_base.py` first.", file=sys.stderr)
        return 1

    if args.paper:
        paper = engine.get_paper(args.paper)
        print_json(paper or {"error": "Paper not found", "paper_id": args.paper})

    elif args.entities:
        entities = engine.list_entities_by_type(args.entities, limit=args.limit)
        print_json(entities)

    elif args.statements:
        stmts = engine.get_statements_for_paper(args.statements)
        print_json(stmts)

    elif args.chunk:
        chunk_records = engine.get_records_for_chunk(args.chunk)
        print_json(chunk_records)

    elif args.methods_for_problem:
        methods = engine.find_methods_for_problem(
            args.methods_for_problem,
            trusted_only=not args.include_unsupported,
            include_unsupported=args.include_unsupported,
            evidence_support=args.evidence_support,
        )
        print_json(methods)

    elif args.relationships:
        rels = engine.get_relationships_for_entity(
            args.relationships,
            trusted_only=not args.include_unsupported,
            include_unsupported=args.include_unsupported,
            evidence_support=args.evidence_support,
        )
        print_json(rels)

    elif args.excluded_relationships:
        excluded = engine.get_excluded_relationships(
            reason=args.reason,
            evidence_support=args.evidence_support,
            limit=args.limit,
        )
        print_json(excluded)

    elif args.trace:
        traces = engine.trace_entity_mentions(args.trace)
        print_json(traces)

    elif args.quarantine:
        quar = engine.inspect_quarantined_records(reason=args.reason, limit=args.limit)
        print_json(quar)

    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())
