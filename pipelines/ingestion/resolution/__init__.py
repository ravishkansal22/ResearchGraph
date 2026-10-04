"""Resolution and Deduplication package for ResearchGraph."""

from pipelines.ingestion.resolution.deduplicator import (
    Deduplicator,
    merge_two_canonical_papers,
)
from pipelines.ingestion.resolution.identity import (
    IdentityResolver,
    compute_title_similarity,
    generate_deterministic_canonical_id,
)

__all__ = [
    "IdentityResolver",
    "Deduplicator",
    "compute_title_similarity",
    "generate_deterministic_canonical_id",
    "merge_two_canonical_papers",
]
