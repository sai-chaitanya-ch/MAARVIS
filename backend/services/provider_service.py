"""
Provider credential service for MAARVIS.
Stores encrypted user API key credentials for AI providers.
Never returns raw keys to API responses or logs.
Compatible with SQLite (local development) and Supabase / PostgreSQL.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from config.settings import get_settings
from utils.logging import get_logger

log = get_logger(__name__)


def _derive_key() -> bytes:
    """Derive encryption key from server PROVIDER_ENCRYPTION_KEY or fallback secret."""
    settings = get_settings()
    secret = (
        settings.provider_encryption_key
        or settings.verify_api_key
        or "maarvis-local-provider-secret-2026"
    )
    seed = f"{secret}:maarvis-provider-creds-v2"
    return hashlib.sha256(seed.encode("utf-8")).digest()


def _encrypt(plaintext: str) -> str:
    """Encrypt plaintext string using key derivation and base64 encoding."""
    key = _derive_key()
    data = plaintext.encode("utf-8")
    encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.b64encode(encrypted).decode("ascii")


def _decrypt(ciphertext: str) -> str:
    """Base64-decode then decrypt ciphertext string."""
    key = _derive_key()
    data = base64.b64decode(ciphertext.encode("ascii"))
    decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return decrypted.decode("utf-8")


def _mask_key(key: str) -> str:
    """Return masked version of API key for display (never reveal entire key)."""
    clean = key.strip()
    if len(clean) <= 8:
        return "*" * len(clean)
    return clean[:4] + "*" * (len(clean) - 8) + clean[-4:]


def _get_db_path() -> Path:
    settings = get_settings()
    p = Path(settings.sqlite_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@contextmanager
def _get_conn():
    conn = sqlite3.connect(str(_get_db_path()), timeout=20.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        yield conn
        conn.commit()
    finally:
        conn.close()


def ensure_provider_table() -> None:
    """Create user_provider_credentials table (Supabase/PostgreSQL schema ready)."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_provider_credentials (
                id TEXT PRIMARY KEY,
                user_id TEXT DEFAULT 'default_user',
                provider TEXT NOT NULL,
                label TEXT,
                model TEXT,
                encrypted_key TEXT NOT NULL,
                key_masked TEXT NOT NULL,
                status TEXT DEFAULT 'unchecked',
                is_active INTEGER DEFAULT 1,
                last_tested_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        # If legacy provider_credentials table exists, migrate rows over
        try:
            legacy_rows = conn.execute("SELECT * FROM provider_credentials").fetchall()
            for row in legacy_rows:
                exists = conn.execute(
                    "SELECT 1 FROM user_provider_credentials WHERE id = ?", (row["id"],)
                ).fetchone()
                if not exists:
                    conn.execute(
                        """
                        INSERT INTO user_provider_credentials
                        (id, user_id, provider, label, model, encrypted_key, key_masked, status, is_active, last_tested_at, created_at, updated_at)
                        VALUES (?, 'default_user', ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                        """,
                        (
                            row["id"],
                            row["provider"],
                            row["label"],
                            row["model"],
                            row["encrypted_key"],
                            row["key_masked"],
                            row["status"],
                            row["last_tested_at"],
                            row["created_at"],
                            row["updated_at"],
                        ),
                    )
        except Exception:
            pass
        conn.commit()


