"""ResearchGraph Phase 2: 50-Paper Processing Pipeline Runner (v0.3.0)."""

import sys
import time
from pathlib import Path

# Add project root to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from pipelines.processing.pipeline import DocumentProcessingPipeline


def main():
    print("=" * 70)
    print("ResearchGraph Phase 2: 50-Paper Expansion Pipeline Execution (v0.3.0)")
    print("=" * 70)

    t0 = time.time()
    pipeline = DocumentProcessingPipeline(processor_version="v0.3.0")
    
    docs, audit = pipeline.run_pipeline()
    t_elapsed = time.time() - t0

    print("=" * 70)
    print(f"PIPELINE RUN COMPLETE in {t_elapsed:.2f} seconds!")
    print(f"Total Documents: {len(docs)}")
    print(f"Successful: {audit['successful_documents']} / {len(docs)} ({audit['success_rate']*100:.1f}%)")
    print(f"Total Pages Detected: {audit['total_pages']}")
    print(f"Extracted Pages with Usable Text: {audit['extracted_pages']} ({audit['usable_page_rate']}%)")
    print(f"Total Characters: {audit['total_characters']:,}")
    print(f"Total Words: {audit['total_words']:,}")
    print(f"Total Sections: {audit['total_sections']:,}")
    print(f"Total Paragraphs: {audit['total_paragraphs']:,}")
    print(f"Total Sentences: {audit['total_sentences']:,}")
    print(f"Strategy A Chunks: {audit['chunk_comparison']['strategy_a_paragraph_based']['total_chunks']:,}")
    print(f"Strategy B Chunks: {audit['chunk_comparison']['strategy_b_structure_aware_fixed']['total_chunks']:,}")
    print("=" * 70)


if __name__ == "__main__":
    main()
