from __future__ import annotations

import ast
import re
from typing import List, Optional

from marvis.schemas import JevCategory, MarvisMode, RequiredCapabilities
from utils.logging import get_logger

log = get_logger(__name__)

# Greeting keywords
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

# Temporal / recency indicators indicating web search requirement
_TEMPORAL_PATTERNS = [
    r"\btoday\b",
    r"\byesterday\b",
    r"\btomorrow\b",
    r"\bcurrent\b",
    r"\bcurrently\b",
    r"\blatest\b",
    r"\brecent\b",
    r"\brecently\b",
    r"\bnews\b",
    r"\bbreaking\b",
    r"\bprice\b",
    r"\bstock\b",
    r"\bweather\b",
    r"\bwho is (?:the )?(?:current|present|new)\b",
    r"\bwho is (?:the )?ceo\b",
    r"\bwho is (?:the )?president\b",
    r"\bin (?:2024|2025|2026)\b",
    r"\bupdates?\b",
    r"\bscore\b",
    r"\bstanding\b",
]

# Explicit web search triggers
_WEB_SEARCH_TRIGGERS = [
    r"\bsearch (?:the )?web\b",
    r"\bgoogle (?:this|it)\b",
    r"\bfind online\b",
    r"\blook up online\b",
    r"\blatest info\b",
]

# Claim verification markers
_CLAIM_VERIFICATION_PATTERNS = [
    r"\b(?:is|are) (?:it|that|this) true\b",
    r"\bverify\b",
    r"\bfact[- ]check\b",
    r"\bcheck if\b",
    r"\breal or fake\b",
    r"\bmyth or fact\b",
    r"\btruth about\b",
]

# Reasoning / comparison markers
_REASONING_PATTERNS = [
    r"\bcompare\b",
    r"\bversus\b",
    r"\b vs \b",
    r"\bdifference between\b",
    r"\bpros and cons\b",
    r"\btrade[- ]offs?\b",
    r"\bstep by step\b",
    r"\banalyze the\b",
]


def is_trivial_greeting(message: str) -> bool:
    """Detect if the message is solely a conversational greeting."""
    text = message.strip().lower().rstrip("!.,?").strip()
    if text in _GREETING_WORDS:
        return True
    text_bare = re.sub(r"[^a-z\s]", "", text).strip()
    return text_bare in _GREETING_WORDS


def is_executable_python(message: str) -> bool:
    """Detect simple executable Python statements via AST."""
    code = message.strip()
    if not any(kw in code for kw in ("print", "=", "import", "def ", "class ", "for ", "if ")):
        return False
    if code.endswith("?") or (len(code.split()) > 8 and "=" not in code):
        return False
    try:
        tree = ast.parse(code)
        if not tree.body:
            return False
        return any(
            isinstance(
                n,
                (
                    ast.Assign,
                    ast.AugAssign,
                    ast.Expr,
                    ast.For,
                    ast.While,
                    ast.FunctionDef,
                    ast.Import,
                    ast.ImportFrom,
                ),
            )
            for n in tree.body
        )
    except SyntaxError:
        return False


