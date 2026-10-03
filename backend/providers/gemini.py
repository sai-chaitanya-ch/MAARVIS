"""
Google Gemini AI Provider Adapter.
Communicates directly with Google's Gemini API (OpenAI-compatible chat completions interface).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import httpx

from .base import OpenAICompatibleProvider, AIProviderError


class GeminiProvider(OpenAICompatibleProvider):
    provider_id: str = "google"
    display_name: str = "Google Gemini"
    default_model: str = "gemini-2.0-flash"

    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    chat_endpoint: str = "/chat/completions"
    test_endpoint: str = "/models"

    async def test_connection(self) -> Dict[str, Any]:
        """Validate Gemini API key using Google's models endpoint or lightweight completion."""
        # 1. Try Google REST models endpoint directly with query param
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
            if resp.status_code in (200, 206):
                return {"success": True, "provider": self.provider_id, "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]}
        except Exception:
            pass

        # 2. Try chat completions endpoint
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp2 = await client.post(
                    self.get_chat_url(),
                    headers=self.get_headers(),
                    json={
                        "model": self.model or self.default_model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 5,
                    },
                )
            if resp2.status_code in (200, 201):
                return {"success": True, "provider": self.provider_id}
            return {
                "success": False,
                "error": f"Google Gemini returned HTTP {resp2.status_code}: {resp2.text[:200]}",
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}
