"""Unit tests for publication date normalization and date model."""

import pytest
from dataset.schemas.canonical_paper import CanonicalPaper
from pipelines.ingestion.normalizers.dates import extract_publication_dates, parse_date_parts


def test_parse_date_parts():
    # Year, month, day
    assert parse_date_parts({"date-parts": [[2024, 3, 15]]}) == "2024-03-15"
    # Year, month
    assert parse_date_parts({"date-parts": [[2023, 11]]}) == "2023-11"
    # Year only
    assert parse_date_parts({"date-parts": [[2022]]}) == "2022"
    # Empty
    assert parse_date_parts(None) is None
    assert parse_date_parts({"date-parts": []}) is None


def test_extract_publication_dates_crossref():
    raw_data = {
        "published-print": {"date-parts": [[2027]]},
        "issued": {"date-parts": [[2027]]},
    }
    res = extract_publication_dates(raw_data, source="crossref")
    assert res["publication_year"] == 2027
    assert res["print_publication_date"] == "2027"
    assert res["issued_date"] == "2027"
    assert res["published_date"] == "2027"


def test_extract_publication_dates_openalex():
    raw_data = {
        "publication_date": "2024-05-12",
        "publication_year": 2024,
    }
    res = extract_publication_dates(raw_data, source="openalex")
    assert res["published_date"] == "2024-05-12"
    assert res["online_publication_date"] == "2024-05-12"
    assert res["publication_year"] == 2024


def test_canonical_paper_granular_dates():
    paper = CanonicalPaper(
        canonical_id="rg_test_dates",
        title="Testing Granular Dates",
        published_date="2024-01-15",
        online_publication_date="2024-01-10",
        print_publication_date="2024-02-01",
        issued_date="2024-01-15",
        publication_year=2024,
    )
    assert paper.online_publication_date == "2024-01-10"
    assert paper.print_publication_date == "2024-02-01"
    assert paper.published_date == "2024-01-15"
