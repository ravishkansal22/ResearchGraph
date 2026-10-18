"""Unit & Regression Tests for ExperimentalScientificExtractor (v0.4.1).

Validates conservative recovery of audit failure modes without keyword spam:
1. Explicit contribution statements and numbered items
2. Bibliometric & meta-analytic methods (co-occurrence analysis, VOSviewer, cluster analysis)
3. Limitations without standard trigger verbs (challenges with data quality, ethical concerns)
4. NLP-based educational methods & tasks (intelligent tutoring systems, essay grading)
5. Named and descriptive datasets (Web of Science, Scopus, descriptive datasets)
6. Varied empirical result expressions
7. Contextual disambiguation (colloquial metric filter, cartesian relation constraint)
8. Exact character grounding preservation
"""

from __future__ import annotations

import pytest

from dataset.schemas.document_processing import ChunkStrategy, ProcessedChunk
from dataset.schemas.scientific_knowledge import (
    ScientificEntityType,
    ScientificRelationType,
    ScientificStatementType,
)
from pipelines.extraction.extractor import RuleBasedScientificExtractor
from pipelines.extraction.extractor_v041 import ExperimentalScientificExtractor


@pytest.fixture
def exp_extractor() -> ExperimentalScientificExtractor:
    return ExperimentalScientificExtractor()


@pytest.fixture
def orig_extractor() -> RuleBasedScientificExtractor:
    return RuleBasedScientificExtractor()


def make_chunk(text: str, cid: str = "rg_doi_test", chk_id: str = "chk_test_01") -> ProcessedChunk:
    return ProcessedChunk(
        chunk_id=chk_id,
        canonical_id=cid,
        section_id="sec_01",
        section_title="Methods",
        page_start=1,
        page_end=1,
        paragraph_start_order=1,
        paragraph_end_order=1,
        text=text,
        strategy=ChunkStrategy.STRATEGY_A_PARAGRAPH,
    )


def test_failure_mode_1_contribution_statements(exp_extractor, orig_extractor):
    """Verify explicit contribution blocks (Chunk 16 failure mode) are recovered."""
    text = (
        "Contributions of this study: "
        "1) Thorough analysis of the literature on cloud, edge, and quantum computing environments using AI, ML, and DL. "
        "2) Comprehensive keyword analysis and co-occurrence mapping to pinpoint important areas of study. "
        "3) Using cluster analysis, one can find new subfields between different computing paradigms."
    )
    chunk = make_chunk(text, chk_id="chk_chunk16")

    # Original extractor produced zero statements for this chunk
    orig_ents, orig_stmts, _ = orig_extractor.extract(chunk)
    assert len(orig_stmts) == 0

    # Experimental extractor recovers contribution statement as CLAIM
    exp_ents, exp_stmts, _ = exp_extractor.extract(chunk)
    claim_stmts = [s for s in exp_stmts if s.category == ScientificStatementType.CLAIM]
    assert len(claim_stmts) > 0

    # Recovers co-occurrence mapping / cluster analysis methods
    method_names = {e.normalized_name for e in exp_ents if e.category == ScientificEntityType.METHOD}
    assert "co-occurrence mapping" in method_names or "cluster analysis" in method_names


def test_failure_mode_2_bibliometric_methods_and_vosviewer(exp_extractor, orig_extractor):
    """Verify bibliometric methods and VOSviewer (Chunk 17, 18 failure mode) are extracted."""
    text = (
        "Following the keyword analysis, a co-occurrence analysis was conducted to explore relationships. "
        "Bibliometric tools VOSviewer were utilized to create a network of co-occurring terms. "
        "Cluster analysis techniques, including hierarchical clustering and k-means clustering, were used."
    )
    chunk = make_chunk(text, chk_id="chk_chunk17")

    orig_ents, _, _ = orig_extractor.extract(chunk)
    orig_methods = {e.normalized_name for e in orig_ents if e.category == ScientificEntityType.METHOD}
    # Original extractor missed all of these bibliometric methods
    assert "co-occurrence analysis" not in orig_methods
    assert "vosviewer" not in orig_methods
    assert "hierarchical clustering" not in orig_methods

    exp_ents, _, _ = exp_extractor.extract(chunk)
    exp_methods = {e.normalized_name.lower() for e in exp_ents if e.category == ScientificEntityType.METHOD}
    assert "co-occurrence analysis" in exp_methods
    assert "vosviewer" in exp_methods
    assert "hierarchical clustering" in exp_methods
    assert "k-means clustering" in exp_methods


