from __future__ import annotations

from typing import Literal

from graph.state import ConversationState


def after_route(state: ConversationState) -> Literal["math", "code", "rag", "research", "general"]:
    if state.get("requires_math"):
        return "math"
    if state.get("requires_code"):
        return "code"
    if state.get("requires_rag"):
        return "rag"
    if state.get("requires_web") or state.get("task_type") in {
        "research",
        "current_information",
        "verification",
        "comparison",
    }:
        return "research"
    return "general"


def after_gate(state: ConversationState) -> Literal["verify", "finalize"]:
    if state.get("gate_decision") in {"REQUIRED", "RECOMMENDED"} and not state.get("skip_llm_finalize"):
        if state.get("task_type") == "math":
            return "finalize"
        return "verify"
    return "finalize"


def after_critic(state: ConversationState) -> Literal["correct", "finalize"]:
    if state.get("correction_count", 0) >= 3:
        return "finalize"
    verification = state.get("verification") or {}
    critic = state.get("critic_result") or {}
    status = verification.get("status")
    if status in {"CONTRADICTED", "INSUFFICIENT_EVIDENCE", "PARTIALLY_VERIFIED"} and critic.get("ok") is False:
        return "correct"
    if status in {"CONTRADICTED"} and state.get("correction_count", 0) < 3:
        return "correct"
    issues = critic.get("issues") or []
    if issues and state.get("correction_count", 0) < 2:
        return "correct"
    return "finalize"