def create_provider(
    provider: str,
    api_key: str,
    model: str = "",
    label: str = "",
    user_id: str = "default_user",
    is_active: bool = True,
) -> Dict[str, Any]:
    """Store a new provider credential. Returns safe record (never raw key)."""
    ensure_provider_table()
    import uuid

    cred_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    encrypted = _encrypt(api_key.strip())
    masked = _mask_key(api_key.strip())
    norm_provider = provider.strip().lower()
    if norm_provider == "gemini":
        norm_provider = "google"

    with _get_conn() as conn:
        if is_active:
            # If activating this AI provider, mark other core AI providers as inactive
            conn.execute(
                "UPDATE user_provider_credentials SET is_active = 0 WHERE user_id = ? AND provider NOT IN ('jev', 'tavily', 'web_search')",
                (user_id,),
            )
        conn.execute(
            """
            INSERT INTO user_provider_credentials
            (id, user_id, provider, label, model, encrypted_key, key_masked, status, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cred_id,
                user_id,
                norm_provider,
                label or provider,
                model,
                encrypted,
                masked,
                "unchecked",
                1 if is_active else 0,
                now,
                now,
            ),
        )
        conn.commit()
    log.info("provider_credential_created", provider=norm_provider, id=cred_id)
    return _safe_record(cred_id) or {}


def list_providers(user_id: str = "default_user") -> List[Dict[str, Any]]:
    """List all configured providers for user. Never returns raw keys."""
    ensure_provider_table()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id FROM user_provider_credentials WHERE user_id = ? ORDER BY is_active DESC, updated_at DESC",
            (user_id,),
        ).fetchall()
    return [_safe_record(r["id"]) for r in rows if _safe_record(r["id"]) is not None]


def get_provider(cred_id: str) -> Optional[Dict[str, Any]]:
    """Get a provider record. Never returns raw key."""
    ensure_provider_table()
    return _safe_record(cred_id)


def set_active_provider(cred_id: str, user_id: str = "default_user") -> bool:
    """Designate a specific provider as active."""
    ensure_provider_table()
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        # Check target provider
        target = conn.execute(
            "SELECT provider FROM user_provider_credentials WHERE id = ? AND user_id = ?",
            (cred_id, user_id),
        ).fetchone()
        if not target:
            return False
        # If target is core AI provider, deactivate others
        if target["provider"] not in ("jev", "tavily", "web_search"):
            conn.execute(
                "UPDATE user_provider_credentials SET is_active = 0 WHERE user_id = ? AND provider NOT IN ('jev', 'tavily', 'web_search')",
                (user_id,),
            )
        conn.execute(
            "UPDATE user_provider_credentials SET is_active = 1, updated_at = ? WHERE id = ?",
            (now, cred_id),
        )
        conn.commit()
    return True


def update_provider(cred_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update provider fields. Encrypts new key if provided."""
    ensure_provider_table()
    now = datetime.now(timezone.utc).isoformat()
    fields = []
    values = []
    if "api_key" in updates and updates["api_key"]:
        raw_key = updates["api_key"].strip()
        fields.append("encrypted_key = ?")
        values.append(_encrypt(raw_key))
        fields.append("key_masked = ?")
        values.append(_mask_key(raw_key))
    if "model" in updates:
        fields.append("model = ?")
        values.append(updates["model"])
    if "label" in updates:
        fields.append("label = ?")
        values.append(updates["label"])
    if "is_active" in updates:
        fields.append("is_active = ?")
        values.append(1 if updates["is_active"] else 0)

    if not fields:
        return _safe_record(cred_id)

    fields.append("updated_at = ?")
    values.append(now)
    values.append(cred_id)
    with _get_conn() as conn:
        conn.execute(
            f"UPDATE user_provider_credentials SET {', '.join(fields)} WHERE id = ?", values
        )
        conn.commit()
    return _safe_record(cred_id)


def delete_provider(cred_id: str) -> bool:
    """Delete a provider credential."""
    ensure_provider_table()
    with _get_conn() as conn:
        result = conn.execute("DELETE FROM user_provider_credentials WHERE id = ?", (cred_id,))
        conn.commit()
    return result.rowcount > 0


async def test_provider_connection(cred_id: str) -> Dict[str, Any]:
    """Test whether the stored API key works for the provider."""
    ensure_provider_table()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM user_provider_credentials WHERE id = ?", (cred_id,)
        ).fetchone()
    if not row:
        return {"success": False, "error": "Provider not found"}

    try:
        raw_key = _decrypt(row["encrypted_key"])
        provider = row["provider"]
        model = row["model"]

        result = await _test_connection(provider, raw_key, model)

        now = datetime.now(timezone.utc).isoformat()
        status = "connected" if result.get("success") else "failed"
        with _get_conn() as conn:
            conn.execute(
                "UPDATE user_provider_credentials SET status = ?, last_tested_at = ?, updated_at = ? WHERE id = ?",
                (status, now, now, cred_id),
            )
            conn.commit()
        return result
    except Exception as exc:
        log.warning("provider_test_failed", cred_id=cred_id, error=str(exc))
        return {"success": False, "error": str(exc)}


