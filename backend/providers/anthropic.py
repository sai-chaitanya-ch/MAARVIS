"""
Anthropic Provider Adapter.
Communicates directly with Anthropic's Claude API (/v1/messages).
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx

from .base import AIProvider, AIProviderError
from utils.logging import get_logger
from utils.retry import retry_async

log = get_logger(__name__)


class AnthropicProvider(AIProvider):
    provider_id: str = "anthropic"
    display_name: str = "Anthropic"
    default_model: str = "claude-3-5-haiku-20241022"

    base_url: str = "https://api.anthropic.com/v1"
    messages_endpoint: str = "/messages"

    def get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

    def _split_system_and_messages(
        self, messages: List[Dict[str, str]]
    ) -> tuple[Optional[str], List[Dict[str, str]]]:
        """Anthropic separates system instructions into a top-level field."""
        system_parts = []
        chat_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content)
            else:
                # Anthropic only accepts 'user' and 'assistant' roles in messages
                normalized_role = "assistant" if role == "assistant" else "user"
                chat_messages.append({"role": normalized_role, "content": content})

        # Ensure first message is user
        if not chat_messages:
            chat_messages.append({"role": "user", "content": "Hello"})
        elif chat_messages[0]["role"] != "user":
            chat_messages.insert(0, {"role": "user", "content": "Begin."})

        system_str = "\n\n".join(system_parts) if system_parts else None
        return system_str, chat_messages

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
        system_prompt, chat_msgs = self._split_system_and_messages(messages)

        payload: Dict[str, Any] = {
            "model": active_model,
            "messages": chat_msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        url = f"{self.base_url.rstrip('/')}{self.messages_endpoint}"

        async def _call() -> str:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=self.get_headers(), json=payload)
            if response.status_code >= 400:
                raise AIProviderError(
                    f"Anthropic request failed: HTTP {response.status_code} {response.text[:300]}"
                )
            data = response.json()
            contents = data.get("content") or []
            text_blocks = [c.get("text", "") for c in contents if c.get("type") == "text"]
            if not text_blocks:
                raise AIProviderError("Anthropic returned empty content")
            return "".join(text_blocks)

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
        system_prompt, chat_msgs = self._split_system_and_messages(messages)

        payload: Dict[str, Any] = {
            "model": active_model,
            "messages": chat_msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt

        url = f"{self.base_url.rstrip('/')}{self.messages_endpoint}"

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", url, headers=self.get_headers(), json=payload) as response:
                    if response.status_code >= 400:
                        err_text = await response.aread()
                        raise AIProviderError(
                            f"Anthropic stream failed: HTTP {response.status_code} {err_text[:300].decode('utf-8', errors='ignore')}"
                        )
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if not data_str:
                            continue
                        try:
                            parsed = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        # Check for content_block_delta
                        event_type = parsed.get("type")
                        if event_type == "content_block_delta":
                            delta = parsed.get("delta") or {}
                            if delta.get("type") == "text_delta":
                                text = delta.get("text") or ""
                                if text:
                                    yield text
                        elif event_type == "error":
                            err_info = parsed.get("error") or {}
                            msg = err_info.get("message") or "Unknown Anthropic stream error"
                            yield f"\n⚠️ [Anthropic Stream Error]: {msg}"
                            break
        except AIProviderError as exc:
            log.warning("anthropic_stream_error", error=str(exc))
            yield f"\n⚠️ [Anthropic Error]: {exc}"
        except Exception as exc:
            log.error("anthropic_unexpected_error", error=str(exc))
            yield f"\n⚠️ [Anthropic Connection Error]: {exc}"

    async def test_connection(self) -> Dict[str, Any]:
        """Validate connection using models endpoint or 1-token message."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/models", headers=self.get_headers())
            if resp.status_code in (200, 206):
                return {"success": True, "provider": self.provider_id}
            # Fallback to 1-token message
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp2 = await client.post(
                    f"{self.base_url}/messages",
                    headers=self.get_headers(),
                    json={
                        "model": self.model or self.default_model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 1,
                    },
                )
            if resp2.status_code in (200, 201):
                return {"success": True, "provider": self.provider_id}
            return {
                "success": False,
                "error": f"Anthropic returned HTTP {resp2.status_code}: {resp2.text[:200]}",
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}
