"""
Phase 2 Acceptance Test Suite — MARVIS Orchestration & Optional Capabilities.
Verifies the 5 graceful degradation tiers and smart recommendation engine.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

import pytest

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from marvis.schemas import (
    AgentStatus,
    JevCategory,
    MarvisMode,
    MarvisRoute,
    RequiredCapabilities,
    RoutingEngine,
    TriageDecision,
)
from marvis.capabilities import detect_capabilities, is_trivial_greeting, is_executable_python
from marvis.recommendations import generate_recommendations
from marvis.router import triage
from marvis.dispatcher import dispatch


# ---------------------------------------------------------------------------
# Test 1: Capability Detection Unit Tests
# ---------------------------------------------------------------------------

class TestCapabilityDetection:
    def test_greeting_only_needs_basic_llm(self):
        caps = detect_capabilities("hello there", MarvisMode.AUTO)
        assert caps.basic_llm is True
        assert caps.rag is False
        assert caps.web_search is False
        assert caps.code_execution is False
        assert caps.multi_agent_reasoning is False
        assert caps.verification is False
        assert caps.jev is False

    def test_current_info_detects_web_search(self):
        caps = detect_capabilities("Who is the current CEO of Microsoft in 2026?", MarvisMode.AUTO)
        assert caps.web_search is True
        assert caps.verification is True

    def test_attachment_detects_rag(self):
        caps = detect_capabilities("What is the revenue for Q3?", MarvisMode.AUTO, document_ids=["doc_123"])
        assert caps.rag is True
        assert caps.web_search is False  # Doc query without temporal/online cues should NOT need web search

    def test_python_code_detects_code_execution(self):
        code = "x = 10\ny = 25\nprint(x * y)"
        caps = detect_capabilities(code, MarvisMode.AUTO)
        assert caps.code_execution is True

    def test_complex_logic_puzzle_detects_jev(self):
        puzzle = "If five painters paint five houses in five days, compare the trade-offs and step by step explain how many days ten painters take for twenty houses?"
        caps = detect_capabilities(puzzle, MarvisMode.AUTO)
        assert caps.jev is True
        assert caps.multi_agent_reasoning is True


# ---------------------------------------------------------------------------
# Test 2: Smart Recommendation Engine Tests
# ---------------------------------------------------------------------------

class TestSmartRecommendationEngine:
    def test_greeting_recommends_nothing(self):
        connected = {
            "ai_provider": {"connected": True},
            "web_search": {"connected": False},
            "jev": {"connected": False},
            "rag": {"connected": False},
            "sandbox": {"connected": True},
        }
        req = RequiredCapabilities(basic_llm=True)
        recs = generate_recommendations(req, connected, "hi", MarvisMode.AUTO)
        assert recs == []

    def test_direct_mode_recommends_nothing(self):
        connected = {
            "ai_provider": {"connected": True},
            "web_search": {"connected": False},
            "jev": {"connected": False},
            "rag": {"connected": True},
            "sandbox": {"connected": True},
        }
        req = RequiredCapabilities(basic_llm=True, web_search=True)
        recs = generate_recommendations(req, connected, "What is the latest news?", MarvisMode.DIRECT)
        assert recs == []

    def test_current_info_missing_web_search_recommends_tavily(self):
        connected = {
            "ai_provider": {"connected": True},
            "web_search": {"connected": False},
            "jev": {"connected": False},
            "rag": {"connected": True},
            "sandbox": {"connected": True},
        }
        req = RequiredCapabilities(basic_llm=True, web_search=True)
        recs = generate_recommendations(req, connected, "What is the latest stock price today?", MarvisMode.AUTO)
        assert len(recs) == 1
        assert recs[0]["provider"] == "tavily"
        assert "Current information and independent external sources are unavailable" in recs[0]["reason"]
        assert recs[0]["action_label"] == "Connect Web Search"

    def test_document_query_does_not_recommend_web_search(self):
        connected = {
            "ai_provider": {"connected": True},
            "web_search": {"connected": False},
            "jev": {"connected": True},
            "rag": {"connected": True},
            "sandbox": {"connected": True},
        }
        req = RequiredCapabilities(basic_llm=True, rag=True, web_search=False)
        recs = generate_recommendations(req, connected, "Summarize the attached contract", MarvisMode.AUTO, has_attachment=True)
        # Should NOT recommend web search
        web_recs = [r for r in recs if r["provider"] == "tavily"]
        assert len(web_recs) == 0

    def test_complex_query_missing_jev_recommends_jev(self):
        connected = {
            "ai_provider": {"connected": True},
            "web_search": {"connected": True},
            "jev": {"connected": False},
            "rag": {"connected": True},
            "sandbox": {"connected": True},
        }
        req = RequiredCapabilities(basic_llm=True, jev=True, multi_agent_reasoning=True)
        recs = generate_recommendations(req, connected, "Complex multi-variable analysis with contradictory hypotheses", MarvisMode.AUTO)
        jev_recs = [r for r in recs if r["provider"] == "jev"]
        assert len(jev_recs) == 1
        assert "JEV AI" in jev_recs[0]["name"]
        assert jev_recs[0]["action_label"] == "Connect JEV AI"


# ---------------------------------------------------------------------------
# Test 3: Tier 1 — Basic (Gemini / Provider Only, No Optional Keys)
# ---------------------------------------------------------------------------

class TestTier1BasicProviderOnly:
    @pytest.mark.asyncio
    async def test_basic_provider_only_triage_and_dispatch(self):
        """When JEV, Tavily, and external keys are absent, system triages deterministically

        and executes without failure.
        """
        # Patch JEV to simulate absent/unconfigured key
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock, return_value=None):
            decision = await triage("What is photosynthesis?", MarvisMode.AUTO, [])

        assert decision.routing_engine == RoutingEngine.STAGE3_FALLBACK
        assert decision.confidence is None  # NO fake confidence
        assert decision.active_route in {MarvisRoute.MULTI_AGENT, MarvisRoute.MULTI_AGENT_RAG, MarvisRoute.DIRECT_FAST}

        # Dispatch should produce valid state and trace
        mock_workflow_result = {
            "final_answer": "Photosynthesis is the process by which green plants create food.",
            "draft_answer": "Photosynthesis is the process by which green plants create food.",
            "sources": [],
            "claim_results": [],
            "agent_events": [{"event": "generating", "status": "completed", "duration_ms": 120}],
        }
        with patch("marvis.dispatcher.run_workflow", new_callable=AsyncMock, return_value=mock_workflow_result):
            state = await dispatch(decision, {"user_message": "What is photosynthesis?"})

        assert state["marvis_route"] == decision.active_route.value
        trace = state["execution_trace"]
        assert trace["status"] in {"UNVERIFIED", "DIRECT_ANSWER"}
        # JEV record should indicate fallback
        jev_record = next(a for a in trace["agents"] if a["agent_id"] == "jev_decision")
        assert jev_record["model"] == "deterministic-classifier"
        assert jev_record["status"] == AgentStatus.COMPLETED


# ---------------------------------------------------------------------------
# Test 4: Tier 2 — More Capable (Provider + JEV)
# ---------------------------------------------------------------------------

class TestTier2ProviderPlusJev:
    @pytest.mark.asyncio
    async def test_jev_enabled_triage_and_trace(self):
        """When JEV is configured, JEV returns calibrated probability and category."""
        mock_jev = {
            "category": "LOGICAL_PUZZLE",
            "confidence": 0.94,
            "requires_rag": False,
            "requires_sandbox": False,
        }
        with patch("marvis.router.classify_with_jev", new_callable=AsyncMock, return_value=mock_jev):
            decision = await triage("Solve this logic riddle step by step", MarvisMode.AUTO, [])

        assert decision.routing_engine == RoutingEngine.STAGE3_JEV
        assert decision.category == JevCategory.LOGICAL_PUZZLE
        assert decision.confidence == 0.94
        assert decision.active_route == MarvisRoute.MULTI_AGENT

        mock_workflow_result = {
            "final_answer": "Step 1: ... Step 2: ...",
            "sources": [],
            "claim_results": [],
            "agent_events": [],
        }
        with patch("marvis.dispatcher.run_workflow", new_callable=AsyncMock, return_value=mock_workflow_result):
            state = await dispatch(decision, {"user_message": "Solve this logic riddle step by step"})

        trace = state["execution_trace"]
        jev_record = next(a for a in trace["agents"] if a["agent_id"] == "jev_decision")
        assert jev_record["status"] == AgentStatus.COMPLETED
        assert jev_record["model"] == "typesafe/jev-latest"
        assert jev_record["gateway"] == "TypeSafe SystemOne API"
        assert "0.94" in jev_record["output_summary"]


# ---------------------------------------------------------------------------
# Test 5: Tier 3 — Research Capable (Provider + Web Search)
# ---------------------------------------------------------------------------

class TestTier3ResearchCapable:
    @pytest.mark.asyncio
    async def test_web_search_active_gathers_sources(self):
        """When web search is available, real sources are gathered and verified."""
        decision = TriageDecision(
            selected_mode=MarvisMode.AUTO,
            active_route=MarvisRoute.MULTI_AGENT,
            category=JevCategory.CONFLICTING_SOURCES,
            reasoning="Current topic requiring external evidence",
            confidence=0.89,
            routing_engine=RoutingEngine.STAGE3_JEV,
        )
        mock_sources = [
            {"id": "s1", "title": "News Site", "url": "https://reuters.com/news1", "source_type": "web", "tier": 2}
        ]
        mock_claims = [
            {"claim_id": "c1", "text": "Claim 1", "status": "SUPPORTED", "confidence": 0.92}
        ]
        mock_workflow_result = {
            "final_answer": "According to Reuters, ...",
            "sources": mock_sources,
            "claim_results": mock_claims,
            "requires_web": True,
            "agent_events": [{"event": "research", "status": "completed", "duration_ms": 250}],
        }
        with patch("marvis.dispatcher.run_workflow", new_callable=AsyncMock, return_value=mock_workflow_result):
            state = await dispatch(decision, {"user_message": "Who won the 2026 game?", "web_enabled": True})

        trace = state["execution_trace"]
        assert trace["status"] == "VERIFIED"
        research_rec = next(a for a in trace["agents"] if a["agent_id"] == "researcher_agent")
        assert research_rec["status"] == AgentStatus.COMPLETED
        assert "1 web source" in research_rec["output_summary"]

    @pytest.mark.asyncio
    async def test_web_search_missing_degrades_gracefully_with_recommendation(self):
        """When web search is missing, researcher is SKIPPED, answer is UNVERIFIED,

        and Tavily recommendation is contextually generated.
        """
        decision = TriageDecision(
            selected_mode=MarvisMode.AUTO,
            active_route=MarvisRoute.MULTI_AGENT,
            category=JevCategory.CONFLICTING_SOURCES,
            reasoning="Current topic but web search unavailable",
            confidence=None,
            routing_engine=RoutingEngine.STAGE3_FALLBACK,
        )
        mock_workflow_result = {
            "final_answer": "Based on model knowledge, ...",
            "sources": [],
            "claim_results": [],
            "requires_web": True,
            "agent_events": [],  # No research event ran
        }
        with patch("marvis.dispatcher.run_workflow", new_callable=AsyncMock, return_value=mock_workflow_result):
            with patch("marvis.dispatcher.get_system_capabilities", return_value={
                "ai_provider": {"connected": True},
                "web_search": {"connected": False},
                "jev": {"connected": False},
                "rag": {"connected": True},
                "sandbox": {"connected": True},
            }):
                state = await dispatch(decision, {"user_message": "What is the latest update today?"})

        trace = state["execution_trace"]
        assert trace["status"] == "UNVERIFIED"
        research_rec = next(a for a in trace["agents"] if a["agent_id"] == "researcher_agent")
        assert research_rec["status"] == AgentStatus.SKIPPED
        assert "web search provider not configured" in research_rec["output_summary"].lower()

        # Check recommendations
        recs = trace["recommendations"]
        assert any(r["provider"] == "tavily" for r in recs)


# ---------------------------------------------------------------------------
# Test 6: Tier 4 — Document Capable (Provider + Embeddings + Vector Store)
# ---------------------------------------------------------------------------

class TestTier4DocumentCapable:
    @pytest.mark.asyncio
    async def test_attachment_auto_escalates_to_rag(self):
        """File attachment automatically escalates to MULTI_AGENT_RAG without JEV."""
        decision = await triage("What does section 4 say?", MarvisMode.AUTO, document_ids=["contract_doc"])
        assert decision.active_route == MarvisRoute.MULTI_AGENT_RAG
        assert decision.escalated_by_attachment is True
        assert decision.routing_engine == RoutingEngine.STAGE1_ATTACHMENT

        mock_context = [
            {"chunk_id": "chk_1", "text": "Section 4 covers warranties.", "page": 3, "score": 0.91, "source": "contract.pdf"}
        ]
        mock_claims = [
            {"claim_id": "c1", "text": "Section 4 covers warranties.", "status": "SUPPORTED", "page": 3, "source": "contract.pdf"}
        ]
        mock_workflow_result = {
            "final_answer": "Section 4 explicitly covers warranties.",
            "document_context": mock_context,
            "sources": [{"id": "chk_1", "title": "contract.pdf", "source_type": "document"}],
            "claim_results": mock_claims,
            "requires_rag": True,
            "agent_events": [{"event": "retrieval", "status": "completed", "duration_ms": 35}],
        }
        with patch("marvis.dispatcher.run_workflow", new_callable=AsyncMock, return_value=mock_workflow_result):
            state = await dispatch(decision, {"user_message": "What does section 4 say?", "document_ids": ["contract_doc"]})

        trace = state["execution_trace"]
        assert trace["status"] == "VERIFIED"
        rag_rec = next(a for a in trace["agents"] if a["agent_id"] == "rag_agent")
        assert rag_rec["status"] == AgentStatus.COMPLETED
        assert trace["evidence"]["documents_used"] == 1
        assert len(trace["evidence"]["relevant_chunks"]) == 1
