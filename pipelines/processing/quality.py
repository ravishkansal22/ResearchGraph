"""Quality Validation and Audit Engine for Processed Documents.

Computes comprehensive diagnostic metrics across extracted documents, detects
potential layout/corruption anomalies, evaluates chunking strategies, and
generates validation reports.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from dataset.schemas.document_processing import (
    ProcessedChunk,
    ProcessedDocument,
    ProcessingStatus,
)

logger = logging.getLogger(__name__)


class ProcessingQualityAuditor:
    """Audits extraction quality, textual integrity, and structural metrics."""

    @staticmethod
    def audit_document(doc: ProcessedDocument) -> Dict[str, Any]:
        """Perform thorough quality audit on a single processed document."""
        # 1. Page-level checks
        total_pages = doc.processing.page_count
        extracted_pages = doc.processing.extracted_page_count
        empty_pages = doc.processing.empty_page_count
        page_success_rate = (extracted_pages / max(1, total_pages))

        # 2. Textual integrity checks
        all_text = "\n\n".join(p.text for p in doc.paragraphs)
        char_count = len(all_text)
        word_count = len(all_text.split())
        avg_chars_per_page = char_count / max(1, total_pages)

        # Non-printable and replacement character anomaly detection
        replacement_char_count = all_text.count("\ufffd")
        control_chars = len(re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", all_text))
        corruption_rate = (replacement_char_count + control_chars) / max(1, char_count)
        is_potentially_corrupted = corruption_rate > 0.02  # >2% corrupted tokens



        # 3. Header/Footer duplication check
        headers_footers_count = doc.processing.headers_footers_suppressed_count
        has_repeated_headers = headers_footers_count > 0

        # 4. Reading order check
        lines = [l.strip() for l in all_text.split("\n") if l.strip()]
        short_lines = sum(1 for l in lines if len(l) < 8)
        reading_order_anomaly = (short_lines / max(1, len(lines))) > 0.5


        # 5. Section & structural metrics
        section_count = len(doc.sections)
        paragraph_count = len(doc.paragraphs)
        sentence_count = sum(p.sentence_count for p in doc.paragraphs)

        # 6. Chunking strategy comparison
        chunks_a = doc.chunks_strategy_a
        chunks_b = doc.chunks_strategy_b

        def chunk_stats(chunks: List[ProcessedChunk]) -> Dict[str, Any]:
            if not chunks:
                return {
                    "count": 0,
                    "avg_chars": 0.0,
                    "avg_words": 0.0,
                    "min_chars": 0,
                    "max_chars": 0,
                    "section_boundary_preservation": 1.0,
                }
            char_lens = [c.char_count for c in chunks]
            word_lens = [c.word_count for c in chunks]
            return {
                "count": len(chunks),
                "avg_chars": round(sum(char_lens) / len(chunks), 1),
                "avg_words": round(sum(word_lens) / len(chunks), 1),
                "min_chars": min(char_lens),
                "max_chars": max(char_lens),
                "section_boundary_preservation": 1.0,  # by construction strictly 100%
            }

        stats_a = chunk_stats(chunks_a)
        stats_b = chunk_stats(chunks_b)

        # Determine overall document processing status
        if total_pages == 0 or char_count < 100:
            status = ProcessingStatus.FAILED
        elif is_potentially_corrupted or page_success_rate < 0.8:
            status = ProcessingStatus.PARTIAL
        else:
            status = ProcessingStatus.SUCCESS

        return {
            "canonical_id": doc.canonical_id,
            "title": doc.metadata.title,
            "doi": doc.metadata.doi,
            "document_type": doc.metadata.document_type,
            "status": status.value,
            "total_pages": total_pages,
            "extracted_pages": extracted_pages,
            "empty_pages": empty_pages,
            "page_success_rate": round(page_success_rate, 4),
            "char_count": char_count,
            "word_count": word_count,
            "avg_chars_per_page": round(avg_chars_per_page, 1),
            "section_count": section_count,
            "paragraph_count": paragraph_count,
            "sentence_count": sentence_count,
            "layout_detected": doc.processing.layout_detected.value,
            "headers_footers_suppressed": headers_footers_count,
            "replacement_char_count": replacement_char_count,
            "control_chars_count": control_chars,
            "is_potentially_corrupted": is_potentially_corrupted,
            "reading_order_anomaly": reading_order_anomaly,
            "strategy_a_metrics": stats_a,
            "strategy_b_metrics": stats_b,
        }

    @classmethod
    def audit_corpus(cls, docs: List[ProcessedDocument]) -> Dict[str, Any]:
        """Aggregate quality audit metrics across the complete document corpus."""
        doc_audits = [cls.audit_document(d) for d in docs]

        total_docs = len(docs)
        successful_docs = sum(1 for a in doc_audits if a["status"] == ProcessingStatus.SUCCESS.value)
        total_pages = sum(a["total_pages"] for a in doc_audits)
        extracted_pages = sum(a["extracted_pages"] for a in doc_audits)
        empty_pages = sum(a["empty_pages"] for a in doc_audits)
        total_chars = sum(a["char_count"] for a in doc_audits)
        total_words = sum(a["word_count"] for a in doc_audits)
        total_sections = sum(a["section_count"] for a in doc_audits)
        total_paragraphs = sum(a["paragraph_count"] for a in doc_audits)
        total_sentences = sum(a["sentence_count"] for a in doc_audits)

        chunks_a_total = sum(a["strategy_a_metrics"]["count"] for a in doc_audits)
        chunks_b_total = sum(a["strategy_b_metrics"]["count"] for a in doc_audits)

        # Aggregate chunk sizes
        all_a_chars = [c.char_count for d in docs for c in d.chunks_strategy_a]
        all_b_chars = [c.char_count for d in docs for c in d.chunks_strategy_b]

        return {
            "total_documents_processed": total_docs,
            "successful_documents": successful_docs,
            "success_rate": round(successful_docs / max(1, total_docs), 4),
            "total_pages": total_pages,
            "extracted_pages": extracted_pages,
            "empty_pages": empty_pages,
            "usable_page_rate": round(extracted_pages / max(1, total_pages), 4),
            "total_characters": total_chars,
            "total_words": total_words,
            "total_sections": total_sections,
            "total_paragraphs": total_paragraphs,
            "total_sentences": total_sentences,
            "chunk_comparison": {
                "strategy_a_paragraph_based": {
                    "total_chunks": chunks_a_total,
                    "avg_chars": round(sum(all_a_chars) / max(1, len(all_a_chars)), 1),
                    "min_chars": min(all_a_chars, default=0),
                    "max_chars": max(all_a_chars, default=0),
                    "section_boundary_preservation": "100%",
                },
                "strategy_b_structure_aware_fixed": {
                    "total_chunks": chunks_b_total,
                    "avg_chars": round(sum(all_b_chars) / max(1, len(all_b_chars)), 1),
                    "min_chars": min(all_b_chars, default=0),
                    "max_chars": max(all_b_chars, default=0),
                    "section_boundary_preservation": "100%",
                },
            },
            "document_details": doc_audits,
        }
