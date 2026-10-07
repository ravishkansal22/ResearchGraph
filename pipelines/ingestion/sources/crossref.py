"""Crossref Source Adapter for ResearchGraph.

Handles querying the Crossref REST API (https://api.crossref.org/works), polite pool headers,
pagination, and normalization into CanonicalPaper.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from dataset.schemas.canonical_paper import (
    Author,
    CanonicalPaper,
    ConfidenceLevel,
    DocumentType,
    FulltextStatus,
    Institution,
    OpenAccessInfo,
    ProvenanceRecord,
    RawRecord,
    SourceRecords,
    Topic,
    Venue,
)
from pipelines.ingestion.config import config
from pipelines.ingestion.normalizers.dates import extract_publication_dates
from pipelines.ingestion.normalizers.document_type import classify_document_type
from pipelines.ingestion.normalizers.identifiers import normalize_doi, normalize_orcid
from pipelines.ingestion.normalizers.text import clean_text, parse_author_name
from pipelines.ingestion.sources.base import BaseSourceAdapter

logger = logging.getLogger(__name__)


class CrossrefAdapter(BaseSourceAdapter):
    """Adapter for the Crossref REST API."""

    BASE_URL = "https://api.crossref.org/works"

    def __init__(
        self,
        mailto: Optional[str] = config.CROSSREF_MAILTO,
        rate_limit_delay: float = config.CROSSREF_RATE_LIMIT_DELAY,
    ):
        self.mailto = mailto
        super().__init__(source_name="crossref", rate_limit_delay=rate_limit_delay)

    def _get_default_headers(self) -> Dict[str, str]:
        headers = super()._get_default_headers()
        if self.mailto:
            headers["User-Agent"] = f"ResearchGraph/0.1.0 (mailto:{self.mailto})"
        return headers

    def search(
        self,
        query: str,
        limit: int = 100,
        checkpoint_file: Optional[Path] = None,
        filter_param: Optional[str] = None,
        **kwargs: Any,
    ) -> List[RawRecord]:
        """Search Crossref works for a query string."""
        results: List[RawRecord] = []
        offset = 0
        batch_size = min(limit, 100)

        logger.info(f"[Crossref] Starting search for query='{query}' (target limit={limit})")

        while len(results) < limit:
            params: Dict[str, Any] = {
                "query": query,
                "rows": batch_size,
                "offset": offset,
            }
            if self.mailto:
                params["mailto"] = self.mailto
            if filter_param:
                params["filter"] = filter_param

            try:
                response = self._request_with_retry(
                    method="GET",
                    url=self.BASE_URL,
                    params=params,
                )
                data = response.json()
            except Exception as e:
                logger.error(f"[Crossref] Failed to fetch page at offset {offset}: {e}")
                break

            message = data.get("message", {})
            items = message.get("items", [])
            if not items:
                logger.info("[Crossref] No more results found.")
                break

            page_records: List[RawRecord] = []
            for item in items:
                raw_doi = item.get("DOI")
                if not raw_doi:
                    continue

                clean_doi_str = normalize_doi(raw_doi) or raw_doi
                raw_rec = self.create_raw_record(
                    source_record_id=clean_doi_str,
                    raw_data=item,
                    query=query,
                )
                page_records.append(raw_rec)
                results.append(raw_rec)
                if len(results) >= limit:
                    break

            if checkpoint_file and page_records:
                self.save_raw_records_checkpoint(page_records, checkpoint_file)

            total_results = message.get("total-results", 0)
            offset += len(items)
            if offset >= total_results or len(items) == 0:
                break

            logger.info(f"[Crossref] Acquired {len(results)}/{limit} works...")

        logger.info(f"[Crossref] Finished search. Total acquired: {len(results)}")
        return results

    def fetch_by_id(self, identifier: str) -> Optional[RawRecord]:
        """Fetch a specific work by DOI from Crossref."""
        clean_doi_str = normalize_doi(identifier) or identifier
        url = f"{self.BASE_URL}/{clean_doi_str}"
        params: Dict[str, Any] = {}
        if self.mailto:
            params["mailto"] = self.mailto

        try:
            response = self._request_with_retry(method="GET", url=url, params=params)
            data = response.json()
            item = data.get("message", {})
            return self.create_raw_record(source_record_id=clean_doi_str, raw_data=item)
        except Exception as e:
            logger.warning(f"[Crossref] Failed to fetch DOI {clean_doi_str}: {e}")
            return None

    def normalize(self, raw_record: RawRecord) -> CanonicalPaper:
        """Normalize Crossref work JSON into CanonicalPaper."""
        data = raw_record.raw_data
        raw_doi = raw_record.source_record_id

        # Title
        titles = data.get("title") or []
        raw_title = titles[0] if isinstance(titles, list) and titles else ""
        title = clean_text(raw_title) or "Untitled Crossref Work"

        # Abstract
        abstract = clean_text(data.get("abstract"))

        # Document Type
        raw_type = data.get("type")
        doc_type = classify_document_type(source_type=raw_type, source="crossref", title=title)

        # Dates
        date_info = extract_publication_dates(data, source="crossref")
        pub_date = date_info["published_date"]
        pub_year = date_info["publication_year"]
        online_pub_date = date_info["online_publication_date"]
        print_pub_date = date_info["print_publication_date"]
        issued_date = date_info["issued_date"]

        # DOI
        doi = normalize_doi(data.get("DOI") or raw_doi)

        # Authors & Institutions
        authors: List[Author] = []
        institutions: List[Institution] = []
        for a in data.get("author", []):
            given = a.get("given", "")
            family = a.get("family", "")
            raw_name = f"{given} {family}".strip() if given or family else a.get("name", "")
            if not raw_name:
                continue

            full_name, first_name, last_name = parse_author_name(raw_name)
            orcid = normalize_orcid(a.get("ORCID"))

            affiliations: List[str] = []
            for aff in a.get("affiliation", []):
                aff_name = clean_text(aff.get("name")) if isinstance(aff, dict) else clean_text(str(aff))
                if aff_name:
                    affiliations.append(aff_name)
                    if aff_name not in [inst.name for inst in institutions]:
                        institutions.append(Institution(name=aff_name))

            authors.append(
                Author(
                    name=full_name,
                    first_name=first_name,
                    last_name=last_name,
                    orcid=orcid,
                    affiliations=affiliations,
                )
            )

        # Venue
        venue: Optional[Venue] = None
        containers = data.get("container-title") or []
        container_name = containers[0] if isinstance(containers, list) and containers else None
        if container_name:
            issn_list = data.get("ISSN") or []
            issn = issn_list[0] if isinstance(issn_list, list) and issn_list else None
            venue = Venue(
                name=clean_text(container_name),
                type=data.get("type"),
                issn=issn,
                raw_venue=container_name,
            )

        # Topics / Subjects
        topics: List[Topic] = []
        for subj in data.get("subject", []):
            if subj:
                topics.append(Topic(name=clean_text(subj) or subj, source="crossref_subject"))

        # Open Access & Full text
        fulltext_url: Optional[str] = None
        for link_obj in data.get("link", []):
            content_type = link_obj.get("content-type", "")
            if "pdf" in content_type or not fulltext_url:
                fulltext_url = link_obj.get("URL")

        fulltext_status = (
            FulltextStatus.DISCOVERABLE if fulltext_url else FulltextStatus.NOT_CHECKED
        )

        canonical_id = f"rg_{uuid.uuid5(uuid.NAMESPACE_URL, f'crossref:{doi or raw_doi}').hex[:12]}"

        provenance_rec = ProvenanceRecord(
            source="crossref",
            source_record_id=doi or raw_doi,
            retrieved_at=raw_record.fetched_at,
            source_url=f"https://doi.org/{doi or raw_doi}",
            source_version="v1",
        )

        source_records = SourceRecords(crossref=doi or raw_doi)

        return CanonicalPaper(
            canonical_id=canonical_id,
            title=title,
            abstract=abstract,
            document_type=doc_type,
            authors=authors,
            institutions=institutions,
            venue=venue,
            published_date=pub_date,
            online_publication_date=online_pub_date,
            print_publication_date=print_pub_date,
            issued_date=issued_date,
            publication_date=pub_date,
            publication_year=pub_year,
            doi=doi,
            arxiv_id=None,
            other_source_ids=source_records,
            topics=topics,
            keywords=[],
            references=[],
            citation_count=data.get("is-referenced-by-count"),
            open_access=OpenAccessInfo(
                is_oa=bool(fulltext_url),
                oa_status="gold" if fulltext_url else None,
                oa_url=fulltext_url,
            ),
            fulltext_status=fulltext_status,
            fulltext_available=fulltext_status,
            fulltext_url=fulltext_url,
            source_records=source_records,
            provenance=[provenance_rec],
            identity_confidence=ConfidenceLevel.EXACT,
        )
