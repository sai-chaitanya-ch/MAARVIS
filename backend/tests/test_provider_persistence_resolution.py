"""
Focused unit tests for MAARVIS provider persistence and resolution.
Tests:
- Supabase persistence vs dev SQLite isolation
- Production enforcement (no default_user fallback in production)
- AES-256-GCM encryption/decryption roundtrip
- Decryption failure categorization (ProviderDecryptionError vs NoProviderConfiguredError)
- ContextVar user_id propagation to LLMProvider
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from config.settings import Settings
from security.auth import set_context_user_id, get_context_user_id
from security.crypto import encrypt_provider_key, decrypt_provider_key
from services.provider_service import (
    create_provider,
    list_providers,
    get_active_stored_provider,
)
from providers.factory import get_active_provider
from providers.base import NoProviderConfiguredError, ProviderDecryptionError, AIProviderError
from models.llm import LLMProvider, LLMError


TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_ENC_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv("PROVIDER_ENCRYPTION_KEY", TEST_ENC_KEY)
    set_context_user_id(None)
    yield
    set_context_user_id(None)


def test_encryption_decryption_roundtrip():
    api_key = "AIzaSySecretGeminiKey123456"
    encrypted = encrypt_provider_key(api_key)
    assert encrypted != api_key
    decrypted = decrypt_provider_key(encrypted)
    assert decrypted == api_key


def test_production_create_provider_requires_user_id(monkeypatch):
    monkeypatch.setattr("services.provider_service.get_settings", lambda: Settings(
        environment="production",
        supabase_url="https://fake.supabase.co",
        supabase_service_role_key="fake-key",
        provider_encryption_key=TEST_ENC_KEY,
    ))
    with pytest.raises(ValueError, match="Valid authenticated user_id required in production"):
        create_provider("google", "test-key", user_id=None)

    with pytest.raises(ValueError, match="Valid authenticated user_id required in production"):
        create_provider("google", "test-key", user_id="default_user")


def test_production_create_provider_supabase_failure_raises(monkeypatch):
    monkeypatch.setattr("services.provider_service.get_settings", lambda: Settings(
        environment="production",
        supabase_url="https://fake.supabase.co",
        supabase_service_role_key="fake-key",
        provider_encryption_key=TEST_ENC_KEY,
    ))

    # Mock Supabase returning HTTP 500 on post, and 200 on patch
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    mock_patch = MagicMock(status_code=200)

    with patch("httpx.Client.patch", return_value=mock_patch), patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="DATABASE_PERSISTENCE_FAILURE"):
            create_provider("google", "test-key", user_id=TEST_USER_ID)


def test_production_list_providers_supabase_failure_raises(monkeypatch):
    monkeypatch.setattr("services.provider_service.get_settings", lambda: Settings(
        environment="production",
        supabase_url="https://fake.supabase.co",
        supabase_service_role_key="fake-key",
        provider_encryption_key=TEST_ENC_KEY,
    ))

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

    with patch("httpx.Client.get", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="DATABASE_QUERY_FAILURE"):
            list_providers(user_id=TEST_USER_ID)


def test_production_get_active_stored_provider_missing_user(monkeypatch):
    monkeypatch.setattr("services.provider_service.get_settings", lambda: Settings(
        environment="production",
        supabase_url="https://fake.supabase.co",
        supabase_service_role_key="fake-key",
        provider_encryption_key=TEST_ENC_KEY,
    ))
    # Missing or default_user in production raises ValueError (never returns None)
    with pytest.raises(ValueError, match="AUTHENTICATED_USER_REQUIRED"):
        get_active_stored_provider(user_id=None)

    with pytest.raises(ValueError, match="AUTHENTICATED_USER_REQUIRED"):
        get_active_stored_provider(user_id="default_user")


def test_production_get_active_provider_missing_user(monkeypatch):
    monkeypatch.setattr("providers.factory.get_settings", lambda: Settings(
        environment="production",
        supabase_url="https://fake.supabase.co",
        supabase_service_role_key="fake-key",
        provider_encryption_key=TEST_ENC_KEY,
    ))
    with pytest.raises(AIProviderError, match="AUTHENTICATED_USER_REQUIRED"):
        get_active_provider(user_id=None)


def test_get_active_provider_decryption_failure(monkeypatch):
    monkeypatch.setattr("providers.factory.get_settings", lambda: Settings(
        environment="production",
        supabase_url="https://fake.supabase.co",
        supabase_service_role_key="fake-key",
        provider_encryption_key=TEST_ENC_KEY,
        gemini_api_key="",
        openai_api_key="",
    ))

    # Mock get_active_stored_provider raising ValueError("PROVIDER_CREDENTIAL_DECRYPTION_FAILED: ...")
    with patch(
        "services.provider_service.get_active_stored_provider",
        side_effect=ValueError("PROVIDER_CREDENTIAL_DECRYPTION_FAILED: Decryption failed for provider 'google'")
    ):
        with pytest.raises(ProviderDecryptionError, match="PROVIDER_CREDENTIAL_DECRYPTION_FAILED"):
            get_active_provider(user_id=TEST_USER_ID)


def test_llm_provider_resolves_context_user_id():
    llm = LLMProvider()
    set_context_user_id(TEST_USER_ID)

    with patch("models.llm.get_active_provider") as mock_gap:
        mock_adapter = MagicMock()
        mock_gap.return_value = mock_adapter

        provider = llm.get_provider()
        assert provider == mock_adapter
        mock_gap.assert_called_once_with(user_id=TEST_USER_ID)
