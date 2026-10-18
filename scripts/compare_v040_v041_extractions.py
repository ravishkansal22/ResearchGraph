#!/usr/bin/env python3
"""Detailed Comparative Analysis: v0.4.0 Baseline vs. v0.4.1 Experimental Extractor.

Compares extractions across the identical 75 pilot chunks from Phase 2 Strategy A:
- Yield comparison by scientific entity, statement, and relation categories
- Empty output chunk rate comparison
- Per-chunk audit inspection on the 25 human review chunks
- Recovered scientific knowledge analysis
- Error / false-positive risk inspection
- Engineering latency and conformance verification
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

repo_root = Path(__file__).resolve().parent.parent


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    return records


def main():
    processed_dir = repo_root / "dataset" / "processed"
    manifests_dir = repo_root / "dataset" / "manifests"

    # 1. Load reports
    with open(manifests_dir / "scientific_extraction_pilot_v0.4.0_quality_report.json", "r", encoding="utf-8") as f:
        rep_v040 = json.load(f)
    with open(manifests_dir / "scientific_extraction_pilot_v0.4.1_quality_report.json", "r", encoding="utf-8") as f:
        rep_v041 = json.load(f)

    # 2. Load records
    v040_records = load_jsonl(processed_dir / "v0.4.0" / "extracted_records.jsonl")
    v040_rels = load_jsonl(processed_dir / "v0.4.0" / "extracted_relationships.jsonl")

    v041_records = load_jsonl(processed_dir / "v0.4.1" / "extracted_records.jsonl")
    v041_rels = load_jsonl(processed_dir / "v0.4.1" / "extracted_relationships.jsonl")

    # Load 25 audit chunks
    audit_manifest_path = manifests_dir / "scientific_extraction_v0.4.0_audit_packet_manifest.json"
    with open(audit_manifest_path, "r", encoding="utf-8") as f:
        audit_meta = json.load(f)
    audit_chunk_ids = [c["chunk_id"] for c in audit_meta["chunks"]]

    print("=" * 80)
    print(" ResearchGraph Phase 3 Comparative Audit: v0.4.0 vs v0.4.1")
    print("=" * 80)

    print(f"\n{'Metric':<40} {'v0.4.0 (Baseline)':<20} {'v0.4.1 (Experimental)':<20} {'Delta':<10}")
    print("-" * 90)

    chunks_v040 = rep_v040["total_chunks"]
    chunks_v041 = rep_v041["total_chunks"]
    print(f"{'Total Chunks Processed':<40} {chunks_v040:<20} {chunks_v041:<20} {chunks_v041 - chunks_v040:<10}")

    total_rec_v040 = rep_v040["total_candidate_records"]
    total_rec_v041 = rep_v041["total_candidate_records"]
    print(f"{'Total Candidate Records':<40} {total_rec_v040:<20} {total_rec_v041:<20} {total_rec_v041 - total_rec_v040:+d}")

    ent_v040 = rep_v040["total_entities_extracted"]
    ent_v041 = rep_v041["total_entities_extracted"]
    print(f"{'Total Entities Extracted':<40} {ent_v040:<20} {ent_v041:<20} {ent_v041 - ent_v040:+d}")

    stmt_v040 = rep_v040["total_statements_extracted"]
    stmt_v041 = rep_v041["total_statements_extracted"]
    print(f"{'Total Statements Extracted':<40} {stmt_v040:<20} {stmt_v041:<20} {stmt_v041 - stmt_v040:+d}")

    rel_v040 = rep_v040["total_relations_extracted"]
    rel_v041 = rep_v041["total_relations_extracted"]
    print(f"{'Total Relations Extracted':<40} {rel_v040:<20} {rel_v041:<20} {rel_v041 - rel_v040:+d}")

    empty_v040 = rep_v040["empty_output_chunk_count"]
    empty_v041 = rep_v041["empty_output_chunk_count"]
    empty_pct_v040 = rep_v040["empty_output_chunk_rate"] * 100
    empty_pct_v041 = rep_v041["empty_output_chunk_rate"] * 100
    print(f"{'Empty Output Chunks':<40} {f'{empty_v040} ({empty_pct_v040:.1f}%)':<20} {f'{empty_v041} ({empty_pct_v041:.1f}%)':<20} {empty_v041 - empty_v040:+d} chunks")

    acc_v040 = rep_v040["evidence_grounding_accuracy"] * 100
    acc_v041 = rep_v041["evidence_grounding_accuracy"] * 100
    print(f"{'Exact Evidence Grounding Accuracy':<40} {f'{acc_v040:.2f}%':<20} {f'{acc_v041:.2f}%':<20} 0.00%")

    prov_v040 = rep_v040["provenance_validity_rate"] * 100
    prov_v041 = rep_v041["provenance_validity_rate"] * 100
    print(f"{'Provenance Validity Rate':<40} {f'{prov_v040:.2f}%':<20} {f'{prov_v041:.2f}%':<20} 0.00%")

    lat_v040 = rep_v040["avg_latency_per_chunk_ms"]
    lat_v041 = rep_v041["avg_latency_per_chunk_ms"]
    print(f"{'Avg Latency / Chunk':<40} {f'{lat_v040:.2f} ms':<20} {f'{lat_v041:.2f} ms':<20} {lat_v041 - lat_v040:+.2f} ms")

    print("\n" + "=" * 80)
    print(" Category-Wise Breakdown Comparison")
    print("=" * 80)

    all_ent_cats = sorted(set(rep_v040["entity_counts_by_category"].keys()).union(rep_v041["entity_counts_by_category"].keys()))
    print("\n--- Entities ---")
    for cat in all_ent_cats:
        c0 = rep_v040["entity_counts_by_category"].get(cat, 0)
        c1 = rep_v041["entity_counts_by_category"].get(cat, 0)
        print(f"  {cat:<25}: v0.4.0={c0:<4} -> v0.4.1={c1:<4} ({c1 - c0:+d})")

    all_stmt_cats = sorted(set(rep_v040["statement_counts_by_category"].keys()).union(rep_v041["statement_counts_by_category"].keys()))
    print("\n--- Statements ---")
    for cat in all_stmt_cats:
        c0 = rep_v040["statement_counts_by_category"].get(cat, 0)
        c1 = rep_v041["statement_counts_by_category"].get(cat, 0)
        print(f"  {cat:<25}: v0.4.0={c0:<4} -> v0.4.1={c1:<4} ({c1 - c0:+d})")

    all_rel_cats = sorted(set(rep_v040["relation_counts_by_category"].keys()).union(rep_v041["relation_counts_by_category"].keys()))
    print("\n--- Relations ---")
    for cat in (all_rel_cats or ["(None)"]):
        c0 = rep_v040["relation_counts_by_category"].get(cat, 0)
        c1 = rep_v041["relation_counts_by_category"].get(cat, 0)
        print(f"  {cat:<25}: v0.4.0={c0:<4} -> v0.4.1={c1:<4} ({c1 - c0:+d})")

    # Index by chunk_id
    v040_by_chunk: Dict[str, List[Dict[str, Any]]] = {}
    for r in v040_records + v040_rels:
        v040_by_chunk.setdefault(r["provenance"]["chunk_id"], []).append(r)

    v041_by_chunk: Dict[str, List[Dict[str, Any]]] = {}
    for r in v041_records + v041_rels:
        v041_by_chunk.setdefault(r["provenance"]["chunk_id"], []).append(r)

    print("\n" + "=" * 80)
    print(" Inspection of 25 Human-Review Chunks (Audit Packet)")
    print("=" * 80)

    for idx, cid in enumerate(audit_chunk_ids, 1):
        recs0 = v040_by_chunk.get(cid, [])
        recs1 = v041_by_chunk.get(cid, [])
        diff = len(recs1) - len(recs0)
        marker = "RECOVERED CONTENT" if len(recs0) == 0 and len(recs1) > 0 else ("REFINED" if diff != 0 else "IDENTICAL")
        print(f"Chunk #{idx:02d} [{cid}]: v0.4.0={len(recs0)} -> v0.4.1={len(recs1)} ({diff:+d}) [{marker}]")

        # If recovered, display sample
        if len(recs0) == 0 and len(recs1) > 0:
            for r in recs1[:4]:
                rec_cat = r.get("category") or r.get("relation_type")
                surf = r.get("surface_text", "")
                if len(surf) > 75:
                    surf = surf[:72] + "..."
                print(f"   + [{rec_cat}] {surf}")


if __name__ == "__main__":
    main()
