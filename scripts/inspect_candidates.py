"""Map raw OpenAlex and canonical papers to find candidate PDFs for 42 papers expansion."""

import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

# Load raw openalex records to build openalex_id -> direct_pdf_urls mapping
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
                    if loc.get("pdf_url") and loc.get("pdf_url") not in urls:
                        urls.append(loc.get("pdf_url"))
                if wid and urls:
                    openalex_pdfs[wid] = urls
                    doi = raw.get("doi")
                    if doi:
                        clean_doi = doi.lower().replace("https://doi.org/", "").strip()
                        openalex_pdfs[clean_doi] = urls

print(f"Total OpenAlex direct PDF mappings: {len(openalex_pdfs)}")

# Load canonical papers
papers = []
with open("dataset/processed/v0.1.1/canonical_papers.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            papers.append(json.loads(line))

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

candidates_with_pdf = []
for p in papers:
    if p["canonical_id"] in pilot_8:
        continue
    urls = []
    # check arxiv_id
    if p.get("arxiv_id"):
        urls.append(f"https://arxiv.org/pdf/{p['arxiv_id']}.pdf")
    # check raw openalex
    if p.get("doi"):
        clean_doi = p["doi"].lower().replace("https://doi.org/", "").strip()
        if clean_doi in openalex_pdfs:
            urls.extend(openalex_pdfs[clean_doi])
    # check source_records
    srecs = p.get("source_records")
    if isinstance(srecs, dict):
        for wid in srecs.get("openalex") or []:
            if wid in openalex_pdfs:
                urls.extend(openalex_pdfs[wid])
    elif isinstance(srecs, list):
        for srec in srecs:
            if isinstance(srec, dict) and srec.get("source") == "openalex":
                wid = srec.get("source_record_id")
                if wid in openalex_pdfs:
                    urls.extend(openalex_pdfs[wid])
    # check other_source_ids
    os_ids = p.get("other_source_ids")
    if isinstance(os_ids, dict):
        for wid in os_ids.get("openalex") or []:
            if wid in openalex_pdfs:
                urls.extend(openalex_pdfs[wid])
    # check open_access.oa_url
    oa = p.get("open_access") or {}
    if oa.get("oa_url"):
        urls.append(oa.get("oa_url"))
    if p.get("fulltext_url"):
        urls.append(p.get("fulltext_url"))
    
    unique_urls = list(dict.fromkeys(urls))
    if unique_urls:
        candidates_with_pdf.append((p, unique_urls))

print(f"Candidates with at least one viable URL: {len(candidates_with_pdf)}")

# Check how many have arxiv or direct pdf in their URLs
arxiv_candidates = [c for c in candidates_with_pdf if any("arxiv.org" in u for u in c[1])]
print(f"Candidates with arXiv URL: {len(arxiv_candidates)}")

# Print breakdown of candidates by topics / fields
topic_counts = Counter()
for p, urls in candidates_with_pdf:
    t_list = [t.get("name") for t in p.get("topics", []) if isinstance(t, dict)]
    for t in t_list[:3]:
        topic_counts[t] += 1

print("\nTop candidate topics:")
for t, c in topic_counts.most_common(15):
    print(f"  {t:40s}: {c}")
