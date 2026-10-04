from __future__ import annotations

import ast
import re
from typing import List, Optional

from marvis.schemas import (
    JevCategory,
    MarvisMode,
    MarvisRoute,
    RequiredCapabilities,
    RoutingEngine,
    TriageDecision,
)
from marvis.capabilities import (
    detect_capabilities,
    is_executable_python,
    is_trivial_greeting,
)
from marvis.jev_client import classify_with_jev
from marvis.fallback_classifier import classify_fallback
from utils.logging import get_logger

log = get_logger(__name__)

# Stage 2B: trivial greeting patterns
_GREETING_WORDS = {
    "hi",
    "hello",
    "hey",
    "sup",
    "yo",
    "howdy",
    "good morning",
    "good afternoon",
    "good evening",
}

# JEV category → MarvisRoute mapping
_CATEGORY_TO_ROUTE = {
    JevCategory.CONVERSATIONAL: MarvisRoute.DIRECT_FAST,
    JevCategory.DIRECT_DETERMINISTIC: MarvisRoute.DIRECT_SANDBOX,
    JevCategory.QUANTITATIVE_MATH: MarvisRoute.MULTI_AGENT,
    JevCategory.FACTUAL_RAG: MarvisRoute.MULTI_AGENT_RAG,
    JevCategory.CONFLICTING_SOURCES: MarvisRoute.MULTI_AGENT,
    JevCategory.LOGICAL_PUZZLE: MarvisRoute.MULTI_AGENT,
    JevCategory.CODE_AND_API: MarvisRoute.MULTI_AGENT,
}


def _is_trivial_greeting(message: str) -> bool:
    """Stage 2B: match only genuinely trivial greetings, not queries that contain greetings."""
    text = message.strip().lower().rstrip("!.,?").strip()
    if text in _GREETING_WORDS:
        return True
    # Strip all non-alpha characters and recheck
    text_bare = re.sub(r"[^a-z\s]", "", text).strip()
    return text_bare in _GREETING_WORDS


def _is_executable_python(message: str) -> bool:
    """Stage 2A: detect simple executable Python snippets via AST parse."""
    code = message.strip()
    # Must contain at least one statement indicator
    if not any(kw in code for kw in ("print", "=", "import", "def ", "class ", "for ", "if ")):
        return False
    # Must not be a question or a plain English sentence
    if code.endswith("?") or (len(code.split()) > 8 and "=" not in code):
        return False
    try:
        tree = ast.parse(code)
        if not tree.body:
            return False
        # Must have at least one actual statement node
        has_stmt = any(
            isinstance(n, (ast.Assign, ast.AugAssign, ast.Expr, ast.For, ast.While, ast.FunctionDef, ast.Import, ast.ImportFrom))
            for n in tree.body
        )
        return has_stmt
    except SyntaxError:
        return False


