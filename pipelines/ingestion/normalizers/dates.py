"""Publication Date Normalization Utilities.

Extracts and harmonizes primary, online, print, and issued publication dates.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

DATE_ISO_REGEX = re.compile(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?")


def parse_date_parts(date_obj: Optional[Dict[str, Any]]) -> Optional[str]:
    """Parse Crossref date-parts structure (e.g. {'date-parts': [[2024, 5, 12]]}) into ISO date string."""
    if not date_obj or not isinstance(date_obj, dict):
        return None

    date_parts = date_obj.get("date-parts", [])
    if not date_parts or not isinstance(date_parts, list) or not date_parts[0]:
        return None

    parts = date_parts[0]
    if not isinstance(parts, list) or not parts:
        return None

    year = parts[0]
    if not isinstance(year, int):
        try:
            year = int(year)
        except (ValueError, TypeError):
            return None

    if len(parts) >= 3 and isinstance(parts[1], int) and isinstance(parts[2], int):
        return f"{year:04d}-{parts[1]:02d}-{parts[2]:02d}"
    elif len(parts) >= 2 and isinstance(parts[1], int):
        return f"{year:04d}-{parts[1]:02d}"
    return f"{year:04d}"


def extract_publication_dates(
    raw_data: Dict[str, Any],
    source: str,
) -> Dict[str, Optional[Any]]:
    """Extract granular publication dates and year from raw record data.

    Returns dict with keys:
        - published_date
        - online_publication_date
        - print_publication_date
        - issued_date
        - publication_year
    """
    published_date: Optional[str] = None
    online_date: Optional[str] = None
    print_date: Optional[str] = None
    issued_date: Optional[str] = None
    publication_year: Optional[int] = None

    if source == "crossref":
        online_date = parse_date_parts(raw_data.get("published-online"))
        print_date = parse_date_parts(raw_data.get("published-print"))
        issued_date = parse_date_parts(raw_data.get("issued")) or parse_date_parts(raw_data.get("created"))

        # Primary published date: prefer online date, then print date, then issued date
        published_date = online_date or print_date or issued_date

        if published_date:
            match = DATE_ISO_REGEX.match(published_date)
            if match:
                publication_year = int(match.group(1))

    elif source == "openalex":
        published_date = raw_data.get("publication_date")
        publication_year = raw_data.get("publication_year")
        online_date = published_date  # OpenAlex publication_date represents availability date
        issued_date = raw_data.get("created_date")

    elif source == "arxiv":
        raw_published = raw_data.get("published")
        if raw_published and "T" in str(raw_published):
            published_date = str(raw_published).split("T")[0]
            online_date = published_date
        elif raw_published:
            published_date = str(raw_published)
            online_date = published_date

        if published_date and len(published_date) >= 4 and published_date[:4].isdigit():
            publication_year = int(published_date[:4])

    elif source == "semantic_scholar":
        published_date = raw_data.get("publicationDate")
        publication_year = raw_data.get("year")
        online_date = published_date

    return {
        "published_date": published_date,
        "online_publication_date": online_date,
        "print_publication_date": print_date,
        "issued_date": issued_date,
        "publication_year": publication_year,
    }
