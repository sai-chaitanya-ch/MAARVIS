"""
Base AI Provider abstraction and OpenAI-compatible provider implementation.
Provides generate(), stream(), embed(), and test_connection() interfaces.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from utils.logging import get_logger
from utils.retry import retry_async

log = get_logger(__name__)


class AIProviderError(Exception):
    """Base exception for provider failures."""
    pass


class NoProviderConfiguredError(AIProviderError):
    """Raised when no valid AI provider is configured."""
    pass


class ProviderDecryptionError(AIProviderError):
    """Raised when an encrypted provider credential cannot be decrypted."""
    pass


class AIProvider(ABC):
    """Abstract interface for all MAARVIS AI providers."""

    provider_id: str = "generic"
    display_name: str = "Generic AI Provider"
    default_model: str = "default"

    def __init__(self, api_key: str, model: Optional[str] = None) -> None:
        self.api_key = api_key
        self.model = model or self.default_model

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1800,
        json_mode: bool = False,
    ) -> str:
        """Execute a non-streaming chat completion request."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1800,
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens asynchronously."""
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Verify provider credentials by sending a lightweight test request."""
        pass

    async def embed(
        self,
        texts: List[str],
        *,
        model: Optional[str] = None,
    ) -> List[List[float]]:
        """Generate vector embeddings if supported by this provider."""
        raise NotImplementedError(f"Embedding not implemented for provider '{self.provider_id}'")


class OpenAICompatibleProvider(AIProvider):
    """Reusable implementation for providers supporting the standard OpenAI completions API.

    Used by: OpenAI, Google Gemini (OpenAI endpoint), Groq, DeepSeek.
    """

    base_url: str = "https://api.openai.com/v1"
    chat_endpoint: str = "/chat/completions"
    test_endpoint: str = "/models"

    def get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def get_chat_url(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.chat_endpoint}"

    def get_test_url(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.test_endpoint}"

    async def generate(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1800,
        json_mode: bool = False,
    ) -> str:
        active_model = model or self.model
        payload: Dict[str, Any] = {
            "model": active_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async def _call() -> str:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.get_chat_url(),
                    headers=self.get_headers(),
                    json=payload,
                )
            if response.status_code >= 400:
                raise AIProviderError(
                    f"{self.display_name} request failed: HTTP {response.status_code} "
                    f"{response.text[:300]}"
                )
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                raise AIProviderError(f"{self.display_name} returned no choices")
            content = choices[0].get("message", {}).get("content")
            if content is None:
                raise AIProviderError(f"{self.display_name} returned empty content")
            return str(content)

        return await retry_async(_call, attempts=3, exceptions=(httpx.HTTPError, AIProviderError))

    async def stream(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1800,
    ) -> AsyncIterator[str]:
        active_model = model or self.model
        payload = {
            "model": active_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    self.get_chat_url(),
                    headers=self.get_headers(),
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        err_text = await response.aread()
                        raise AIProviderError(
                            f"{self.display_name} stream failed: HTTP {response.status_code} {err_text[:300].decode('utf-8', errors='ignore')}"
                        )
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            parsed = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        choices = parsed.get("choices") or []
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        token = delta.get("content") or ""
                        if token:
                            yield token
        except AIProviderError as exc:
            log.warning("provider_stream_error", provider=self.provider_id, error=str(exc))
            yield f"\n⚠️ [{self.display_name} Error]: {exc}"
        except Exception as exc:
            log.error("provider_stream_unexpected_error", provider=self.provider_id, error=str(exc))
            yield f"\n⚠️ [{self.display_name} Connection Error]: {exc}"

    async def test_connection(self) -> Dict[str, Any]:
        """Validate connection via test endpoint or lightweight completion."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.get_test_url(), headers=self.get_headers())
            if resp.status_code in (200, 206):
                return {"success": True, "provider": self.provider_id}
            # Fallback to minimal completion if models list is restricted
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp2 = await client.post(
                    self.get_chat_url(),
                    headers=self.get_headers(),
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 2,
                    },
                )
            if resp2.status_code in (200, 201):
                return {"success": True, "provider": self.provider_id}
            return {
                "success": False,
                "error": f"{self.display_name} returned HTTP {resp2.status_code}: {resp2.text[:200]}",
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}
