"""Hierarchical Section Detection for Scientific Documents.

Identifies numbered and unnumbered scientific sections, chapters, subsections,
and structural headers using typography analysis (font size/weight) and syntactic patterns.
Constructs a valid hierarchy without semantic or scientific interpretation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from dataset.schemas.document_processing import ProcessedSection
from pipelines.processing.extractor import PageExtractionResult, TextBlock

logger = logging.getLogger(__name__)

# Common unnumbered scientific section names
UNNUMBERED_SECTION_PATTERNS = [
    re.compile(r"^\s*abstract\s*$", re.IGNORECASE),
    re.compile(r"^\s*introduction\s*$", re.IGNORECASE),
    re.compile(r"^\s*background\s*(and\s+related\s+work)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*related\s+work\s*$", re.IGNORECASE),
    re.compile(r"^\s*(materials?\s+and\s+)?methods?\s*$", re.IGNORECASE),
    re.compile(r"^\s*methodology\s*$", re.IGNORECASE),
    re.compile(r"^\s*system\s+(architecture|overview|model)\s*$", re.IGNORECASE),
    re.compile(r"^\s*(experimental\s+)?results?(\s+and\s+discussion)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*experiments?(\s+and\s+evaluation)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*discussion\s*$", re.IGNORECASE),
    re.compile(r"^\s*conclusions?(\s+and\s+future\s+work)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*limitations?(\s+and\s+threats\s+to\s+validity)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*future\s+(work|directions?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*references?\s*$", re.IGNORECASE),
    re.compile(r"^\s*bibliography\s*$", re.IGNORECASE),
    re.compile(r"^\s*acknowledg(e)?ments?\s*$", re.IGNORECASE),
    re.compile(r"^\s*author\s+contributions?\s*$", re.IGNORECASE),
    re.compile(r"^\s*declarations?\s*$", re.IGNORECASE),
    re.compile(r"^\s*competing\s+interests?\s*$", re.IGNORECASE),
    re.compile(r"^\s*data\s+availability\s*(statement)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*appendi(x|ces)(\s+[A-Z0-9]+)?\s*$", re.IGNORECASE),
]

# Section numbering regexes
RE_CHAPTER = re.compile(r"^\s*(chapter\s+\d+[:\.]?\s*)(.+)?$", re.IGNORECASE)
RE_DECIMAL_3 = re.compile(r"^\s*(\d+\.\d+\.\d+)\.?\s+(.+)$")
RE_DECIMAL_2 = re.compile(r"^\s*(\d+\.\d+)\.?\s+(.+)$")
RE_DECIMAL_1 = re.compile(r"^\s*(\d+)\.\s+(.+)$")
RE_NUM_SPACE_1 = re.compile(r"^\s*(\d+)\s+([A-Z][A-Za-z0-9\s,\-\:]{2,80})$")
RE_ROMAN_NUM = re.compile(r"^\s*([IVXLCDM]+)\.\s+(.+)$", re.IGNORECASE)


@dataclass
class DetectedHeader:
    """Intermediate candidate section header."""
    title: str
    number: Optional[str]
    level: int  # 1=H1, 2=H2, 3=H3
    page_number: int
    block_index: int
    font_size: float
    is_bold: bool
    full_block_text: str


class SectionDetector:
    """Detects and organizes hierarchical sections from extracted pages."""

    def __init__(self, body_font_size_threshold: float = 10.5):
        self.body_font_size_threshold = body_font_size_threshold

    def detect_sections(
        self,
        pages: List[PageExtractionResult],
        canonical_id: str,
    ) -> List[ProcessedSection]:
        """Parse pages into ordered, hierarchical ProcessedSection objects."""
        headers: List[DetectedHeader] = []

        # Step 1: Scan all blocks across all pages to find section headers
        for p in pages:
            for b_idx, b in enumerate(p.blocks):
                if b.is_header_or_footer:
                    continue

                header_info = self._check_if_block_is_header(b, p.page_number, b_idx)
                if header_info:
                    headers.append(header_info)

        # If no explicit headers were detected, create a single fallback section
        if not headers:
            all_text = "\n\n".join(p.cleaned_text for p in pages if not p.is_blank).strip()
            total_words = len(all_text.split())
            return [
                ProcessedSection(
                    section_id=f"sec_{canonical_id}_01",
                    section_title="Document Body",
                    section_level=1,
                    section_number=None,
                    section_order=1,
                    parent_section_id=None,
                    start_page=1,
                    end_page=len(pages),
                    text=all_text,
                    char_count=len(all_text),
                    word_count=total_words,
                )
            ]

        # Step 2: Build section hierarchy and assign text content
        sections: List[ProcessedSection] = []
        current_h1_id: Optional[str] = None
        current_h2_id: Optional[str] = None

        # If there is content before the first detected section (e.g. title/authors),
        # create a "Front Matter / Document Header" section
        first_hdr = headers[0]
        pre_text_parts: List[str] = []
        pre_end_page = first_hdr.page_number

        for p in pages:
            if p.page_number > first_hdr.page_number:
                break
            for b_idx, b in enumerate(p.blocks):
                if b.is_header_or_footer:
                    continue
                if p.page_number == first_hdr.page_number and b_idx >= first_hdr.block_index:
                    break
                pre_text_parts.append(b.text)

        pre_text = "\n\n".join(pre_text_parts).strip()
        sec_order = 1
        if pre_text:
            pre_sec_id = f"sec_{canonical_id}_{sec_order:02d}"
            sections.append(
                ProcessedSection(
                    section_id=pre_sec_id,
                    section_title="Front Matter / Document Header",
                    section_level=1,
                    section_number=None,
                    section_order=sec_order,
                    parent_section_id=None,
                    start_page=1,
                    end_page=pre_end_page,
                    text=pre_text,
                    char_count=len(pre_text),
                    word_count=len(pre_text.split()),
                )
            )
            sec_order += 1

        # Now assemble each detected section's content up to the next section
        for h_idx, hdr in enumerate(headers):
            next_hdr = headers[h_idx + 1] if h_idx + 1 < len(headers) else None
            sec_id = f"sec_{canonical_id}_{sec_order:02d}"

            # Establish hierarchy parent link
            parent_id: Optional[str] = None
            if hdr.level == 1:
                current_h1_id = sec_id
                current_h2_id = None
                parent_id = None
            elif hdr.level == 2:
                current_h2_id = sec_id
                parent_id = current_h1_id
            elif hdr.level >= 3:
                parent_id = current_h2_id or current_h1_id

            # Collect body text for this section
            sec_text_parts: List[str] = []
            start_p = hdr.page_number
            end_p = start_p

            for p in pages:
                if p.page_number < start_p:
                    continue
                if next_hdr and p.page_number > next_hdr.page_number:
                    break

                for b_idx, b in enumerate(p.blocks):
                    if b.is_header_or_footer:
                        continue
                    # Skip blocks prior to header start on start page
                    if p.page_number == start_p and b_idx < hdr.block_index:
                        continue
                    # Skip header text line itself if block matches header
                    if p.page_number == start_p and b_idx == hdr.block_index:
                        # Extract any remaining lines in block after header title
                        lines = b.text.split("\n")
                        remaining_lines = lines[1:] if len(lines) > 1 else []
                        if remaining_lines:
                            sec_text_parts.append("\n".join(remaining_lines).strip())
                        continue
                    # Stop if we hit the next header
                    if next_hdr and p.page_number == next_hdr.page_number and b_idx >= next_hdr.block_index:
                        break

                    sec_text_parts.append(b.text)
                    end_p = max(end_p, p.page_number)

            sec_full_text = "\n\n".join(part for part in sec_text_parts if part).strip()
            total_chars = len(sec_full_text)
            total_words = len(sec_full_text.split())

            sections.append(
                ProcessedSection(
                    section_id=sec_id,
                    section_title=hdr.title,
                    section_level=hdr.level,
                    section_number=hdr.number,
                    section_order=sec_order,
                    parent_section_id=parent_id,
                    start_page=start_p,
                    end_page=max(start_p, end_p),
                    text=sec_full_text,
                    char_count=total_chars,
                    word_count=total_words,
                )
            )
            sec_order += 1

        return sections

    def _check_if_block_is_header(
        self,
        b: TextBlock,
        page_num: int,
        block_idx: int,
    ) -> Optional[DetectedHeader]:
        """Examine block typography and text patterns to detect section headers."""
        text = b.text.strip()
        if not text:
            return None

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            return None

        first_line = lines[0]
        # Ignore long lines (>120 chars) as header candidates unless explicit chapter
        if len(first_line) > 120 and not first_line.lower().startswith("chapter"):
            return None

        # 1. Chapter headers (e.g. 'Chapter 1 ...')
        m_chap = RE_CHAPTER.match(first_line)
        if m_chap:
            num = m_chap.group(1).strip()
            title = first_line.strip()
            return DetectedHeader(
                title=title,
                number=num,
                level=1,
                page_number=page_num,
                block_index=block_idx,
                font_size=b.max_font_size,
                is_bold=b.is_bold_dominant,
                full_block_text=text,
            )

        # 2. Sub-subsections: 3-level decimal numbering (e.g. '1.1.1 Dataset')
        m_dec3 = RE_DECIMAL_3.match(first_line)
        if m_dec3:
            num = m_dec3.group(1)
            title = first_line.strip()
            return DetectedHeader(
                title=title,
                number=num,
                level=3,
                page_number=page_num,
                block_index=block_idx,
                font_size=b.max_font_size,
                is_bold=b.is_bold_dominant,
                full_block_text=text,
            )

        # 3. Subsections: 2-level decimal numbering (e.g. '1.2 Methodology')
        m_dec2 = RE_DECIMAL_2.match(first_line)
        if m_dec2:
            num = m_dec2.group(1)
            title = first_line.strip()
            # Filter out table/figure decimals like 'Table 1.1' or 'Figure 2.1'
            if any(first_line.lower().startswith(pfx) for pfx in ["table", "fig", "figure", "tab."]):
                return None
            return DetectedHeader(
                title=title,
                number=num,
                level=2,
                page_number=page_num,
                block_index=block_idx,
                font_size=b.max_font_size,
                is_bold=b.is_bold_dominant,
                full_block_text=text,
            )

        # 4. Main Section: 1-level decimal numbering (e.g. '1. Introduction' or '1 Introduction')
        m_dec1 = RE_DECIMAL_1.match(first_line)
        if m_dec1:
            num = m_dec1.group(1)
            title = first_line.strip()
            if any(first_line.lower().startswith(pfx) for pfx in ["table", "fig", "figure", "tab."]):
                return None
            return DetectedHeader(
                title=title,
                number=num,
                level=1,
                page_number=page_num,
                block_index=block_idx,
                font_size=b.max_font_size,
                is_bold=b.is_bold_dominant,
                full_block_text=text,
            )

        # 5. Number space pattern (e.g. '1 Introduction' or '3 Methodology')
        m_num_sp = RE_NUM_SPACE_1.match(first_line)
        if m_num_sp and (b.is_bold_dominant or b.max_font_size > self.body_font_size_threshold or len(lines) == 1):
            num = m_num_sp.group(1)
            title = first_line.strip()
            if int(num) <= 20 and not any(first_line.lower().startswith(pfx) for pfx in ["table", "fig", "figure"]):
                return DetectedHeader(
                    title=title,
                    number=num,
                    level=1,
                    page_number=page_num,
                    block_index=block_idx,
                    font_size=b.max_font_size,
                    is_bold=b.is_bold_dominant,
                    full_block_text=text,
                )

        # 6. Roman numeral numbering (e.g. 'I. INTRODUCTION', 'II. RELATED WORK')
        m_rom = RE_ROMAN_NUM.match(first_line)
        if m_rom:
            num = m_rom.group(1)
            title = first_line.strip()
            return DetectedHeader(
                title=title,
                number=num,
                level=1,
                page_number=page_num,
                block_index=block_idx,
                font_size=b.max_font_size,
                is_bold=b.is_bold_dominant,
                full_block_text=text,
            )

        # 7. Unnumbered standard scientific sections
        clean_first = re.sub(r"[\.:\-\—]+$", "", first_line).strip()
        for pat in UNNUMBERED_SECTION_PATTERNS:
            if pat.match(clean_first):
                return DetectedHeader(
                    title=first_line.strip(),
                    number=None,
                    level=1,
                    page_number=page_num,
                    block_index=block_idx,
                    font_size=b.max_font_size,
                    is_bold=b.is_bold_dominant,
                    full_block_text=text,
                )

        # 8. Prominent bold standalone heading (typographical cue)
        if (
            len(lines) == 1
            and len(first_line) < 70
            and (b.is_bold_dominant or b.max_font_size >= 12.5)
            and not first_line.endswith((".", ",", ";"))
            and not first_line.lower().startswith(("table", "fig", "figure", "http", "doi"))
        ):
            return DetectedHeader(
                title=first_line.strip(),
                number=None,
                level=2 if b.max_font_size < 13.0 else 1,
                page_number=page_num,
                block_index=block_idx,
                font_size=b.max_font_size,
                is_bold=b.is_bold_dominant,
                full_block_text=text,
            )

        return None
