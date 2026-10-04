"""Unit tests for AI relevance filter."""

from dataset.schemas.canonical_paper import CanonicalPaper, Topic
from pipelines.ingestion.filters.relevance import AIRelevanceFilter


def test_ai_relevance_evaluation():
    filt = AIRelevanceFilter(mode="broad_ai")

    ai_paper = CanonicalPaper(
        canonical_id="ai_p",
        title="Deep Residual Learning for Image Recognition",
        abstract="We present a residual learning framework to ease the training of neural networks.",
        topics=[Topic(name="Computer Science"), Topic(name="Artificial Intelligence")],
    )
    is_rel, tag, score = filt.evaluate(ai_paper)
    assert is_rel is True
    assert score >= 0.3

    non_ai_paper = CanonicalPaper(
        canonical_id="geo_p",
        title="Sedimentary geology of Cretaceous sandstone formations",
        abstract="Geological stratification analysis in continental shelves.",
    )
    is_rel2, _, score2 = filt.evaluate(non_ai_paper)
    assert is_rel2 is False
    assert score2 < 0.3


def test_strict_vs_broad_filter():
    strict = AIRelevanceFilter(mode="strict_ai")
    broad = AIRelevanceFilter(mode="broad_ai")

    adjacent_paper = CanonicalPaper(
        canonical_id="adj_p",
        title="Optimization methods for control systems",
        abstract="We study optimization in dynamic controllers.",
    )

    is_strict, _, _ = strict.evaluate(adjacent_paper)
    is_broad, _, _ = broad.evaluate(adjacent_paper)

    assert is_broad is True
    assert is_strict is False
