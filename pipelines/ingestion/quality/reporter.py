"""Dataset Quality Reporting and Manifest Generation.

Computes comprehensive metadata completeness, deduplication metrics, source overlap matrices,
temporal distributions, and full-text availability reports.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from dataset.schemas.canonical_paper import CanonicalPaper, FulltextStatus
from pipelines.ingestion.config import config

logger = logging.getLogger(__name__)


class QualityReporter:
    """Generates dataset manifests and rigorous scientific data quality reports."""

    def __init__(
        self,
        schema_version: str = config.SCHEMA_VERSION,
        pipeline_version: str = config.PIPELINE_VERSION,
    ):
        self.schema_version = schema_version
        self.pipeline_version = pipeline_version

    def generate_manifest(
        self,
        canonical_papers: List[CanonicalPaper],
        dataset_version: str,
        sources_used: List[str],
        dedup_stats: Dict[str, Any],
        relevance_stats: Optional[Dict[str, Any]] = None,
        fulltext_stats: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Compile formal dataset release manifest."""
        total_canonical = len(canonical_papers)
        fulltext_count = sum(
            1 for p in canonical_papers if p.fulltext_available == FulltextStatus.FULLTEXT_AVAILABLE
        )

        with_abstracts = sum(1 for p in canonical_papers if p.abstract and len(p.abstract) > 20)
        with_doi = sum(1 for p in canonical_papers if p.doi)
        with_arxiv = sum(1 for p in canonical_papers if p.arxiv_id)
        with_authors = sum(1 for p in canonical_papers if len(p.authors) > 0)
        with_pub_date = sum(1 for p in canonical_papers if p.publication_date or p.publication_year)
        with_citations = sum(1 for p in canonical_papers if p.citation_count is not None)
        with_references = sum(1 for p in canonical_papers if len(p.references) > 0)

        # Papers per source
        source_counts: Counter[str] = Counter()
        for p in canonical_papers:
            for prov in p.provenance:
                source_counts[prov.source] += 1

        # Papers per year
        year_counts: Counter[int] = Counter()
        for p in canonical_papers:
            if p.publication_year:
                year_counts[p.publication_year] += 1

        manifest = {
            "dataset_version": dataset_version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": self.schema_version,
            "pipeline_version": self.pipeline_version,
            "sources": sources_used,
            "paper_count": total_canonical,
            "fulltext_count": fulltext_count,
            "statistics": {
                "total_input_records": dedup_stats.get("total_input_records", total_canonical),
                "canonical_papers": total_canonical,
                "duplicates_merged": dedup_stats.get("duplicates_merged", 0),
                "duplicate_rate": dedup_stats.get("duplicate_rate", 0.0),
                "unresolved_matches": dedup_stats.get("unresolved_possible_matches", 0),
                "papers_with_abstracts": with_abstracts,
                "papers_with_doi": with_doi,
                "papers_with_arxiv_id": with_arxiv,
                "papers_with_authors": with_authors,
                "papers_with_publication_date": with_pub_date,
                "papers_with_citations": with_citations,
                "papers_with_references": with_references,
                "papers_with_fulltext": fulltext_count,
                "papers_per_source": dict(source_counts),
                "papers_per_year": dict(sorted(year_counts.items())),
                "relevance_filtering": relevance_stats or {},
                "fulltext_pipeline": fulltext_stats or {},
            },
        }
        return manifest

    def compute_quality_report(
        self,
        canonical_papers: List[CanonicalPaper],
        manifest: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], str]:
        """Compute comprehensive quality metrics and render markdown report."""
        total = len(canonical_papers)
        if total == 0:
            return {"error": "Empty dataset"}, "# ResearchGraph Quality Report\n\nDataset is empty."

        # Completeness metrics
        completeness = {
            "title_pct": 100.0,
            "abstract_pct": round((sum(1 for p in canonical_papers if p.abstract) / total) * 100, 2),
            "authors_pct": round((sum(1 for p in canonical_papers if p.authors) / total) * 100, 2),
            "doi_pct": round((sum(1 for p in canonical_papers if p.doi) / total) * 100, 2),
            "arxiv_id_pct": round((sum(1 for p in canonical_papers if p.arxiv_id) / total) * 100, 2),
            "publication_date_pct": round(
                (sum(1 for p in canonical_papers if p.publication_date or p.publication_year) / total) * 100, 2
            ),
            "venue_pct": round((sum(1 for p in canonical_papers if p.venue and p.venue.name) / total) * 100, 2),
            "topics_pct": round((sum(1 for p in canonical_papers if p.topics) / total) * 100, 2),
            "citations_pct": round(
                (sum(1 for p in canonical_papers if p.citation_count is not None) / total) * 100, 2
            ),
            "open_access_pct": round(
                (sum(1 for p in canonical_papers if p.open_access and p.open_access.is_oa) / total) * 100, 2
            ),
        }

        # Source overlap matrix
        sources_list = manifest.get("sources", [])
        overlap_matrix: Dict[str, Dict[str, int]] = {s1: {s2: 0 for s2 in sources_list} for s1 in sources_list}

        for p in canonical_papers:
            p_sources = {prov.source for prov in p.provenance}
            for s1 in p_sources:
                for s2 in p_sources:
                    if s1 in overlap_matrix and s2 in overlap_matrix[s1]:
                        overlap_matrix[s1][s2] += 1

        stats = manifest.get("statistics", {})

        report_dict = {
            "dataset_version": manifest.get("dataset_version"),
            "timestamp": manifest.get("created_at"),
            "paper_count": total,
            "metadata_completeness": completeness,
            "deduplication": {
                "total_input_records": stats.get("total_input_records"),
                "canonical_papers": total,
                "duplicate_count": stats.get("duplicates_merged"),
                "duplicate_rate": stats.get("duplicate_rate"),
                "unresolved_matches": stats.get("unresolved_matches"),
            },
            "source_coverage": {
                "records_per_source": stats.get("papers_per_source"),
                "overlap_matrix": overlap_matrix,
            },
            "temporal_distribution": stats.get("papers_per_year"),
            "fulltext_summary": {
                "available": stats.get("papers_with_fulltext"),
                "details": stats.get("fulltext_pipeline"),
            },
            "relevance_summary": stats.get("relevance_filtering"),
        }

        # Build Markdown Document
        lines = [
            f"# ResearchGraph Dataset Quality Report — {manifest.get('dataset_version')}",
            "",
            f"**Generated**: {manifest.get('created_at')}  ",
            f"**Schema Version**: `{self.schema_version}` | **Pipeline Version**: `{self.pipeline_version}`  ",
            f"**Canonical Corpus Size**: **{total:,} papers**",
            "",
            "---",
            "",
            "## 1. Metadata Completeness",
            "",
            "| Field | Count | Completeness (%) | Status |",
            "|---|---|---|---|",
            f"| **Title** | {total} | {completeness['title_pct']}% | Optimal |",
            f"| **Abstract** | {stats.get('papers_with_abstracts', 0)} | {completeness['abstract_pct']}% | {'High' if completeness['abstract_pct'] >= 80 else 'Moderate'} |",
            f"| **Authors** | {stats.get('papers_with_authors', 0)} | {completeness['authors_pct']}% | Optimal |",
            f"| **DOI** | {stats.get('papers_with_doi', 0)} | {completeness['doi_pct']}% | Normal |",
            f"| **arXiv ID** | {stats.get('papers_with_arxiv_id', 0)} | {completeness['arxiv_id_pct']}% | Normal |",
            f"| **Publication Date** | {stats.get('papers_with_publication_date', 0)} | {completeness['publication_date_pct']}% | High |",
            f"| **Venue** | {round(completeness['venue_pct'] * total / 100)} | {completeness['venue_pct']}% | Normal |",
            f"| **Topics / Concepts** | {round(completeness['topics_pct'] * total / 100)} | {completeness['topics_pct']}% | High |",
            f"| **Citation Counts** | {stats.get('papers_with_citations', 0)} | {completeness['citations_pct']}% | Normal |",
            f"| **Open Access Flag** | {round(completeness['open_access_pct'] * total / 100)} | {completeness['open_access_pct']}% | Normal |",
            "",
            "---",
            "",
            "## 2. Identity Resolution & Deduplication",
            "",
            f"- **Raw Source Records Ingested**: {stats.get('total_input_records', total):,}",
            f"- **Canonical Unique Papers**: {total:,}",
            f"- **Duplicates Merged**: {stats.get('duplicates_merged', 0):,}",
            f"- **Deduplication Rate**: {stats.get('duplicate_rate', 0.0) * 100:.2f}%",
            f"- **Unresolved Candidate Matches**: {stats.get('unresolved_matches', 0):,}",
            "",
            "---",
            "",
            "## 3. Source Coverage & Cross-Source Overlap",
            "",
            "### Records by Ingestion Source",
            "| Source | Papers Ingested |",
            "|---|---|",
        ]

        for src, cnt in stats.get("papers_per_source", {}).items():
            lines.append(f"| `{src}` | {cnt:,} |")

        lines.extend([
            "",
            "### Source Overlap Matrix",
            "| Source | " + " | ".join(f"`{s}`" for s in sources_list) + " |",
            "|---|" + "|".join(["---"] * len(sources_list)) + "|",
        ])

        for s1 in sources_list:
            row = [f"**`{s1}`**"]
            for s2 in sources_list:
                val = overlap_matrix.get(s1, {}).get(s2, 0)
                row.append(str(val))
            lines.append("| " + " | ".join(row) + " |")

        lines.extend([
            "",
            "---",
            "",
            "## 4. Full-Text Acquisition",
            "",
            f"- **Full-Text Accessible / Acquired**: {stats.get('papers_with_fulltext', 0):,}",
            f"- **Full-Text Acquisition Details**: `{stats.get('fulltext_pipeline', {})}`",
            "",
            "---",
            "",
            "## 5. Temporal Distribution (Publication Years)",
            "",
            "| Year | Paper Count |",
            "|---|---|",
        ])

        for yr, cnt in sorted(stats.get("papers_per_year", {}).items(), reverse=True):
            lines.append(f"| {yr} | {cnt:,} |")

        lines.extend([
            "",
            "---",
            "",
            "## 6. Relevance Filtering Summary",
            "",
            f"- **Criteria Mode**: `{stats.get('relevance_filtering', {}).get('filter_mode', 'N/A')}`",
            f"- **Passed Relevance Filter**: {stats.get('relevance_filtering', {}).get('passed_count', total):,}",
            f"- **Filtered Out**: {stats.get('relevance_filtering', {}).get('rejected_count', 0):,}",
            f"- **Pass Rate**: {stats.get('relevance_filtering', {}).get('pass_rate', 1.0) * 100:.2f}%",
            "",
        ])

        markdown_text = "\n".join(lines)
        return report_dict, markdown_text
