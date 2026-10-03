from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urlparse

from tools.web_search import web_extract, web_search
from utils.tracing import new_id


async def gather_evidence(
    claims: List[Dict[str, Any]],
    existing: List[Dict[str, Any]] | None = None,
    allow_web: bool = True,
) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    seen_urls = set()
    has_documents = False
    for src in existing or []:
        url = src.get("url")
        if url:
            seen_urls.add(url)
        if src.get("source_type") in {"document", "calculation", "code_execution"} or src.get("evidence"):
            has_documents = True
            evidence.append(_as_evidence(src, claims_hint="primary document"))
        elif url:
            evidence.append(_as_evidence(src, claims_hint="existing research"))

    if not allow_web or has_documents:
        return evidence

    # If we already have sufficient research evidence from the query search, avoid redundant web scraping
    if len(evidence) >= 3:
        return evidence

    # Gather targeted evidence for claims concurrently to eliminate sequential search latency
    import asyncio
    claims_to_check = [c for c in claims if c.get("verification_required", True)][:2]
    search_tasks = [web_search(claim["claim_text"], max_results=3) for claim in claims_to_check]
    search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    for claim, results in zip(claims_to_check, search_results):
        if isinstance(results, Exception) or not results:
            continue
        for item in results[:2]:
            url = item.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            content = item.get("content") or ""
            evidence.append(
                {
                    "id": new_id("e_"),
                    "title": item.get("title") or item.get("domain") or "Web Source",
                    "url": url,
                    "domain": urlparse(url).hostname or item.get("domain"),
                    "source_type": "web",
                    "tier": item.get("tier"),
                    "evidence": content[:2500],
                    "published_at": item.get("published_date"),
                    "claim_id": claim.get("claim_id", "c_"),
                }
            )
            if len(evidence) >= 6:
                break
        if len(evidence) >= 6:
            break
    return evidence



def _as_evidence(src: Dict[str, Any], claims_hint: str) -> Dict[str, Any]:
    return {
        "id": src.get("id") or new_id("e_"),
        "title": src.get("title"),
        "url": src.get("url"),
        "domain": src.get("domain"),
        "source_type": src.get("source_type") or "web",
        "tier": src.get("tier"),
        "evidence": src.get("evidence") or src.get("content") or "",
        "published_at": src.get("published_at"),
        "claim_id": claims_hint,
    }