def detect_capabilities(
    message: str,
    mode: MarvisMode = MarvisMode.AUTO,
    document_ids: Optional[List[str]] = None,
    code: Optional[str] = None,
    jev_category: Optional[JevCategory] = None,
) -> RequiredCapabilities:
    """Determine which system capabilities are strictly required to answer the query.

    Evaluates:
    - basic_llm: Always True for natural language answering
    - rag: Document grounding via vector store
    - web_search: Real-time search for current events/external facts
    - code_execution: Python sandbox for numeric/code evaluation
    - multi_agent_reasoning: Cross-agent planning and multi-perspective verification
    - verification: Strict factual verification against independent sources
    - jev: Advanced semantic triage and decision routing
    """
    clean_msg = message.strip()
    msg_lower = clean_msg.lower()
    has_attachment = bool(document_ids and len(document_ids) > 0)
    has_code = bool(code and code.strip()) or is_executable_python(clean_msg)

    # 1. Trivial greeting: only basic LLM needed
    if is_trivial_greeting(clean_msg):
        return RequiredCapabilities(
            basic_llm=True,
            rag=False,
            web_search=False,
            code_execution=False,
            multi_agent_reasoning=False,
            verification=False,
            jev=False,
        )

    # 2. Pure code snippet: code execution + basic LLM
    if has_code and not has_attachment and len(clean_msg.splitlines()) > 1:
        return RequiredCapabilities(
            basic_llm=True,
            rag=False,
            web_search=False,
            code_execution=True,
            multi_agent_reasoning=False,
            verification=False,
            jev=False,
        )

    # 3. Detect math / computation
    has_math_symbols = (
        any(op in clean_msg for op in ["+", "-", "*", "/", "=", "^", "%"])
        and any(c.isdigit() for c in clean_msg)
    )
    is_math = bool(
        jev_category in {JevCategory.QUANTITATIVE_MATH, JevCategory.DIRECT_DETERMINISTIC}
        or any(w in msg_lower for w in ["calculate", "compute", "evaluate", "math", "equation"])
        or has_math_symbols
    )

    # 4. Detect RAG requirement
    is_rag = bool(
        has_attachment
        or (jev_category == JevCategory.FACTUAL_RAG and has_attachment)
        or any(w in msg_lower for w in ["in this document", "uploaded file", "attached pdf", "the report"])
    )

    # 5. Detect Web Search requirement
    # Only if NOT a pure document query (unless document query specifically asks to cross-verify online)
    has_temporal = any(re.search(pat, msg_lower) for pat in _TEMPORAL_PATTERNS)
    has_web_trigger = any(re.search(pat, msg_lower) for pat in _WEB_SEARCH_TRIGGERS)
    is_conflicting = jev_category == JevCategory.CONFLICTING_SOURCES

    is_web = False
    if has_web_trigger:
        is_web = True
    elif has_attachment:
        # Document attached: do not enable web search unless user explicitly requested external/live cross-verification
        is_web = has_web_trigger or ("internet" in msg_lower and "verify" in msg_lower)
    else:
        is_web = has_temporal or is_conflicting

    # 6. Detect Multi-Agent Reasoning requirement
    has_reasoning_keyword = any(re.search(pat, msg_lower) for pat in _REASONING_PATTERNS)
    is_multi_agent = bool(
        mode == MarvisMode.MULTI_AGENT
        or jev_category in {JevCategory.LOGICAL_PUZZLE, JevCategory.CONFLICTING_SOURCES}
        or has_reasoning_keyword
        or (len(clean_msg.split()) > 35 and "?" in clean_msg)
    )

    # 7. Detect Verification requirement
    has_claim_check = any(re.search(pat, msg_lower) for pat in _CLAIM_VERIFICATION_PATTERNS)
    is_verification = bool(
        mode == MarvisMode.MULTI_AGENT
        or is_rag
        or is_web
        or has_claim_check
        or is_conflicting
    )
    if mode == MarvisMode.DIRECT:
        is_verification = False

    # 8. Detect JEV requirement
    # JEV provides advanced semantic routing and structured decision triage
    # Required for complex multi-intent, ambiguous logic puzzles, or conflicting claims
    # NOT required for simple questions, greetings, math, or direct execution
    is_jev_beneficial = bool(
        (is_conflicting or jev_category == JevCategory.LOGICAL_PUZZLE)
        or (len(clean_msg.split()) > 25 and has_reasoning_keyword)
        or (has_temporal and has_attachment)  # complex mixed routing
    )

    return RequiredCapabilities(
        basic_llm=True,
        rag=is_rag,
        web_search=is_web,
        code_execution=bool(has_code or is_math),
        multi_agent_reasoning=is_multi_agent,
        verification=is_verification,
        jev=is_jev_beneficial,
    )
