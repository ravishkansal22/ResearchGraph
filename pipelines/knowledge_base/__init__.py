"""ResearchGraph Phase 4: Scientific Knowledge Base Pipeline Package."""

from pipelines.knowledge_base.config import KnowledgeBaseConfig
from pipelines.knowledge_base.normalizer import (
    generate_canonical_entity_id,
    generate_canonical_relationship_id,
    generate_canonical_statement_id,
    generate_mention_id,
    generate_quarantine_id,
    normalize_text,
    resolve_canonical_entity,
)
from pipelines.knowledge_base.pipeline import ScientificKnowledgeBasePipeline
from pipelines.knowledge_base.query import KnowledgeBaseQueryEngine
from pipelines.knowledge_base.reporter import KnowledgeBaseReporter
from pipelines.knowledge_base.storage import KnowledgeBaseStorage
from pipelines.knowledge_base.validator import (
    validate_entity_mention_record,
    validate_evidence_span,
    validate_provenance,
    validate_relationship_record,
    validate_statement_record,
)

__all__ = [
    "KnowledgeBaseConfig",
    "KnowledgeBaseQueryEngine",
    "KnowledgeBaseReporter",
    "KnowledgeBaseStorage",
    "ScientificKnowledgeBasePipeline",
    "generate_canonical_entity_id",
    "generate_canonical_relationship_id",
    "generate_canonical_statement_id",
    "generate_mention_id",
    "generate_quarantine_id",
    "normalize_text",
    "resolve_canonical_entity",
    "validate_entity_mention_record",
    "validate_evidence_span",
    "validate_provenance",
    "validate_relationship_record",
    "validate_statement_record",
]
