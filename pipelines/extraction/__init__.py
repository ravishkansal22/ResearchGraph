"""ResearchGraph Scientific Information Extraction Pipelines (Phase 3)."""

from dataset.schemas.scientific_knowledge import (
    AttributionType,
    EvidenceSpan,
    ExtractionBatchResult,
    ExtractionProvenance,
    ScientificEntityRecord,
    ScientificEntityType,
    ScientificRelationRecord,
    ScientificRelationType,
    ScientificStatementRecord,
    ScientificStatementType,
    ValidationStatus,
)
from pipelines.extraction.config import ExtractionConfig, config
from pipelines.extraction.evaluator import ExtractionEvaluationReport, ExtractionEvaluator
from pipelines.extraction.extractor import (
    BaseScientificExtractor,
    LLMScientificExtractor,
    RuleBasedScientificExtractor,
)
from pipelines.extraction.normalizer import ScientificNormalizer
from pipelines.extraction.pipeline import ScientificExtractionPipeline
from pipelines.extraction.reporter import ExtractionReporter
from pipelines.extraction.selection import ChunkSampler, SampledChunkRecord
from pipelines.extraction.validator import EvidenceGroundingValidator

__all__ = [
    # Schemas
    "ScientificEntityType",
    "ScientificStatementType",
    "ScientificRelationType",
    "AttributionType",
    "ValidationStatus",
    "EvidenceSpan",
    "ExtractionProvenance",
    "ScientificEntityRecord",
    "ScientificStatementRecord",
    "ScientificRelationRecord",
    "ExtractionBatchResult",
    # Pipeline components
    "ExtractionConfig",
    "config",
    "BaseScientificExtractor",
    "RuleBasedScientificExtractor",
    "LLMScientificExtractor",
    "ScientificNormalizer",
    "EvidenceGroundingValidator",
    "ChunkSampler",
    "SampledChunkRecord",
    "ExtractionEvaluator",
    "ExtractionEvaluationReport",
    "ExtractionReporter",
    "ScientificExtractionPipeline",
]
