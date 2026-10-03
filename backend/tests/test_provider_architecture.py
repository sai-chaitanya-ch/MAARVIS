"""
Test suite for MAARVIS Provider Adapter Architecture.
Tests Google Gemini, OpenAI, Anthropic, Groq, DeepSeek adapters,
encryption at rest, user_provider_credentials table, and zero OmniRoute dependency.
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

import sys
sys.path.insert(0, 'd:/Temp/Projects/MARVIS/MARVIS/backend')

from providers.base import AIProvider, AIProviderError, NoProviderConfiguredError
from providers.gemini import GeminiProvider
from providers.openai_provider import OpenAIProvider
from providers.anthropic import AnthropicProvider
from providers.groq import GroqProvider
from providers.deepseek import DeepSeekProvider
from providers.factory import PROVIDER_REGISTRY, get_active_provider, resolve_provider
from models.llm import LLMProvider, get_llm
from services.provider_service import (
    create_provider,
    list_providers,
    get_provider,
    update_provider,
    delete_provider,
    set_active_provider,
    _encrypt,
    _decrypt,
    _mask_key,
)
from config.settings import get_settings


class TestProviderRegistry:
    def test_supported_providers_registered(self):
        assert "google" in PROVIDER_REGISTRY
        assert "gemini" in PROVIDER_REGISTRY
        assert "openai" in PROVIDER_REGISTRY
        assert "anthropic" in PROVIDER_REGISTRY
        assert "groq" in PROVIDER_REGISTRY
        assert "deepseek" in PROVIDER_REGISTRY
        # Confirm OmniRoute is NOT in the registry
        assert "omniroute" not in PROVIDER_REGISTRY

    def test_settings_has_no_omniroute_attributes(self):
        settings = get_settings()
        assert not hasattr(settings, "omniroute_api_key")
        assert not hasattr(settings, "omniroute_base_url")
        assert not hasattr(settings, "omniroute_model")


class TestProviderAdapters:
    @pytest.mark.asyncio
    async def test_gemini_generate(self):
        provider = GeminiProvider(api_key="test-gemini-key")
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Gemini response text"}}]
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            result = await provider.generate([{"role": "user", "content": "Hello"}])
            assert result == "Gemini response text"
            assert mock_post.called
            call_kwargs = mock_post.call_args[1]
            assert "Bearer test-gemini-key" in call_kwargs["headers"]["Authorization"]

    @pytest.mark.asyncio
    async def test_openai_generate(self):
        provider = OpenAIProvider(api_key="test-openai-key")
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "OpenAI response text"}}]
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.generate([{"role": "user", "content": "Hello"}])
            assert result == "OpenAI response text"

    @pytest.mark.asyncio
    async def test_anthropic_generate(self):
        provider = AnthropicProvider(api_key="test-anthropic-key")
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Claude response text"}]
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            result = await provider.generate([
                {"role": "system", "content": "Be concise"},
                {"role": "user", "content": "Hello"},
            ])
            assert result == "Claude response text"
            call_kwargs = mock_post.call_args[1]
            # System prompt separated out
            assert call_kwargs["json"]["system"] == "Be concise"
            # Headers have x-api-key and anthropic-version
            assert call_kwargs["headers"]["x-api-key"] == "test-anthropic-key"
            assert call_kwargs["headers"]["anthropic-version"] == "2023-06-01"

    @pytest.mark.asyncio
    async def test_groq_generate(self):
        provider = GroqProvider(api_key="test-groq-key")
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Groq fast response"}}]
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.generate([{"role": "user", "content": "Quick question"}])
            assert result == "Groq fast response"

    @pytest.mark.asyncio
    async def test_deepseek_generate(self):
        provider = DeepSeekProvider(api_key="test-deepseek-key")
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "DeepSeek reasoning"}}]
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.generate([{"role": "user", "content": "Solve this puzzle"}])
            assert result == "DeepSeek reasoning"


class TestEncryptionAndCredentials:
    def test_encrypt_decrypt_roundtrip(self):
        secret_key = "sk-live-secret-test-key-12345"
        encrypted = _encrypt(secret_key)
        assert encrypted != secret_key
        assert secret_key not in encrypted
        decrypted = _decrypt(encrypted)
        assert decrypted == secret_key

    def test_mask_key(self):
        key = "sk-proj-1234567890abcdef"
        masked = _mask_key(key)
        assert masked.startswith("sk-p")
        assert masked.endswith("cdef")
        assert "1234567890" not in masked

    def test_create_and_list_provider_credentials(self):
        # Create an Anthropic provider credential
        cred = create_provider(
            provider="anthropic",
            api_key="sk-ant-test-secret-value-9999",
            model="claude-3-5-sonnet-20241022",
            label="My Claude Sonnet",
        )
        assert cred is not None
        assert cred["provider"] == "anthropic"
        # Verify raw key is NEVER returned
        assert "sk-ant-test-secret-value-9999" not in str(cred)
        assert "key_masked" in cred
        assert cred["key_masked"].startswith("sk-a")

        # Test listing
        all_provs = list_providers()
        found = next((p for p in all_provs if p["id"] == cred["id"]), None)
        assert found is not None
        assert "encrypted_key" not in found
        assert "api_key" not in found

        # Test activate
        set_active_provider(cred["id"])
        updated = get_provider(cred["id"])
        assert updated["is_active"] is True

        # Clean up
        delete_provider(cred["id"])
        assert get_provider(cred["id"]) is None


class TestNoProviderConfiguredGracefulHandling:
    @pytest.mark.asyncio
    async def test_llm_stream_handles_no_provider_cleanly(self):
        """When no provider is configured, llm.stream() yields a clear message without raising."""
        llm = LLMProvider()
        msg = (
            "No AI provider configured. Please configure at least one AI provider "
            "(Google Gemini, OpenAI, Anthropic, Groq, or DeepSeek) in Settings → API & Providers to activate MAARVIS."
        )
        with patch.object(llm, "get_provider", side_effect=NoProviderConfiguredError(msg)):
            tokens = []
            async for token in llm.stream([{"role": "user", "content": "hi"}]):
                tokens.append(token)
            joined = "".join(tokens)
            assert "No AI provider configured" in joined
            assert "Settings" in joined
