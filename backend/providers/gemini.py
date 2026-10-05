"""
Google Gemini AI Provider Adapter.
Communicates directly with Google's Gemini API (OpenAI-compatible chat completions interface).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import httpx

from .base import OpenAICompatibleProvider, AIProviderError


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
SUPPORTED_GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]
OBSOLETE_GEMINI_MODELS = {
    "gemini-2.0-flash",
    "gemini-2.0-flash-exp",
    "gemini-2.0-pro-exp",
    "gemini-1.0-pro",
    "gemini-pro",
    "models/gemini-2.0-flash",
    "models/gemini-2.0-flash-exp",
}


def normalize_gemini_model(model: Optional[str]) -> str:
    """Normalize and gracefully migrate Gemini model names.

    1. If empty or None, return DEFAULT_GEMINI_MODEL.
    2. If the stored model is an obsolete/retired model (e.g. gemini-2.0-flash),
       migrate gracefully to DEFAULT_GEMINI_MODEL.
    3. If the user explicitly configured a valid supported model, preserve it.
    """
    if not model or not model.strip():
        return DEFAULT_GEMINI_MODEL
    clean = model.strip()
    # Strip optional "models/" prefix Google sometimes prepends
    stripped = clean[7:].strip() if clean.startswith("models/") else clean
    if stripped.lower() in {m.lower() for m in OBSOLETE_GEMINI_MODELS}:
        return DEFAULT_GEMINI_MODEL
    return stripped


class GeminiProvider(OpenAICompatibleProvider):
    provider_id: str = "google"
    display_name: str = "Google Gemini"
    default_model: str = DEFAULT_GEMINI_MODEL

    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    chat_endpoint: str = "/chat/completions"
    test_endpoint: str = "/models"

    def __init__(self, api_key: str, model: Optional[str] = None) -> None:
        normalized = normalize_gemini_model(model)
        super().__init__(api_key=api_key, model=normalized)

    async def test_connection(self) -> Dict[str, Any]:
        """Validate Gemini API key using Google's models endpoint or lightweight completion."""
        # 1. Try Google REST models endpoint directly with query param
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
            if resp.status_code in (200, 206):
                return {"success": True, "provider": self.provider_id, "models": list(SUPPORTED_GEMINI_MODELS)}
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
