from __future__ import annotations

import httpx
from typing import Optional, Dict, Any

from config.settings import get_settings
from utils.logging import get_logger

log = get_logger(__name__)

JEV_CATEGORIES = [
    "CONVERSATIONAL",
    "DIRECT_DETERMINISTIC",
    "QUANTITATIVE_MATH",
    "FACTUAL_RAG",
    "CONFLICTING_SOURCES",
    "LOGICAL_PUZZLE",
    "CODE_AND_API",
]

STATE_CONTEXT = """The user submitted this query to MAARVIS, an AI verification and reasoning platform:

{query}

Classify this query to determine the best processing route."""


async def classify_with_jev(query: str) -> Optional[Dict[str, Any]]:
    """Call JEV to classify the query.

    Returns a dict with keys:
        ``category``        – one of JEV_CATEGORIES
        ``confidence``      – float from the winning category's probability, or None
        ``requires_rag``    – bool
        ``requires_sandbox``– bool

    Returns None on any failure so the caller can fall back to the deterministic classifier.
    """
    settings = get_settings()
    jev_key = None
    try:
        try:
            from services.provider_service import get_jev_credentials
        except ImportError:
            from backend.services.provider_service import get_jev_credentials
        cred = get_jev_credentials()
        if cred and cred.get("api_key"):
            jev_key = cred["api_key"]
    except Exception:
        pass
    if not jev_key:
        jev_key = settings.jev_api_key

    if not jev_key:
        log.warning("MARVIS: JEV_API_KEY not configured; skipping JEV classification")
        return None

    payload = {
        "model": settings.jev_model,
        "state": STATE_CONTEXT.format(query=query[:4000]),
        "questions": {
            "category": {"type": "choice", "options": JEV_CATEGORIES},
            "requires_rag": {"type": "noul"},
            "requires_sandbox": {"type": "noul"},
        },
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                settings.jev_base_url.rstrip("/"),
                headers={
                    "Authorization": f"Bearer {jev_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        if response.status_code >= 400:
            log.warning(f"MARVIS: JEV returned HTTP {response.status_code}; falling back")
            return None

        data = response.json()
        answers = data.get("answers") or {}
        category_ans = answers.get("category") or {}
        rag_ans = answers.get("requires_rag") or {}
        sandbox_ans = answers.get("requires_sandbox") or {}

        raw_category = category_ans.get("value", "")
        if raw_category not in JEV_CATEGORIES:
            log.warning(f"MARVIS: JEV returned unknown category '{raw_category}'; falling back")
            return None

        # Confidence: JEV choice gives probabilities dict; use max probability as confidence
        probs = category_ans.get("probabilities") or {}
        confidence = probs.get(raw_category) if probs else None

        requires_rag = float(rag_ans.get("value") or 0) > 0.5
        requires_sandbox = float(sandbox_ans.get("value") or 0) > 0.5

        return {
            "category": raw_category,
            "confidence": confidence,
            "requires_rag": requires_rag,
            "requires_sandbox": requires_sandbox,
        }

    except httpx.TimeoutException:
        log.warning("MARVIS: JEV request timed out; falling back to deterministic classifier")
        return None
    except Exception as exc:
        log.warning(f"MARVIS: JEV classification failed: {exc}; falling back")
        return None
