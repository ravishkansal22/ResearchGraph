"""Deduplication and Canonical Entity Consolidation.

Groups multi-source paper records into canonical papers while merging metadata
and preserving complete source lineage and provenance.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from dataset.schemas.canonical_paper import (
    Author,
    CanonicalPaper,
    ConfidenceLevel,
    DocumentType,
    FulltextStatus,
    Institution,
    OpenAccessInfo,
    ProvenanceRecord,
    SourceRecords,
    Topic,
    Venue,
)
from pipelines.ingestion.normalizers.text import clean_text, normalize_title_for_matching
from pipelines.ingestion.resolution.identity import (
    IdentityResolver,
    generate_deterministic_canonical_id,
)

logger = logging.getLogger(__name__)


def merge_two_canonical_papers(base: CanonicalPaper, incoming: CanonicalPaper) -> CanonicalPaper:
    """Consolidate two matching paper records into an enriched canonical paper.

    Preserves provenance from both records and prefers richer metadata fields.
    """
    # 1. Deterministic canonical ID derivation
    doi = base.doi or incoming.doi
    arxiv_id = base.arxiv_id or incoming.arxiv_id

    # 2. Title (prefer cleaner, longer)
    title = base.title
    if len(incoming.title) > len(base.title) and not base.title.isupper():
        title = incoming.title

    # 3. Abstract (prefer the longer, more comprehensive abstract)
    abstract = base.abstract
    if not abstract and incoming.abstract:
        abstract = incoming.abstract
    elif incoming.abstract and len(incoming.abstract) > len(abstract or ""):
        abstract = incoming.abstract

    # 4. Document Type
    doc_type = base.document_type
    if doc_type in (DocumentType.UNKNOWN, DocumentType.OTHER) and incoming.document_type not in (DocumentType.UNKNOWN, DocumentType.OTHER):
        doc_type = incoming.document_type
    elif incoming.document_type in (DocumentType.SURVEY, DocumentType.REVIEW):
        doc_type = incoming.document_type

    # 5. Publication Dates & Year
    pub_date = base.published_date or incoming.published_date or base.publication_date or incoming.publication_date
    pub_year = base.publication_year or incoming.publication_year
    online_pub_date = base.online_publication_date or incoming.online_publication_date
    print_pub_date = base.print_publication_date or incoming.print_publication_date
    issued_date = base.issued_date or incoming.issued_date

    # 6. Authors & Affiliations (Merge author information, preferring records with ORCIDs/affiliations)
    merged_authors: List[Author] = []
    author_names_seen: Set[str] = set()

    for auth in list(base.authors) + list(incoming.authors):
        norm_name = normalize_title_for_matching(auth.name)
        if not norm_name:
            continue
        if norm_name not in author_names_seen:
            author_names_seen.add(norm_name)
            merged_authors.append(auth)
        else:
            for existing in merged_authors:
                if normalize_title_for_matching(existing.name) == norm_name:
                    if not existing.orcid and auth.orcid:
                        existing.orcid = auth.orcid
                    for aff in auth.affiliations:
                        if aff not in existing.affiliations:
                            existing.affiliations.append(aff)
                    break

    # 7. Institutions
    merged_institutions: List[Institution] = list(base.institutions)
    inst_names = {i.name for i in merged_institutions}
    for inst in incoming.institutions:
        if inst.name not in inst_names:
            inst_names.add(inst.name)
            merged_institutions.append(inst)

    # 8. Venue (Prefer peer-reviewed venue over preprint repository if available)
    venue = base.venue
    if not venue and incoming.venue:
        venue = incoming.venue
    elif venue and incoming.venue:
        if venue.type == "repository" and incoming.venue.type != "repository":
            venue = incoming.venue

    # 9. Topics (Deduplicate by normalized name)
    merged_topics: List[Topic] = list(base.topics)
    topic_names = {t.name.lower() for t in merged_topics}
    for top in incoming.topics:
        if top.name.lower() not in topic_names:
            topic_names.add(top.name.lower())
            merged_topics.append(top)

    # 10. Keywords
    merged_keywords = list(dict.fromkeys(base.keywords + incoming.keywords))

    # 11. References
    merged_references = list(dict.fromkeys(base.references + incoming.references))

    # 12. Citations
    citation_count = None
    if base.citation_count is not None and incoming.citation_count is not None:
        citation_count = max(base.citation_count, incoming.citation_count)
    else:
        citation_count = base.citation_count or incoming.citation_count

    influential_citation_count = (
        base.influential_citation_count or incoming.influential_citation_count
    )

    # 13. Open Access & Full text
    is_oa = base.open_access.is_oa or incoming.open_access.is_oa
    oa_url = base.open_access.oa_url or incoming.open_access.oa_url
    oa_status = base.open_access.oa_status or incoming.open_access.oa_status
    oa_license = base.open_access.license or incoming.open_access.license

    fulltext_url = base.fulltext_url or incoming.fulltext_url
    fulltext_path = base.fulltext_path or incoming.fulltext_path

    # Hierarchy: DOWNLOADED > DISCOVERABLE > NOT_CHECKED > UNAVAILABLE > FAILED
    status_ranks = {
        FulltextStatus.DOWNLOADED: 5,
        FulltextStatus.DISCOVERABLE: 4,
        FulltextStatus.NOT_CHECKED: 3,
        FulltextStatus.UNAVAILABLE: 2,
        FulltextStatus.FAILED: 1,
    }
    
    base_rank = status_ranks.get(base.fulltext_status, 3)
    incoming_rank = status_ranks.get(incoming.fulltext_status, 3)
    
    fulltext_status = base.fulltext_status if base_rank >= incoming_rank else incoming.fulltext_status
    if fulltext_url and fulltext_status in (FulltextStatus.NOT_CHECKED, FulltextStatus.UNAVAILABLE):
        fulltext_status = FulltextStatus.DISCOVERABLE
    if fulltext_path:
        fulltext_status = FulltextStatus.DOWNLOADED

    # 14. Source records mapping
    merged_source_records = SourceRecords(
        openalex=base.source_records.openalex or incoming.source_records.openalex,
        semantic_scholar=base.source_records.semantic_scholar or incoming.source_records.semantic_scholar,
        arxiv=base.source_records.arxiv or incoming.source_records.arxiv,
        crossref=base.source_records.crossref or incoming.source_records.crossref,
        other={**base.source_records.other, **incoming.source_records.other},
    )

    # 15. Provenance tracking
    merged_provenance: List[ProvenanceRecord] = list(base.provenance)
    seen_prov_ids = {(p.source, p.source_record_id) for p in merged_provenance}
    for prov in incoming.provenance:
        if (prov.source, prov.source_record_id) not in seen_prov_ids:
            seen_prov_ids.add((prov.source, prov.source_record_id))
            merged_provenance.append(prov)

    temp_paper = CanonicalPaper(
        canonical_id="temp",
        title=title,
        abstract=abstract,
        document_type=doc_type,
        authors=merged_authors,
        institutions=merged_institutions,
        venue=venue,
        published_date=pub_date,
        online_publication_date=online_pub_date,
        print_publication_date=print_pub_date,
        issued_date=issued_date,
        publication_date=pub_date,
        publication_year=pub_year,
        doi=doi,
        arxiv_id=arxiv_id,
        other_source_ids=merged_source_records,
        topics=merged_topics,
        keywords=merged_keywords,
        references=merged_references,
        citation_count=citation_count,
        influential_citation_count=influential_citation_count,
        open_access=OpenAccessInfo(
            is_oa=is_oa,
            oa_status=oa_status,
            oa_url=oa_url,
            license=oa_license,
        ),
        fulltext_status=fulltext_status,
        fulltext_available=fulltext_status,
        fulltext_url=fulltext_url,
        fulltext_path=fulltext_path,
        source_records=merged_source_records,
        provenance=merged_provenance,
        identity_confidence=ConfidenceLevel.EXACT,
    )

    canonical_id = generate_deterministic_canonical_id(temp_paper)
    temp_paper.canonical_id = canonical_id
    return temp_paper


class Deduplicator:
    """High-throughput multi-source deduplicator for scientific literature."""

    def __init__(self, resolver: Optional[IdentityResolver] = None):
        self.resolver = resolver or IdentityResolver()

    def deduplicate(
        self,
        papers: List[CanonicalPaper],
    ) -> Tuple[List[CanonicalPaper], Dict[str, Any]]:
        """Deduplicate a stream of normalized papers into canonical consolidated papers."""
        logger.info(f"[Deduplicator] Starting deduplication of {len(papers)} input records...")

        doi_index: Dict[str, CanonicalPaper] = {}
        arxiv_index: Dict[str, CanonicalPaper] = {}
        title_index: Dict[str, List[CanonicalPaper]] = defaultdict(list)

        canonical_papers_map: Dict[str, CanonicalPaper] = {}
        duplicate_count = 0
        unresolved_count = 0
        unresolved_candidates: List[Dict[str, Any]] = []

        for paper in papers:
            matched_canonical: Optional[CanonicalPaper] = None

            # 1. Match by DOI
            if paper.doi and paper.doi.lower() in doi_index:
                matched_canonical = doi_index[paper.doi.lower()]

            # 2. Match by arXiv ID
            elif paper.arxiv_id and paper.arxiv_id.lower() in arxiv_index:
                matched_canonical = arxiv_index[paper.arxiv_id.lower()]

            # 3. Match by exact or fuzzy title
            else:
                norm_title = normalize_title_for_matching(paper.title)
                candidate_list = title_index.get(norm_title, [])

                for candidate in candidate_list:
                    is_match, conf, reason = self.resolver.match_papers(paper, candidate)
                    if is_match and conf in (ConfidenceLevel.EXACT, ConfidenceLevel.HIGH_CONFIDENCE):
                        matched_canonical = candidate
                        break
                    elif conf == ConfidenceLevel.POSSIBLE:
                        unresolved_count += 1
                        unresolved_candidates.append({
                            "incoming_title": paper.title,
                            "candidate_title": candidate.title,
                            "incoming_id": paper.canonical_id,
                            "candidate_id": candidate.canonical_id,
                            "reason": reason,
                        })

            if matched_canonical is not None:
                merged = merge_two_canonical_papers(matched_canonical, paper)
                duplicate_count += 1

                old_id = matched_canonical.canonical_id
                canonical_papers_map[old_id] = merged

                if merged.doi:
                    doi_index[merged.doi.lower()] = merged
                if merged.arxiv_id:
                    arxiv_index[merged.arxiv_id.lower()] = merged
                norm_t = normalize_title_for_matching(merged.title)
                title_index[norm_t] = [merged]
            else:
                paper.canonical_id = generate_deterministic_canonical_id(paper)
                canonical_papers_map[paper.canonical_id] = paper

                if paper.doi:
                    doi_index[paper.doi.lower()] = paper
                if paper.arxiv_id:
                    arxiv_index[paper.arxiv_id.lower()] = paper
                norm_t = normalize_title_for_matching(paper.title)
                title_index[norm_t].append(paper)

        canonical_list = list(canonical_papers_map.values())
        duplicate_rate = (duplicate_count / len(papers)) if papers else 0.0

        stats = {
            "total_input_records": len(papers),
            "canonical_papers_count": len(canonical_list),
            "duplicates_merged": duplicate_count,
            "duplicate_rate": round(duplicate_rate, 4),
            "unresolved_possible_matches": unresolved_count,
            "unresolved_details": unresolved_candidates,
        }

        logger.info(
            f"[Deduplicator] Completed. Inputs: {len(papers)} -> Canonical: {len(canonical_list)} "
            f"(Duplicates merged: {duplicate_count}, rate: {duplicate_rate:.1%})"
        )
        return canonical_list, stats
