"""
Provider Factory and Active Provider Resolution.
Discovers and instantiates the active AI provider based on configured credentials.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from config.settings import get_settings
from .base import AIProvider, AIProviderError, NoProviderConfiguredError, ProviderDecryptionError
from .gemini import (
    GeminiProvider,
    DEFAULT_GEMINI_MODEL,
    SUPPORTED_GEMINI_MODELS,
    normalize_gemini_model,
)
from .openai_provider import OpenAIProvider
from .anthropic import AnthropicProvider
from .groq import GroqProvider
from .deepseek import DeepSeekProvider
from utils.logging import get_logger

log = get_logger(__name__)

# Registry mapping provider identifier to its concrete adapter class
PROVIDER_REGISTRY: Dict[str, Type[AIProvider]] = {
    "google": GeminiProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "groq": GroqProvider,
    "deepseek": DeepSeekProvider,
}

SUPPORTED_PROVIDER_METADATA = [
    {
        "id": "google",
        "name": "Google Gemini",
        "category": "core",
        "default_model": DEFAULT_GEMINI_MODEL,
        "models": list(SUPPORTED_GEMINI_MODELS),
        "description": "Google's state-of-the-art multimodal reasoning models.",
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "category": "core",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "description": "Industry benchmark reasoning and general-purpose models.",
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "category": "core",
        "default_model": "claude-3-5-haiku-20241022",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
        "description": "High-accuracy nuanced reasoning and factuality.",
    },
    {
        "id": "groq",
        "name": "Groq",
        "category": "core",
        "default_model": "llama-3.3-70b-versatile",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "description": "Ultra-low-latency LPU inference engine.",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "category": "core",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "description": "Advanced open-weight reasoning and code intelligence.",
    },
]


def resolve_provider(provider_id: str, api_key: str, model: Optional[str] = None) -> AIProvider:
    """Instantiate a provider adapter for the given provider_id."""
    normalized_id = provider_id.strip().lower()
    provider_cls = PROVIDER_REGISTRY.get(normalized_id)
    if not provider_cls:
        raise ValueError(
            f"Unsupported provider: '{provider_id}'. Supported: {', '.join(PROVIDER_REGISTRY.keys())}"
        )
    if normalized_id in ("google", "gemini"):
        model = normalize_gemini_model(model)
    return provider_cls(api_key=api_key, model=model)


def get_active_provider(user_id: Optional[str] = None) -> AIProvider:
    """Discover the active configured provider.

    Resolution order:
    1. Active or latest valid credential stored in user_provider_credentials / database.
    2. Fallback to server environment variables (.env / settings):
       - GEMINI_API_KEY
       - OPENAI_API_KEY
       - ANTHROPIC_API_KEY
       - GROQ_API_KEY
       - DEEPSEEK_API_KEY
    3. Raises NoProviderConfiguredError if no provider has credentials.
    """
    settings = get_settings()
    is_prod = settings.environment.lower() == "production"

    try:
        from security.auth import get_context_user_id
    except ImportError:
        from backend.security.auth import get_context_user_id

    effective_user_id = user_id or get_context_user_id()

    if is_prod and (not effective_user_id or effective_user_id == "default_user"):
        log.warning("get_active_provider_missing_user_in_production")
        raise AIProviderError("AUTHENTICATED_USER_REQUIRED: Authenticated user context is required to resolve AI provider in production.")

    # 1. Check database credentials
    try:
        try:
            from services.provider_service import get_active_stored_provider
        except ImportError:
            from backend.services.provider_service import get_active_stored_provider

        stored = get_active_stored_provider(user_id=effective_user_id)
        if stored and stored.get("api_key"):
            prov_name = stored["provider"].lower()
            if prov_name in PROVIDER_REGISTRY:
                return resolve_provider(
                    provider_id=prov_name,
                    api_key=stored["api_key"],
                    model=stored.get("model"),
                )
    except ValueError as exc:
        if "AUTHENTICATED_USER_REQUIRED" in str(exc):
            log.error("active_provider_missing_user_context", error=str(exc))
            raise AIProviderError(str(exc)) from exc
        if "PROVIDER_CREDENTIAL_DECRYPTION_FAILED" in str(exc):
            log.error("active_provider_decryption_failed", error=str(exc), user_id=effective_user_id)
            raise ProviderDecryptionError(
                f"Failed to decrypt stored provider credentials: {exc}. Please verify PROVIDER_ENCRYPTION_KEY or re-enter your API key in Settings → API & Providers."
            ) from exc
        raise
    except RuntimeError as exc:
        if is_prod:
            log.error("active_provider_db_query_failed", error=str(exc), user_id=effective_user_id)
            raise AIProviderError(f"Database error resolving AI provider: {exc}") from exc
        log.warning("error_checking_stored_provider", error=str(exc))
    except Exception as exc:
        if is_prod:
            log.error("active_provider_resolution_failed", error=str(exc), user_id=effective_user_id)
            raise AIProviderError(f"Failed to resolve active provider: {exc}") from exc
        log.warning("error_checking_stored_provider", error=str(exc))

    # 2. Check environment variables
    env_candidates = [
        ("google", settings.gemini_api_key, normalize_gemini_model(settings.gemini_model)),
        ("openai", settings.openai_api_key, None),
        ("anthropic", settings.anthropic_api_key, None),
        ("groq", settings.groq_api_key, None),
        ("deepseek", settings.deepseek_api_key, None),
    ]

    # If DEFAULT_AI_PROVIDER is specified in settings, check it first
    preferred = (settings.default_ai_provider or "").lower()
    if preferred:
        for p_id, key, model in env_candidates:
            if (p_id == preferred or (preferred == "gemini" and p_id == "google")) and key and key.strip():
                return resolve_provider(provider_id=p_id, api_key=key.strip(), model=model)

    for p_id, key, model in env_candidates:
        if key and key.strip():
            return resolve_provider(provider_id=p_id, api_key=key.strip(), model=model)

    raise NoProviderConfiguredError(
        "No AI provider configured. Please configure at least one AI provider "
        "(Google Gemini, OpenAI, Anthropic, Groq, or DeepSeek) in Settings → API & Providers to activate MAARVIS."
    )


def list_available_providers() -> List[Dict[str, Any]]:
    return list(SUPPORTED_PROVIDER_METADATA)
