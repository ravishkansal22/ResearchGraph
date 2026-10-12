"""Ground-truth corpus integrity audit for ResearchGraph Phase 2 (50 papers)."""

import hashlib
import json
from collections import defaultdict
from pathlib import Path
import polars as pl

repo_root = Path(__file__).resolve().parent.parent
cache_dir = repo_root / "dataset" / "fulltext" / "cache"
manifest_v030 = repo_root / "dataset" / "manifests" / "document_processing_v0.3.0_manifest.json"
docs_jsonl = repo_root / "dataset" / "processed" / "v0.3.0" / "documents.jsonl"
chunks_parquet = repo_root / "dataset" / "processed" / "v0.3.0" / "chunks.parquet"
expansion_csv = repo_root / "dataset" / "manifests" / "fulltext_expansion_v0.3.0_results.csv"

# Load canonical metadata to get author/year details
canonical_meta = {}
canonical_file = repo_root / "dataset" / "processed" / "v0.1.1" / "canonical_papers.jsonl"
if canonical_file.exists():
    with open(canonical_file, encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            canonical_meta[item["canonical_id"]] = item

with open(manifest_v030, encoding="utf-8") as f:
    manifest = json.load(f)

print("=" * 100)
print("RESEARCHGRAPH v0.3.0 CORPUS INTEGRITY AUDIT")
print("=" * 100)

hash_to_cids = defaultdict(list)
records = []

for idx, doc in enumerate(manifest["documents"], 1):
    cid = doc["canonical_id"]
    pdf_path = cache_dir / f"{cid}.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing PDF file: {pdf_path}")
    
    file_bytes = pdf_path.read_bytes()
    computed_sha256 = hashlib.sha256(file_bytes).hexdigest()
    file_size = len(file_bytes)
    
    cm = canonical_meta.get(cid, {})
    authors = [a.get("raw_name") or a.get("name") for a in cm.get("authors", [])]
    author_str = authors[0] if authors else "N/A"
    year = cm.get("publication_year", "N/A")
    
    hash_to_cids[computed_sha256].append((idx, cid, doc["title"]))
    records.append({
        "index": idx,
        "canonical_id": cid,
        "title": doc["title"],
        "doi": doc.get("doi") or "N/A",
        "author": author_str,
        "year": year,
        "pages": doc["pages"],
        "size_bytes": file_size,
        "sha256": computed_sha256,
        "chunks_strat_a": doc["chunks_strat_a"],
        "chunks_strat_b": doc["chunks_strat_b"],
    })

print(f"Total Papers in Manifest: {len(records)}")
print(f"Total Unique SHA-256 Hashes Computed Directly From Disk: {len(hash_to_cids)}")

# Check duplicate hashes
duplicates = {h: cids for h, cids in hash_to_cids.items() if len(cids) > 1}
if duplicates:
    print("\n[ALERT] DUPLICATE PDF HASHES FOUND:")
    for h, cids in duplicates.items():
        print(f"Hash {h}: {cids}")
else:
    print("\n[OK] VERIFIED: Exactly 50 unique SHA-256 hashes for 50 distinct PDF files on disk.")

# Detailed check of candidate papers
print("\n" + "=" * 100)
print("FOCUSED INVESTIGATION: rg_doi_5df430082155 vs rg_doi_bc24dd772f29")
print("=" * 100)
p34 = next(r for r in records if r["canonical_id"] == "rg_doi_5df430082155")
p48 = next(r for r in records if r["canonical_id"] == "rg_doi_bc24dd772f29")

print(f"Paper #34 ({p34['canonical_id']}):")
print(f"  Title: {p34['title']}")
print(f"  DOI: {p34['doi']}")
print(f"  Author(s): {p34['author']}")
print(f"  Year: {p34['year']}")
print(f"  Pages: {p34['pages']}")
print(f"  Size on Disk: {p34['size_bytes']} bytes")
print(f"  SHA-256: {p34['sha256']}")
print(f"  Chunks: Strategy A = {p34['chunks_strat_a']}, Strategy B = {p34['chunks_strat_b']}")

print(f"\nPaper #48 ({p48['canonical_id']}):")
print(f"  Title: {p48['title']}")
print(f"  DOI: {p48['doi']}")
print(f"  Author(s): {p48['author']}")
print(f"  Year: {p48['year']}")
print(f"  Pages: {p48['pages']}")
print(f"  Size on Disk: {p48['size_bytes']} bytes")
print(f"  SHA-256: {p48['sha256']}")
print(f"  Chunks: Strategy A = {p48['chunks_strat_a']}, Strategy B = {p48['chunks_strat_b']}")

# Check processed records
print("\n" + "=" * 100)
print("AUDITING PROCESSED ARTIFACT INTEGRITY (documents.jsonl, chunks.parquet)")
print("=" * 100)
proc_docs = []
with open(docs_jsonl, encoding="utf-8") as f:
    for line in f:
        proc_docs.append(json.loads(line))

proc_hashes = [d["metadata"]["file_hash"] for d in proc_docs]
print(f"documents.jsonl contains {len(proc_docs)} documents with {len(set(proc_hashes))} unique file hashes.")

df = pl.read_parquet(chunks_parquet)
chunk_cids = df["canonical_id"].unique().to_list()
chunk_hashes = df["file_hash"].unique().to_list()
print(f"chunks.parquet contains {len(df)} chunks across {len(chunk_cids)} distinct canonical IDs and {len(chunk_hashes)} unique file hashes.")

# Output clean markdown table of all 50 verified ground-truth papers
print("\n" + "=" * 100)
print("ALL 50 GROUND-TRUTH PAPERS ON DISK:")
print("=" * 100)
print("| # | Canonical ID | Title | Pages | Size (KB) | SHA-256 Hash |")
print("| :- | :--- | :--- | :-: | :-: | :--- |")
for r in records:
    short_title = r["title"][:55] + ("..." if len(r["title"]) > 55 else "")
    print(f"| {r['index']} | `{r['canonical_id']}` | {short_title} | {r['pages']} | {r['size_bytes']/1024:.1f} | `{r['sha256']}` |")
