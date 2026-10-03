from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from models.llm import get_llm
from schemas.chat import TaskType
from tools.calculator import looks_like_math, is_incomplete_expression

GREETINGS = {"hi", "hello", "hey", "yo", "sup", "good morning", "good evening", "good afternoon", "thanks", "thank you"}

ROUTER_SYSTEM = """You classify a user request for an AI assistant.
Return JSON only:
{
  "task_type": "conversation|factual|current_information|research|math|code|document|reasoning|comparison|summarization|verification|multi_step",
  "requires_web": false,
  "requires_rag": false,
  "requires_math": false,
  "requires_code": false,
  "requires_verification": false,
  "verification_level": 0,
  "reason": "short"
}
Rules:
- greetings and small talk: conversation, all flags false
- conceptual explanations (recursion, what is a list): factual or conversation, web false unless current data is needed
- latest/current/news/who is currently: current_information, requires_web true, requires_verification true, level 2
- research/compare latest frameworks: research, web true, verification true, level 3
- arithmetic: math
- code questions: code
- uploaded document questions: document, requires_rag true
- "is this true" / fact check: verification
Never enable every agent. Choose the minimum path.
"""


def heuristic_route(message: str, document_ids: List[str] | None = None, code: str | None = None) -> Dict[str, Any] | None:
    text = message.strip()
    lowered = text.lower().strip()
    if document_ids:
        return {
            "task_type": TaskType.DOCUMENT.value,
            "requires_web": False,
            "requires_rag": True,
            "requires_math": False,
            "requires_code": False,
            "requires_verification": False,
            "verification_level": 0,
            "reason": "Document context attached.",
        }
    if code or _looks_like_code(text):
        return {
            "task_type": TaskType.CODE.value,
            "requires_web": False,
            "requires_rag": False,
            "requires_math": False,
            "requires_code": True,
            "requires_verification": False,
            "verification_level": 0,
            "reason": "Code analysis requested.",
        }
    if lowered in GREETINGS or lowered.rstrip("!") in GREETINGS:
        return {
            "task_type": TaskType.CONVERSATION.value,
            "requires_web": False,
            "requires_rag": False,
            "requires_math": False,
            "requires_code": False,
            "requires_verification": False,
            "verification_level": 0,
            "reason": "Greeting.",
        }
    if looks_like_math(text) or is_incomplete_expression(text):
        return {
            "task_type": TaskType.MATH.value,
            "requires_web": False,
            "requires_rag": False,
            "requires_math": True,
            "requires_code": False,
            "requires_verification": False,
            "verification_level": 0,
            "reason": "Mathematical expression.",
        }
    if lowered.startswith("research ") or "research the latest" in lowered:
        return {
            "task_type": TaskType.RESEARCH.value,
            "requires_web": True,
            "requires_rag": False,
            "requires_math": False,
            "requires_code": False,
            "requires_verification": True,
            "verification_level": 3,
            "reason": "Multi-source research request.",
        }
    if any(p in lowered for p in ("latest", "current ceo", "who is the current", "what happened today", "news today")):
        return {
            "task_type": TaskType.CURRENT_INFO.value,
            "requires_web": True,
            "requires_rag": False,
            "requires_math": False,
            "requires_code": False,
            "requires_verification": True,
            "verification_level": 2,
            "reason": "Current information request.",
        }
    if any(p in lowered for p in ("is this true", "is it true", "fact check", "verify this", "is this claim")):
        return {
            "task_type": TaskType.VERIFICATION.value,
            "requires_web": True,
            "requires_rag": False,
            "requires_math": False,
            "requires_code": False,
            "requires_verification": True,
            "verification_level": 3,
            "reason": "Explicit verification request.",
        }
    # Fast path for common explanatory/informational queries to avoid remote router latency
    common_starters = (
        "explain", "what is", "what are", "how does", "how do", "how to", "why is", "why does",
        "why do", "tell me about", "describe", "write a", "write an", "summarize", "can you explain",
        "definition of", "difference between", "give me an overview", "history of"
    )
    if any(lowered.startswith(prefix) for prefix in common_starters):
        return {
            "task_type": TaskType.FACTUAL.value,
            "requires_web": False,
            "requires_rag": False,
            "requires_math": False,
            "requires_code": False,
            "requires_verification": True,
            "verification_level": 1,
            "reason": "General factual/conceptual explanation.",
        }
    return None


def _looks_like_code(text: str) -> bool:
    if "```" in text:
        return True
    lowered = text.lower()
    if "is this" in lowered and "code" in lowered:
        return True
    if any(k in text for k in ("public static void", "def ", "function ", "#include", "console.log")):
        return True
    return False


async def route_intent(message: str, document_ids: List[str] | None = None, code: str | None = None) -> Dict[str, Any]:
    heuristic = heuristic_route(message, document_ids, code)
    if heuristic:
        return heuristic
    llm = get_llm()
    raw = await llm.complete(
        [
            {"role": "system", "content": ROUTER_SYSTEM},
            {"role": "user", "content": message},
        ],
        temperature=0,
        max_tokens=400,
        json_mode=True,
    )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(match.group(0)) if match else {}
    task = data.get("task_type") or TaskType.FACTUAL.value
    return {
        "task_type": task,
        "requires_web": bool(data.get("requires_web")),
        "requires_rag": bool(data.get("requires_rag")),
        "requires_math": bool(data.get("requires_math")),
        "requires_code": bool(data.get("requires_code")),
        "requires_verification": bool(data.get("requires_verification")),
        "verification_level": int(data.get("verification_level") or 0),
        "reason": data.get("reason") or "",
    }
