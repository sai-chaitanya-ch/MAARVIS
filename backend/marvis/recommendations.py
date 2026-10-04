from __future__ import annotations

from typing import Any, Dict, List, Optional
from marvis.schemas import MarvisMode, RequiredCapabilities
from utils.logging import get_logger

log = get_logger(__name__)


def generate_recommendations(
    required: RequiredCapabilities,
    connected_caps: Dict[str, Any],
    query: str,
    mode: MarvisMode = MarvisMode.AUTO,
    has_attachment: bool = False,
) -> List[Dict[str, Any]]:
    """Context-aware Smart API Recommendation Engine.

    Rules:
    - Never show generic 'Connect all APIs'.
    - If current information query and web search is not connected:
        Recommend Web Search.
    - If complex routing / logical puzzle / conflicting sources query and JEV not connected:
        Recommend JEV.
    - If document query and RAG is available:
        Do NOT recommend web search unless external verification materially helps.
    - If document query and vector store is NOT connected:
        Recommend Vector Store.
    - If code execution required and sandbox not available:
        Recommend AST Sandbox.
    - If simple greeting or general reasoning:
        Do NOT recommend anything.
    """
    clean_query = query.strip()
    q_lower = clean_query.lower()

    # Rule: Direct mode or trivial greeting needs no recommendations
    if mode == MarvisMode.DIRECT:
        return []

    from marvis.capabilities import is_trivial_greeting
    if is_trivial_greeting(clean_query):
        return []

    recommendations: List[Dict[str, Any]] = []

    web_connected = bool(connected_caps.get("web_search", {}).get("connected"))
    jev_connected = bool(connected_caps.get("jev", {}).get("connected"))
    rag_connected = bool(connected_caps.get("rag", {}).get("connected"))
    sandbox_connected = bool(connected_caps.get("sandbox", {}).get("connected"))

    # 1. Web Search recommendation:
    # Only if web_search is required AND not connected
    if required.web_search and not web_connected:
        # Check document constraint:
        # If document attached and user did not explicitly ask for online/web search, suppress web recommendation
        if has_attachment and not any(w in q_lower for w in ["online", "web", "internet", "google"]):
            pass
        else:
            recommendations.append(
                {
                    "provider": "tavily",
                    "name": "Web Search (Tavily)",
                    "reason": "Current information and independent external sources are unavailable. Connect Web Search (Tavily) to verify live information.",
                    "action_label": "Connect Web Search",
                    "category": "web_search",
                }
            )

    # 2. JEV AI recommendation:
    # Only if JEV capability is beneficial (complex query, puzzle, conflicting claims) AND not connected
    if required.jev and not jev_connected:
        recommendations.append(
            {
                "provider": "jev",
                "name": "JEV AI",
                "reason": "Complex decision triage would benefit from JEV AI semantic classification.",
                "action_label": "Connect JEV AI",
                "category": "jev",
            }
        )

    # 3. Document Vector Store recommendation:
    # If user provided a document or asks document query, but vector store (Supabase pgvector) is offline
    if (has_attachment or required.rag) and not rag_connected:
        recommendations.append(
            {
                "provider": "rag",
                "name": "Document Vector Store",
                "reason": "Document retrieval requires an active vector database (Supabase pgvector).",
                "action_label": "Configure Vector Store",
                "category": "rag",
            }
        )

    # 4. AST Sandbox recommendation:
    if required.code_execution and not sandbox_connected:
        recommendations.append(
            {
                "provider": "sandbox",
                "name": "AST Sandbox",
                "reason": "Deterministic code execution and numeric verification requires sandbox capability.",
                "action_label": "Enable Sandbox",
                "category": "sandbox",
            }
        )

    return recommendations
