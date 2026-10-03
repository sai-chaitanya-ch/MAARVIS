from __future__ import annotations

from typing import Any, Dict

from schemas.chat import GateDecision, TaskType, VerificationLevel

CURRENT_HINTS = (
    "latest",
    "current",
    "today",
    "now",
    "this year",
    "released",
    "who is the",
    "ceo",
    "president",
    "news",
    "happened",
)

FACT_HINTS = (
    "is it true",
    "is this true",
    "verify",
    "fact check",
    "confirm",
    "claim",
)

SENSITIVE = (
    "medical",
    "legal",
    "election",
    "stock",
    "gdp",
    "inflation",
    "study shows",
    "according to",
)


def decide_gate(
    task_type: str,
    requires_web: bool,
    user_message: str,
) -> Dict[str, Any]:
    text = user_message.lower()
    if task_type in {TaskType.CONVERSATION.value, TaskType.MATH.value}:
        if task_type == TaskType.MATH.value and ("=" in text or "is " in text) and not text.strip().endswith("="):
            return {
                "decision": GateDecision.NOT_REQUIRED.value,
                "level": VerificationLevel.NONE.value,
                "reason": "Deterministic calculation; no external verification.",
            }
        return {
            "decision": GateDecision.NOT_REQUIRED.value,
            "level": VerificationLevel.NONE.value,
            "reason": "Conversational or deterministic task.",
        }
    if task_type in {TaskType.CURRENT_INFO.value, TaskType.RESEARCH.value, TaskType.VERIFICATION.value}:
        level = VerificationLevel.DEEP if task_type == TaskType.RESEARCH.value else VerificationLevel.MULTI_SOURCE
        return {
            "decision": GateDecision.REQUIRED.value,
            "level": int(level),
            "reason": "External factual claims require independent verification.",
        }
    if any(h in text for h in FACT_HINTS) or any(h in text for h in CURRENT_HINTS) or requires_web:
        return {
            "decision": GateDecision.REQUIRED.value,
            "level": VerificationLevel.MULTI_SOURCE.value,
            "reason": "Current or checkable factual content.",
        }
    if task_type in {TaskType.COMPARISON.value, TaskType.FACTUAL.value} or any(h in text for h in SENSITIVE):
        return {
            "decision": GateDecision.RECOMMENDED.value,
            "level": VerificationLevel.BASIC.value,
            "reason": "Factual explanation may benefit from verification.",
        }
    if task_type == TaskType.DOCUMENT.value:
        return {
            "decision": GateDecision.NOT_REQUIRED.value,
            "level": VerificationLevel.NONE.value,
            "reason": "Document summary uses provided content as data, not external facts.",
        }
    if task_type == TaskType.CODE.value:
        return {
            "decision": GateDecision.NOT_REQUIRED.value,
            "level": VerificationLevel.NONE.value,
            "reason": "Code analysis uses sandbox/tools rather than web verification.",
        }
    return {
        "decision": GateDecision.NOT_REQUIRED.value,
        "level": VerificationLevel.NONE.value,
        "reason": "No independent factual verification required.",
    }
