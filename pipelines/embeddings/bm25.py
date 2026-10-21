"""ResearchGraph Phase 5: Lexical BM25 Retrieval Engine.

Implements Okapi BM25 retrieval over scientific chunks, statements, entities, and papers.
Provides the rigorous lexical baseline required to evaluate dense semantic embeddings.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't",
    "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having",
    "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how",
    "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
    "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
    "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the",
    "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's",
    "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
}


def tokenize(text: Optional[str]) -> List[str]:
    """Tokenize and normalize text into lowercase alphanumeric tokens without stopwords."""
    if not text:
        return []
    cleaned = re.sub(r"[^\w\s-]", " ", text.lower())
    tokens = [t.strip() for t in cleaned.split() if len(t.strip()) > 2 and t.strip() not in STOPWORDS]
    return tokens


@dataclass
class BM25Document:
    """Document representation in the BM25 index."""
    doc_id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tokens: List[str] = field(default_factory=list)
    token_counts: Dict[str, int] = field(default_factory=dict)
    length: int = 0


@dataclass
class RetrievalHit:
    """Standardized retrieval search result across lexical and semantic engines."""
    record_id: str
    score: float
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    retrieval_method: str = "bm25"


class BM25Index:
    """Okapi BM25 Index with robust term-frequency and inverse document frequency scoring."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: Dict[str, BM25Document] = {}
        self.doc_freqs: Dict[str, int] = {}
        self.num_docs: int = 0
        self.avg_doc_len: float = 0.0
        self._idf_cache: Dict[str, float] = {}

    def add_document(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a single document to the index."""
        tokens = tokenize(text)
        token_counts: Dict[str, int] = {}
        for t in tokens:
            token_counts[t] = token_counts.get(t, 0) + 1

        doc = BM25Document(
            doc_id=doc_id,
            text=text,
            metadata=metadata or {},
            tokens=tokens,
            token_counts=token_counts,
            length=len(tokens),
        )
        self.documents[doc_id] = doc

    def build(self) -> None:
        """Finalize the index and precalculate document frequencies and average lengths."""
        self.num_docs = len(self.documents)
        if self.num_docs == 0:
            self.avg_doc_len = 0.0
            return

        total_length = 0
        self.doc_freqs.clear()
        for doc in self.documents.values():
            total_length += doc.length
            for token in doc.token_counts.keys():
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        self.avg_doc_len = total_length / self.num_docs
        self._idf_cache.clear()

    def _get_idf(self, term: str) -> float:
        """Compute standard Robertson-Spärck Jones IDF with smoothing."""
        if term in self._idf_cache:
            return self._idf_cache[term]
        df = self.doc_freqs.get(term, 0)
        # Smoothed BM25 IDF: ln((N - n + 0.5) / (n + 0.5) + 1)
        idf = math.log(((self.num_docs - df + 0.5) / (df + 0.5)) + 1.0)
        self._idf_cache[term] = max(idf, 0.0)
        return self._idf_cache[term]

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_fn: Optional[Any] = None,
    ) -> List[RetrievalHit]:
        """Search the index for matching documents ranked by Okapi BM25 score."""
        if self.num_docs == 0 or not self.documents:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores: Dict[str, float] = {}
        for token in query_tokens:
            if token not in self.doc_freqs:
                continue
            idf = self._get_idf(token)
            for doc_id, doc in self.documents.items():
                if filter_fn and not filter_fn(doc):
                    continue
                tf = doc.token_counts.get(token, 0)
                if tf > 0:
                    numerator = tf * (self.k1 + 1.0)
                    denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc.length / (self.avg_doc_len or 1.0)))
                    scores[doc_id] = scores.get(doc_id, 0.0) + idf * (numerator / denominator)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        hits: List[RetrievalHit] = []
        for doc_id, score in ranked:
            doc = self.documents[doc_id]
            hits.append(
                RetrievalHit(
                    record_id=doc.doc_id,
                    score=round(score, 4),
                    text=doc.text,
                    metadata=doc.metadata,
                    retrieval_method="bm25",
                )
            )
        return hits
