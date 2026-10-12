import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from dataset.schemas.canonical_paper import CanonicalPaper
from pipelines.processing.pipeline import DocumentProcessingPipeline

# 1. Load newly acquired papers manifest
with open("dataset/manifests/fulltext_expansion_v0.3.0_manifest.json", "r", encoding="utf-8") as f:
    exp_manifest = json.load(f)

# Pick 5 diverse papers from the new inventory
sample_inventory = exp_manifest["acquired_inventory"][:5]

# Load canonical metadata
canon_map = {}
with open("dataset/processed/v0.1.1/canonical_papers.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            d = json.loads(line)
            canon_map[d["canonical_id"]] = d

pipeline = DocumentProcessingPipeline(processor_version="v0.3.0-test")
cache_dir = Path("dataset/fulltext/cache")

batch_inputs = []
for item in sample_inventory:
    cid = item["canonical_id"]
    pdf_path = cache_dir / f"{cid}.pdf"
    canon = canon_map.get(cid, {})
    batch_inputs.append({
        "canonical_id": cid,
        "title": item["title"],
        "doi": item.get("doi") or canon.get("doi"),
        "source": canon.get("source", "openalex"),
        "source_url": item.get("url"),
        "local_pdf_path": str(pdf_path),
        "absolute_pdf_path": pdf_path,
        "file_hash": item["file_hash"],
        "file_size_bytes": item["file_size"],
        "document_type": item.get("document_type") or canon.get("document_type"),
    })

print(f"Running small batch validation on {len(batch_inputs)} papers...")
for i, inp in enumerate(batch_inputs, 1):
    doc = pipeline.process_single_pdf(inp)
    print(f"\n[{i}/{len(batch_inputs)}] {doc.canonical_id} - {doc.metadata.title[:50]}")
    print(f"    Pages: {len(doc.pages)} | Chars: {doc.processing.character_count:,} | Words: {doc.processing.word_count:,}")
    print(f"    Sections: {len(doc.sections)} | Paragraphs: {len(doc.paragraphs)} | Sentences: {doc.processing.sentence_count}")
    print(f"    Strategy A Chunks: {len(doc.chunks_strategy_a)} | Strategy B Chunks: {len(doc.chunks_strategy_b)}")
    print(f"    Dominant Layout: {doc.processing.layout_detected.value}")
    print(f"    Duration: {doc.processing.processing_duration_ms:.1f}ms")

    assert len(doc.pages) > 0
    assert doc.processing.character_count > 0
    assert len(doc.sections) > 0
    assert len(doc.paragraphs) > 0
    assert len(doc.chunks_strategy_a) > 0

print("\nSTAGE B SMALL BATCH VALIDATION: 100% PASSED!")
