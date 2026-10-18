#!/usr/bin/env python3
"""Generate 25-Chunk Human Review Audit Packet for Phase 3 Extraction Pipeline.

Selects 25 chunks reproducibly from the v0.4.0 75-chunk pilot:
- 15 chunks where the extractor generated records (covering claims, relations, entities)
- 10 chunks where the extractor generated NO records (investigating recall, substantive content, edge cases)

Outputs:
1. dataset/manifests/scientific_extraction_v0.4.0_audit_packet_manifest.json
2. dataset/manifests/scientific_extraction_v0.4.0_audit_packet_25.csv
3. dataset/manifests/scientific_extraction_v0.4.0_audit_packet_review_sheet.md
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

# Ensure repository root is in sys.path
repo_root = Path(__file__).resolve().parent.parent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AuditPacketGenerator")

# Explicit, reproducible chunk IDs selected according to stratification protocol
SELECTED_CHUNK_IDS_WITH_OUTPUT = [
    "chk_rg_doi_03232127251a_A_0002",  # Paper 1 (rg_doi_03232127251a, Abstract): CLAIM, METHOD, DOMAIN
    "chk_rg_doi_05ebadfdfb92_A_0005",  # Paper 2 (rg_doi_05ebadfdfb92, Intro): METHOD, DOMAIN
    "chk_rg_doi_0e010e052fc7_A_0009",  # Paper 3 (rg_doi_0e010e052fc7, Intro): FUTURE_DIRECTION
    "chk_rg_doi_1e4a04e65f34_A_0008",  # Paper 4 (rg_doi_1e4a04e65f34, Intro): FUTURE_DIRECTION, METHOD
    "chk_rg_doi_213043f2963d_A_0005",  # Paper 5 (rg_doi_213043f2963d, Intro): METHOD, DOMAIN
    "chk_rg_doi_21feca2c78f6_A_0018",  # Paper 6 (rg_doi_21feca2c78f6, Methods): METHOD, DOMAIN
    "chk_rg_doi_255e1165891c_A_0010",  # Paper 7 (rg_doi_255e1165891c, Methods): METHOD, DOMAIN
    "chk_rg_doi_27eab0b15f64_A_0023",  # Paper 8 (rg_doi_27eab0b15f64, Methods): METHOD, DOMAIN
    "chk_rg_doi_3e3972368876_A_0010",  # Paper 9 (rg_doi_3e3972368876, Results): METHOD, DOMAIN
    "chk_rg_doi_3e5df365b74c_A_0077",  # Paper 10 (rg_doi_3e5df365b74c, Conclusion): METHOD, DOMAIN
    "chk_rg_doi_4e5057959cae_A_0030",  # Paper 11 (rg_doi_4e5057959cae, Results): METHOD, METRIC
    "chk_rg_doi_54fb00b286a6_A_0011",  # Paper 12 (rg_doi_54fb00b286a6, Discussion): METHOD, METRIC
    "chk_rg_doi_5df430082155_A_0033",  # Paper 13 (rg_doi_5df430082155, Results): METHOD, METRIC
    "chk_rg_doi_dd68a04b1c62_A_0135",  # Paper 14 (rg_doi_dd68a04b1c62, Chapter 6): METHOD, DOMAIN
    "chk_rg_doi_ebe643c2b3dd_A_0135",  # Paper 15 (rg_doi_ebe643c2b3dd, Key Function): ADDRESSES, LIMITED_BY, BOTTLENECK, PROBLEM, METHOD
]

SELECTED_CHUNK_IDS_WITHOUT_OUTPUT = [
    "chk_rg_doi_1e4a04e65f34_A_0009",  # Paper 3, Intro: Study contributions & cluster analysis (SUBSTANTIVE MISSED)
    "chk_rg_doi_255e1165891c_A_0011",  # Paper 8, Methods: VOSviewer co-occurrence methodology (SUBSTANTIVE MISSED)
    "chk_rg_doi_378ae311b997_A_0019",  # Paper 15, Methods: Bibliometric cluster mapping (SUBSTANTIVE MISSED)
    "chk_rg_doi_3e5df365b74c_A_0079",  # Paper 11, Conclusion: Clinical challenges & data quality limits (SUBSTANTIVE MISSED)
    "chk_rg_doi_27eab0b15f64_A_0024",  # Paper 9, Methods: NLP for essay grading (SUBSTANTIVE MISSED)
    "chk_rg_doi_50cd23001d0a_A_0045",  # Paper 16, Results: Captioning metrics (SUBSTANTIVE MISSED)
    "chk_rg_doi_3dc8a65e8820_A_0032",  # Paper 17, Discussion: Perspective on unfolding ML future (CONCEPTUAL)
    "chk_rg_doi_4e5057959cae_A_0038",  # Paper 12, Results: Tabular observational comparability (TABLE ARTIFACT)
    "chk_rg_doi_3891d117baca_A_0210",  # Paper 18, Other: Section header (SHORT EDGE CASE, 42 chars)
    "chk_rg_doi_e86cbb9d12e2_A_0006",  # Paper 19, Front matter: Preface fragment (SHORT EDGE CASE, 7 chars)
]

ALL_SELECTED_IDS = SELECTED_CHUNK_IDS_WITH_OUTPUT + SELECTED_CHUNK_IDS_WITHOUT_OUTPUT


def main():
    manifests_dir = repo_root / "dataset" / "manifests"
    processed_dir = repo_root / "dataset" / "processed"

    # 1. Load 75-chunk pilot sample manifest
    sample_manifest_file = manifests_dir / "scientific_extraction_v0.4.0_sample_manifest.json"
    with open(sample_manifest_file, "r", encoding="utf-8") as f:
        sampled_75 = json.load(f)
    sampled_75_map = {s["chunk_id"]: s for s in sampled_75}

    # 2. Load chunk texts from v0.3.0
    chunks_v030_file = processed_dir / "v0.3.0" / "chunks.jsonl"
    chunk_texts: Dict[str, str] = {}
    with open(chunks_v030_file, "r", encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            if c["chunk_id"] in ALL_SELECTED_IDS:
                chunk_texts[c["chunk_id"]] = c["text"]

    # 3. Load extractions from v0.4.0
    extracted_records: Dict[str, List[Dict[str, Any]]] = {}
    with open(processed_dir / "v0.4.0" / "extracted_records.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            cid = d["provenance"]["chunk_id"]
            if cid in ALL_SELECTED_IDS:
                extracted_records.setdefault(cid, []).append(d)

    with open(processed_dir / "v0.4.0" / "extracted_relationships.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            cid = d["provenance"]["chunk_id"]
            if cid in ALL_SELECTED_IDS:
                extracted_records.setdefault(cid, []).append(d)

    # 4. Generate Audit Packet Manifest JSON
    audit_manifest = {
        "audit_version": "v0.4.0-human-review-25",
        "sample_size": 25,
        "selected_chunks_with_output_count": len(SELECTED_CHUNK_IDS_WITH_OUTPUT),
        "selected_chunks_without_output_count": len(SELECTED_CHUNK_IDS_WITHOUT_OUTPUT),
        "unique_papers_represented": len({sampled_75_map[cid]["canonical_id"] for cid in ALL_SELECTED_IDS if cid in sampled_75_map}),
        "selection_criteria": {
            "with_output_criteria": "Diverse scientific categories (CLAIM, FUTURE_DIRECTION, ADDRESSES, LIMITED_BY, METHOD, DOMAIN, METRIC) across 14 distinct papers",
            "without_output_criteria": "Deliberately stratified into substantive missed content (6), conceptual discussions (1), tabular fragments (1), and short edge cases (2)",
        },
        "chunks": [],
    }

    for idx, cid in enumerate(ALL_SELECTED_IDS, 1):
        s_meta = sampled_75_map[cid]
        preds = extracted_records.get(cid, [])
        has_out = cid in SELECTED_CHUNK_IDS_WITH_OUTPUT
        audit_manifest["chunks"].append({
            "packet_index": idx,
            "chunk_id": cid,
            "canonical_id": s_meta["canonical_id"],
            "section_title": s_meta["section_title"],
            "section_bucket": s_meta["section_bucket"],
            "char_count": len(chunk_texts.get(cid, "")),
            "has_system_output": has_out,
            "predicted_records_count": len(preds),
            "is_edge_case": s_meta["is_edge_case"],
            "edge_case_reason": s_meta["edge_case_reason"],
            "audit_investigation_goal": "Extraction Precision & Span Grounding" if has_out else "Recall Gap & Missed Knowledge Detection",
        })

    audit_manifest_path = manifests_dir / "scientific_extraction_v0.4.0_audit_packet_manifest.json"
    with open(audit_manifest_path, "w", encoding="utf-8") as f:
        json.dump(audit_manifest, f, indent=2)
    logger.info(f"Saved audit packet manifest to {audit_manifest_path}")

    # 5. Generate Audit Packet CSVs (Master, Reviewer 1, Reviewer 2)
    csv_fieldnames = [
        "packet_index",
        "chunk_id",
        "canonical_id",
        "section_title",
        "section_bucket",
        "has_system_output",
        "audit_investigation_goal",
        "chunk_text",
        "system_record_type",
        "system_predicted_category",
        "system_predicted_surface_text",
        "system_evidence_span",
        "system_relation_source",
        "system_relation_target",
        "human_ground_truth_category",
        "human_ground_truth_normalized_text",
        "human_ground_truth_evidence_span",
        "human_relation_source",
        "human_relation_target",
        "human_attribution",
        "human_verdict",
        "human_reviewer_comments",
        "reviewer_id",
    ]

    def write_csv_packet(target_path: Path, rev_id: str = "") -> None:
        with open(target_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
            writer.writeheader()

            for idx, cid in enumerate(ALL_SELECTED_IDS, 1):
                s_meta = sampled_75_map[cid]
                full_text = chunk_texts.get(cid, "")
                preds = extracted_records.get(cid, [])
                has_out = cid in SELECTED_CHUNK_IDS_WITH_OUTPUT
                goal = "Precision & Evidence Grounding Verification" if has_out else "Recall Gap & Missed Knowledge Detection"

                if not preds:
                    # Provide 5 structured blank rows for chunks with zero predictions to allow thorough recall annotation
                    for slot in range(1, 6):
                        writer.writerow({
                            "packet_index": idx,
                            "chunk_id": cid,
                            "canonical_id": s_meta["canonical_id"],
                            "section_title": s_meta["section_title"],
                            "section_bucket": s_meta["section_bucket"],
                            "has_system_output": False,
                            "audit_investigation_goal": goal,
                            "chunk_text": full_text,
                            "system_record_type": "ADD_MISSING",
                            "system_predicted_category": "",
                            "system_predicted_surface_text": "",
                            "system_evidence_span": "",
                            "system_relation_source": "",
                            "system_relation_target": "",
                            "human_ground_truth_category": "",
                            "human_ground_truth_normalized_text": "",
                            "human_ground_truth_evidence_span": "",
                            "human_relation_source": "",
                            "human_relation_target": "",
                            "human_attribution": "",
                            "human_verdict": "",
                            "human_reviewer_comments": "",
                            "reviewer_id": rev_id,
                        })
                else:
                    # 1. Existing predictions to assess
                    for p in preds:
                        rec_type = "RELATION" if "relation_type" in p else ("STATEMENT" if "normalized_statement" in p else "ENTITY")
                        cat = p.get("category") or p.get("relation_type", "")
                        surf = p.get("surface_text", "")
                        ev = p.get("evidence", {}).get("text", "")
                        sys_src = p.get("source_id", "") if rec_type == "RELATION" else ""
                        sys_tgt = p.get("target_id", "") if rec_type == "RELATION" else ""
                        writer.writerow({
                            "packet_index": idx,
                            "chunk_id": cid,
                            "canonical_id": s_meta["canonical_id"],
                            "section_title": s_meta["section_title"],
                            "section_bucket": s_meta["section_bucket"],
                            "has_system_output": True,
                            "audit_investigation_goal": goal,
                            "chunk_text": full_text,
                            "system_record_type": rec_type,
                            "system_predicted_category": cat,
                            "system_predicted_surface_text": surf,
                            "system_evidence_span": ev,
                            "system_relation_source": sys_src,
                            "system_relation_target": sys_tgt,
                            "human_ground_truth_category": "",
                            "human_ground_truth_normalized_text": "",
                            "human_ground_truth_evidence_span": "",
                            "human_relation_source": "",
                            "human_relation_target": "",
                            "human_attribution": "",
                            "human_verdict": "",
                            "human_reviewer_comments": "",
                            "reviewer_id": rev_id,
                        })
                    # 2. Add 3 blank candidate rows for adding missed items in chunks with predictions
                    for slot in range(1, 4):
                        writer.writerow({
                            "packet_index": idx,
                            "chunk_id": cid,
                            "canonical_id": s_meta["canonical_id"],
                            "section_title": s_meta["section_title"],
                            "section_bucket": s_meta["section_bucket"],
                            "has_system_output": True,
                            "audit_investigation_goal": goal,
                            "chunk_text": full_text,
                            "system_record_type": "ADD_MISSING",
                            "system_predicted_category": "",
                            "system_predicted_surface_text": "",
                            "system_evidence_span": "",
                            "system_relation_source": "",
                            "system_relation_target": "",
                            "human_ground_truth_category": "",
                            "human_ground_truth_normalized_text": "",
                            "human_ground_truth_evidence_span": "",
                            "human_relation_source": "",
                            "human_relation_target": "",
                            "human_attribution": "",
                            "human_verdict": "",
                            "human_reviewer_comments": "",
                            "reviewer_id": rev_id,
                        })

    master_csv_path = manifests_dir / "scientific_extraction_v0.4.0_audit_packet_25.csv"
    reviewer1_csv_path = manifests_dir / "scientific_extraction_v0.4.0_audit_packet_reviewer1.csv"
    reviewer2_csv_path = manifests_dir / "scientific_extraction_v0.4.0_audit_packet_reviewer2.csv"

    write_csv_packet(master_csv_path, rev_id="")
    write_csv_packet(reviewer1_csv_path, rev_id="reviewer_1")
    write_csv_packet(reviewer2_csv_path, rev_id="reviewer_2")

    logger.info(f"Saved master audit packet CSV to {master_csv_path}")
    logger.info(f"Saved Reviewer 1 packet CSV to {reviewer1_csv_path}")
    logger.info(f"Saved Reviewer 2 packet CSV to {reviewer2_csv_path}")

    # 6. Generate Markdown Human Review Sheet
    md_path = manifests_dir / "scientific_extraction_v0.4.0_audit_packet_review_sheet.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# ResearchGraph Phase 3: Human Validation Review Packet (25 Chunks)\n\n")
        f.write("**Packet Identifier**: `v0.4.0-human-review-25`  \n")
        f.write("**Total Evaluation Units**: 25 Stratified Chunks (15 with system output, 10 without system output)  \n")
        f.write("**Unique Papers Represented**: 19 Distinct Canonical Papers  \n")
        f.write("**Status**: **READY FOR INDEPENDENT HUMAN ANNOTATION**  \n\n")
        f.write("---\n\n")
        f.write("## Reviewer Instructions & Ground-Truth Protocol\n\n")
        f.write("1. **Do not prefill human fields** using system predictions. All human ground-truth fields must be independently assessed.\n")
        f.write("2. **For Chunks with Predictions (1–15)**:\n")
        f.write("   - **Part A (Assess Existing Predictions)**: For every machine extraction, assign `CORRECT`, `PARTIALLY_CORRECT`, or `UNSUPPORTED`.\n")
        f.write("     - If `CORRECT`: System category and evidence span are accurate verbatim extractions.\n")
        f.write("     - If `PARTIALLY_CORRECT`: Specify corrected category or exact evidence span in human fields.\n")
        f.write("     - If `UNSUPPORTED`: Extraction is hallucinated, misinterpreted, or unsupported by chunk text.\n")
        f.write("   - **Part B (Discover Missed Knowledge)**: Use the provided blank rows to record any missed scientific entities, statements, or relations with verdict `MISSING`.\n")
        f.write("3. **For Chunks without Predictions (16–25)**:\n")
        f.write("   - Read the chunk text carefully. Record any valid scientific entities, contributions, methods, or limitations in the provided rows (`MISSING`). If chunk has no scientific assertions (e.g. front matter, header), leave blank or note in comments.\n")
        f.write("4. **Allowed Categories**:\n")
        f.write("   - Entities: `METHOD`, `PROBLEM`, `BOTTLENECK`, `METRIC`, `DATASET`, `TASK`, `ASSUMPTION`, `DOMAIN`\n")
        f.write("   - Statements: `CLAIM`, `RESULT`, `LIMITATION`, `FUTURE_DIRECTION`, `FAILURE_MODE`\n")
        f.write("   - Relations: `ADDRESSES`, `USES`, `IMPROVES`, `OUTPERFORMS`, `LIMITED_BY`, `EVALUATED_ON`, `ASSUMES`, `REPORTS`, `SUGGESTS`\n")
        f.write("5. **Attribution**: Distinguish `AUTHOR_STATED` (explicitly declared in primary text) from `SYSTEM_INFERRED`.\n")
        f.write("6. **Exact Evidence Grounding**: The evidence span must be a verbatim exact substring from the source chunk.\n\n")
        f.write("---\n\n")

        for idx, cid in enumerate(ALL_SELECTED_IDS, 1):
            s_meta = sampled_75_map[cid]
            full_text = chunk_texts.get(cid, "")
            preds = extracted_records.get(cid, [])
            has_out = cid in SELECTED_CHUNK_IDS_WITH_OUTPUT
            goal = "Precision & Evidence Grounding Verification" if has_out else "Recall Gap & Missed Scientific Content Investigation"

            f.write(f"### Chunk #{idx:02d}: `{cid}`\n\n")
            f.write(f"- **Paper Canonical ID**: `{s_meta['canonical_id']}`\n")
            f.write(f"- **Section Title**: `{s_meta['section_title']}` (Bucket: `{s_meta['section_bucket']}`)\n")
            f.write(f"- **Audit Focus**: **{goal}**\n")
            f.write(f"- **Edge Case**: {s_meta['is_edge_case']} ({s_meta['edge_case_reason'] or 'Standard text'})\n\n")
            f.write("#### Source Chunk Text:\n")
            f.write("```text\n")
            f.write(full_text.strip() + "\n")
            f.write("```\n\n")

            if preds:
                f.write(f"#### Part A: System Predictions Assessment ({len(preds)} records to assess)\n\n")
                f.write("| Pred # | Type | System Category | Extracted Surface Text | Predicted Evidence Span | Human Verdict (CORRECT / PARTIALLY_CORRECT / UNSUPPORTED) | Human Category (if corrected) | Human Evidence (if corrected) | Attribution | Reviewer Notes |\n")
                f.write("| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
                for p_idx, p in enumerate(preds, 1):
                    rec_type = "RELATION" if "relation_type" in p else ("STATEMENT" if "normalized_statement" in p else "ENTITY")
                    cat = p.get("category") or p.get("relation_type", "")
                    surf = p.get("surface_text", "")
                    ev = p.get("evidence", {}).get("text", "")
                    f.write(f"| {p_idx} | `{rec_type}` | `{cat}` | {surf} | *\"{ev}\"* | | | | AUTHOR_STATED | |\n")
                f.write("\n")

                f.write("#### Part B: Discovered / Missing Scientific Knowledge (Recall Audit)\n\n")
                f.write("| Item # | Ground-Truth Category | Normalized Concept / Statement | Exact Supporting Evidence Span | Attribution | Verdict (MISSING) | Reviewer Notes |\n")
                f.write("| :---: | :--- | :--- | :--- | :--- | :--- | :--- |\n")
                for slot in range(1, 4):
                    f.write(f"| {slot} | | | | AUTHOR_STATED | | |\n")
                f.write("\n---\n\n")
            else:
                f.write("#### System Predictions:\n")
                f.write("> **[NO SYSTEM EXTRACTIONS PRODUCED]** — *Review chunk text for missed scientific entities, methods, claims, or limitations.*\n\n")

                f.write("#### Discovered Scientific Knowledge (Recall Audit)\n\n")
                f.write("| Item # | Ground-Truth Category | Normalized Concept / Statement | Exact Supporting Evidence Span | Attribution | Verdict (MISSING) | Reviewer Notes |\n")
                f.write("| :---: | :--- | :--- | :--- | :--- | :--- | :--- |\n")
                for slot in range(1, 6):
                    f.write(f"| {slot} | | | | AUTHOR_STATED | | |\n")
                f.write("\n---\n\n")

    logger.info(f"Saved review sheet markdown to {md_path}")


if __name__ == "__main__":
    main()
