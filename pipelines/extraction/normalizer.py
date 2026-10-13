"""Conservative Scientific Knowledge Normalizer.

Standardizes surface strings and statements without altering their technical
meaning, epistemic modalities (e.g. 'may', 'suggests'), or negative polarities.
"""

from __future__ import annotations

import re
from typing import Optional

# Regex for stripping structural list bullets and numberings from start of lines
RE_LEADING_BULLET = re.compile(r"^(\s*[\-\*\•\–\—]\s*|\s*\d+[\.\)]\s*|\s*\([a-zA-Z0-9]+\)\s*)+")
# Regex for redundant whitespace
RE_MULTI_WHITESPACE = re.compile(r"\s+")
# Regex for trailing punctuation that shouldn't belong to entity names
RE_TRAILING_PUNCT = re.compile(r"[\s\.,;:!?\)]+$")
# Regex for leading punctuation
RE_LEADING_PUNCT = re.compile(r"^[\s\.,;:!?\(\[]+")

# Preserved scientific acronyms that should maintain exact uppercase casing
ACRONYM_ALLOWLIST = {
    "CNN", "RNN", "LSTM", "GRU", "BERT", "GPT", "SVM", "KNN", "GAN", "VAE",
    "RL", "DRL", "NLP", "ML", "AI", "DL", "LLM", "GNN", "Transformer",
    "SGD", "Adam", "AUC", "ROC", "MSE", "RMSE", "MAE", "F1", "FPR", "TPR",
    "IoT", "IDS", "NIDS", "API", "CPU", "GPU", "TPU", "RAM", "NSL-KDD",
    "CICIDS2017", "UNSW-NB15", "KDD99", "MNIST", "ImageNet", "MIMIC-III",
}


class ScientificNormalizer:
    """Conservative normalizer for scientific entities and statements."""

    @staticmethod
    def normalize_entity_name(surface_text: str) -> str:
        """Conservatively normalize entity surface text.

        Removes leading bullets, surrounding punctuation, and redundant whitespace,
        while strictly preserving casing of technical acronyms and scientific terms.
        """
        if not surface_text:
            return ""

        # 1. Strip leading bullets
        cleaned = RE_LEADING_BULLET.sub("", surface_text.strip())
        # 2. Collapse internal whitespace
        cleaned = RE_MULTI_WHITESPACE.sub(" ", cleaned).strip()
        # 3. Iteratively strip leading/trailing quotes, brackets, and punctuation
        prev = None
        while cleaned != prev:
            prev = cleaned
            cleaned = re.sub(r"^[\s\.,;:!?\"\'`\(\[\{]+", "", cleaned)
            cleaned = re.sub(r"[\s\.,;:!?\"\'`\)\]\}]+$", "", cleaned)

        # Check if entire term matches a known acronym with minor casing variations
        cleaned_upper = cleaned.upper()
        if cleaned_upper in ACRONYM_ALLOWLIST:
            return cleaned_upper

        return cleaned

    @staticmethod
    def normalize_statement_text(statement_text: str) -> str:
        """Conservatively clean up statement string.

        Collapses whitespace, removes leading bullets, but preserves all modal
        hedges, epistemic markers, and negative polarities.
        """
        if not statement_text:
            return ""

        # 1. Strip leading list bullets/numbers
        cleaned = RE_LEADING_BULLET.sub("", statement_text.strip())
        # 2. Collapse whitespace
        cleaned = RE_MULTI_WHITESPACE.sub(" ", cleaned).strip()
        # 3. Ensure sentence terminates with period if not already punctuated
        if cleaned and cleaned[-1] not in ".!?":
            cleaned = f"{cleaned}."

        return cleaned

    @staticmethod
    def extract_evidence_span(chunk_text: str, target_phrase: str) -> Optional[tuple[int, int]]:
        """Locate exact or fuzzy character offsets for a given phrase within chunk text."""
        if not chunk_text or not target_phrase:
            return None

        # Exact substring search first
        idx = chunk_text.find(target_phrase)
        if idx != -1:
            return idx, idx + len(target_phrase)

        # Case-insensitive search fallback
        target_lower = target_phrase.lower()
        chunk_lower = chunk_text.lower()
        idx_lower = chunk_lower.find(target_lower)
        if idx_lower != -1:
            return idx_lower, idx_lower + len(target_phrase)

        # Whitespace-collapsed search fallback
        norm_target = RE_MULTI_WHITESPACE.sub(" ", target_phrase).strip()
        idx_norm = chunk_text.find(norm_target)
        if idx_norm != -1:
            return idx_norm, idx_norm + len(norm_target)

        return None
