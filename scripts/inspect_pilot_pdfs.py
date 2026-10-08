#!/usr/bin/env python3
"""Inspect the 8 validated PDFs from v0.1.2 pilot."""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
import fitz
import pypdf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


repo_root = Path(__file__).resolve().parent.parent
cache_dir = repo_root / "dataset" / "fulltext" / "cache"
results_csv = repo_root / "dataset" / "manifests" / "fulltext_pilot_v0.1.2_results.csv"
canonical_jsonl = repo_root / "dataset" / "processed" / "v0.1.1" / "canonical_papers.jsonl"

def main():
    papers_meta = {}
    with open(canonical_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                papers_meta[data["canonical_id"]] = data

    with open(results_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        pilot_records = [r for r in reader if r["validation_status"] == "SUCCESS_PDF"]

    print(f"Found {len(pilot_records)} successful pilot PDFs\n")

    for i, rec in enumerate(pilot_records, 1):
        cid = rec["canonical_id"]
        pdf_path = cache_dir / f"{cid}.pdf"
        meta = papers_meta.get(cid, {})
        title = rec["title"]
        doi = meta.get("doi", "N/A")
        doc_type = rec["document_type"]

        print(f"[{i}/8] {cid}")
        print(f"    Title: {title[:75]}")
        print(f"    DOI: {doi} | Type: {doc_type} | File: {pdf_path.name} ({pdf_path.stat().st_size} bytes)")

        # PyMuPDF inspection
        t0 = time.perf_counter()
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        fitz_total_chars = 0
        fitz_total_words = 0
        empty_pages = []

        for p_num in range(page_count):
            page = doc[p_num]
            text = page.get_text("text")
            char_count = len(text.strip())
            word_count = len(text.split())
            fitz_total_chars += char_count
            fitz_total_words += word_count
            if char_count == 0:
                empty_pages.append(p_num + 1)
        t_fitz = time.perf_counter() - t0

        # pypdf inspection (first 3 pages benchmark)
        t0 = time.perf_counter()
        pypdf_sample_chars = 0
        pypdf_error = None
        try:
            reader_py = pypdf.PdfReader(str(pdf_path))
            for p in reader_py.pages[:3]:
                txt = p.extract_text() or ""
                pypdf_sample_chars += len(txt)
            t_pypdf = time.perf_counter() - t0
        except Exception as e:
            pypdf_error = str(e)
            t_pypdf = time.perf_counter() - t0

        print(f"    PyMuPDF (all {page_count} pages): {fitz_total_chars:,} chars, {fitz_total_words:,} words, time={t_fitz*1000:.1f}ms, empty={empty_pages}")
        if pypdf_error:
            print(f"    pypdf (first 3 pages): ERROR ({pypdf_error}), time={t_pypdf*1000:.1f}ms")
        else:
            print(f"    pypdf (first 3 pages): {pypdf_sample_chars:,} chars, time={t_pypdf*1000:.1f}ms")


        # Layout & Font inspection across first 3 pages
        print("    Page Layout Analysis:")
        for p_num in range(min(3, page_count)):
            page = doc[p_num]
            page_dict = page.get_text("dict")
            blocks = page_dict.get("blocks", [])
            text_blocks = [b for b in blocks if b.get("type") == 0]
            
            # Check for column structure by inspecting horizontal positions (bbox x0)
            x0s = [b["bbox"][0] for b in text_blocks]
            col_guess = "single-column"
            if len(x0s) >= 4:
                # If there are blocks on left (e.g. < 250) and blocks on right (e.g. > 300)
                left_blocks = [x for x in x0s if x < 250]
                right_blocks = [x for x in x0s if x > 280]
                if len(left_blocks) >= 2 and len(right_blocks) >= 2:
                    col_guess = "two-column / multi-column"

            # Check font sizes
            fonts = set()
            for b in text_blocks:
                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        fonts.add((round(span["size"], 1), span["flags"], span["font"]))
            
            print(f"      Page {p_num+1}: {len(text_blocks)} text blocks, {col_guess}, fonts: {sorted(list(fonts), key=lambda x: -x[0])[:3]}")

        doc.close()
        print("-" * 80)


if __name__ == "__main__":
    main()
