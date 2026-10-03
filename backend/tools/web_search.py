from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from config.settings import get_settings
from utils.retry import retry_async

TIER1_DOMAINS = {
    "gov",
    "mil",
    "edu",
    "ac.uk",
    "europa.eu",
    "who.int",
    "un.org",
    "nih.gov",
    "nasa.gov",
    "python.org",
    "docs.python.org",
    "ietf.org",
    "w3.org",
    "iso.org",
    "arxiv.org",
    "nature.com",
    "science.org",
    "ieee.org",
    "acm.org",
    "openai.com",
    "anthropic.com",
    "google.com",
    "microsoft.com",
    "amazon.com",
    "github.com",
}

TIER2_DOMAINS = {
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "bbc.co.uk",
    "nytimes.com",
    "wsj.com",
    "ft.com",
    "theguardian.com",
    "economist.com",
    "bloomberg.com",
    "npr.org",
    "wikipedia.org",
    "stackoverflow.com",
    "mdn",
}


def classify_source_tier(url: str) -> int:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if any(host.endswith(d) for d in TIER1_DOMAINS) or host.endswith(".gov") or host.endswith(".edu"):
        return 1
    if any(host.endswith(d) for d in TIER2_DOMAINS):
        return 2
    return 3


class TavilyError(Exception):
    pass


class TavilyClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _get_api_key(self) -> str:
        try:
            try:
                from services.provider_service import get_web_search_credentials
            except ImportError:
                from backend.services.provider_service import get_web_search_credentials
            cred = get_web_search_credentials()
            if cred and cred.get("api_key"):
                return cred["api_key"]
        except Exception:
            pass
        return self.settings.tavily_api_key

    def _ensure_configured(self) -> str:
        key = self._get_api_key()
        if not key:
            raise TavilyError("Tavily is not configured. Set TAVILY_API_KEY.")
        return key

    async def search(self, query: str, *, max_results: int = 8) -> List[Dict[str, Any]]:
        api_key = self._ensure_configured()

        async def _call() -> List[Dict[str, Any]]:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.settings.tavily_base_url}/search",
                    json={
                        "api_key": api_key,
                        "query": query,
                        "search_depth": "basic",
                        "include_answer": False,
                        "max_results": max_results,
                    },
                )
            if response.status_code >= 400:
                raise TavilyError(f"Tavily search failed: HTTP {response.status_code}")
            data = response.json()
            results = []
            for item in data.get("results") or []:
                url = item.get("url") or ""
                if not url.startswith("http"):
                    continue
                results.append(
                    {
                        "title": item.get("title") or url,
                        "url": url,
                        "content": item.get("content") or "",
                        "score": item.get("score"),
                        "published_date": item.get("published_date"),
                        "domain": urlparse(url).hostname,
                        "tier": classify_source_tier(url),
                    }
                )
            return results

        return await retry_async(_call, attempts=2, exceptions=(httpx.HTTPError, TavilyError))

    async def extract(self, url: str) -> Dict[str, Any]:
        self._ensure_configured()
        if not url.startswith("http"):
            raise TavilyError("Refusing to extract a non-http URL")

        async def _call() -> Dict[str, Any]:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(
                    f"{self.settings.tavily_base_url}/extract",
                    json={"api_key": self.settings.tavily_api_key, "urls": [url]},
                )
            if response.status_code >= 400:
                raise TavilyError(f"Tavily extract failed: HTTP {response.status_code}")
            data = response.json()
            results = data.get("results") or []
            if not results:
                failed = data.get("failed_results") or []
                reason = failed[0].get("error") if failed else "No extractable content"
                raise TavilyError(f"Tavily extract returned no content: {reason}")
            item = results[0]
            raw = item.get("raw_content") or item.get("content") or ""
            return {
                "url": item.get("url") or url,
                "title": item.get("title") or url,
                "content": _clean_text(raw)[:20000],
                "domain": urlparse(url).hostname,
                "tier": classify_source_tier(url),
            }

        return await retry_async(_call, attempts=2, exceptions=(httpx.HTTPError, TavilyError))


def _clean_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


_tavily: Optional[TavilyClient] = None


def get_tavily() -> TavilyClient:
    global _tavily
    if _tavily is None:
        _tavily = TavilyClient()
    return _tavily


async def web_search(query: str, max_results: int = 8) -> List[Dict[str, Any]]:
    return await get_tavily().search(query, max_results=max_results)


async def web_extract(url: str) -> Dict[str, Any]:
    return await get_tavily().extract(url)
