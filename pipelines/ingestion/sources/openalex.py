"""OpenAlex Source Adapter for ResearchGraph.

Handles querying OpenAlex API (https://api.openalex.org), polite pool handling,
cursor pagination, and normalization of works into CanonicalPaper representations.
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
from pipelines.ingestion.normalizers.identifiers import normalize_arxiv_id, normalize_doi, normalize_orcid
from pipelines.ingestion.normalizers.text import (
    clean_text,
    parse_author_name,
    reconstruct_openalex_abstract,
)
from pipelines.ingestion.sources.base import BaseSourceAdapter

logger = logging.getLogger(__name__)


class OpenAlexAdapter(BaseSourceAdapter):
    """Adapter for the OpenAlex Works API."""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(
        self,
        api_key: Optional[str] = config.OPENALEX_API_KEY,
        mailto: Optional[str] = config.OPENALEX_MAILTO,
        rate_limit_delay: float = config.OPENALEX_RATE_LIMIT_DELAY,
    ):
        self.api_key = api_key
        self.mailto = mailto
        super().__init__(source_name="openalex", rate_limit_delay=rate_limit_delay)

    def _get_default_headers(self) -> Dict[str, str]:
        headers = super()._get_default_headers()
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def search(
        self,
        query: str,
        limit: int = 100,
        checkpoint_file: Optional[Path] = None,
        filter_param: Optional[str] = None,
        **kwargs: Any,
    ) -> List[RawRecord]:
        """Search OpenAlex works matching a query string or concept filter."""
        results: List[RawRecord] = []
        cursor = "*"
        per_page = min(limit, 100)

        logger.info(f"[OpenAlex] Starting search for query='{query}' (target limit={limit})")

        while len(results) < limit and cursor:
            params: Dict[str, Any] = {
                "search": query,
                "per_page": per_page,
                "cursor": cursor,
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
                logger.error(f"[OpenAlex] Failed to fetch page at cursor {cursor}: {e}")
                break

            works = data.get("results", [])
            if not works:
                logger.info("[OpenAlex] No more results found.")
                break

            page_records: List[RawRecord] = []
            for work in works:
                work_id = work.get("id", "").replace("https://openalex.org/", "")
                raw_rec = self.create_raw_record(
                    source_record_id=work_id,
                    raw_data=work,
                    query=query,
                )
                page_records.append(raw_rec)
                results.append(raw_rec)
                if len(results) >= limit:
                    break

            if checkpoint_file and page_records:
                self.save_raw_records_checkpoint(page_records, checkpoint_file)

            meta = data.get("meta", {})
            next_cursor = meta.get("next_cursor")
            if next_cursor == cursor or not next_cursor:
                break
            cursor = next_cursor

            logger.info(f"[OpenAlex] Acquired {len(results)}/{limit} works...")

        logger.info(f"[OpenAlex] Finished search. Total acquired: {len(results)}")
        return results

    def fetch_by_id(self, identifier: str) -> Optional[RawRecord]:
        """Fetch a single work from OpenAlex by ID or DOI."""
        work_id = identifier.replace("https://openalex.org/", "")
        url = f"{self.BASE_URL}/{work_id}"
        params: Dict[str, Any] = {}
        if self.mailto:
            params["mailto"] = self.mailto

        try:
            response = self._request_with_retry(method="GET", url=url, params=params)
            data = response.json()
            return self.create_raw_record(
                source_record_id=work_id,
                raw_data=data,
            )
        except Exception as e:
            logger.warning(f"[OpenAlex] Failed to fetch work ID {identifier}: {e}")
            return None

    def normalize(self, raw_record: RawRecord) -> CanonicalPaper:
        """Normalize raw OpenAlex work JSON into CanonicalPaper."""
        data = raw_record.raw_data
        work_id = raw_record.source_record_id

        # Title & Abstract
        title = clean_text(data.get("title") or data.get("display_name")) or "Untitled Paper"
        abstract = reconstruct_openalex_abstract(data.get("abstract_inverted_index"))

        # Document Type
        raw_type = data.get("type")
        doc_type = classify_document_type(source_type=raw_type, source="openalex", title=title)

        # Dates
        date_info = extract_publication_dates(data, source="openalex")
        pub_date = date_info["published_date"]
        pub_year = date_info["publication_year"]
        online_pub_date = date_info["online_publication_date"]
        issued_date = date_info["issued_date"]

        # Identifiers
        doi = normalize_doi(data.get("doi"))
        ids_dict = data.get("ids", {})
        arxiv_raw = ids_dict.get("arxiv") or data.get("arxiv_id")
        arxiv_id = normalize_arxiv_id(arxiv_raw)

        # Authors & Institutions
        authors: List[Author] = []
        institutions_map: Dict[str, Institution] = {}

        for authorship in data.get("authorships", []):
            author_data = authorship.get("author", {})
            raw_name = author_data.get("display_name")
            if not raw_name:
                continue

            full_name, first_name, last_name = parse_author_name(raw_name)
            orcid = normalize_orcid(author_data.get("orcid"))
            affiliations: List[str] = []

            for raw_affil in authorship.get("raw_affiliation_strings", []):
                cleaned_affil = clean_text(raw_affil)
                if cleaned_affil:
                    affiliations.append(cleaned_affil)

            for inst in authorship.get("institutions", []):
                inst_name = clean_text(inst.get("display_name"))
                if inst_name:
                    if inst_name not in affiliations:
                        affiliations.append(inst_name)
                    if inst_name not in institutions_map:
                        institutions_map[inst_name] = Institution(
                            name=inst_name,
                            ror_id=inst.get("ror"),
                            country_code=inst.get("country_code"),
                        )

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
        primary_location = data.get("primary_location") or {}
        source_loc = primary_location.get("source") or {}
        if source_loc:
            venue = Venue(
                name=source_loc.get("display_name"),
                type=source_loc.get("type"),
                issn=source_loc.get("issn_l"),
                raw_venue=source_loc.get("display_name"),
            )

        # Topics / Concepts
        topics: List[Topic] = []
        for concept in data.get("concepts", []):
            name = concept.get("display_name")
            if name:
                topics.append(
                    Topic(
                        name=name,
                        score=concept.get("score"),
                        source="openalex_concept",
                        source_id=concept.get("id"),
                    )
                )

        for top in data.get("topics", []):
            name = top.get("display_name")
            if name:
                topics.append(
                    Topic(
                        name=name,
                        score=top.get("score"),
                        source="openalex_topic",
                        source_id=top.get("id"),
                    )
                )

        # Keywords
        keywords: List[str] = []
        for kw in data.get("keywords", []):
            kw_name = clean_text(kw.get("display_name"))
            if kw_name and kw_name not in keywords:
                keywords.append(kw_name)

        # Citations & References
        citation_count = data.get("cited_by_count")
        references: List[str] = []
        for ref in data.get("referenced_works", []):
            clean_ref = ref.replace("https://openalex.org/", "")
            references.append(clean_ref)

        # Open Access & Full text
        oa_dict = data.get("open_access", {})
        is_oa = bool(oa_dict.get("is_oa", False))
        oa_status = oa_dict.get("oa_status")
        oa_url = oa_dict.get("oa_url")

        fulltext_url = None
        fulltext_status = FulltextStatus.NOT_CHECKED
        if primary_location and primary_location.get("pdf_url"):
            fulltext_url = primary_location.get("pdf_url")
            fulltext_status = FulltextStatus.DISCOVERABLE
        elif oa_url:
            fulltext_url = oa_url
            fulltext_status = FulltextStatus.DISCOVERABLE
        elif not is_oa:
            fulltext_status = FulltextStatus.UNAVAILABLE

        # Generate canonical ID seed
        canonical_id = f"rg_{uuid.uuid5(uuid.NAMESPACE_URL, f'openalex:{work_id}').hex[:12]}"

        # Provenance
        provenance_rec = ProvenanceRecord(
            source="openalex",
            source_record_id=work_id,
            retrieved_at=raw_record.fetched_at,
            source_url=f"https://openalex.org/{work_id}",
            source_version="v1",
        )

        source_records = SourceRecords(openalex=work_id)

        return CanonicalPaper(
            canonical_id=canonical_id,
            title=title,
            abstract=abstract,
            document_type=doc_type,
            authors=authors,
            institutions=list(institutions_map.values()),
            venue=venue,
            published_date=pub_date,
            online_publication_date=online_pub_date,
            issued_date=issued_date,
            publication_date=pub_date,
            publication_year=pub_year,
            doi=doi,
            arxiv_id=arxiv_id,
            other_source_ids=source_records,
            topics=topics,
            keywords=keywords,
            references=references,
            citation_count=citation_count,
            open_access=OpenAccessInfo(
                is_oa=is_oa,
                oa_status=oa_status,
                oa_url=oa_url,
            ),
            fulltext_status=fulltext_status,
            fulltext_available=fulltext_status,
            fulltext_url=fulltext_url,
            source_records=source_records,
            provenance=[provenance_rec],
            identity_confidence=ConfidenceLevel.EXACT,
        )