def test_failure_mode_3_limitations_without_trigger_verbs(exp_extractor, orig_extractor):
    """Verify non-standard limitation phrasing (Chunk 19 failure mode) is extracted."""
    text = (
        "There are also preeminent challenges, including challenges with data quality, "
        "challenges with how the AI systems will harmonize with existing systems, "
        "and more to do with ethical concerns about patient privacy."
    )
    chunk = make_chunk(text, chk_id="chk_chunk19")

    # Original extractor missed limitation statement
    _, orig_stmts, _ = orig_extractor.extract(chunk)
    assert not any(s.category == ScientificStatementType.LIMITATION for s in orig_stmts)

    # Experimental extractor identifies LIMITATION and BOTTLENECK / PROBLEM
    exp_ents, exp_stmts, _ = exp_extractor.extract(chunk)
    assert any(s.category == ScientificStatementType.LIMITATION for s in exp_stmts)
    bottlenecks_or_problems = {e.normalized_name.lower() for e in exp_ents if e.category in (ScientificEntityType.BOTTLENECK, ScientificEntityType.PROBLEM)}
    assert "data quality" in bottlenecks_or_problems or "patient privacy" in bottlenecks_or_problems


def test_failure_mode_4_nlp_and_educational_tasks(exp_extractor, orig_extractor):
    """Verify NLP and educational tasks (Chunk 20 failure mode) are extracted."""
    text = (
        "It is a learning system that utilizes natural language processing to analyze and grade written responses. "
        "Intelligent tutoring systems provide immediate feedback and guidance for automated assessment."
    )
    chunk = make_chunk(text, chk_id="chk_chunk20")

    orig_ents, _, _ = orig_extractor.extract(chunk)
    orig_methods = {e.normalized_name.lower() for e in orig_ents if e.category == ScientificEntityType.METHOD}
    assert "natural language processing" not in orig_methods
    assert "intelligent tutoring systems" not in orig_methods

    exp_ents, _, _ = exp_extractor.extract(chunk)
    exp_methods = {e.normalized_name.lower() for e in exp_ents if e.category == ScientificEntityType.METHOD}
    exp_tasks = {e.normalized_name.lower() for e in exp_ents if e.category == ScientificEntityType.TASK}
    assert "natural language processing" in exp_methods
    assert "intelligent tutoring systems" in exp_methods
    assert "automated assessment" in exp_tasks


def test_failure_mode_5_named_and_descriptive_datasets(exp_extractor, orig_extractor):
    """Verify named literature databases and descriptive datasets (Chunk 1, 18) are extracted."""
    text = (
        "The algorithm is trained on a diverse dataset of mental health-related information. "
        "Data related to the topic was downloaded from Web of Science and Scopus."
    )
    chunk = make_chunk(text, chk_id="chk_chunk01_18")

    orig_ents, _, _ = orig_extractor.extract(chunk)
    orig_datasets = {e.normalized_name.lower() for e in orig_ents if e.category == ScientificEntityType.DATASET}
    assert "web of science" not in orig_datasets
    assert "scopus" not in orig_datasets

    exp_ents, _, _ = exp_extractor.extract(chunk)
    exp_datasets = {e.normalized_name.lower() for e in exp_ents if e.category == ScientificEntityType.DATASET}
    assert "web of science" in exp_datasets
    assert "scopus" in exp_datasets
    assert any("mental health" in d for d in exp_datasets)


