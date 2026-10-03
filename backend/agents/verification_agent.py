from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from verification.claim_extractor import extract_claims
from verification.contradiction import find_contradictions
from verification.evidence import gather_evidence
from verification.fact_checker import verify_claim, verify_claims_batch
from verification.confidence import build_verification_payload
from utils.events import EventSpan, current_bus


async def run_verification(
    question: str,
    draft: str,
    existing_sources: List[Dict[str, Any]] | None,
    level: int,
    allow_web: bool = True,
    event_cb=None,
) -> Dict[str, Any]:
    bus = current_bus()
    async with EventSpan(bus, "claim_extraction"):
        claims = await extract_claims(draft, question)
    if not claims:
        return {
            "claims": [],
            "claim_results": [],
            "evidence": existing_sources or [],
            "contradictions": {"has_conflict": False, "contradictions": []},
            "verification": build_verification_payload(True, [], None, level, independent_completed=True),
        }
    async with EventSpan(bus, "verification"):
        evidence = await gather_evidence(claims, existing_sources, allow_web=allow_web)
        results = await verify_claims_batch(claims, evidence)
    contradictions = {"has_conflict": False, "contradictions": []}
    if level >= 2:
        async with EventSpan(bus, "contradiction_check"):
            contradictions = await find_contradictions(evidence)
    verification = build_verification_payload(True, results, contradictions, level)
    sources = []
    for item in evidence:
        if item.get("url") or item.get("source_type") in {"document", "calculation", "code_execution"}:
            # Tag these as verification evidence so they are not shown as
            # primary cited sources in the UI — they were gathered to
            # fact-check claims, not to author the answer.
            sources.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title") or item.get("domain") or "Source",
                    "url": item.get("url"),
                    "domain": item.get("domain"),
                    "source_type": item.get("source_type") or "web",
                    "source_role": "verification_evidence",
                    "evidence": item.get("evidence"),
                    "published_at": item.get("published_at"),
                    "tier": item.get("tier"),
                }
            )
    return {
        "claims": claims,
        "claim_results": results,
        "evidence": evidence,
        "contradictions": contradictions,
        "verification": verification,
        "sources": sources,
    }
