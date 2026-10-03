"""
MAARVIS Provider Architecture.
Pluggable AI Provider Abstraction for Google Gemini, OpenAI, Anthropic, Groq, DeepSeek.
"""
from .base import AIProvider, AIProviderError, NoProviderConfiguredError
from .gemini import GeminiProvider
from .openai_provider import OpenAIProvider
from .anthropic import AnthropicProvider
from .groq import GroqProvider
from .deepseek import DeepSeekProvider
from .factory import get_active_provider, resolve_provider, list_available_providers, PROVIDER_REGISTRY

__all__ = [
    "AIProvider",
    "AIProviderError",
    "NoProviderConfiguredError",
    "GeminiProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GroqProvider",
    "DeepSeekProvider",
    "get_active_provider",
    "resolve_provider",
    "list_available_providers",
    "PROVIDER_REGISTRY",
]
