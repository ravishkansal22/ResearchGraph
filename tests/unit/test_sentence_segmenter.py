"""Unit tests for scientific sentence segmenter."""

from pipelines.processing.sentence_segmenter import ScientificSentenceSegmenter


def test_segment_standard_sentences():
    segmenter = ScientificSentenceSegmenter()
    text = "Machine learning is powerful. Deep learning extends it further. We evaluate performance."
    sentences = segmenter.segment_text(text, paragraph_id="p_001")
    assert len(sentences) == 3
    assert sentences[0].text == "Machine learning is powerful."
    assert sentences[1].text == "Deep learning extends it further."
    assert sentences[2].text == "We evaluate performance."


def test_protect_scientific_abbreviations():
    segmenter = ScientificSentenceSegmenter()
    text = (
        "According to Smith et al., the proposed method achieves high accuracy. "
        "For example, e.g., the F1 score was 0.95 vs. 0.82 for the baseline model. "
        "See Fig. 2 and Tab. 1 for details."
    )
    sentences = segmenter.segment_text(text, paragraph_id="p_002")
    assert len(sentences) == 3
    assert "Smith et al.," in sentences[0].text
    assert "e.g.," in sentences[1].text
    assert "0.95 vs. 0.82" in sentences[1].text
    assert "Fig. 2 and Tab. 1" in sentences[2].text


def test_protect_decimals_and_initials():
    segmenter = ScientificSentenceSegmenter()
    text = "Prof. J. Doe reported p < 0.001 with 99.8% confidence. The second study confirmed it."
    sentences = segmenter.segment_text(text, paragraph_id="p_003")
    assert len(sentences) == 2
    assert "p < 0.001" in sentences[0].text
    assert "J. Doe" in sentences[0].text
    assert sentences[1].text == "The second study confirmed it."
