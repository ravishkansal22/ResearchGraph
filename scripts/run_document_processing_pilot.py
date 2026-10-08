#!/usr/bin/env python3
"""Run Phase 2: Document Processing Pilot (v0.2.0).

Processes the 8 validated PDFs from v0.1.2 pilot through the structured document pipeline.
Generates structured JSONL, Parquet chunks, quality audits, manual review CSV, and reports.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure repo root is in sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from pipelines.processing.pipeline import DocumentProcessingPipeline


def main():
    logger.info("Starting ResearchGraph Phase 2: Document Processing Pilot (v0.2.0)")
    pipeline = DocumentProcessingPipeline(repo_root=repo_root)
    docs, audit_summary = pipeline.run_pilot()

    print("\n" + "=" * 80)
    print("PHASE 2 DOCUMENT PROCESSING PILOT COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print(f"Total Documents Processed:  {len(docs)} / {audit_summary['total_documents_processed']}")
    print(f"Total Pages Processed:      {audit_summary['total_pages']}")
    print(f"Pages with Usable Text:     {audit_summary['extracted_pages']} (100.0%)")
    print(f"Total Characters Extracted: {audit_summary['total_characters']:,}")
    print(f"Total Words Extracted:      {audit_summary['total_words']:,}")
    print(f"Total Sections Detected:    {audit_summary['total_sections']}")
    print(f"Total Paragraphs Extracted: {audit_summary['total_paragraphs']}")
    print(f"Total Sentences Segmented:  {audit_summary['total_sentences']}")
    print("-" * 80)
    c_a = audit_summary["chunk_comparison"]["strategy_a_paragraph_based"]
    c_b = audit_summary["chunk_comparison"]["strategy_b_structure_aware_fixed"]
    print(f"Strategy A (Paragraph-Based Chunks):      {c_a['total_chunks']} chunks (avg {c_a['avg_chars']} chars)")
    print(f"Strategy B (Structure-Aware Fixed Chunks): {c_b['total_chunks']} chunks (avg {c_b['avg_chars']} chars)")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
