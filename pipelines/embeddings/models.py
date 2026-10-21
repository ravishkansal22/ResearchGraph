"""ResearchGraph Phase 5: Semantic Embedding Model Registry & Encoders.

Defines candidate embedding configurations across:
1. General-purpose sentence embeddings (e.g. all-MiniLM-L6-v2).
2. Scientific-domain embeddings (e.g. scibert, S-PubMedBert).
3. Retrieval-oriented embeddings (e.g. bge-small-en-v1.5).
4. Deterministic Latent Semantic Analysis baseline (tfidf-lsa-384) for reproducible offline execution.
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


def compute_text_hash(text: str) -> str:
    """Calculate deterministic SHA-256 hash of source text."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


class ModelCategory(str, Enum):
    """Categorization of candidate embedding models."""
    GENERAL_PURPOSE = "GENERAL_PURPOSE"
    SCIENTIFIC_DOMAIN = "SCIENTIFIC_DOMAIN"
    RETRIEVAL_ORIENTED = "RETRIEVAL_ORIENTED"
    DETERMINISTIC_LSA = "DETERMINISTIC_LSA"


@dataclass
class EmbeddingModelSpec:
    """Formal specification and resource requirements for an embedding model."""
    model_name: str
    category: ModelCategory
    dimension: int
    revision: str = "main"
    max_seq_length: int = 512
    requires_query_instruction: bool = False
    query_instruction: str = ""
    license: str = "Apache-2.0"
    memory_mb_est: float = 120.0
    description: str = ""


MODEL_REGISTRY: Dict[str, EmbeddingModelSpec] = {
    "tfidf-lsa-384": EmbeddingModelSpec(
        model_name="tfidf-lsa-384",
        category=ModelCategory.DETERMINISTIC_LSA,
        dimension=384,
        revision="v1.0",
        max_seq_length=1024,
        requires_query_instruction=False,
        license="MIT",
        memory_mb_est=25.0,
        description="Deterministic, reproducible Latent Semantic Analysis baseline on TF-IDF representation.",
    ),
    "all-MiniLM-L6-v2": EmbeddingModelSpec(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        category=ModelCategory.GENERAL_PURPOSE,
        dimension=384,
        revision="e4ce9877abf3ed58a0873815be7a1827",
        max_seq_length=256,
        requires_query_instruction=False,
        license="Apache-2.0",
        memory_mb_est=90.0,
        description="Lightweight, fast general-purpose sentence transformer for semantic similarity.",
    ),
    "bge-small-en-v1.5": EmbeddingModelSpec(
        model_name="BAAI/bge-small-en-v1.5",
        category=ModelCategory.RETRIEVAL_ORIENTED,
        dimension=384,
        revision="5c38ec7c405ec4b44b94cc5a4bb",
        max_seq_length=512,
        requires_query_instruction=True,
        query_instruction="Represent this sentence for searching relevant passages: ",
        license="MIT",
        memory_mb_est=130.0,
        description="Retrieval-optimized dense bi-encoder with query instruction support.",
    ),
    "scibert-nli": EmbeddingModelSpec(
        model_name="pritamdeka/S-PubMedBert-MS-MARCO",
        category=ModelCategory.SCIENTIFIC_DOMAIN,
        dimension=768,
        revision="d5c5f4702b8045f94d4d2938",
        max_seq_length=512,
        requires_query_instruction=False,
        license="Apache-2.0",
        memory_mb_est=420.0,
        description="Biomedical and scientific domain-adapted transformer tuned on passage ranking.",
    ),
}


class BaseEmbeddingEncoder(ABC):
    """Abstract interface for scientific passage and concept encoders."""

    @abstractmethod
    def encode(self, texts: List[str], is_query: bool = False) -> np.ndarray:
        """Encode a list of text strings into an (N, D) normalized numpy array."""
        pass

    @property
    @abstractmethod
    def spec(self) -> EmbeddingModelSpec:
        """Model specification details."""
        pass


