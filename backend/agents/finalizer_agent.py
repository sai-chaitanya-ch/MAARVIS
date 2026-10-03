from __future__ import annotations

import json
from typing import Any, Dict, List

from models.llm import get_llm
from security.validation import wrap_untrusted

SYSTEM = """You produce the final user-facing answer for MAARVIS.
Rules:
- Never introduce unsupported claims.
- Preserve uncertainty and conflicts.
- Do not mention internal agents, tools internals, or chain-of-thought.
- Do not fabricate sources, URLs, or confidence percentages.
- Keep the tone of a premium assistant.
- If a verification note is provided, you may weave uncertainty into the prose; the system will append the official note separately if needed.
- If math or code tool output exists, treat it as authoritative for that part.
- If research failed, say research could not be completed. Never pretend it succeeded.
"""


async def finalize(
    question: str,
    draft: str,
    claim_results: List[Dict[str, Any]] | None,
    contradictions: Dict[str, Any] | None,
    critic: Dict[str, Any] | None,
    sources: List[Dict[str, Any]] | None,
    tool_notes: str = "",
) -> str:
    llm = get_llm()
    bundle = {
        "question": question,
        "draft": draft,
        "claim_results": claim_results or [],
        "contradictions": contradictions or {},
        "critic": critic or {},
        "sources": [
            {"title": s.get("title"), "url": s.get("url"), "domain": s.get("domain")}
            for s in (sources or [])[:10]
            if s.get("url") or s.get("source_type") == "document"
        ],
        "tool_notes": tool_notes,
    }
    return await llm.complete(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": wrap_untrusted("internal_bundle", json.dumps(bundle)[:16000])},
        ],
        temperature=0.2,
        max_tokens=1800,
    )
