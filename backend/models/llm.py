"""
MAARVIS Core LLM Provider Interface.
Dispatches requests to the configured active AI Provider (Gemini, OpenAI, Anthropic, Groq, DeepSeek).
Zero runtime dependency on OmniRoute.
"""
from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional

try:
    from providers.base import AIProvider, AIProviderError, NoProviderConfiguredError
    from providers.factory import get_active_provider
    from security.auth import get_context_user_id
except ImportError:
    from backend.providers.base import AIProvider, AIProviderError, NoProviderConfiguredError
    from backend.providers.factory import get_active_provider
    from backend.security.auth import get_context_user_id
from utils.logging import get_logger

log = get_logger(__name__)


class LLMError(AIProviderError):
    """Exception raised when an LLM call fails."""
    pass


class LLMProvider:
    """Delegates LLM generation and streaming to the active AIProvider adapter."""

    def get_provider(self, user_id: Optional[str] = None) -> AIProvider:
        """Resolve and return active AIProvider adapter."""
        resolved_user = user_id or get_context_user_id()
        try:
            return get_active_provider(user_id=resolved_user)
        except (NoProviderConfiguredError, AIProviderError) as exc:
            raise LLMError(str(exc)) from exc

    def get_active_route(
        self,
        requested_model: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> tuple[str, Dict[str, str], str, str]:
        """Diagnostic helper returning endpoint info for the active provider."""
        provider = self.get_provider(user_id=user_id)
        active_model = requested_model or provider.model
        headers = {}
        if hasattr(provider, "get_headers"):
            headers = provider.get_headers()
        url = getattr(provider, "base_url", "https://api")
        return url, headers, active_model, provider.display_name

    async def complete(
        self,
        messages: List[Dict[str, str]],
        *,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1800,
        json_mode: bool = False,
    ) -> str:
        """Execute chat completion using active provider."""
        try:
            provider = self.get_provider(user_id=user_id)
        except (LLMError, NoProviderConfiguredError) as err:
            raise LLMError(str(err)) from err

        try:
            return await provider.generate(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
        except AIProviderError as err:
            raise LLMError(str(err)) from err

    async def stream(
        self,
        messages: List[Dict[str, str]],
        *,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1800,
    ) -> AsyncIterator[str]:
        """Stream chat tokens using active provider."""
        try:
            provider = self.get_provider(user_id=user_id)
        except (LLMError, NoProviderConfiguredError) as err:
            yield f"⚠️ {err}"
            return

        try:
            async for token in provider.stream(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield token
        except Exception as exc:
            log.error("llm_stream_error", error=str(exc))
            yield f"\n⚠️ [Provider Error]: {exc}"


_provider: Optional[LLMProvider] = None


def get_llm() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = LLMProvider()
    return _provider
