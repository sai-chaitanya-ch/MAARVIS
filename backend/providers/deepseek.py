"""
DeepSeek Provider Adapter.
Communicates directly with DeepSeek API (OpenAI-compatible).
"""
from __future__ import annotations

from .base import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    provider_id: str = "deepseek"
    display_name: str = "DeepSeek"
    default_model: str = "deepseek-chat"

    base_url: str = "https://api.deepseek.com"
    chat_endpoint: str = "/chat/completions"
    test_endpoint: str = "/models"