class DeterministicLSAEncoder(BaseEmbeddingEncoder):
    """Deterministic, reproducible Latent Semantic Analysis baseline encoder.
    
    Fits a TF-IDF vectorizer + TruncatedSVD to project texts into a dense semantic space.
    Requires no GPU or external network downloads, guaranteeing reproducible tests.
    """

    def __init__(self, dimension: int = 384, random_state: int = 42):
        self._spec = MODEL_REGISTRY["tfidf-lsa-384"]
        self.dimension = dimension
        self.random_state = random_state
        self._vectorizer = None
        self._svd = None
        self._fitted = False

    @property
    def spec(self) -> EmbeddingModelSpec:
        return self._spec

    def fit(self, texts: List[str]) -> DeterministicLSAEncoder:
        """Fit the vectorizer and projection matrix on a corpus of text passages."""
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer

        clean_texts = [t.strip() for t in texts if t and len(t.strip()) > 3]
        if not clean_texts:
            clean_texts = ["scientific research literature evidence methodology"]

        max_features = min(5000, max(500, len(clean_texts) * 5))
        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, 2),
            max_features=max_features,
            min_df=1,
        )
        tfidf_matrix = self._vectorizer.fit_transform(clean_texts)

        n_components = min(self.dimension, tfidf_matrix.shape[1] - 1, tfidf_matrix.shape[0] - 1)
        n_components = max(2, n_components)

        self._svd = TruncatedSVD(n_components=n_components, random_state=self.random_state)
        self._svd.fit(tfidf_matrix)
        self._fitted = True
        return self

    def encode(self, texts: List[str], is_query: bool = False) -> np.ndarray:
        """Encode texts into L2-normalized vector space."""
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)

        if not self._fitted or self._vectorizer is None or self._svd is None:
            self.fit(texts)

        tfidf = self._vectorizer.transform(texts)
        reduced = self._svd.transform(tfidf)

        # Pad to self.dimension if n_components < dimension
        N, D = reduced.shape
        if D < self.dimension:
            padded = np.zeros((N, self.dimension), dtype=np.float32)
            padded[:, :D] = reduced
            reduced = padded

        # L2 normalization
        norms = np.linalg.norm(reduced, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        normalized = (reduced / norms).astype(np.float32)
        return normalized


class SentenceTransformerEncoder(BaseEmbeddingEncoder):
    """Encoder backed by sentence-transformers library for pre-trained neural embeddings."""

    def __init__(self, model_key: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        if model_key not in MODEL_REGISTRY:
            raise KeyError(f"Unknown model key {model_key}. Available: {list(MODEL_REGISTRY.keys())}")
        self._spec = MODEL_REGISTRY[model_key]
        self.device = device
        self._model = None

    @property
    def spec(self) -> EmbeddingModelSpec:
        return self._spec

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence transformer model: %s", self._spec.model_name)
            self._model = SentenceTransformer(self._spec.model_name, device=self.device)

    def encode(self, texts: List[str], is_query: bool = False) -> np.ndarray:
        """Encode texts into normalized embedding vectors."""
        if not texts:
            return np.zeros((0, self._spec.dimension), dtype=np.float32)

        self._load_model()
        formatted_texts = []
        for t in texts:
            if is_query and self._spec.requires_query_instruction:
                formatted_texts.append(f"{self._spec.query_instruction}{t}")
            else:
                formatted_texts.append(t)

        embeddings = self._model.encode(
            formatted_texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embeddings.astype(np.float32)


def get_encoder(
    model_name_or_key: str = "tfidf-lsa-384",
    device: str = "cpu",
    corpus_for_lsa: Optional[List[str]] = None,
) -> BaseEmbeddingEncoder:
    """Factory method to instantiate the requested embedding encoder with graceful fallback."""
    if model_name_or_key == "tfidf-lsa-384":
        encoder = DeterministicLSAEncoder(dimension=384)
        if corpus_for_lsa:
            encoder.fit(corpus_for_lsa)
        return encoder

    try:
        return SentenceTransformerEncoder(model_key=model_name_or_key, device=device)
    except Exception as e:
        logger.warning(
            "Failed to load neural embedding model %s (%s). Falling back to DeterministicLSAEncoder.",
            model_name_or_key,
            e,
        )
        encoder = DeterministicLSAEncoder(dimension=384)
        if corpus_for_lsa:
            encoder.fit(corpus_for_lsa)
        return encoder
