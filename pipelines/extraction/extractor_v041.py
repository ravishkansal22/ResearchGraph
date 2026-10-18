"""ResearchGraph Phase 3 Experimental Scientific Information Extractor (v0.4.1).

Implements targeted, conservative improvements over the v0.4.0 baseline
to resolve audit failure modes without indiscriminate keyword inflation:
1. Contribution statements (e.g. "Contributions of this study:", numbered items)
2. Bibliometric and meta-analytic methods (co-occurrence analysis, cluster analysis, VOSviewer)
3. Non-trigger limitation expressions (challenges with data quality, ethical concerns, obstacles)
4. NLP and educational domain methods & tasks (intelligent tutoring systems, essay grading)
5. Named and descriptive dataset mentions (Web of Science, Scopus, descriptive datasets)
6. Varied empirical result expressions (initial testing demonstrates promising results, etc.)
7. Disambiguation and grounded relationship extraction without cartesian explosion
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from dataset.schemas.document_processing import ProcessedChunk
from dataset.schemas.scientific_knowledge import (
    AttributionType,
    EvidenceSpan,
    ExtractionProvenance,
    ScientificEntityRecord,
    ScientificEntityType,
    ScientificRelationRecord,
    ScientificRelationType,
    ScientificStatementRecord,
    ScientificStatementType,
    ValidationStatus,
)
from pipelines.extraction.extractor import BaseScientificExtractor
from pipelines.extraction.normalizer import ScientificNormalizer

logger = logging.getLogger(__name__)


# ==============================================================================
# Curated Lexicons for Experimental Baseline (v0.4.1)
# ==============================================================================

METHODS_LEXICON_V041 = {
    # Architectures & Classical ML Models
    "deep learning", "machine learning", "neural network", "neural networks",
    "convolutional neural network", "convolutional neural networks", "cnn", "cnns",
    "recurrent neural network", "recurrent neural networks", "rnn", "rnns",
    "long short-term memory", "lstm", "lstms", "gated recurrent unit", "gru",
    "transformer", "transformers", "bert", "gpt", "autoencoder", "autoencoders",
    "variational autoencoder", "vae", "generative adversarial network", "gan", "gans",
    "support vector machine", "support vector machines", "svm", "svms",
    "random forest", "random forests", "decision tree", "decision trees",
    "k-nearest neighbors", "knn", "logistic regression", "naive bayes",
    "deep reinforcement learning", "reinforcement learning", "q-learning",
    "federated learning", "transfer learning", "self-supervised learning",
    "xgboost", "lightgbm", "catboost", "yolo", "resnet", "vgg",
    "intrusion detection system", "intrusion detection systems", "ids", "nids",
    "adaptive intrusion detection systems", "ensemble learning",
    # Bibliometric, Meta-Analytic, and Network Methods (Audit Recovery)
    "co-occurrence analysis", "co-occurrence mapping", "cluster analysis",
    "hierarchical clustering", "k-means clustering", "vosviewer",
    "bibliometric network analysis", "bibliometric analysis", "bibliographic coupling",
    "co-citation analysis", "keyword analysis", "predictive analytics",
    "decision support systems", "intelligent automation",
    # NLP & Educational Systems (Audit Recovery)
    "natural language processing", "nlp", "computer vision", "machine vision",
    "intelligent tutoring systems", "intelligent tutoring system",
    "model-tracing tutors", "constraint-based tutors", "generative ai",
    "large language models", "large language model", "llm", "llms",
}

PROBLEMS_LEXICON_V041 = {
    "cyber threats", "cyber threat", "cyber attacks", "cyber attack", "cyberattacks",
    "intrusion detection", "anomaly detection", "adversarial manipulation",
    "adversarial attacks", "adversarial attack", "data imbalance", "class imbalance",
    "model interpretability", "interpretability", "overfitting", "concept drift",
    "malware detection", "zero-day attacks", "zero-day threats", "phishing detection",
    "epileptic seizure detection", "seizure prediction", "cardiovascular disease",
    "air quality prediction", "traffic congestion", "high dimensional network traffic",
    "false positive rate", "false alarms",
    # Clinical & Systems Problems (Audit Recovery)
    "data quality", "patient privacy", "model hallucination",
    "supply chain resilience", "runtime supply chain attacks", "insider threats",
}

BOTTLENECKS_LEXICON_V041 = {
    "adversarial manipulation", "data imbalance", "class imbalance", "model interpretability",
    "interpretability", "black-box nature", "computational complexity", "computational cost",
    "latency overhead", "resource constraints", "lack of labeled data", "scarcity of data",
    "high dimensional network traffic", "noisy data", "feature redundancy", "scalability limits",
    # Additional Stated Bottlenecks (Audit Recovery)
    "data quality", "ethical concerns", "lack of explainability", "limited scalability",
}

METRICS_LEXICON_V041 = {
    "accuracy", "precision", "recall", "f1 score", "f1-score", "f1",
    "false positive rate", "fpr", "true positive rate", "tpr", "area under curve", "auc",
    "roc", "roc-auc", "mean squared error", "mse", "root mean squared error", "rmse",
    "mean absolute error", "mae", "latency", "throughput", "p-value", "loss",
}

DATASETS_LEXICON_V041 = {
    "kdd cup 99", "kdd99", "nsl-kdd", "cicids2017", "unsw-nb15", "kyoto 2006+",
    "imagenet", "mnist", "cifar-10", "cifar-100", "mimic-iii", "chb-mit",
    # Curated Literature Databases & Public Benchmarks (Audit Recovery)
    "web of science", "scopus", "pubmed", "crossref", "semantic scholar",
    "squad", "glue benchmark", "glue",
}

TASKS_LEXICON_V041 = {
    "threat detection", "intelligent threat detection", "intrusion detection",
    "anomaly identification", "predictive threat intelligence", "feature extraction",
    "traffic classification", "binary classification", "multi-class classification",
    "packet inspection", "seizure detection", "air quality prediction",
    # Educational, Captioning, and Materials Tasks (Audit Recovery)
    "automated assessment", "automated essay grading", "essay grading",
    "image captioning", "materials characterization", "materials discovery",
}

DOMAINS_LEXICON_V041 = {
    "cybersecurity", "healthcare", "aviation", "optical communications",
    "civil engineering", "mental health", "biomedical signal processing",
    "supply chain management", "logistics and supply chain management",
    "oncology", "applied superconductivity", "superconductivity",
}


# ==============================================================================
# Syntactic & Discourse Regex Patterns (v0.4.1)
# ==============================================================================

# Entity Syntactic Frames
RE_METHOD_SYNTACTIC_V041 = re.compile(
    r"\b(?:we\s+(?:propose|develop|introduce|design)|our\s+proposed)\s+(?:a\s+|an\s+|the\s+)?([A-Za-z0-9\-\s]{3,35}?(?:model|framework|architecture|algorithm|system|technique|methodology))\b",
    re.IGNORECASE,
)

RE_PROBLEM_SYNTACTIC_V041 = re.compile(
    r"\b(?:problem\s+of|challenge\s+of|vulnerability\s+to|threat\s+of|challenges?\s+with)\s+([a-z0-9\-\s]{4,35}?)(?:[\.,;]|\s+and|\s+in)\b",
    re.IGNORECASE,
)

RE_DATASET_SYNTACTIC_V041 = re.compile(
    r"\btrained\s+on\s+(?:a\s+|an\s+)?(?:diverse|large|public|benchmark|clinical|curated)?\s*dataset\s+of\s+([A-Za-z0-9\-\s]{4,45}?)(?:,\s*including|[,\.]|\s+to|\s+for|\s*$)",
    re.IGNORECASE,
)

RE_ASSUMPTION_SYNTACTIC_V041 = re.compile(
    r"\b(?:assuming\s+that|under\s+the\s+assumption\s+that|we\s+assume\s+that)\s+([A-Za-z0-9\-\s,\'\"]{8,80}?(?:[\.;]|$))",
    re.IGNORECASE,
)

# Statement Discourse Patterns
RE_CONTRIBUTION_HEADER_V041 = re.compile(
    r"\b(?:(?:the\s+)?contributions\s+of\s+this\s+(?:study|paper|research\s+work|work)|"
    r"(?:our\s+)?main\s+contributions\s+are|contributions:)\b",
    re.IGNORECASE,
)

RE_CLAIM_SENTENCE_V041 = re.compile(
    r"\b(?:this\s+paper\s+(?:examines|proposes|presents|investigates|evaluates|reviews)|"
    r"this\s+study\s+(?:provides|analyzes|explores|demonstrates|employs)|"
    r"we\s+(?:propose|introduce|present|develop|argue\s+that|hypothesize\s+that|examine)|"
    r"the\s+goal\s+of\s+this\s+(?:study|paper|work)\s+is|"
    r"(?:the\s+)?contributions\s+of\s+this\s+(?:study|paper|research\s+work)|"
    r"the\s+objectives\s+of\s+this\s+work\s+are)\b",
    re.IGNORECASE,
)

RE_RESULT_SENTENCE_V041 = re.compile(
    r"\b(?:achieved\s+(?:an?\s+)?(?:accuracy|precision|f1|score)|"
    r"results?\s+(?:show|demonstrate|indicate|reveal)\s+that|"
    r"outperformed\s+(?:traditional|conventional|baseline|state-of-the-art)|"
    r"exhibited\s+(?:superior|improved|high)\s+performance|"
    r"demonstrated\s+a\s+(?:significant\s+)?(?:reduction|improvement|increase)|"
    r"attained\s+an?\s+accuracy\s+of|"
    r"revealed\s+that\s+deep\s+learning\s+models|"
    r"(?:initial\s+testing|preliminary\s+results?|experimental\s+results?)\s+(?:of\s+.*?\s+)?(?:demonstrates?|shows?|indicates?)\s+(?:promising|strong|superior|competitive|significant)\s+results?|"
    r"findings?\s+(?:indicate|demonstrate|show|reveal)\s+that|"
    r"yielded\s+(?:an?\s+)?(?:accuracy|precision|recall|f1|improvement|reduction)|"
    r"to\s+evaluate\s+the\s+performance\s+of\s+.*?\s+(?:metrics?\s+(?:can\s+be|were|are)\s+employed))\b",
    re.IGNORECASE,
)

RE_LIMITATION_SENTENCE_V041 = re.compile(
    r"\b(?:a\s+limitation\s+of|limitations?\s+include|suffers?\s+from|"
    r"is\s+constrained\s+by|remains?\s+a\s+(?:major\s+)?(?:challenge|concern)|"
    r"ongoing\s+concerns\s+related\s+to|does\s+not\s+account\s+for|"
    r"restricted\s+by|susceptible\s+to\s+adversarial|"
    r"preeminent\s+challenges|significant\s+challenges|major\s+obstacles|"
    r"obstacles\s+still\s+exist|challenges\s+with\s+(?:data\s+quality|scalability|integration|privacy|security)|"
    r"problems\s+that\s+have\s+been\s+culminating|difficult\s+undertaking|"
    r"ethical\s+concerns\s+about|concerns\s+regarding\s+patient\s+privacy)\b",
    re.IGNORECASE,
)

RE_FUTURE_DIRECTION_SENTENCE_V041 = re.compile(
    r"\b(?:future\s+(?:research|work|directions?|studies)|"
    r"outlines\s+emerging\s+directions\s+for|"
    r"emerging\s+directions\s+for\s+building|"
    r"remains\s+an\s+open\s+question|"
    r"we\s+plan\s+to\s+(?:investigate|extend|explore))\b",
    re.IGNORECASE,
)

RE_FAILURE_MODE_SENTENCE_V041 = re.compile(
    r"\b(?:fails?\s+to\s+(?:detect|generalize|converge)|"
    r"struggle\s+to\s+detect|"
    r"underperforms?\s+(?:when|under|on)|"
    r"leads?\s+to\s+high\s+false\s+(?:positives|alarms)|"
    r"performance\s+degrades?\s+(?:sharply|under|when))\b",
    re.IGNORECASE,
)

# Colloquial metric filter (avoids false positive on "reduced to accuracy alone")
RE_METRIC_COLLOQUIAL_CONTEXT = re.compile(
    r"\b(?:reduced\s+to|beyond|fixation\s+on|cannot\s+be\s+reduced\s+to)\s+accuracy\b",
    re.IGNORECASE,
)

# Connective frames for grounded relation extraction
RE_ADDRESSES_RELATION = re.compile(
    r"\b(?:addresses?|mitigates?|tackles?|solves?|combats?|for\s+(?:intelligent\s+)?modelling\s+of|developed\s+to\s+address)\b",
    re.IGNORECASE,
)

RE_LIMITED_BY_RELATION = re.compile(
    r"\b(?:limited\s+by|constrained\s+by|suffers\s+from|struggles\s+with|challenges\s+with|susceptible\s+to)\b",
    re.IGNORECASE,
)

RE_USES_RELATION = re.compile(
    r"\b(?:uses?|utilizes?|employs?|integrat(?:ed|ing)\s+(?:in|into)|based\s+on)\b",
    re.IGNORECASE,
)

RE_EVALUATED_ON_RELATION = re.compile(
    r"\b(?:evaluated\s+on|tested\s+on|benchmarked\s+on|trained\s+on)\b",
    re.IGNORECASE,
)


class ExperimentalScientificExtractor(BaseScientificExtractor):
    """Refined, evidence-grounded scientific NLP extractor for Phase 3 (v0.4.1).

    Preserves exact evidence grounding (100% character span match) and provenance
    while conservatively addressing audit-documented failure modes:
    - Recovers contribution propositions and numbered item structures
    - Identifies bibliometric, clustering, and NLP educational methods
    - Extracts limitations without requiring explicit trigger verbs
    - Normalizes and extracts named and descriptive datasets
    - Enforces grounded relational constraints to prevent cartesian explosion
    """

    def __init__(
        self,
        schema_version: str = "0.4.0",
        pipeline_version: str = "v0.4.1",
    ):
        self.schema_version = schema_version
        self.pipeline_version = pipeline_version
        self.normalizer = ScientificNormalizer()

    def _create_provenance(self, chunk: ProcessedChunk) -> ExtractionProvenance:
        """Create structured provenance model from ProcessedChunk."""
        return ExtractionProvenance(
            canonical_id=chunk.canonical_id,
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            section_id=chunk.section_id,
            section_title=chunk.section_title,
            section_level=chunk.section_level,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            file_hash=chunk.file_hash,
        )

    def _generate_record_id(self, prefix: str, chunk_id: str, index: int, text: str) -> str:
        """Generate stable deterministic record ID."""
        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
        return f"{prefix}_{chunk_id}_{index:02d}_{text_hash}"

    def extract(
        self,
        chunk: ProcessedChunk,
    ) -> Tuple[
        List[ScientificEntityRecord],
        List[ScientificStatementRecord],
        List[ScientificRelationRecord],
    ]:
        """Execute conservative experimental extraction on chunk."""
        entities: List[ScientificEntityRecord] = []
        statements: List[ScientificStatementRecord] = []
        relations: List[ScientificRelationRecord] = []

        provenance = self._create_provenance(chunk)
        chunk_text = chunk.text
        if not chunk_text or len(chunk_text.strip()) < 10:
            return entities, statements, relations

        entity_index = 0
        statement_index = 0
        relation_index = 0

        # Track spans already extracted to prevent overlapping duplicates
        seen_entity_spans: Set[Tuple[int, int]] = set()
        # Track (category, normalized_name) to avoid emitting duplicate identical concepts per chunk
        seen_concepts_per_chunk: Set[Tuple[str, str]] = set()

        # ======================================================================
        # 1. Scientific Entity Extraction
        # ======================================================================

        def add_entity_if_valid(
            category: ScientificEntityType,
            surface: str,
            start: int,
            end: int,
            conf: float = 1.0,
            allow_duplicate_concept: bool = False,
        ):
            nonlocal entity_index
            span = (start, end)
            # Suppress sub-spans that overlap with an already extracted longer/more specific span
            for s, e in seen_entity_spans:
                if max(start, s) < min(end, e):
                    return

            # Verify exact character slice
            if chunk_text[start:end] != surface:
                return

            # Check colloquial context filter for generic metric words
            if category == ScientificEntityType.METRIC and surface.lower() == "accuracy":
                surrounding = chunk_text[max(0, start - 30) : min(len(chunk_text), end + 30)]
                if RE_METRIC_COLLOQUIAL_CONTEXT.search(surrounding):
                    return

            normalized = self.normalizer.normalize_entity_name(surface)
            if not normalized or len(normalized) < 2:
                return

            concept_key = (category.value, normalized.lower())
            # Conservative deduplication: if exact concept already extracted in chunk, skip redundant emission
            if not allow_duplicate_concept and concept_key in seen_concepts_per_chunk:
                return

            entity_index += 1
            rec_id = self._generate_record_id("ent", chunk.chunk_id, entity_index, surface)
            entities.append(
                ScientificEntityRecord(
                    record_id=rec_id,
                    schema_version=self.schema_version,
                    category=category,
                    surface_text=surface,
                    normalized_name=normalized,
                    evidence=EvidenceSpan(
                        text=surface,
                        start_char=start,
                        end_char=end,
                        is_exact_match=True,
                        confidence=conf,
                    ),
                    provenance=provenance,
                    attribution=AttributionType.AUTHOR_STATED,
                    confidence_score=conf,
                    extraction_method="conservative_rule_based_v041",
                    extraction_version=self.pipeline_version,
                    validation_status=ValidationStatus.VALIDATED,
                )
            )
            seen_entity_spans.add(span)
            seen_concepts_per_chunk.add(concept_key)

        # A. Syntactic Frames for Entities First (Captures specific multi-word phrases)
        # Method frames
        for m in RE_METHOD_SYNTACTIC_V041.finditer(chunk_text):
            group_surface = m.group(1).strip()
            g_start = m.start(1)
            g_end = m.end(1)
            add_entity_if_valid(ScientificEntityType.METHOD, group_surface, g_start, g_end, 0.88)

        # Problem frames
        for m in RE_PROBLEM_SYNTACTIC_V041.finditer(chunk_text):
            group_surface = m.group(1).strip()
            g_start = m.start(1)
            g_end = m.end(1)
            add_entity_if_valid(ScientificEntityType.PROBLEM, group_surface, g_start, g_end, 0.86)

        # Descriptive Dataset frames
        for m in RE_DATASET_SYNTACTIC_V041.finditer(chunk_text):
            group_surface = m.group(1).strip()
            g_start = m.start(1)
            g_end = m.end(1)
            add_entity_if_valid(ScientificEntityType.DATASET, group_surface, g_start, g_end, 0.88)

        # Assumption frames
        for m in RE_ASSUMPTION_SYNTACTIC_V041.finditer(chunk_text):
            group_surface = m.group(1).strip().rstrip(".;")
            g_start = m.start(1)
            g_end = g_start + len(group_surface)
            add_entity_if_valid(ScientificEntityType.ASSUMPTION, group_surface, g_start, g_end, 0.85)

        # B. Lexicon Matching (Sorted by length descending so longer terms match first)
        lexicon_specs = [
            (ScientificEntityType.METHOD, METHODS_LEXICON_V041, 0.95),
            (ScientificEntityType.PROBLEM, PROBLEMS_LEXICON_V041, 0.92),
            (ScientificEntityType.BOTTLENECK, BOTTLENECKS_LEXICON_V041, 0.90),
            (ScientificEntityType.METRIC, METRICS_LEXICON_V041, 0.95),
            (ScientificEntityType.DATASET, DATASETS_LEXICON_V041, 0.98),
            (ScientificEntityType.TASK, TASKS_LEXICON_V041, 0.92),
            (ScientificEntityType.DOMAIN, DOMAINS_LEXICON_V041, 0.92),
        ]

        for cat, term_set, conf in lexicon_specs:
            for term in sorted(term_set, key=len, reverse=True):
                pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
                for m in pattern.finditer(chunk_text):
                    start, end = m.span()
                    surface = chunk_text[start:end]
                    add_entity_if_valid(cat, surface, start, end, conf)

        # ======================================================================
        # 2. Scientific Statement Extraction
        # ======================================================================

        sentence_spans = self._split_sentences_with_offsets(chunk_text)

        # Check for explicit contribution block in chunk
        has_contribution_header = bool(RE_CONTRIBUTION_HEADER_V041.search(chunk_text))

        for sent_text, s_start, s_end in sentence_spans:
            sent_clean = sent_text.strip()
            if len(sent_clean) < 15:
                continue

            stmt_category: Optional[ScientificStatementType] = None
            conf = 0.90

            # Priority 1: Check if sentence is part of an explicit contribution declaration
            if has_contribution_header or RE_CONTRIBUTION_HEADER_V041.search(sent_clean):
                stmt_category = ScientificStatementType.CLAIM
                conf = 0.96
            # Priority 2: Standard discourse categories
            elif RE_LIMITATION_SENTENCE_V041.search(sent_clean):
                stmt_category = ScientificStatementType.LIMITATION
                conf = 0.94
            elif RE_FAILURE_MODE_SENTENCE_V041.search(sent_clean):
                stmt_category = ScientificStatementType.FAILURE_MODE
                conf = 0.92
            elif RE_RESULT_SENTENCE_V041.search(sent_clean):
                stmt_category = ScientificStatementType.RESULT
                conf = 0.93
            elif RE_FUTURE_DIRECTION_SENTENCE_V041.search(sent_clean):
                stmt_category = ScientificStatementType.FUTURE_DIRECTION
                conf = 0.95
            elif RE_CLAIM_SENTENCE_V041.search(sent_clean):
                stmt_category = ScientificStatementType.CLAIM
                conf = 0.93

            if stmt_category:
                statement_index += 1
                rec_id = self._generate_record_id("stmt", chunk.chunk_id, statement_index, sent_clean)
                norm_stmt = self.normalizer.normalize_statement_text(sent_clean)

                # Identify entities contained within this statement span
                related_entity_ids = [
                    e.record_id for e in entities
                    if e.evidence.start_char >= s_start and e.evidence.end_char <= s_end
                ]

                statements.append(
                    ScientificStatementRecord(
                        record_id=rec_id,
                        schema_version=self.schema_version,
                        category=stmt_category,
                        surface_text=sent_clean,
                        normalized_statement=norm_stmt,
                        evidence=EvidenceSpan(
                            text=chunk_text[s_start:s_end],
                            start_char=s_start,
                            end_char=s_end,
                            is_exact_match=True,
                            confidence=conf,
                        ),
                        provenance=provenance,
                        attribution=AttributionType.AUTHOR_STATED,
                        confidence_score=conf,
                        extraction_method="conservative_rule_based_v041",
                        extraction_version=self.pipeline_version,
                        validation_status=ValidationStatus.VALIDATED,
                        related_entity_ids=related_entity_ids,
                    )
                )

        # ======================================================================
        # 3. Grounded Scientific Relationship Extraction
        # ======================================================================

        # Emit relationships ONLY when connected by explicit syntactic relation triggers
        # within the supporting sentence. Avoids cartesian explosion.
        for stmt in statements:
            stmt_text = stmt.surface_text
            stmt_entities = [e for e in entities if e.record_id in stmt.related_entity_ids]
            methods = [e for e in stmt_entities if e.category == ScientificEntityType.METHOD]
            problems = [e for e in stmt_entities if e.category == ScientificEntityType.PROBLEM]
            bottlenecks = [e for e in stmt_entities if e.category == ScientificEntityType.BOTTLENECK]
            datasets = [e for e in stmt_entities if e.category == ScientificEntityType.DATASET]
            metrics = [e for e in stmt_entities if e.category == ScientificEntityType.METRIC]

            # A. METHOD -> ADDRESSES -> PROBLEM (Requires ADDRESSES trigger or close syntactic proximity)
            if RE_ADDRESSES_RELATION.search(stmt_text):
                for m in methods:
                    for p in problems:
                        relation_index += 1
                        rel_id = self._generate_record_id("rel", chunk.chunk_id, relation_index, f"{m.record_id}_{p.record_id}")
                        relations.append(
                            ScientificRelationRecord(
                                relation_id=rel_id,
                                schema_version=self.schema_version,
                                relation_type=ScientificRelationType.ADDRESSES,
                                source_id=m.record_id,
                                target_id=p.record_id,
                                source_category="METHOD",
                                target_category="PROBLEM",
                                surface_text=f"{m.surface_text} addresses {p.surface_text}",
                                evidence=stmt.evidence,
                                provenance=provenance,
                                attribution=AttributionType.AUTHOR_STATED,
                                is_directed=True,
                                confidence_score=0.90,
                                extraction_method="conservative_rule_based_v041",
                                extraction_version=self.pipeline_version,
                                validation_status=ValidationStatus.VALIDATED,
                            )
                        )

            # B. METHOD -> LIMITED_BY -> BOTTLENECK (Requires LIMITED_BY trigger)
            if RE_LIMITED_BY_RELATION.search(stmt_text):
                for m in methods:
                    for b in bottlenecks:
                        relation_index += 1
                        rel_id = self._generate_record_id("rel", chunk.chunk_id, relation_index, f"{m.record_id}_{b.record_id}")
                        relations.append(
                            ScientificRelationRecord(
                                relation_id=rel_id,
                                schema_version=self.schema_version,
                                relation_type=ScientificRelationType.LIMITED_BY,
                                source_id=m.record_id,
                                target_id=b.record_id,
                                source_category="METHOD",
                                target_category="BOTTLENECK",
                                surface_text=f"{m.surface_text} limited by {b.surface_text}",
                                evidence=stmt.evidence,
                                provenance=provenance,
                                attribution=AttributionType.AUTHOR_STATED,
                                is_directed=True,
                                confidence_score=0.88,
                                extraction_method="conservative_rule_based_v041",
                                extraction_version=self.pipeline_version,
                                validation_status=ValidationStatus.VALIDATED,
                            )
                        )

            # C. METHOD -> EVALUATED_ON -> DATASET (Requires EVALUATED_ON trigger)
            if RE_EVALUATED_ON_RELATION.search(stmt_text):
                for m in methods:
                    for d in datasets:
                        relation_index += 1
                        rel_id = self._generate_record_id("rel", chunk.chunk_id, relation_index, f"{m.record_id}_{d.record_id}")
                        relations.append(
                            ScientificRelationRecord(
                                relation_id=rel_id,
                                schema_version=self.schema_version,
                                relation_type=ScientificRelationType.EVALUATED_ON,
                                source_id=m.record_id,
                                target_id=d.record_id,
                                source_category="METHOD",
                                target_category="DATASET",
                                surface_text=f"{m.surface_text} evaluated on {d.surface_text}",
                                evidence=stmt.evidence,
                                provenance=provenance,
                                attribution=AttributionType.AUTHOR_STATED,
                                is_directed=True,
                                confidence_score=0.92,
                                extraction_method="conservative_rule_based_v041",
                                extraction_version=self.pipeline_version,
                                validation_status=ValidationStatus.VALIDATED,
                            )
                        )

            # D. METHOD -> USES -> METRIC / COMPONENT
            if RE_USES_RELATION.search(stmt_text):
                for m in methods:
                    for met in metrics:
                        relation_index += 1
                        rel_id = self._generate_record_id("rel", chunk.chunk_id, relation_index, f"{m.record_id}_{met.record_id}")
                        relations.append(
                            ScientificRelationRecord(
                                relation_id=rel_id,
                                schema_version=self.schema_version,
                                relation_type=ScientificRelationType.USES,
                                source_id=m.record_id,
                                target_id=met.record_id,
                                source_category="METHOD",
                                target_category="METRIC",
                                surface_text=f"{m.surface_text} uses {met.surface_text}",
                                evidence=stmt.evidence,
                                provenance=provenance,
                                attribution=AttributionType.AUTHOR_STATED,
                                is_directed=True,
                                confidence_score=0.86,
                                extraction_method="conservative_rule_based_v041",
                                extraction_version=self.pipeline_version,
                                validation_status=ValidationStatus.VALIDATED,
                            )
                        )

        return entities, statements, relations

    @staticmethod
    def _split_sentences_with_offsets(text: str) -> List[Tuple[str, int, int]]:
        """Split text into sentences while tracking exact character offsets (0-indexed)."""
        results: List[Tuple[str, int, int]] = []
        if not text:
            return results

        # Boundary regex on period/question/exclamation/colon followed by space or newline and capital/digit
        pattern = re.compile(r'([.?!:])(?:\s+|\n+)(?=[A-Z0-9"\'\(\[\{\b])')
        start = 0

        for match in pattern.finditer(text):
            punc_pos = match.start(1)
            end = punc_pos + 1
            sent = text[start:end]
            if sent.strip():
                l_strip = len(sent) - len(sent.lstrip())
                actual_start = start + l_strip
                actual_sent = text[actual_start:end]
                results.append((actual_sent, actual_start, end))
            start = match.end()

        # Final sentence
        if start < len(text):
            sent = text[start:]
            if sent.strip():
                l_strip = len(sent) - len(sent.lstrip())
                actual_start = start + l_strip
                results.append((text[actual_start:], actual_start, len(text)))

        return results
