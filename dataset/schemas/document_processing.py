"""ResearchGraph Phase 2: Document Processing Pilot Schemas.

Defines the structured, provenance-preserving document representation
for scientific papers extracted from PDFs (Schema Version 0.2.0).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    """Execution status of document processing."""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    NOT_PROCESSED = "NOT_PROCESSED"


class ChunkStrategy(str, Enum):
    """Chunking strategy identifier."""
    STRATEGY_A_PARAGRAPH = "STRATEGY_A_PARAGRAPH"
    STRATEGY_B_STRUCTURE_FIXED = "STRATEGY_B_STRUCTURE_FIXED"


class LayoutType(str, Enum):
    """Detected page layout topology."""
    SINGLE_COLUMN = "SINGLE_COLUMN"
    TWO_COLUMN = "TWO_COLUMN"
    MULTI_COLUMN = "MULTI_COLUMN"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class ProcessedSentence(BaseModel):
    """Sentence-level segmented unit with provenance."""
    sentence_id: str = Field(..., description="Unique sentence ID (e.g. s_rg_xxx_p1_1)")
    paragraph_id: str = Field(..., description="ID of parent paragraph")
    sentence_order: int = Field(..., description="1-indexed sentence position within paragraph")
    text: str = Field(..., description="Sentence text content")
    char_count: int = Field(default=0, description="Character count")
    word_count: int = Field(default=0, description="Word count")


class ProcessedParagraph(BaseModel):
    """Paragraph-level unit with complete document provenance."""
    paragraph_id: str = Field(..., description="Unique paragraph ID (e.g. p_rg_xxx_001)")
    canonical_id: str = Field(..., description="Canonical paper identifier")
    section_id: str = Field(..., description="ID of containing section")
    section_title: str = Field(..., description="Title of containing section")
    page_number: int = Field(..., description="1-indexed page where paragraph begins")
    paragraph_order: int = Field(..., description="1-indexed order within document")
    text: str = Field(..., description="Paragraph text content")
    char_count: int = Field(default=0, description="Character count")
    word_count: int = Field(default=0, description="Word count")
    sentence_count: int = Field(default=0, description="Number of segmented sentences")
    sentences: List[ProcessedSentence] = Field(default_factory=list, description="Child sentences if segmented")


class ProcessedSection(BaseModel):
    """Hierarchical structural section within the scientific document."""
    section_id: str = Field(..., description="Unique section ID (e.g. sec_rg_xxx_01)")
    section_title: str = Field(..., description="Extracted section heading title")
    section_level: int = Field(default=1, description="Hierarchy level: 1=top (H1), 2=subsection (H2), 3=sub-sub (H3)")
    section_number: Optional[str] = Field(default=None, description="Extracted section number (e.g. '1', '1.2', 'III')")
    section_order: int = Field(..., description="1-indexed appearance order in document")
    parent_section_id: Optional[str] = Field(default=None, description="Parent section ID for nested hierarchy")
    start_page: int = Field(..., description="Page where section starts")
    end_page: int = Field(..., description="Page where section ends")
    text: str = Field(default="", description="Full aggregated text belonging to section")
    paragraph_count: int = Field(default=0, description="Number of paragraphs in section")
    char_count: int = Field(default=0, description="Total characters in section")
    word_count: int = Field(default=0, description="Total words in section")
    paragraph_ids: List[str] = Field(default_factory=list, description="Ordered list of contained paragraph IDs")


class ProcessedPage(BaseModel):
    """Extracted page-level container."""
    page_number: int = Field(..., description="1-indexed page number")
    text: str = Field(default="", description="Raw extracted text of page")
    char_count: int = Field(default=0, description="Extracted character count")
    word_count: int = Field(default=0, description="Extracted word count")
    block_count: int = Field(default=0, description="Extracted text block count")
    is_blank: bool = Field(default=False, description="True if page yielded zero extractable text")
    layout_type: LayoutType = Field(default=LayoutType.UNKNOWN, description="Detected column layout")
    headers_footers_detected: List[str] = Field(default_factory=list, description="Detected repetitive header/footer lines")


class ProcessedChunk(BaseModel):
    """Traceable, structure-aware document chunk for downstream retrieval/analysis."""
    chunk_id: str = Field(..., description="Unique chunk ID (e.g. chk_rg_xxx_A_001)")
    canonical_id: str = Field(..., description="Canonical paper identifier")
    section_id: str = Field(..., description="Containing section identifier")
    section_title: str = Field(..., description="Containing section heading")
    section_level: int = Field(default=1, description="Section hierarchy level")
    page_start: int = Field(..., description="Starting page number")
    page_end: int = Field(..., description="Ending page number")
    paragraph_start_order: int = Field(..., description="First paragraph order included")
    paragraph_end_order: int = Field(..., description="Last paragraph order included")
    paragraph_ids: List[str] = Field(default_factory=list, description="IDs of paragraphs spanned")
    text: str = Field(..., description="Chunk text content")
    char_count: int = Field(default=0, description="Character count")
    word_count: int = Field(default=0, description="Word count")
    token_count_est: int = Field(default=0, description="Estimated token count (approx. words * 1.3)")
    strategy: ChunkStrategy = Field(..., description="Chunking strategy used")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Complete provenance metadata dictionary")


class DocumentMetadata(BaseModel):
    """Identity and source metadata preserved from Phase 1 canonical dataset."""
    canonical_id: str = Field(..., description="Unique canonical paper identifier")
    title: str = Field(..., description="Paper title")
    doi: Optional[str] = Field(default=None, description="Digital Object Identifier")
    source: str = Field(..., description="Scholarly source (e.g. openalex)")
    source_url: Optional[str] = Field(default=None, description="Original source / acquisition URL")
    local_pdf_path: str = Field(..., description="Relative local path to PDF file")
    file_hash: str = Field(..., description="SHA-256 cryptographic checksum of input PDF")
    file_size_bytes: int = Field(default=0, description="Size of PDF in bytes")
    document_type: Optional[str] = Field(default=None, description="Classified document type from Phase 1")


class DocumentProcessingMetadata(BaseModel):
    """Audit and diagnostic metadata for document processing execution."""
    processor_version: str = Field(default="v0.2.0", description="Pipeline processor version")
    processing_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of execution",
    )
    parser_used: str = Field(default="fitz-pymupdf", description="Primary parser library used")
    fallback_parser: Optional[str] = Field(default=None, description="Fallback parser if primary failed")
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.SUCCESS, description="Execution status")
    processing_errors: List[str] = Field(default_factory=list, description="Encountered non-fatal warnings or errors")
    page_count: int = Field(default=0, description="Total physical pages in PDF")
    extracted_page_count: int = Field(default=0, description="Pages yielding text")
    empty_page_count: int = Field(default=0, description="Pages with no extractable text")
    character_count: int = Field(default=0, description="Total characters extracted")
    word_count: int = Field(default=0, description="Total words extracted")
    section_count: int = Field(default=0, description="Number of detected sections")
    paragraph_count: int = Field(default=0, description="Number of extracted paragraphs")
    sentence_count: int = Field(default=0, description="Number of segmented sentences")
    chunk_count_strategy_a: int = Field(default=0, description="Chunks generated by Strategy A (Paragraph-based)")
    chunk_count_strategy_b: int = Field(default=0, description="Chunks generated by Strategy B (Structure Fixed-size)")
    processing_duration_ms: float = Field(default=0.0, description="Processing time in milliseconds")
    layout_detected: LayoutType = Field(default=LayoutType.UNKNOWN, description="Predominant layout topology")
    headers_footers_suppressed_count: int = Field(default=0, description="Number of repeated header/footer lines filtered")


class ProcessedDocument(BaseModel):
    """Complete structured machine-readable document representation (Schema v0.2.0)."""
    document_id: str = Field(..., description="Unique document processing identifier (e.g. doc_rg_xxx)")
    canonical_id: str = Field(..., description="Canonical paper identifier")
    metadata: DocumentMetadata = Field(..., description="Preserved identity and source metadata")
    processing: DocumentProcessingMetadata = Field(..., description="Diagnostic and execution metadata")
    pages: List[ProcessedPage] = Field(default_factory=list, description="Extracted page-level contents")
    sections: List[ProcessedSection] = Field(default_factory=list, description="Extracted hierarchical sections")
    paragraphs: List[ProcessedParagraph] = Field(default_factory=list, description="Extracted provenance-preserving paragraphs")
    chunks: List[ProcessedChunk] = Field(default_factory=list, description="Primary chunks (recommended strategy)")
    chunks_strategy_a: List[ProcessedChunk] = Field(default_factory=list, description="Chunks generated via Strategy A")
    chunks_strategy_b: List[ProcessedChunk] = Field(default_factory=list, description="Chunks generated via Strategy B")
