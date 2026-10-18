"""Curated Domain Alias and Entity Normalization Registry.

Provides explicit, auditable dictionaries of:
1. Confirmed Synonyms & Acronym Expansions (CONFIRMED)
2. Candidate Synonyms awaiting domain verification (CANDIDATE)
3. Explicit Non-Merges (SEPARATE) to prevent conflating distinct concepts.
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple
from dataset.schemas.scientific_knowledge_base import AliasResolutionStatus

# 1. Confirmed Acronym / Full-Name Expansions
# Standardized to lowercase for canonical matching
CONFIRMED_ALIASES: Dict[Tuple[str, str], str] = {
    # (Category, Surface Variant) -> Canonical Name
    # Methods
    ("METHOD", "cnn"): "convolutional neural network",
    ("METHOD", "cnns"): "convolutional neural network",
    ("METHOD", "convolutional neural networks"): "convolutional neural network",
    ("METHOD", "convolutional neural network (cnn)"): "convolutional neural network",
    ("METHOD", "svm"): "support vector machine",
    ("METHOD", "svms"): "support vector machine",
    ("METHOD", "support vector machines"): "support vector machine",
    ("METHOD", "lstm"): "long short-term memory",
    ("METHOD", "lstms"): "long short-term memory",
    ("METHOD", "long short term memory"): "long short-term memory",
    ("METHOD", "long short-term memory network"): "long short-term memory",
    ("METHOD", "nlp"): "natural language processing",
    ("METHOD", "natural language processing (nlp)"): "natural language processing",
    ("METHOD", "bert"): "bert",
    ("METHOD", "bidirectional encoder representations from transformers"): "bert",
    ("METHOD", "vosviewer software"): "vosviewer",
    ("METHOD", "vosviewer tool"): "vosviewer",
    ("METHOD", "co-occurrence analysis"): "co-occurrence analysis",
    ("METHOD", "cooccurrence analysis"): "co-occurrence analysis",
    ("METHOD", "co-occurrence mapping"): "co-occurrence mapping",
    ("METHOD", "cluster analysis"): "cluster analysis",
    ("METHOD", "clustering analysis"): "cluster analysis",
    ("METHOD", "k-means"): "k-means clustering",
    ("METHOD", "kmeans"): "k-means clustering",
    ("METHOD", "hierarchical clustering"): "hierarchical clustering",
    ("METHOD", "intelligent tutoring system"): "intelligent tutoring systems",
    ("METHOD", "intelligent tutoring systems (its)"): "intelligent tutoring systems",
    ("METHOD", "federated learning (fl)"): "federated learning",
    ("METHOD", "generative adversarial network"): "generative adversarial networks",
    ("METHOD", "generative adversarial network (gan)"): "generative adversarial networks",
    ("METHOD", "gan"): "generative adversarial networks",
    ("METHOD", "gans"): "generative adversarial networks",
    ("METHOD", "deep learning techniques"): "deep learning",
    ("METHOD", "deep learning methods"): "deep learning",
    ("METHOD", "machine learning algorithms"): "machine learning",
    ("METHOD", "machine learning techniques"): "machine learning",

    # Datasets
    ("DATASET", "scopus database"): "scopus",
    ("DATASET", "web of science database"): "web of science",
    ("DATASET", "wos"): "web of science",
    ("DATASET", "pubmed database"): "pubmed",
    ("DATASET", "nsl-kdd dataset"): "nsl-kdd",
    ("DATASET", "cicids2017 dataset"): "cicids2017",
    ("DATASET", "crossref metadata"): "crossref",

    # Metrics
    ("METRIC", "f1"): "f1-score",
    ("METRIC", "f1 score"): "f1-score",
    ("METRIC", "f-measure"): "f1-score",
    ("METRIC", "auc-roc"): "area under the roc curve",
    ("METRIC", "auroc"): "area under the roc curve",

    # Tasks
    ("TASK", "image captioning"): "image captioning",
    ("TASK", "image caption generation"): "image captioning",
    ("TASK", "automated essay grading"): "automated assessment",
    ("TASK", "automated essay scoring"): "automated assessment",
    ("TASK", "automated assessment"): "automated assessment",
    ("TASK", "materials characterization"): "materials characterization",
    ("TASK", "materials discovery"): "materials discovery",
    ("TASK", "threat detection"): "threat detection",
    ("TASK", "intrusion detection"): "intrusion detection",

    # Problems
    ("PROBLEM", "data quality issues"): "data quality",
    ("PROBLEM", "poor data quality"): "data quality",
    ("PROBLEM", "patient privacy concerns"): "patient privacy",
    ("PROBLEM", "privacy risks"): "data privacy",
    ("PROBLEM", "data privacy concerns"): "data privacy",

    # Bottlenecks
    ("BOTTLENECK", "computational overhead"): "computational cost",
    ("BOTTLENECK", "high computational cost"): "computational cost",
    ("BOTTLENECK", "lack of explainability"): "lack of explainability",
    ("BOTTLENECK", "ethical concerns"): "ethical concerns",
}

# 2. Candidate Aliases awaiting domain verification (Do NOT automatically merge)
CANDIDATE_ALIASES: Dict[Tuple[str, str], str] = {
    ("METHOD", "generative ai"): "generative artificial intelligence",
    ("METHOD", "hierarchical clustering"): "cluster analysis",
    ("METHOD", "k-means clustering"): "cluster analysis",
    ("METHOD", "bibliographic coupling"): "bibliometric network analysis",
    ("PROBLEM", "data privacy"): "patient privacy",
    ("BOTTLENECK", "data imbalance"): "lack of training data",
}

# 3. Explicit Non-Merges (Must never be merged)
SEPARATE_CONCEPTS: Set[Tuple[str, str, str]] = {
    ("METHOD", "machine learning", "deep learning"),
    ("METHOD", "lstm", "transformer"),
    ("METRIC", "accuracy", "balanced accuracy"),
    ("METRIC", "precision", "recall"),
    ("PROBLEM", "data quality", "data privacy"),
}
