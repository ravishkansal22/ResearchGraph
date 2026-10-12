import json
import sys
from pathlib import Path

# Ensure repository root is in sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from dataset.schemas.canonical_paper import CanonicalPaper
from pipelines.ingestion.fulltext.acquirer import OnDemandFullTextAcquirer
from pipelines.ingestion.fulltext.retrieval import MetadataCandidateRetriever

# Load canonical papers
papers = []
with open("dataset/processed/v0.1.1/canonical_papers.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            papers.append(CanonicalPaper(**json.loads(line)))

pilot_8 = {
    "rg_doi_b29976e1c44e",
    "rg_doi_3891d117baca",
    "rg_doi_cb0ceeff2e31",
    "rg_doi_da062bd35ba4",
    "rg_doi_7c2fa4c39358",
    "rg_doi_4e5057959cae",
    "rg_doi_5c65e2d95d8f",
    "rg_doi_21feca2c78f6",
}

candidates = [p for p in papers if p.canonical_id not in pilot_8]
print(f"Loaded {len(candidates)} candidates.")

# Test acquirer on first 15 candidates that have open_access or fulltext_url
acquirer = OnDemandFullTextAcquirer()
tested = 0
success = 0

for p in candidates:
    url, stype = acquirer.determine_source_priority(p)
    if not url:
        continue
    tested += 1
    print(f"\n[{tested}] Testing {p.canonical_id} | {p.title[:50]} | {url[:60]} ({stype})")
    updated_p, res = acquirer.fetch_paper(p)
    print(f"    Result: {res.validation_status.value} | Valid PDF: {res.is_valid_pdf} | Size: {res.file_size_bytes} | HTTP: {res.http_status}")
    if res.is_valid_pdf:
        success += 1
    if tested >= 15:
        break

print(f"\nSummary: {success}/{tested} successful.")
