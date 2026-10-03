from __future__ import annotations

from typing import Dict, Any

from agents.master_agent import heuristic_route
from schemas.chat import TaskType

# Map existing TaskType to JEV categories
_TASK_TO_CATEGORY: Dict[str, str] = {
    TaskType.CONVERSATION.value: "CONVERSATIONAL",
    TaskType.FACTUAL.value: "FACTUAL_RAG",
    TaskType.CURRENT_INFO.value: "FACTUAL_RAG",
    TaskType.RESEARCH.value: "CONFLICTING_SOURCES",
    TaskType.MATH.value: "QUANTITATIVE_MATH",
    TaskType.CODE.value: "CODE_AND_API",
    TaskType.DOCUMENT.value: "FACTUAL_RAG",
    TaskType.REASONING.value: "LOGICAL_PUZZLE",
    TaskType.COMPARISON.value: "CONFLICTING_SOURCES",
    TaskType.SUMMARIZATION.value: "FACTUAL_RAG",
    TaskType.VERIFICATION.value: "CONFLICTING_SOURCES",
    TaskType.MULTI_STEP.value: "LOGICAL_PUZZLE",
}


def classify_fallback(query: str, document_ids=None) -> Dict[str, Any]:
    """Use existing heuristic router to classify when JEV is unavailable.

    Returns a dict with keys ``category``, ``confidence``, ``requires_rag``,
    ``requires_sandbox`` mirroring the shape returned by ``classify_with_jev``.
    """
    route = heuristic_route(query, document_ids)
    if route:
        task_type = route.get("task_type", TaskType.FACTUAL.value)
    else:
        # Cannot determine without LLM; default to safe MULTI_AGENT path
        task_type = TaskType.FACTUAL.value

    category = _TASK_TO_CATEGORY.get(task_type, "FACTUAL_RAG")
    requires_rag = bool(document_ids) or task_type == TaskType.DOCUMENT.value
    requires_sandbox = task_type == TaskType.CODE.value

    return {
        "category": category,
        "confidence": None,
        "requires_rag": requires_rag,
        "requires_sandbox": requires_sandbox,
    }
