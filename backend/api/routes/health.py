from fastapi import APIRouter

from config.settings import get_settings
from rag.vector_store import VectorStoreError, get_vector_store
from services.provider_service import (
    get_gemini_credentials,
    get_jev_credentials,
    get_web_search_credentials,
    get_system_capabilities,
)
try:
    from providers.factory import get_active_provider
except ImportError:
    from backend.providers.factory import get_active_provider

router = APIRouter()


@router.get("")
async def health():
    settings = get_settings()
    rag_status = {"ok": False, "type": "pgvector"}
    try:
        get_vector_store().ping()
        rag_status = {"ok": True, "type": "pgvector"}
    except Exception as exc:
        rag_status = {"ok": False, "type": "pgvector", "error": str(exc)}

    gemini = get_gemini_credentials()
    jev = get_jev_credentials()
    web = get_web_search_credentials()

    try:
        active_prov = get_active_provider()
        active_llm = {
            "provider": active_prov.display_name,
            "provider_id": active_prov.provider_id,
            "model": active_prov.model,
            "api_key_configured": True,
            "required": True,
        }
    except Exception:
        active_llm = {
            "provider": "None",
            "provider_id": None,
            "model": "None",
            "api_key_configured": False,
            "required": True,
        }

    return {
        "status": "ok",
        "app": "MAARVIS",
        "supported_core_providers": ["google", "openai", "anthropic", "groq", "deepseek"],
        "gemini_configured": bool(gemini),
        "llm_configured": active_llm["api_key_configured"],
        "llm": active_llm,
        "jev_configured": bool(jev),
        "tavily_configured": bool(web),
        "vector_store": rag_status,
        "capabilities": get_system_capabilities(),
    }
