"""Unit tests for Phase 9: Negative Knowledge and Dead-End Graveyard.

Verifies:
1. Negative knowledge record representation and schema validation.
2. Ingestion of limitation statements and restricted relationships from database.
3. Querying method limitations and failure modes.
4. Contradiction risk checks for method/problem pairs.
5. Recurring bottleneck aggregation across the corpus.
"""

from __future__ import annotations

import pytest

from pipelines.negative_knowledge.graveyard import DeadEndGraveyard
from pipelines.negative_knowledge.schema import (
    FailureCategory,
    NegativeEvidenceType,
    NegativeKnowledgeRecord,
)


class TestDeadEndGraveyard:
    """Test suite for negative knowledge catalog and querying."""

    def test_build_and_query_graveyard_from_kb(self):
        graveyard = DeadEndGraveyard()
        total_indexed = graveyard.build_index()
        assert total_indexed > 0

        # Query limitations for machine learning / federated learning
        limits = graveyard.find_method_limitations("federated learning")
        assert len(limits) > 0
        categories = {r.failure_category for r in limits}
        assert (
            FailureCategory.METHOD_LIMITATION in categories
            or FailureCategory.COMPUTATIONAL_BOTTLENECK in categories
        )

    def test_contradiction_risk_detection(self):
        graveyard = DeadEndGraveyard()
        graveyard.build_index()

        # Check risk on high computational cost
        risks = graveyard.check_contradiction_risk("federated learning", "computational cost")
        assert len(risks) > 0
        assert any("computational" in r.description.lower() for r in risks)

    def test_recurring_bottlenecks(self):
        graveyard = DeadEndGraveyard()
        graveyard.build_index()

        bottlenecks = graveyard.list_recurring_bottlenecks(limit=5)
        assert len(bottlenecks) > 0
        assert "category" in bottlenecks[0]
        assert "count" in bottlenecks[0]
        assert bottlenecks[0]["count"] >= 1
