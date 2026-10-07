"""arXiv Source Adapter for ResearchGraph.

Handles querying the arXiv API (export.arxiv.org/api/query), parsing Atom XML feeds,
rate limiting, and normalization into CanonicalPaper.
"""

from __future__ import annotations

import logging
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

from dataset.schemas.canonical_paper import (
    Author,
    CanonicalPaper,
    ConfidenceLevel,
    DocumentType,
    FulltextStatus,
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
from pipelines.ingestion.normalizers.identifiers import normalize_arxiv_id, normalize_doi
from pipelines.ingestion.normalizers.text import clean_text, parse_author_name
from pipelines.ingestion.sources.base import BaseSourceAdapter

logger = logging.getLogger(__name__)

ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


def format_arxiv_query(raw_query: str) -> str:
    """Format raw query string into valid arXiv API search_query syntax."""
    cleaned = raw_query.strip()
    if ":" in cleaned:
        return cleaned

    words = cleaned.split()
    if len(words) <= 2:
        return f"all:{cleaned}"
    
    return f'ti:"{cleaned}" OR abs:"{cleaned}" OR all:"{words[0]} {words[1]}"'


class ArxivAdapter(BaseSourceAdapter):
    """Adapter for the arXiv Export API."""

    BASE_URL = "https://export.arxiv.org/api/query"

    def __init__(
        self,
        user_agent: str = config.ARXIV_USER_AGENT,
        rate_limit_delay: float = config.ARXIV_RATE_LIMIT_DELAY,
    ):
        self.user_agent = user_agent
        super().__init__(source_name="arxiv", rate_limit_delay=rate_limit_delay)

    def _get_default_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/atom+xml, application/xml",
        }

    def search(
        self,
        query: str,
        limit: int = 100,
        checkpoint_file: Optional[Path] = None,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
        **kwargs: Any,
    ) -> List[RawRecord]:
        """Search arXiv matching a query."""
        results: List[RawRecord] = []
        start = 0
        batch_size = min(limit, 100)
        formatted_query = format_arxiv_query(query)

        logger.info(f"[arXiv] Starting search for query='{formatted_query}' (target limit={limit})")

        while len(results) < limit:
            params = {
                "search_query": formatted_query,
                "start": start,
                "max_results": batch_size,
                "sortBy": sort_by,
                "sortOrder": sort_order,
            }

            try:
                response = self._request_with_retry(
                    method="GET",
                    url=self.BASE_URL,
                    params=params,
                )
                xml_content = response.text
            except Exception as e:
                logger.error(f"[arXiv] Failed to fetch page at start={start}: {e}")
                break

            parsed_entries = self._parse_feed(xml_content)
            if not parsed_entries:
                logger.info("[arXiv] No more entries found.")
                break

            page_records: List[RawRecord] = []
            for entry_dict in parsed_entries:
                arxiv_id = entry_dict.get("arxiv_id")
                if not arxiv_id:
                    continue

                raw_rec = self.create_raw_record(
                    source_record_id=arxiv_id,
                    raw_data=entry_dict,
                    query=query,
                )
                page_records.append(raw_rec)
                results.append(raw_rec)
                if len(results) >= limit:
                    break

            if checkpoint_file and page_records:
                self.save_raw_records_checkpoint(page_records, checkpoint_file)

            start += len(parsed_entries)
            logger.info(f"[arXiv] Acquired {len(results)}/{limit} papers...")

            if len(parsed_entries) < batch_size:
                break

        logger.info(f"[arXiv] Finished search. Total acquired: {len(results)}")
        return results

    def fetch_by_id(self, identifier: str) -> Optional[RawRecord]:
        """Fetch a specific paper by arXiv ID."""
        clean_id = normalize_arxiv_id(identifier) or identifier
        params = {"id_list": clean_id}
        try:
            response = self._request_with_retry(method="GET", url=self.BASE_URL, params=params)
            entries = self._parse_feed(response.text)
            if entries:
                return self.create_raw_record(source_record_id=clean_id, raw_data=entries[0])
            return None
        except Exception as e:
            logger.warning(f"[arXiv] Failed to fetch arXiv ID {clean_id}: {e}")
            return None

    def _parse_feed(self, xml_text: str) -> List[Dict[str, Any]]:
        """Parse Atom XML string into a list of dictionaries."""
        entries: List[Dict[str, Any]] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"[arXiv] XML ParseError: {e}")
            return entries

        for entry in root.findall(f"{ATOM_NS}entry"):
            id_elem = entry.find(f"{ATOM_NS}id")
            raw_id = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
            arxiv_id = normalize_arxiv_id(raw_id) or raw_id.split("/abs/")[-1]

            title_elem = entry.find(f"{ATOM_NS}title")
            title = clean_text(title_elem.text) if title_elem is not None and title_elem.text else ""

            summary_elem = entry.find(f"{ATOM_NS}summary")
            summary = clean_text(summary_elem.text) if summary_elem is not None and summary_elem.text else ""

            published_elem = entry.find(f"{ATOM_NS}published")
            published = published_elem.text.strip() if published_elem is not None and published_elem.text else None

            updated_elem = entry.find(f"{ATOM_NS}updated")
            updated = updated_elem.text.strip() if updated_elem is not None and updated_elem.text else None

            authors: List[str] = []
            for author_elem in entry.findall(f"{ATOM_NS}author"):
                name_elem = author_elem.find(f"{ATOM_NS}name")
                if name_elem is not None and name_elem.text:
                    authors.append(clean_text(name_elem.text) or "")

            categories: List[str] = []
            for cat_elem in entry.findall(f"{ATOM_NS}category"):
                term = cat_elem.attrib.get("term")
                if term:
                    categories.append(term)

            doi: Optional[str] = None
            doi_elem = entry.find(f"{ARXIV_NS}doi")
            if doi_elem is not None and doi_elem.text:
                doi = normalize_doi(doi_elem.text)

            pdf_url: Optional[str] = None
            for link in entry.findall(f"{ATOM_NS}link"):
                if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                    pdf_url = link.attrib.get("href")

            if not pdf_url and arxiv_id:
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

            entry_dict = {
                "arxiv_id": arxiv_id,
                "raw_id": raw_id,
                "title": title,
                "summary": summary,
                "published": published,
                "updated": updated,
                "authors": authors,
                "categories": categories,
                "doi": doi,
                "pdf_url": pdf_url,
            }
            entries.append(entry_dict)

        return entries

    def normalize(self, raw_record: RawRecord) -> CanonicalPaper:
        """Normalize parsed arXiv entry into CanonicalPaper."""
        data = raw_record.raw_data
        arxiv_id = raw_record.source_record_id

        title = data.get("title") or "Untitled arXiv Paper"
        abstract = data.get("summary")

        # Document Type
        doc_type = classify_document_type(source_type="preprint", source="arxiv", title=title)

        # Dates
        date_info = extract_publication_dates(data, source="arxiv")
        pub_date = date_info["published_date"]
        pub_year = date_info["publication_year"]
        online_pub_date = date_info["online_publication_date"]

        doi = normalize_doi(data.get("doi"))

        authors: List[Author] = []
        for raw_author in data.get("authors", []):
            full_name, first_name, last_name = parse_author_name(raw_author)
            authors.append(
                Author(
                    name=full_name,
                    first_name=first_name,
                    last_name=last_name,
                )
            )

        topics: List[Topic] = []
        for cat in data.get("categories", []):
            topics.append(Topic(name=cat, source="arxiv_category"))

        pdf_url = data.get("pdf_url") or f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        canonical_id = f"rg_{uuid.uuid5(uuid.NAMESPACE_URL, f'arxiv:{arxiv_id}').hex[:12]}"

        provenance_rec = ProvenanceRecord(
            source="arxiv",
            source_record_id=arxiv_id,
            retrieved_at=raw_record.fetched_at,
            source_url=f"https://arxiv.org/abs/{arxiv_id}",
            source_version="v1",
        )

        source_records = SourceRecords(arxiv=arxiv_id)

        return CanonicalPaper(
            canonical_id=canonical_id,
            title=title,
            abstract=abstract,
            document_type=doc_type,
            authors=authors,
            institutions=[],
            venue=Venue(name="arXiv", type="repository", raw_venue="arXiv preprint"),
            published_date=pub_date,
            online_publication_date=online_pub_date,
            publication_date=pub_date,
            publication_year=pub_year,
            doi=doi,
            arxiv_id=arxiv_id,
            other_source_ids=source_records,
            topics=topics,
            keywords=[],
            references=[],
            citation_count=None,
            open_access=OpenAccessInfo(
                is_oa=True,
                oa_status="green",
                oa_url=pdf_url,
            ),
            fulltext_status=FulltextStatus.DISCOVERABLE,
            fulltext_available=FulltextStatus.DISCOVERABLE,
            fulltext_url=pdf_url,
            source_records=source_records,
            provenance=[provenance_rec],
            identity_confidence=ConfidenceLevel.EXACT,
        )
