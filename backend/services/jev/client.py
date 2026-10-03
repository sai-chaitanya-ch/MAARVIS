from __future__ import annotations

import time
from typing import Any, Dict, Optional
import httpx

from config.settings import get_settings
from utils.logging import get_logger
from .schemas import JevCategory, JevDecision, JevExecutionRoute, JevQuestion, JevRequest

log = get_logger(__name__)

JEV_CATEGORIES = [c.value for c in JevCategory]

STATE_PROMPT = """The user submitted this query to MAARVIS, an AI verification and reasoning platform:

{query}

Classify this query to determine complexity, RAG requirement, code execution requirement, and optimal processing route."""


class JevClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def classify(self, query: str) -> Optional[JevDecision]:
        """Call the official JEV AI API (/v1/systemone) with structured questions."""
        if not self.settings.jev_api_key:
            log.info("JEV_API_KEY not configured; skipping remote JEV call")
            return None

        payload = JevRequest(
            model=self.settings.jev_model or "jev-latest",
            state=STATE_PROMPT.format(query=query[:4000]),
            questions={
                "category": JevQuestion(type="choice", options=JEV_CATEGORIES),
                "requires_rag": JevQuestion(type="noul"),
                "requires_code": JevQuestion(type="noul"),
                "complexity": JevQuestion(type="choice", options=["low", "standard", "high"]),
            },
        )

        headers = {
            "Authorization": f"Bearer {self.settings.jev_api_key}",
            "Content-Type": "application/json",
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    self.settings.jev_base_url.rstrip("/"),
                    headers=headers,
                    json=payload.model_dump(),
                )
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            if resp.status_code >= 400:
                log.warning(
                    f"JEV API returned HTTP {resp.status_code}",
                    extra={"status_code": resp.status_code, "latency_ms": latency_ms},
                )
                return None

            data = resp.json()
            answers = data.get("answers") or {}
            cat_ans = answers.get("category") or {}
            rag_ans = answers.get("requires_rag") or {}
            code_ans = answers.get("requires_code") or {}
            comp_ans = answers.get("complexity") or {}

            raw_cat = cat_ans.get("value", "")
            if raw_cat not in JEV_CATEGORIES:
                log.warning(f"JEV API returned unsupported category '{raw_cat}'")
                return None

            category = JevCategory(raw_cat)
            probs = cat_ans.get("probabilities") or {}
            confidence = probs.get(raw_cat) if probs else None

            requires_rag = float(rag_ans.get("value") or 0.0) > 0.5
            requires_code = float(code_ans.get("value") or 0.0) > 0.5
            complexity = str(comp_ans.get("value") or "standard")

            # Route mapping
            if category == JevCategory.CONVERSATIONAL:
                route = JevExecutionRoute.DIRECT_FAST
                requires_verification = False
            elif category == JevCategory.DIRECT_DETERMINISTIC:
                route = JevExecutionRoute.DIRECT_SANDBOX
                requires_verification = False
            elif category == JevCategory.QUANTITATIVE_MATH:
                route = JevExecutionRoute.MULTI_AGENT
                requires_verification = True
            elif category == JevCategory.FACTUAL_RAG:
                route = JevExecutionRoute.MULTI_AGENT_RAG
                requires_verification = True
                requires_rag = True
            elif category == JevCategory.CODE_AND_API:
                route = JevExecutionRoute.DIRECT_SANDBOX if not requires_rag else JevExecutionRoute.MULTI_AGENT
                requires_verification = True
            else:
                route = JevExecutionRoute.MULTI_AGENT
                requires_verification = True

            return JevDecision(
                category=category,
                route=route,
                complexity=complexity,
                requires_rag=requires_rag,
                requires_verification=requires_verification,
                requires_code_execution=requires_code,
                confidence=confidence,
                reasoning=f"JEV AI classified query as {category.value} with complexity={complexity}",
                is_fallback=False,
                latency_ms=latency_ms,
            )
        except httpx.TimeoutException:
            log.warning("JEV API request timed out after 8s; using deterministic fallback")
            return None
        except Exception as exc:
            log.warning(f"JEV API request failed: {exc}; using deterministic fallback")
            return None


_client: Optional[JevClient] = None


def get_jev_client() -> JevClient:
    global _client
    if _client is None:
        _client = JevClient()
    return _client
