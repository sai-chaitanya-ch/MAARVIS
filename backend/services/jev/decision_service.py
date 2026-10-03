from __future__ import annotations

from typing import List, Optional
from utils.logging import get_logger
from .client import get_jev_client
from .fallback import fallback_decision
from .schemas import JevDecision

log = get_logger(__name__)


class JevDecisionService:
    def __init__(self) -> None:
        self.client = get_jev_client()

    async def decide(self, query: str, document_ids: Optional[List[str]] = None) -> JevDecision:
        """Execute decision layer: try remote JEV AI API first, gracefully fall back on failure."""
        # When documents are attached, document grounded retrieval is deterministically required
        if document_ids:
            return fallback_decision(query, document_ids)

        decision = await self.client.classify(query)
        if decision is not None:
            log.info(
                "jev_decision_success",
                extra={
                    "category": decision.category.value,
                    "route": decision.route.value,
                    "confidence": decision.confidence,
                    "latency_ms": decision.latency_ms,
                },
            )
            return decision

        fallback = fallback_decision(query, document_ids)
        log.info(
            "jev_decision_fallback",
            extra={
                "category": fallback.category.value,
                "route": fallback.route.value,
            },
        )
        return fallback


_decision_service: Optional[JevDecisionService] = None


def get_jev_decision_service() -> JevDecisionService:
    global _decision_service
    if _decision_service is None:
        _decision_service = JevDecisionService()
    return _decision_service
