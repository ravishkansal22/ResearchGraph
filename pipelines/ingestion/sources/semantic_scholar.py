"""Semantic Scholar Source Adapter for ResearchGraph.

Handles querying Semantic Scholar Academic Graph API (https://api.semanticscholar.org/graph/v1),
offset pagination, rate limiting, and normalization into CanonicalPaper.
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
    FulltextStatus,
    OpenAccessInfo,
    ProvenanceRecord,
    RawRecord,
    SourceRecords,
    Topic,
    Venue,
)
from pipelines.ingestion.config import config
from pipelines.ingestion.normalizers.identifiers import normalize_arxiv_id, normalize_doi
from pipelines.ingestion.normalizers.text import clean_text, parse_author_name
from pipelines.ingestion.sources.base import BaseSourceAdapter

logger = logging.getLogger(__name__)


class SemanticScholarAdapter(BaseSourceAdapter):
    """Adapter for the Semantic Scholar Graph API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    DEFAULT_FIELDS = (
        "paperId,title,abstract,authors,year,venue,publicationDate,externalIds,"
        "isOpenAccess,openAccessPdf,fieldsOfStudy,s2FieldsOfStudy,citationCount,"
        "influentialCitationCount,referenceCount"
    )

    def __init__(
        self,
        api_key: Optional[str] = config.SEMANTIC_SCHOLAR_API_KEY,
        rate_limit_delay: float = config.SEMANTIC_SCHOLAR_RATE_LIMIT_DELAY,
    ):
        super().__init__(source_name="semantic_scholar", rate_limit_delay=rate_limit_delay)
        self.api_key = api_key

    def _get_default_headers(self) -> Dict[str, str]:
        headers = super()._get_default_headers()
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def search(
        self,
        query: str,
        limit: int = 100,
        checkpoint_file: Optional[Path] = None,
        year: Optional[str] = None,
        fields_of_study: Optional[str] = None,
        **kwargs: Any,
    ) -> List[RawRecord]:
        """Search Semantic Scholar papers matching a query.

        Uses offset-based pagination.
        """
        results: List[RawRecord] = []
        offset = 0
        batch_size = min(limit, 100)

        logger.info(f"[SemanticScholar] Starting search for query='{query}' (target limit={limit})")

        while len(results) < limit:
            params: Dict[str, Any] = {
                "query": query,
                "offset": offset,
                "limit": batch_size,
                "fields": self.DEFAULT_FIELDS,
            }
            if year:
                params["year"] = year
            if fields_of_study:
                params["fieldsOfStudy"] = fields_of_study

            try:
                response = self._request_with_retry(
                    method="GET",
                    url=f"{self.BASE_URL}/paper/search",
                    params=params,
                )
                data = response.json()
            except Exception as e:
                logger.error(f"[SemanticScholar] Failed to fetch page at offset {offset}: {e}")
                break

            papers = data.get("data", [])
            if not papers:
                logger.info("[SemanticScholar] No more results found.")
                break

            page_records: List[RawRecord] = []
            for paper in papers:
                paper_id = paper.get("paperId")
                if not paper_id:
                    continue

                raw_rec = self.create_raw_record(
                    source_record_id=paper_id,
                    raw_data=paper,
                    query=query,
                )
                page_records.append(raw_rec)
                results.append(raw_rec)
                if len(results) >= limit:
                    break

            if checkpoint_file and page_records:
                self.save_raw_records_checkpoint(page_records, checkpoint_file)

            total = data.get("total", 0)
            offset += len(papers)
            if offset >= total or len(papers) == 0:
                break

            logger.info(f"[SemanticScholar] Acquired {len(results)}/{limit} papers...")

        logger.info(f"[SemanticScholar] Finished search. Total acquired: {len(results)}")
        return results

    def fetch_by_id(self, identifier: str) -> Optional[RawRecord]:
        """Fetch a specific paper by S2 PaperId, DOI, or arXiv ID."""
        url = f"{self.BASE_URL}/paper/{identifier}"
        params = {"fields": self.DEFAULT_FIELDS}
        try:
            response = self._request_with_retry(method="GET", url=url, params=params)
            data = response.json()
            paper_id = data.get("paperId", identifier)
            return self.create_raw_record(source_record_id=paper_id, raw_data=data)
        except Exception as e:
            logger.warning(f"[SemanticScholar] Failed to fetch paper ID {identifier}: {e}")
            return None

    def normalize(self, raw_record: RawRecord) -> CanonicalPaper:
        """Normalize Semantic Scholar paper data into CanonicalPaper."""
        data = raw_record.raw_data
        paper_id = raw_record.source_record_id

        title = clean_text(data.get("title")) or "Untitled Paper"
        abstract = clean_text(data.get("abstract"))

        pub_date = data.get("publicationDate")
        pub_year = data.get("year")

        # External IDs
        ext_ids = data.get("externalIds") or {}
        doi = normalize_doi(ext_ids.get("DOI"))
        arxiv_id = normalize_arxiv_id(ext_ids.get("ArXiv"))

        # Authors
        authors: List[Author] = []
        for a in data.get("authors", []):
            raw_name = a.get("name")
            if not raw_name:
                continue
            full_name, first_name, last_name = parse_author_name(raw_name)
            authors.append(
                Author(
                    name=full_name,
                    first_name=first_name,
                    last_name=last_name,
                )
            )

        # Venue
        venue: Optional[Venue] = None
        raw_venue = data.get("venue")
        if raw_venue:
            venue = Venue(name=clean_text(raw_venue), raw_venue=raw_venue)

        # Topics
        topics: List[Topic] = []
        for fos in data.get("fieldsOfStudy") or []:
            if fos:
                topics.append(Topic(name=fos, source="s2_fos"))

        for s2_fos in data.get("s2FieldsOfStudy") or []:
            cat = s2_fos.get("category")
            if cat and cat not in [t.name for t in topics]:
                topics.append(Topic(name=cat, source="s2_category"))

        # Open Access & Full text
        is_oa = bool(data.get("isOpenAccess", False))
        oa_pdf = data.get("openAccessPdf") or {}
        fulltext_url = oa_pdf.get("url") if isinstance(oa_pdf, dict) else None

        fulltext_status = FulltextStatus.FULLTEXT_NOT_CHECKED
        if fulltext_url:
            fulltext_status = FulltextStatus.FULLTEXT_AVAILABLE
        elif not is_oa:
            fulltext_status = FulltextStatus.FULLTEXT_UNAVAILABLE

        # Canonical ID seed
        canonical_id = f"rg_{uuid.uuid5(uuid.NAMESPACE_URL, f'semantic_scholar:{paper_id}').hex[:12]}"

        # Provenance
        provenance_rec = ProvenanceRecord(
            source="semantic_scholar",
            source_record_id=paper_id,
            retrieved_at=raw_record.fetched_at,
            source_url=f"https://www.semanticscholar.org/paper/{paper_id}",
            source_version="v1",
        )

        source_records = SourceRecords(semantic_scholar=paper_id)

        return CanonicalPaper(
            canonical_id=canonical_id,
            title=title,
            abstract=abstract,
            authors=authors,
            institutions=[],
            venue=venue,
            publication_date=pub_date,
            publication_year=pub_year,
            doi=doi,
            arxiv_id=arxiv_id,
            other_source_ids=source_records,
            topics=topics,
            keywords=[],
            references=[],
            citation_count=data.get("citationCount"),
            influential_citation_count=data.get("influentialCitationCount"),
            open_access=OpenAccessInfo(
                is_oa=is_oa,
                oa_status="gold" if is_oa else "closed",
                oa_url=fulltext_url,
            ),
            fulltext_available=fulltext_status,
            fulltext_url=fulltext_url,
            source_records=source_records,
            provenance=[provenance_rec],
            identity_confidence=ConfidenceLevel.EXACT,
        )
