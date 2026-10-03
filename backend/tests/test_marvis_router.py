"""
MAARVIS / MARVIS Router Test Suite (Part 22 of the integration spec).

Covers:
  TEST 1  - "hi" in AUTO -> DIRECT_FAST, 0 JEV calls
  TEST 2  - "hello" in AUTO -> DIRECT_FAST, 0 JEV calls
  TEST 3  - Python code in AUTO -> DIRECT_SANDBOX, 0 JEV calls
  TEST 4  - Math query -> JEV called -> QUANTITATIVE_MATH -> MULTI_AGENT
  TEST 5  - News claim -> JEV called -> verification route
  TEST 6  - Attachment in AUTO -> MULTI_AGENT_RAG, 0 JEV calls
  TEST 7  - "hi" in MULTI_AGENT -> MULTI_AGENT, 0 JEV calls
  TEST 8  - Complex query in DIRECT -> DIRECT_FAST, 0 JEV calls
  TEST 9  - JEV timeout -> fallback, app continues
  TEST 10 - Malformed JEV response -> fallback
  TEST 11 - Unsupported JEV category -> safe fallback
  TEST 12 - Greeting/AST helpers unit tests
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import AsyncMock, patch

from marvis.router import _is_trivial_greeting, _is_executable_python, triage
from marvis.schemas import MarvisMode, MarvisRoute, RoutingEngine, JevCategory


# ---------------------------------------------------------------------------
# Unit: greeting detection
# ---------------------------------------------------------------------------

class TestGreetingDetection:
    def test_hi(self):
        assert _is_trivial_greeting("hi") is True

    def test_hello(self):
        assert _is_trivial_greeting("hello") is True

    def test_hey(self):
        assert _is_trivial_greeting("hey") is True

    def test_good_morning(self):
        assert _is_trivial_greeting("good morning") is True

    def test_good_afternoon(self):
        assert _is_trivial_greeting("good afternoon") is True

    def test_good_evening(self):
        assert _is_trivial_greeting("good evening") is True

    def test_hi_with_query_not_greeting(self):
        assert _is_trivial_greeting("Hi, can you verify whether this claim is true?") is False

    def test_hello_with_question_not_greeting(self):
        assert _is_trivial_greeting("Hello, what is quantum computing?") is False

    def test_factual_query_not_greeting(self):
        assert _is_trivial_greeting("Is 100 million equal to 10 crores?") is False

    def test_exclamation_hi(self):
        assert _is_trivial_greeting("hi!") is True


# ---------------------------------------------------------------------------
# Unit: Python AST detection
# ---------------------------------------------------------------------------

class TestPythonASTDetection:
    def test_simple_assignment_and_print(self):
        assert _is_executable_python("x = 15\ny = 27\nprint(x + y)") is True

    def test_inline_python(self):
        assert _is_executable_python("x = 15; y = 27; print(x + y)") is True

    def test_sentence_not_python(self):
        assert _is_executable_python("Is 100 million equal to 10 crores?") is False

    def test_greeting_not_python(self):
        assert _is_executable_python("hi") is False

    def test_claim_not_python(self):
        assert _is_executable_python("Can you tell me whether this news claim is true?") is False

    def test_syntax_error_not_python(self):
        assert _is_executable_python("def foo(") is False


# ---------------------------------------------------------------------------
# Triage: Stage 1 + 2 (no JEV calls)
# ---------------------------------------------------------------------------

class TestTriageStage1And2:

    @pytest.mark.asyncio
    async def test_1_hi_auto_direct_fast(self):
        """TEST 1: 'hi' in AUTO -> DIRECT_FAST, 0 JEV calls."""
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock) as mock_jev:
            decision = await triage("hi", MarvisMode.AUTO, [])
        assert decision.active_route == MarvisRoute.DIRECT_FAST
        mock_jev.assert_not_called()
        assert decision.routing_engine == RoutingEngine.STAGE2_GREETING

    @pytest.mark.asyncio
    async def test_2_hello_auto_direct_fast(self):
        """TEST 2: 'hello' in AUTO -> DIRECT_FAST, 0 JEV calls."""
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock) as mock_jev:
            decision = await triage("hello", MarvisMode.AUTO, [])
        assert decision.active_route == MarvisRoute.DIRECT_FAST
        mock_jev.assert_not_called()

    @pytest.mark.asyncio
    async def test_3_python_code_direct_sandbox(self):
        """TEST 3: Python code in AUTO -> DIRECT_SANDBOX, 0 JEV calls."""
        code = "x = 15\ny = 27\nprint(x + y)"
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock) as mock_jev:
            decision = await triage(code, MarvisMode.AUTO, [])
        assert decision.active_route == MarvisRoute.DIRECT_SANDBOX
        mock_jev.assert_not_called()
        assert decision.routing_engine == RoutingEngine.STAGE2_AST
        assert decision.requires_sandbox is True

    @pytest.mark.asyncio
    async def test_6_attachment_escalation(self):
        """TEST 6: File attachment in AUTO -> MULTI_AGENT_RAG, 0 JEV calls."""
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock) as mock_jev:
            decision = await triage("What was the Q3 revenue?", MarvisMode.AUTO, ["doc_abc123"])
        assert decision.active_route == MarvisRoute.MULTI_AGENT_RAG
        mock_jev.assert_not_called()
        assert decision.escalated_by_attachment is True
        assert decision.routing_engine == RoutingEngine.STAGE1_ATTACHMENT

    @pytest.mark.asyncio
    async def test_7_greeting_multi_agent_mode(self):
        """TEST 7: 'hi' in MULTI_AGENT -> MULTI_AGENT, 0 JEV calls."""
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock) as mock_jev:
            decision = await triage("hi", MarvisMode.MULTI_AGENT, [])
        assert decision.active_route == MarvisRoute.MULTI_AGENT
        mock_jev.assert_not_called()
        assert decision.routing_engine == RoutingEngine.STAGE1_USER_OVERRIDE

    @pytest.mark.asyncio
    async def test_8_complex_direct_mode(self):
        """TEST 8: Complex query in DIRECT -> DIRECT_FAST, 0 JEV calls."""
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock) as mock_jev:
            decision = await triage(
                "Explain the geopolitical implications of the Russia-Ukraine war in detail",
                MarvisMode.DIRECT,
                [],
            )
        assert decision.active_route == MarvisRoute.DIRECT_FAST
        mock_jev.assert_not_called()
        assert decision.routing_engine == RoutingEngine.STAGE1_USER_OVERRIDE


# ---------------------------------------------------------------------------
# Triage: Stage 3 (JEV + fallback)
# ---------------------------------------------------------------------------

class TestTriageStage3:

    @pytest.mark.asyncio
    async def test_4_quantitative_math_via_jev(self):
        """TEST 4: Math query -> JEV called -> QUANTITATIVE_MATH -> MULTI_AGENT."""
        mock_response = {
            "category": "QUANTITATIVE_MATH",
            "confidence": 0.91,
            "requires_rag": False,
            "requires_sandbox": False,
        }
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock, return_value=mock_response) as mock_jev:
            decision = await triage("Is 100 million equal to 10 crores?", MarvisMode.AUTO, [])
        mock_jev.assert_called_once()
        assert decision.category == JevCategory.QUANTITATIVE_MATH
        assert decision.active_route == MarvisRoute.MULTI_AGENT
        assert decision.routing_engine == RoutingEngine.STAGE3_JEV
        assert decision.confidence == pytest.approx(0.91)

    @pytest.mark.asyncio
    async def test_5_news_claim_via_jev(self):
        """TEST 5: News claim -> JEV called -> verification route."""
        mock_response = {
            "category": "FACTUAL_RAG",
            "confidence": 0.85,
            "requires_rag": True,
            "requires_sandbox": False,
        }
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock, return_value=mock_response) as mock_jev:
            decision = await triage(
                "Can you tell me whether this news claim is true?", MarvisMode.AUTO, []
            )
        mock_jev.assert_called_once()
        assert decision.active_route in (MarvisRoute.MULTI_AGENT_RAG, MarvisRoute.MULTI_AGENT)
        assert decision.routing_engine == RoutingEngine.STAGE3_JEV

    @pytest.mark.asyncio
    async def test_9_jev_timeout_fallback(self):
        """TEST 9: JEV returns None (timeout/network) -> fallback, app continues."""
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock, return_value=None) as mock_jev:
            decision = await triage("What is the capital of France?", MarvisMode.AUTO, [])
        mock_jev.assert_called_once()
        # Fallback must produce a valid, non-crashing route
        assert decision.active_route in (
            MarvisRoute.MULTI_AGENT,
            MarvisRoute.MULTI_AGENT_RAG,
            MarvisRoute.DIRECT_FAST,
            MarvisRoute.DIRECT_SANDBOX,
        )
        assert decision.routing_engine == RoutingEngine.STAGE3_FALLBACK

    @pytest.mark.asyncio
    async def test_10_malformed_jev_response_fallback(self):
        """TEST 10: JEV returns None (malformed/parse failure) -> fallback executes."""
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock, return_value=None):
            decision = await triage("What is the speed of light?", MarvisMode.AUTO, [])
        assert decision.routing_engine == RoutingEngine.STAGE3_FALLBACK
        assert decision.active_route is not None

    @pytest.mark.asyncio
    async def test_11_unsupported_jev_category_fallback(self):
        """TEST 11: JEV returns unsupported category -> safe fallback route."""
        bad_response = {
            "category": "SOME_FUTURE_UNKNOWN_CATEGORY_XYZ",
            "confidence": 0.7,
            "requires_rag": False,
            "requires_sandbox": False,
        }
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock, return_value=bad_response):
            decision = await triage("Tell me something", MarvisMode.AUTO, [])
        assert decision.routing_engine == RoutingEngine.STAGE3_FALLBACK
        assert decision.active_route is not None

    @pytest.mark.asyncio
    async def test_factual_rag_upgrades_to_rag_route(self):
        """FACTUAL_RAG + requires_rag=True -> MULTI_AGENT_RAG."""
        mock_response = {
            "category": "FACTUAL_RAG",
            "confidence": 0.80,
            "requires_rag": True,
            "requires_sandbox": False,
        }
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock, return_value=mock_response):
            decision = await triage("Who is the current CEO of Apple?", MarvisMode.AUTO, [])
        assert decision.active_route == MarvisRoute.MULTI_AGENT_RAG
        assert decision.requires_rag is True

    @pytest.mark.asyncio
    async def test_code_and_api_route(self):
        """CODE_AND_API -> MULTI_AGENT."""
        mock_response = {
            "category": "CODE_AND_API",
            "confidence": 0.92,
            "requires_rag": False,
            "requires_sandbox": True,
        }
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock, return_value=mock_response):
            decision = await triage(
                "How do I fix a race condition in Python asyncio?", MarvisMode.AUTO, []
            )
        assert decision.active_route == MarvisRoute.MULTI_AGENT

    @pytest.mark.asyncio
    async def test_conversational_direct_fast(self):
        """CONVERSATIONAL -> DIRECT_FAST."""
        mock_response = {
            "category": "CONVERSATIONAL",
            "confidence": 0.99,
            "requires_rag": False,
            "requires_sandbox": False,
        }
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock, return_value=mock_response):
            decision = await triage("What do you think about AI ethics?", MarvisMode.AUTO, [])
        assert decision.active_route == MarvisRoute.DIRECT_FAST