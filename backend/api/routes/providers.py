"""
Provider credentials API for MAARVIS.
Secure user-scoped CRUD + connection testing + active provider management.
Never returns raw API keys.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from security.auth import get_current_user_id
from services.provider_service import (
    create_provider,
    list_providers,
    get_provider,
    update_provider,
    delete_provider,
    test_provider_connection,
    set_active_provider,
    ensure_provider_table,
    get_system_capabilities,
)

router = APIRouter()

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
    """Return supported provider list (public metadata, no secrets)."""
    return {"providers": SUPPORTED_PROVIDERS}


@router.get("/capabilities")
async def get_capabilities(
    request: Request = None,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
):
    """Return real system capabilities for the caller."""
    user_id = None
    try:
        user_id = await get_current_user_id(request, authorization, x_user_id)
    except Exception:
        pass
    return get_system_capabilities(user_id=user_id)


@router.post("", status_code=201)
async def create_provider_credential(
    body: ProviderCreateRequest,
    request: Request = None,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
):
    """Store a new provider credential. Scoped strictly to authenticated user."""
    user_id = await get_current_user_id(request, authorization, x_user_id)
    p_norm = body.provider.lower().strip()
    if p_norm == "gemini":
        p_norm = "google"
    elif p_norm == "web_search":
        p_norm = "tavily"

    valid_ids = [p["id"] for p in SUPPORTED_PROVIDERS]
    if p_norm not in valid_ids:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {body.provider}")
    record = create_provider(
        provider=p_norm,
        api_key=body.api_key,
        model=body.model,
        label=body.label,
        user_id=user_id,
        is_active=body.is_active,
    )
    return record


@router.get("")
async def list_provider_credentials(
    request: Request = None,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
):
    """List all configured providers for the authenticated user. Never returns raw keys."""
    user_id = await get_current_user_id(request, authorization, x_user_id)
    return {"providers": list_providers(user_id=user_id)}


@router.get("/{cred_id}")
async def get_provider_credential(
    cred_id: str,
    request: Request = None,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
):
    """Get a specific provider credential. Returns 404 if not found or not owned."""
    user_id = await get_current_user_id(request, authorization, x_user_id)
    record = get_provider(cred_id, user_id=user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Provider not found")
    return record


@router.post("/{cred_id}/activate")
async def activate_provider_credential(
    cred_id: str,
    request: Request = None,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
):
    """Set provider as active AI provider for the authenticated user."""
    user_id = await get_current_user_id(request, authorization, x_user_id)
    ok = set_active_provider(cred_id, user_id=user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"status": "activated", "id": cred_id}


@router.patch("/{cred_id}")
async def update_provider_credential(
    cred_id: str,
    body: ProviderUpdateRequest,
    request: Request = None,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
):
    """Update provider fields for authenticated user."""
    user_id = await get_current_user_id(request, authorization, x_user_id)
    record = get_provider(cred_id, user_id=user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Provider not found")
    updates = body.model_dump(exclude_none=True)
    updated = update_provider(cred_id, updates, user_id=user_id)
    return updated


@router.delete("/{cred_id}")
async def delete_provider_credential(
    cred_id: str,
    request: Request = None,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
):
    """Delete a provider credential. Returns 404 if not found or not owned."""
    user_id = await get_current_user_id(request, authorization, x_user_id)
    ok = delete_provider(cred_id, user_id=user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"status": "deleted", "id": cred_id}


@router.post("/{cred_id}/test")
async def test_provider(
    cred_id: str,
    request: Request = None,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
):
    """Test a provider connection. Scoped to authenticated user."""
    user_id = await get_current_user_id(request, authorization, x_user_id)
    record = get_provider(cred_id, user_id=user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Provider not found")
    result = await test_provider_connection(cred_id, user_id=user_id)
    return result