async def _test_connection(provider: str, api_key: str, model: str = "") -> Dict[str, Any]:
    """Test connection using concrete provider adapters."""
    p_lower = provider.strip().lower()
    if p_lower in ("gemini", "google"):
        p_lower = "google"

    # Capability providers: JEV AI
    if p_lower == "jev":
        settings = get_settings()
        url = settings.jev_base_url.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model or settings.jev_model,
                        "state": "Test query connection probe",
                        "questions": {
                            "category": {
                                "type": "choice",
                                "options": ["CONVERSATIONAL", "FACTUAL_RAG"],
                            }
                        },
                    },
                )
            if resp.status_code in (200, 201):
                return {"success": True, "provider": "jev"}
            return {"success": False, "error": f"JEV AI returned HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # Capability providers: Web search / Tavily
    if p_lower in ("tavily", "web_search"):
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={"api_key": api_key, "query": "test", "max_results": 1},
                )
            if resp.status_code == 200:
                return {"success": True, "provider": "tavily"}
            return {"success": False, "error": f"Tavily returned HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    try:
        try:
            from providers.factory import PROVIDER_REGISTRY
        except ImportError:
            from backend.providers.factory import PROVIDER_REGISTRY
        if p_lower in PROVIDER_REGISTRY:
            adapter_cls = PROVIDER_REGISTRY[p_lower]
            adapter = adapter_cls(api_key=api_key, model=model)
            return await adapter.test_connection()
    except Exception as exc:
        log.warning("adapter_test_failed", provider=provider, error=str(exc))

    return {"success": False, "error": f"Unsupported provider: {provider}"}


def _safe_record(cred_id: str) -> Optional[Dict[str, Any]]:
    """Return a provider record with key masked. Never returns raw key."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM user_provider_credentials WHERE id = ?", (cred_id,)
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "provider": row["provider"],
        "label": row["label"],
        "model": row["model"],
        "key_masked": row["key_masked"],
        "status": row["status"],
        "is_active": bool(row["is_active"]),
        "last_tested_at": row["last_tested_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_active_stored_provider(user_id: Optional[str] = "default_user") -> Optional[Dict[str, Any]]:
    """Retrieve active AI provider credentials from database."""
    ensure_provider_table()
    with _get_conn() as conn:
        # Check active provider first
        row = conn.execute(
            """
            SELECT * FROM user_provider_credentials
            WHERE provider NOT IN ('jev', 'tavily', 'web_search')
              AND is_active = 1
            ORDER BY updated_at DESC LIMIT 1
            """
        ).fetchone()
        # Fallback to any configured core provider if none marked active
        if not row:
            row = conn.execute(
                """
                SELECT * FROM user_provider_credentials
                WHERE provider NOT IN ('jev', 'tavily', 'web_search')
                ORDER BY updated_at DESC LIMIT 1
                """
            ).fetchone()

        if row:
            try:
                raw_key = _decrypt(row["encrypted_key"])
                if raw_key and raw_key.strip():
                    return {
                        "id": row["id"],
                        "provider": row["provider"],
                        "api_key": raw_key.strip(),
                        "model": row["model"],
                        "label": row["label"],
                        "status": row["status"],
                        "key_masked": row["key_masked"],
                    }
            except Exception as exc:
                log.warning("failed_decrypting_stored_provider_key", error=str(exc))

    return None


def get_gemini_credentials() -> Optional[Dict[str, Any]]:
    """Retrieve Google Gemini credentials if configured."""
    ensure_provider_table()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM user_provider_credentials WHERE provider IN ('google', 'gemini') ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        if row:
            try:
                raw_key = _decrypt(row["encrypted_key"])
                if raw_key and raw_key.strip():
                    return {
                        "id": row["id"],
                        "provider": "google",
                        "api_key": raw_key.strip(),
                        "model": row["model"] or "gemini-2.0-flash",
                        "label": row["label"] or "Google Gemini",
                        "status": row["status"],
                        "key_masked": row["key_masked"],
                    }
            except Exception as exc:
                log.warning("failed_decrypting_gemini_key", error=str(exc))

    settings = get_settings()
    if settings.gemini_api_key and settings.gemini_api_key.strip():
        raw_key = settings.gemini_api_key.strip()
        return {
            "id": "env_gemini",
            "provider": "google",
            "api_key": raw_key,
            "model": settings.gemini_model or "gemini-2.0-flash",
            "label": "Google Gemini (.env)",
            "status": "connected",
            "key_masked": _mask_key(raw_key),
        }
    return None


def get_jev_credentials() -> Optional[Dict[str, Any]]:
    """Retrieve JEV credentials if configured."""
    ensure_provider_table()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM user_provider_credentials WHERE provider = 'jev' ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        if row:
            try:
                raw_key = _decrypt(row["encrypted_key"])
                if raw_key and raw_key.strip():
                    return {
                        "id": row["id"],
                        "provider": "jev",
                        "api_key": raw_key.strip(),
                        "model": row["model"] or "jev-latest",
                        "status": row["status"],
                        "key_masked": row["key_masked"],
                    }
            except Exception:
                pass
    settings = get_settings()
    if settings.jev_api_key and settings.jev_api_key.strip():
        raw_key = settings.jev_api_key.strip()
        return {
            "id": "env_jev",
            "provider": "jev",
            "api_key": raw_key,
            "model": settings.jev_model or "jev-latest",
            "status": "connected",
            "key_masked": _mask_key(raw_key),
        }
    return None


def get_web_search_credentials() -> Optional[Dict[str, Any]]:
    """Retrieve Web Search (Tavily) credentials if configured."""
    ensure_provider_table()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM user_provider_credentials WHERE provider IN ('tavily', 'web_search') ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        if row:
            try:
                raw_key = _decrypt(row["encrypted_key"])
                if raw_key and raw_key.strip():
                    return {
                        "id": row["id"],
                        "provider": "tavily",
                        "api_key": raw_key.strip(),
                        "status": row["status"],
                        "key_masked": row["key_masked"],
                    }
            except Exception:
                pass
    settings = get_settings()
    if settings.tavily_api_key and settings.tavily_api_key.strip():
        raw_key = settings.tavily_api_key.strip()
        return {
            "id": "env_tavily",
            "provider": "tavily",
            "api_key": raw_key,
            "status": "connected",
            "key_masked": _mask_key(raw_key),
        }
    return None


def get_system_capabilities() -> Dict[str, Any]:
    """Evaluate system capabilities across required AI provider and optional layers."""
    active_prov_info = None
    try:
        try:
            from providers.factory import get_active_provider
        except ImportError:
            from backend.providers.factory import get_active_provider
        prov = get_active_provider()
        active_prov_info = {
            "connected": True,
            "provider": prov.provider_id,
            "display_name": prov.display_name,
            "model": prov.model,
        }
    except Exception:
        active_prov_info = None

    jev = get_jev_credentials()
    web = get_web_search_credentials()

    qdrant_ok = True
    try:
        from rag.vector_store import get_vector_store
        get_vector_store().ping()
    except Exception:
        qdrant_ok = False

    return {
        "ai_provider": {
            "connected": bool(active_prov_info),
            "required": True,
            "provider": active_prov_info["provider"] if active_prov_info else None,
            "label": active_prov_info["display_name"] if active_prov_info else "AI Provider",
            "model": active_prov_info["model"] if active_prov_info else "None",
            "description": "Core answer generation, reasoning, synthesis, and verification",
        },
        # Compatibility field for existing UI components looking for gemini
        "gemini": {
            "connected": bool(active_prov_info),
            "required": True,
            "model": active_prov_info["model"] if active_prov_info else "gemini-2.0-flash",
            "label": active_prov_info["display_name"] if active_prov_info else "Google Gemini",
            "description": "Core answer generation, reasoning, synthesis, and verification",
        },
        "rag": {
            "connected": qdrant_ok,
            "required": False,
            "label": "Document RAG",
            "description": "Vector grounding and document chunk retrieval via Qdrant",
        },
        "jev": {
            "connected": bool(jev),
            "required": False,
            "label": "JEV AI",
            "description": "Advanced semantic routing and structured decision making",
            "key_masked": jev.get("key_masked") if jev else None,
        },
        "web_search": {
            "connected": bool(web),
            "required": False,
            "label": "Web Search",
            "description": "Independent external sources, current web info, and multi-source verification",
            "key_masked": web.get("key_masked") if web else None,
        },
        "sandbox": {
            "connected": True,
            "required": False,
            "label": "AST Sandbox",
            "description": "Deterministic Python calculation and numeric verification",
        },
    }
