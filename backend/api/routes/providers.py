"""
Provider credentials API for MAARVIS.
Secure CRUD + connection testing + active provider management.
Never returns raw API keys.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.provider_service import (
    create_provider,
    list_providers,
    get_provider,
    update_provider,
    delete_provider,
    test_provider_connection,
    set_active_provider,
    ensure_provider_table,
)

router = APIRouter()

# Ensure table exists on import
try:
    ensure_provider_table()
except Exception:
    pass


class ProviderCreateRequest(BaseModel):
    provider: str = Field(..., description="Provider name: google, openai, anthropic, groq, deepseek, jev, tavily")
    api_key: str = Field(..., min_length=1, description="API key (stored encrypted, never returned)")
    model: str = Field("", description="Default model identifier")
    label: str = Field("", description="Display label")
    is_active: bool = Field(True, description="Designate as active provider")


class ProviderUpdateRequest(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None
    label: Optional[str] = None
    is_active: Optional[bool] = None


# Supported providers metadata (no keys, just display info)
SUPPORTED_PROVIDERS = [
    {
        "id": "google",
        "name": "Google Gemini",
        "category": "core",
        "required": False,
        "default_model": "gemini-2.0-flash",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "description": "Google's high-speed multimodal reasoning models.",
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "category": "core",
        "required": False,
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "description": "Industry benchmark reasoning and general-purpose models.",
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "category": "core",
        "required": False,
        "default_model": "claude-3-5-haiku-20241022",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
        "description": "Nuanced reasoning and factuality via Claude.",
    },
    {
        "id": "groq",
        "name": "Groq",
        "category": "core",
        "required": False,
        "default_model": "llama-3.3-70b-versatile",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "description": "Ultra-low latency inference powered by LPUs.",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "category": "core",
        "required": False,
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "description": "Advanced open-weight reasoning and code intelligence.",
    },
    {
        "id": "jev",
        "name": "JEV AI",
        "category": "optional",
        "required": False,
        "default_model": "jev-latest",
        "models": ["jev-latest"],
        "description": "Advanced semantic routing and structured decision making (Optional).",
    },
    {
        "id": "tavily",
        "name": "Web Search (Tavily)",
        "category": "optional",
        "required": False,
        "default_model": "",
        "models": [],
        "description": "Independent external sources and live web retrieval (Optional).",
    },
]


@router.get("/supported")
async def get_supported_providers():
    """Return supported provider list (no credentials)."""
    return {"providers": SUPPORTED_PROVIDERS}


@router.get("/capabilities")
async def get_capabilities():
    """Return real system capabilities across required and optional layers."""
    from services.provider_service import get_system_capabilities
    return get_system_capabilities()


@router.post("", status_code=201)
async def create_provider_credential(body: ProviderCreateRequest):
    """Store a new provider credential. Returns safe record (no raw key)."""
    p_norm = body.provider.lower().strip()
    if p_norm == "gemini":
        p_norm = "google"
    elif p_norm == "web_search":
        p_norm = "tavily"

    valid_ids = [p["id"] for p in SUPPORTED_PROVIDERS]
    if p_norm not in valid_ids:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {body.provider}")
    record = create_provider(p_norm, body.api_key, body.model, body.label, is_active=body.is_active)
    return record


@router.get("")
async def list_provider_credentials():
    """List all configured providers. Never returns raw keys."""
    return {"providers": list_providers()}


@router.get("/{cred_id}")
async def get_provider_credential(cred_id: str):
    """Get a specific provider. Never returns raw key."""
    record = get_provider(cred_id)
    if not record:
        raise HTTPException(status_code=404, detail="Provider not found")
    return record


@router.post("/{cred_id}/activate")
async def activate_provider_credential(cred_id: str):
    """Set provider as active AI provider."""
    ok = set_active_provider(cred_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"status": "activated", "id": cred_id}


@router.patch("/{cred_id}")
async def update_provider_credential(cred_id: str, body: ProviderUpdateRequest):
    """Update provider fields. Encrypts new key if provided."""
    record = get_provider(cred_id)
    if not record:
        raise HTTPException(status_code=404, detail="Provider not found")
    updates = body.model_dump(exclude_none=True)
    updated = update_provider(cred_id, updates)
    return updated


@router.delete("/{cred_id}")
async def delete_provider_credential(cred_id: str):
    """Delete a provider credential."""
    ok = delete_provider(cred_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"status": "deleted", "id": cred_id}


@router.post("/{cred_id}/test")
async def test_provider(cred_id: str):
    """Test a provider connection using the stored key."""
    record = get_provider(cred_id)
    if not record:
        raise HTTPException(status_code=404, detail="Provider not found")
    result = await test_provider_connection(cred_id)
    return result
