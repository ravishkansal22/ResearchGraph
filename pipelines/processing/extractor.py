"""PDF Text and Structural Extractor for Scientific Documents.

Provides robust, layout-aware extraction using PyMuPDF (fitz) with pypdf fallback.
Handles multi-column layout reordering, page boundary preservation, font styling
extraction, and repeated header/footer detection.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import pypdf

from dataset.schemas.document_processing import LayoutType, ProcessedPage

logger = logging.getLogger(__name__)


@dataclass
class TextSpan:
    """Detailed typography span within a line."""
    text: str
    size: float
    flags: int  # 2^4 = 16 (bold), 2^1 = 2 (italic), etc.
    font: str
    is_bold: bool = False
    is_italic: bool = False
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


@dataclass
class TextLine:
    """A line of text within a block."""
    text: str
    spans: List[TextSpan] = field(default_factory=list)
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    avg_font_size: float = 10.0
    is_bold: bool = False


@dataclass
class TextBlock:
    """Structural text block with bounding box coordinates and typography."""
    block_id: int
    text: str
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    lines: List[TextLine] = field(default_factory=list)
    page_number: int = 1
    max_font_size: float = 10.0
    avg_font_size: float = 10.0
    is_bold_dominant: bool = False
    is_header_or_footer: bool = False


@dataclass
class PageExtractionResult:
    """Intermediate extraction container for a single page."""
    page_number: int
    raw_text: str
    cleaned_text: str
    blocks: List[TextBlock]
    layout_type: LayoutType
    char_count: int
    word_count: int
    is_blank: bool
    headers_footers: List[str] = field(default_factory=list)


class PDFExtractor:
    """Extracts text and layout structure from scientific PDF documents."""

    def __init__(
        self,
        header_margin_ratio: float = 0.07,  # Top 7% of page considered header zone
        footer_margin_ratio: float = 0.07,  # Bottom 7% of page considered footer zone
    ):
        self.header_margin_ratio = header_margin_ratio
        self.footer_margin_ratio = footer_margin_ratio

    def extract_document(self, pdf_path: Path) -> Tuple[List[PageExtractionResult], Dict[str, Any]]:
        """Extract all pages from a PDF with layout analysis and typography metadata."""
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        parser_used = "fitz-pymupdf"
        fallback_used = None
        errors: List[str] = []

        try:
            pages, doc_stats = self._extract_with_fitz(pdf_path)
        except Exception as fitz_err:
            logger.warning(f"PyMuPDF failed on {pdf_path.name} ({fitz_err}), falling back to pypdf")
            try:
                pages, doc_stats = self._extract_with_pypdf(pdf_path)
                parser_used = "pypdf"
                fallback_used = f"pypdf (fitz failed: {fitz_err})"
            except Exception as pypdf_err:
                errors.append(f"Both fitz ({fitz_err}) and pypdf ({pypdf_err}) failed")
                raise RuntimeError(f"Failed to extract text from {pdf_path}: {errors}")

        # Document-wide repeated header/footer detection & filtering
        self._detect_and_tag_repeated_headers_footers(pages)

        meta_info = {
            "parser_used": parser_used,
            "fallback_used": fallback_used,
            "errors": errors,
            "total_pages": len(pages),
            "doc_stats": doc_stats,
        }
        return pages, meta_info

    def _extract_with_fitz(self, pdf_path: Path) -> Tuple[List[PageExtractionResult], Dict[str, Any]]:
        doc = fitz.open(pdf_path)
        pages: List[PageExtractionResult] = []

        for p_idx in range(len(doc)):
            page = doc[p_idx]
            p_num = p_idx + 1
            page_width = page.rect.width
            page_height = page.rect.height

            page_dict = page.get_text("dict")
            raw_blocks = page_dict.get("blocks", [])

            extracted_blocks: List[TextBlock] = []
            block_idx = 0

            for raw_b in raw_blocks:
                if raw_b.get("type") != 0:  # 0 is text block, 1 is image
                    continue

                bbox = tuple(raw_b.get("bbox", (0, 0, 0, 0)))
                lines_data = raw_b.get("lines", [])
                text_lines: List[TextLine] = []
                all_spans: List[TextSpan] = []
                block_text_parts: List[str] = []

                for l_data in lines_data:
                    line_spans: List[TextSpan] = []
                    line_text_parts: List[str] = []
                    for s_data in l_data.get("spans", []):
                        stext = s_data.get("text", "")
                        if not stext:
                            continue
                        size = float(s_data.get("size", 10.0))
                        flags = int(s_data.get("flags", 0))
                        font = str(s_data.get("font", ""))
                        is_bold = bool(flags & 2**4) or ("bold" in font.lower()) or ("black" in font.lower())
                        is_italic = bool(flags & 2**1) or ("italic" in font.lower()) or ("oblique" in font.lower())
                        s_bbox = tuple(s_data.get("bbox", (0, 0, 0, 0)))

                        span_obj = TextSpan(
                            text=stext,
                            size=size,
                            flags=flags,
                            font=font,
                            is_bold=is_bold,
                            is_italic=is_italic,
                            bbox=s_bbox,
                        )
                        line_spans.append(span_obj)
                        all_spans.append(span_obj)
                        line_text_parts.append(stext)

                    line_str = "".join(line_text_parts).strip()
                    if line_str:
                        avg_sz = sum(s.size for s in line_spans) / max(1, len(line_spans))
                        line_is_bold = any(s.is_bold for s in line_spans)
                        text_lines.append(
                            TextLine(
                                text=line_str,
                                spans=line_spans,
                                bbox=tuple(l_data.get("bbox", (0, 0, 0, 0))),
                                avg_font_size=avg_sz,
                                is_bold=line_is_bold,
                            )
                        )
                        block_text_parts.append(line_str)

                full_b_text = "\n".join(block_text_parts).strip()
                if not full_b_text:
                    continue

                max_sz = max((s.size for s in all_spans), default=10.0)
                avg_sz = sum(s.size for s in all_spans) / max(1, len(all_spans))
                bold_spans = sum(1 for s in all_spans if s.is_bold)
                is_bold_dom = (bold_spans / max(1, len(all_spans))) > 0.5

                tb = TextBlock(
                    block_id=block_idx,
                    text=full_b_text,
                    bbox=bbox,
                    lines=text_lines,
                    page_number=p_num,
                    max_font_size=max_sz,
                    avg_font_size=avg_sz,
                    is_bold_dominant=is_bold_dom,
                )
                extracted_blocks.append(tb)
                block_idx += 1

            # Detect layout topology & sort reading order
            layout_type, ordered_blocks = self._order_blocks_for_reading(
                extracted_blocks, page_width, page_height
            )

            page_raw_text = "\n\n".join(b.text for b in ordered_blocks)
            char_count = len(page_raw_text)
            word_count = len(page_raw_text.split())
            is_blank = (char_count == 0)

            pages.append(
                PageExtractionResult(
                    page_number=p_num,
                    raw_text=page_raw_text,
                    cleaned_text=page_raw_text,
                    blocks=ordered_blocks,
                    layout_type=layout_type,
                    char_count=char_count,
                    word_count=word_count,
                    is_blank=is_blank,
                )
            )

        doc.close()
        return pages, {"page_count": len(pages)}

    def _extract_with_pypdf(self, pdf_path: Path) -> Tuple[List[PageExtractionResult], Dict[str, Any]]:
        reader = pypdf.PdfReader(str(pdf_path))
        pages: List[PageExtractionResult] = []

        for p_idx, page in enumerate(reader.pages):
            p_num = p_idx + 1
            raw_text = page.extract_text() or ""
            char_count = len(raw_text)
            word_count = len(raw_text.split())
            is_blank = (char_count == 0)

            # Create simple block representation
            blocks: List[TextBlock] = []
            paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
            for b_idx, p_txt in enumerate(paragraphs):
                tb = TextBlock(
                    block_id=b_idx,
                    text=p_txt,
                    bbox=(0.0, float(b_idx * 50), 500.0, float(b_idx * 50 + 40)),
                    lines=[TextLine(text=p_txt)],
                    page_number=p_num,
                )
                blocks.append(tb)

            pages.append(
                PageExtractionResult(
                    page_number=p_num,
                    raw_text=raw_text,
                    cleaned_text=raw_text,
                    blocks=blocks,
                    layout_type=LayoutType.SINGLE_COLUMN,
                    char_count=char_count,
                    word_count=word_count,
                    is_blank=is_blank,
                )
            )

        return pages, {"page_count": len(pages)}

    def _order_blocks_for_reading(
        self,
        blocks: List[TextBlock],
        page_width: float,
        page_height: float,
    ) -> Tuple[LayoutType, List[TextBlock]]:
        """Sort blocks into correct reading order handling 1-column and 2-column layouts."""
        if not blocks:
            return LayoutType.SINGLE_COLUMN, []

        midpoint = page_width / 2.0
        left_col_threshold = midpoint - 15.0
        right_col_threshold = midpoint + 15.0

        # Classify blocks into full-width top, left column, right column, full-width bottom
        left_blocks: List[TextBlock] = []
        right_blocks: List[TextBlock] = []
        full_width_top: List[TextBlock] = []
        full_width_bottom: List[TextBlock] = []

        is_two_col = False
        left_count = 0
        right_count = 0

        for b in blocks:
            x0, y0, x1, y1 = b.bbox
            width = x1 - x0

            # Block is clearly spanning both columns if width > 65% of page
            if width > (page_width * 0.65) or (x0 < page_width * 0.3 and x1 > page_width * 0.7):
                if y0 < page_height * 0.4:
                    full_width_top.append(b)
                else:
                    full_width_bottom.append(b)
            elif x1 <= left_col_threshold + 50.0 and x0 < midpoint:
                left_blocks.append(b)
                left_count += 1
            elif x0 >= right_col_threshold - 50.0 and x1 > midpoint:
                right_blocks.append(b)
                right_count += 1
            else:
                # Ambiguous / centered block
                if x0 < midpoint:
                    left_blocks.append(b)
                else:
                    right_blocks.append(b)

        # Determine if page is genuinely two-column
        if left_count >= 2 and right_count >= 2:
            is_two_col = True

        if is_two_col:
            # Sort top full-width blocks by vertical position y0
            full_width_top.sort(key=lambda b: b.bbox[1])
            # Sort left column top to bottom
            left_blocks.sort(key=lambda b: b.bbox[1])
            # Sort right column top to bottom
            right_blocks.sort(key=lambda b: b.bbox[1])
            # Sort bottom full-width blocks by vertical position y0
            full_width_bottom.sort(key=lambda b: b.bbox[1])

            ordered = full_width_top + left_blocks + right_blocks + full_width_bottom
            layout = LayoutType.TWO_COLUMN
        else:
            # Standard single column top-to-bottom sorting
            ordered = sorted(blocks, key=lambda b: b.bbox[1])
            layout = LayoutType.SINGLE_COLUMN

        # Re-index block IDs
        for idx, b in enumerate(ordered):
            b.block_id = idx

        return layout, ordered

    def _detect_and_tag_repeated_headers_footers(self, pages: List[PageExtractionResult]) -> None:
        """Identify repeated running headers and footers across 3+ pages and tag them."""
        if len(pages) < 2:
            return

        header_lines: Dict[str, int] = {}
        footer_lines: Dict[str, int] = {}

        # Collect candidate lines from top and bottom blocks
        for p in pages:
            if not p.blocks:
                continue
            for b in p.blocks:
                y0 = b.bbox[1]
                # Check if block is near top or bottom
                first_line = b.lines[0].text.strip() if b.lines else b.text.split("\n")[0].strip()
                if len(first_line) > 5 and len(first_line) < 120:
                    normalized = re.sub(r"\b\d+\b", "#", first_line).strip()
                    if y0 < 80:
                        header_lines[normalized] = header_lines.get(normalized, 0) + 1
                    elif y0 > 700:
                        footer_lines[normalized] = footer_lines.get(normalized, 0) + 1

        repeated_headers = {k for k, count in header_lines.items() if count >= 2}
        repeated_footers = {k for k, count in footer_lines.items() if count >= 2}

        for p in pages:
            detected_for_page = []
            cleaned_blocks = []
            for b in p.blocks:
                first_line = b.lines[0].text.strip() if b.lines else b.text.split("\n")[0].strip()
                normalized = re.sub(r"\b\d+\b", "#", first_line).strip()
                if normalized in repeated_headers or normalized in repeated_footers:
                    b.is_header_or_footer = True
                    detected_for_page.append(first_line)
                else:
                    cleaned_blocks.append(b)

            p.headers_footers = detected_for_page
            # Update cleaned text without headers/footers
            p.cleaned_text = "\n\n".join(b.text for b in cleaned_blocks)
