"""Find and test direct PDF URLs from OpenAlex raw data for candidates."""

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from dataset.schemas.canonical_paper import CanonicalPaper
from pipelines.ingestion.fulltext.acquirer import OnDemandFullTextAcquirer

# 1. Map openalex raw records
raw_openalex_files = list(Path("dataset/raw/openalex").glob("**/openalex_records.jsonl"))
openalex_pdfs = {}
for p in raw_openalex_files:
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                raw = rec.get("raw_data", {})
                wid = raw.get("id")
                urls = []
                best_oa = raw.get("best_oa_location") or {}
                if best_oa.get("pdf_url"):
                    urls.append(best_oa.get("pdf_url"))
                for loc in raw.get("locations") or []:
                    u = loc.get("pdf_url")
                    if u and u not in urls:
                        urls.append(u)
                doi = raw.get("doi")
                if wid and urls:
                    openalex_pdfs[wid] = urls
                if doi and urls:
                    clean_doi = doi.lower().replace("https://doi.org/", "").strip()
                    openalex_pdfs[clean_doi] = urls

print(f"Total mapped OpenAlex records with direct PDF URLs: {len(openalex_pdfs)}")

# 2. Match with candidates
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

matched_candidates = []
for p in papers:
    if p.canonical_id in pilot_8:
        continue
    urls = []
    if p.arxiv_id:
        urls.append(f"https://arxiv.org/pdf/{p.arxiv_id}.pdf")
    if p.doi:
        clean_doi = p.doi.lower().replace("https://doi.org/", "").strip()
        if clean_doi in openalex_pdfs:
            urls.extend(openalex_pdfs[clean_doi])
    # check source_records
    srecs = p.source_records
    if isinstance(srecs, dict):
        for wid in srecs.get("openalex") or []:
            if wid in openalex_pdfs:
                urls.extend(openalex_pdfs[wid])
    oa = p.open_access
    if oa and oa.oa_url and ("pdf" in oa.oa_url.lower() or "arxiv.org" in oa.oa_url):
        urls.append(oa.oa_url)
    if p.fulltext_url and ("pdf" in p.fulltext_url.lower() or "arxiv.org" in p.fulltext_url):
        urls.append(p.fulltext_url)

    # Dedup urls
    seen = set()
    dedup_urls = []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            dedup_urls.append(u)

    if dedup_urls:
        matched_candidates.append((p, dedup_urls))

print(f"Total non-pilot candidates with direct PDF URLs: {len(matched_candidates)}")

# Print first 20 candidates with their hosts and titles
for p, urls in matched_candidates[:20]:
    hosts = [urlparse(u).netloc for u in urls]
    print(f"{p.canonical_id:25s} | {p.title[:45]:45s} | {hosts}")
