from __future__ import annotations

import re
from typing import List, Optional
from agents.master_agent import heuristic_route
from schemas.chat import TaskType
from .schemas import JevCategory, JevDecision, JevExecutionRoute

_GREETING_WORDS = {"hi", "hello", "hey", "sup", "yo", "howdy", "good morning", "good afternoon", "good evening", "hello there"}

_TASK_MAP = {
    TaskType.CONVERSATION.value: (JevCategory.CONVERSATIONAL, JevExecutionRoute.DIRECT_FAST, False, False, False),
    TaskType.FACTUAL.value: (JevCategory.FACTUAL_RAG, JevExecutionRoute.MULTI_AGENT, False, True, False),
    TaskType.CURRENT_INFO.value: (JevCategory.FACTUAL_RAG, JevExecutionRoute.MULTI_AGENT, False, True, False),
    TaskType.RESEARCH.value: (JevCategory.CONFLICTING_SOURCES, JevExecutionRoute.MULTI_AGENT, False, True, False),
    TaskType.MATH.value: (JevCategory.QUANTITATIVE_MATH, JevExecutionRoute.MULTI_AGENT, False, True, True),
    TaskType.CODE.value: (JevCategory.CODE_AND_API, JevExecutionRoute.DIRECT_SANDBOX, False, False, True),
    TaskType.DOCUMENT.value: (JevCategory.FACTUAL_RAG, JevExecutionRoute.MULTI_AGENT_RAG, True, True, False),
    TaskType.REASONING.value: (JevCategory.LOGICAL_PUZZLE, JevExecutionRoute.MULTI_AGENT, False, True, False),
    TaskType.COMPARISON.value: (JevCategory.CONFLICTING_SOURCES, JevExecutionRoute.MULTI_AGENT, False, True, False),
    TaskType.SUMMARIZATION.value: (JevCategory.FACTUAL_RAG, JevExecutionRoute.MULTI_AGENT, False, True, False),
    TaskType.VERIFICATION.value: (JevCategory.CONFLICTING_SOURCES, JevExecutionRoute.MULTI_AGENT, False, True, False),
    TaskType.MULTI_STEP.value: (JevCategory.LOGICAL_PUZZLE, JevExecutionRoute.MULTI_AGENT, False, True, False),
}


def fallback_decision(query: str, document_ids: Optional[List[str]] = None) -> JevDecision:
    """Deterministic classifier used when JEV AI is unavailable or unconfigured."""
    has_docs = bool(document_ids)
    if has_docs:
        return JevDecision(
            category=JevCategory.FACTUAL_RAG,
            route=JevExecutionRoute.MULTI_AGENT_RAG,
            complexity="standard",
            requires_rag=True,
            requires_verification=True,
            requires_code_execution=False,
            confidence=None,
            reasoning="Document attached; deterministic fallback routed to MULTI_AGENT_RAG",
            is_fallback=True,
            latency_ms=1,
        )

    clean_text = re.sub(r"[^a-zA-Z\s]", "", query.lower()).strip()
    if clean_text in _GREETING_WORDS:
        return JevDecision(
            category=JevCategory.CONVERSATIONAL,
            route=JevExecutionRoute.DIRECT_FAST,
            complexity="low",
            requires_rag=False,
            requires_verification=False,
            requires_code_execution=False,
            confidence=None,
            reasoning="Greeting detected; deterministic fallback routed to DIRECT_FAST",
            is_fallback=True,
            latency_ms=1,
        )

    route_info = heuristic_route(query, document_ids)
    task_type = route_info.get("task_type", TaskType.FACTUAL.value) if route_info else TaskType.FACTUAL.value

    cat, route, req_rag, req_ver, req_code = _TASK_MAP.get(
        task_type,
        (JevCategory.FACTUAL_RAG, JevExecutionRoute.MULTI_AGENT, False, True, False),
    )

    return JevDecision(
        category=cat,
        route=route,
        complexity="low" if route == JevExecutionRoute.DIRECT_FAST else "standard",
        requires_rag=req_rag,
        requires_verification=req_ver,
        requires_code_execution=req_code,
        confidence=None,
        reasoning=f"Deterministic fallback classifier resolved query to {cat.value} -> {route.value}",
        is_fallback=True,
        latency_ms=1,
    )
