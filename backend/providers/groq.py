"""
Groq Provider Adapter.
Communicates directly with Groq Cloud API (OpenAI-compatible).
"""
from __future__ import annotations

from .base import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    provider_id: str = "groq"
    display_name: str = "Groq"
    default_model: str = "llama-3.3-70b-versatile"

    base_url: str = "https://api.groq.com/openai/v1"
    chat_endpoint: str = "/chat/completions"
    test_endpoint: str = "/models"
