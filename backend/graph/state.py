from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from utils.events import EventBus


class ConversationState(TypedDict, total=False):
    conversation_id: str
    user_message: str
    messages: List[Dict[str, str]]
    document_ids: List[str]
    code: Optional[str]
    language: Optional[str]
    web_enabled: Optional[bool]

    intent: str
    task_type: str
    requires_web: bool
    requires_rag: bool
    requires_math: bool
    requires_code: bool
    requires_verification: bool
    verification_level: int
    gate_decision: str

    research_results: Dict[str, Any]
    document_context: List[Dict[str, Any]]
    calculation_result: Dict[str, Any]
    code_result: Dict[str, Any]

    draft_answer: str
    claims: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    claim_results: List[Dict[str, Any]]
    contradictions: Dict[str, Any]
    critic_result: Dict[str, Any]
    correction_count: int

    final_answer: str
    verification: Dict[str, Any]
    sources: List[Dict[str, Any]]
    agent_events: List[Dict[str, Any]]
    errors: List[str]
    skip_llm_finalize: bool

    # MARVIS routing and execution metadata (annotated by dispatcher)
    marvis_route: str
    marvis_decision: Dict[str, Any]
    execution_id: str
    execution_trace: Dict[str, Any]


def empty_state() -> ConversationState:
    return {
        "messages": [],
        "document_ids": [],
        "claims": [],
        "evidence": [],
        "claim_results": [],
        "sources": [],
        "agent_events": [],
        "errors": [],
        "correction_count": 0,
        "verification": {"performed": False},
        "skip_llm_finalize": False,
    }