def test_failure_mode_6_varied_empirical_results(exp_extractor, orig_extractor):
    """Verify varied empirical finding phrasing (Chunk 1, 21) is recognized as RESULT."""
    text = (
        "Initial testing of the AI robot demonstrates promising results in its ability to recognize emotional cues. "
        "To evaluate the performance of the image captioning system creative caption metrics were employed."
    )
    chunk = make_chunk(text, chk_id="chk_results_var")

    _, orig_stmts, _ = orig_extractor.extract(chunk)
    assert not any(s.category == ScientificStatementType.RESULT for s in orig_stmts)

    _, exp_stmts, _ = exp_extractor.extract(chunk)
    result_stmts = [s for s in exp_stmts if s.category == ScientificStatementType.RESULT]
    assert len(result_stmts) >= 1


def test_failure_mode_7_contextual_filtering_and_relation_grounding(exp_extractor, orig_extractor):
    """Verify colloquial 'accuracy' is filtered and cartesian relation explosion is avoided."""
    # 1. Colloquial metric avoidance
    colloquial_text = (
        "Model success cannot be reduced to accuracy alone when rights, safety, or equity are at stake."
    )
    chunk_colloquial = make_chunk(colloquial_text, chk_id="chk_colloquial")

    orig_ents, _, _ = orig_extractor.extract(chunk_colloquial)
    assert any(e.category == ScientificEntityType.METRIC and e.surface_text == "accuracy" for e in orig_ents)

    exp_ents, _, _ = exp_extractor.extract(chunk_colloquial)
    assert not any(e.category == ScientificEntityType.METRIC and e.surface_text == "accuracy" for e in exp_ents)

    # 2. Relation grounding without cartesian explosion
    # Chunk with 2 methods and 2 problems listed in unrelated contexts
    unrelated_text = (
        "We discuss machine learning and deep learning. "
        "Elsewhere in the system, administrators monitor cyber attacks and data imbalance."
    )
    chunk_unrelated = make_chunk(unrelated_text, chk_id="chk_unrelated")
    # Experimental extractor should NOT emit 4 cartesian relations because there is no connecting verb
    _, _, exp_rels = exp_extractor.extract(chunk_unrelated)
    assert len(exp_rels) == 0

    # But when explicit connecting verb is present:
    related_text = (
        "We propose an adaptive intrusion detection system that addresses cyber attacks in industrial IoT."
    )
    chunk_related = make_chunk(related_text, chk_id="chk_related")
    _, _, exp_rels_valid = exp_extractor.extract(chunk_related)
    assert len(exp_rels_valid) == 1
    assert exp_rels_valid[0].relation_type == ScientificRelationType.ADDRESSES


def test_exact_character_grounding_invariant(exp_extractor):
    """Verify that 100% of extractions from experimental extractor match source slice exactly."""
    text = (
        "Purpose – This study explores the feasibility of utilizing deep learning for mental health support. "
        "Bibliometric tools VOSviewer were utilized to perform co-occurrence analysis on Web of Science data. "
        "Initial testing demonstrates promising results in detecting emotional cues."
    )
    chunk = make_chunk(text, chk_id="chk_grounding_inv")
    ents, stmts, rels = exp_extractor.extract(chunk)

    assert len(ents) > 0
    assert len(stmts) > 0

    for ent in ents:
        assert ent.evidence.is_exact_match is True
        assert chunk.text[ent.evidence.start_char : ent.evidence.end_char] == ent.evidence.text

    for stmt in stmts:
        assert stmt.evidence.is_exact_match is True
        assert chunk.text[stmt.evidence.start_char : stmt.evidence.end_char] == stmt.evidence.text

    for rel in rels:
        assert rel.evidence.is_exact_match is True
        assert chunk.text[rel.evidence.start_char : rel.evidence.end_char] == rel.evidence.text