async def triage(
    message: str,
    mode: MarvisMode,
    document_ids: Optional[List[str]] = None,
) -> TriageDecision:
    """MARVIS 3-stage triage router.

    Priority order:
    1. Stage 1 — Attachment escalation + explicit user override
    2. Stage 2 — Deterministic fast paths (greeting, AST Python)
    3. Stage 3 — JEV semantic classification (with deterministic fallback)
    """
    has_attachment = bool(document_ids)
    req_caps = detect_capabilities(message, mode, document_ids)

    # ── STAGE 1A: Attachment escalation (AUTO mode + attachment = MULTI_AGENT_RAG) ──
    if mode == MarvisMode.AUTO and has_attachment:
        log.info("MARVIS: mode=AUTO stage=1 result=attachment_escalation route=MULTI_AGENT_RAG")
        req_caps.rag = True
        return TriageDecision(
            selected_mode=mode,
            active_route=MarvisRoute.MULTI_AGENT_RAG,
            reasoning="File attachment detected in AUTO mode; escalated to MULTI_AGENT_RAG without JEV call.",
            requires_rag=True,
            requires_sandbox=False,
            escalated_by_attachment=True,
            routing_engine=RoutingEngine.STAGE1_ATTACHMENT,
            required_capabilities=req_caps,
        )

    # ── STAGE 1B: Explicit MULTI_AGENT override ──
    if mode == MarvisMode.MULTI_AGENT:
        log.info("MARVIS: mode=MULTI_AGENT stage=1 result=user_override route=MULTI_AGENT")
        requires_rag = has_attachment
        req_caps.multi_agent_reasoning = True
        req_caps.verification = True
        return TriageDecision(
            selected_mode=mode,
            active_route=MarvisRoute.MULTI_AGENT_RAG if requires_rag else MarvisRoute.MULTI_AGENT,
            reasoning="User explicitly selected MULTI_AGENT mode.",
            requires_rag=requires_rag,
            requires_sandbox=False,
            escalated_by_attachment=False,
            routing_engine=RoutingEngine.STAGE1_USER_OVERRIDE,
            required_capabilities=req_caps,
        )

    # ── STAGE 1C: Explicit DIRECT override ──
    if mode == MarvisMode.DIRECT:
        log.info("MARVIS: mode=DIRECT stage=1 result=user_override route=DIRECT_FAST")
        req_caps.verification = False
        req_caps.multi_agent_reasoning = False
        return TriageDecision(
            selected_mode=mode,
            active_route=MarvisRoute.DIRECT_FAST,
            reasoning="User explicitly selected DIRECT mode.",
            requires_rag=False,
            requires_sandbox=False,
            escalated_by_attachment=False,
            routing_engine=RoutingEngine.STAGE1_USER_OVERRIDE,
            required_capabilities=req_caps,
        )

    # ── STAGE 2: Deterministic fast paths (AUTO only, no attachment) ──

    # Stage 2B: Greeting fast path
    if _is_trivial_greeting(message):
        log.info("MARVIS: stage=2 result=greeting route=DIRECT_FAST")
        return TriageDecision(
            selected_mode=mode,
            active_route=MarvisRoute.DIRECT_FAST,
            category=JevCategory.CONVERSATIONAL,
            reasoning="Trivial greeting detected; routed directly without JEV.",
            confidence=None,
            requires_rag=False,
            requires_sandbox=False,
            escalated_by_attachment=False,
            routing_engine=RoutingEngine.STAGE2_GREETING,
            required_capabilities=req_caps,
        )

    # Stage 2A: Python AST fast path
    if _is_executable_python(message):
        log.info("MARVIS: stage=2 result=python_ast route=DIRECT_SANDBOX")
        req_caps.code_execution = True
        return TriageDecision(
            selected_mode=mode,
            active_route=MarvisRoute.DIRECT_SANDBOX,
            category=JevCategory.CODE_AND_API,
            reasoning="Executable Python code detected via AST; routed to DIRECT_SANDBOX without JEV.",
            confidence=None,
            requires_rag=False,
            requires_sandbox=True,
            escalated_by_attachment=False,
            routing_engine=RoutingEngine.STAGE2_AST,
            required_capabilities=req_caps,
        )

    # ── STAGE 3: JEV semantic classification ──
    log.info(f"MARVIS: stage=3 engine=JEV query_len={len(message)}")
    jev_result = await classify_with_jev(message)

    # Validate category returned by JEV
    if jev_result is not None:
        raw_category = jev_result["category"]
        try:
            JevCategory(raw_category)  # validate; we'll use the string below
        except ValueError:
            log.warning(f"MARVIS: JEV returned unsupported category '{raw_category}'; falling back")
            jev_result = None

    if jev_result is None:
        # Fallback to deterministic classifier
        log.info("MARVIS: stage=3 JEV routing failed; deterministic fallback used")
        jev_result = classify_fallback(message, document_ids)
        try:
            category = JevCategory(jev_result["category"])
        except ValueError:
            category = JevCategory.FACTUAL_RAG
        route = _CATEGORY_TO_ROUTE.get(category, MarvisRoute.MULTI_AGENT)
        if not has_attachment and route == MarvisRoute.MULTI_AGENT_RAG:
            route = MarvisRoute.MULTI_AGENT
            jev_result["requires_rag"] = False
        log.info(f"MARVIS: stage=3 engine=FALLBACK category={category} route={route}")
        req_caps_fallback = detect_capabilities(message, mode, document_ids, jev_category=category)
        return TriageDecision(
            selected_mode=mode,
            active_route=route,
            category=category,
            reasoning=f"JEV unavailable; deterministic fallback classified as {category.value}.",
            confidence=None,
            requires_rag=jev_result["requires_rag"] if has_attachment else False,
            requires_sandbox=jev_result["requires_sandbox"],
            escalated_by_attachment=False,
            routing_engine=RoutingEngine.STAGE3_FALLBACK,
            required_capabilities=req_caps_fallback,
        )

    category = JevCategory(jev_result["category"])
    route = _CATEGORY_TO_ROUTE.get(category, MarvisRoute.MULTI_AGENT)

    # If JEV also signals requires_rag, upgrade MULTI_AGENT → MULTI_AGENT_RAG
    if jev_result["requires_rag"] and route == MarvisRoute.MULTI_AGENT:
        route = MarvisRoute.MULTI_AGENT_RAG

    log.info(
        f"MARVIS: stage=3 engine=JEV category={category} route={route} "
        f"confidence={jev_result.get('confidence')}"
    )
    req_caps_jev = detect_capabilities(message, mode, document_ids, jev_category=category)
    return TriageDecision(
        selected_mode=mode,
        active_route=route,
        category=category,
        reasoning=f"JEV classified query as {category.value}; routed to {route.value}.",
        confidence=jev_result.get("confidence"),
        requires_rag=jev_result["requires_rag"],
        requires_sandbox=jev_result["requires_sandbox"],
        escalated_by_attachment=False,
        routing_engine=RoutingEngine.STAGE3_JEV,
        required_capabilities=req_caps_jev,
    )

