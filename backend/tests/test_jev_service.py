from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.jev.schemas import JevCategory, JevExecutionRoute
from services.jev.fallback import fallback_decision
from services.jev.decision_service import get_jev_decision_service


def test_fallback_greeting():
    dec = fallback_decision("hello there")
    assert dec.category == JevCategory.CONVERSATIONAL
    assert dec.route == JevExecutionRoute.DIRECT_FAST
    assert dec.is_fallback is True


def test_fallback_attachment():
    dec = fallback_decision("What was the revenue?", document_ids=["doc_123"])
    assert dec.category == JevCategory.FACTUAL_RAG
    assert dec.route == JevExecutionRoute.MULTI_AGENT_RAG
    assert dec.requires_rag is True


def test_fallback_math():
    dec = fallback_decision("Calculate 17 * 24 + 19")
    assert dec.category == JevCategory.QUANTITATIVE_MATH
    assert dec.route == JevExecutionRoute.MULTI_AGENT


@pytest.mark.asyncio
async def test_decision_service_with_remote_jev():
    service = get_jev_decision_service()
    mock_resp = {
        "category": JevCategory.QUANTITATIVE_MATH,
        "route": JevExecutionRoute.MULTI_AGENT,
        "complexity": "standard",
        "requires_rag": False,
        "requires_verification": True,
        "requires_code_execution": True,
        "confidence": 0.94,
        "reasoning": "Mocked test",
        "is_fallback": False,
        "latency_ms": 110,
    }
    from services.jev.schemas import JevDecision
    with patch.object(service.client, "classify", new_callable=AsyncMock, return_value=JevDecision(**mock_resp)):
        res = await service.decide("Is 100 million equal to 10 crores?")
    assert res.category == JevCategory.QUANTITATIVE_MATH
    assert res.confidence == 0.94
    assert res.is_fallback is False


@pytest.mark.asyncio
async def test_decision_service_fallback_on_client_none():
    service = get_jev_decision_service()
    with patch.object(service.client, "classify", new_callable=AsyncMock, return_value=None):
        res = await service.decide("What is the capital of Japan?")
    assert res.is_fallback is True
    assert res.route in (JevExecutionRoute.MULTI_AGENT, JevExecutionRoute.DIRECT_FAST)
