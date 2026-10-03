"""
OpenAI Provider Adapter.
Communicates directly with the OpenAI API.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import httpx

from .base import OpenAICompatibleProvider, AIProviderError


class OpenAIProvider(OpenAICompatibleProvider):
    provider_id: str = "openai"
    display_name: str = "OpenAI"
    default_model: str = "gpt-4o-mini"

    base_url: str = "https://api.openai.com/v1"
    chat_endpoint: str = "/chat/completions"
    test_endpoint: str = "/models"

    async def embed(
        self,
        texts: List[str],
        *,
        model: Optional[str] = "text-embedding-3-small",
    ) -> List[List[float]]:
        """Generate OpenAI embeddings."""
        url = f"{self.base_url.rstrip('/')}/embeddings"
        payload = {
            "model": model or "text-embedding-3-small",
            "input": texts,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=self.get_headers(), json=payload)
        if resp.status_code >= 400:
            raise AIProviderError(f"OpenAI embedding failed: HTTP {resp.status_code} {resp.text[:200]}")
        data = resp.json()
        return [item["embedding"] for item in data.get("data", [])]
