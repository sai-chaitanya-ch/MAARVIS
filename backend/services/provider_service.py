"""
Provider credential service for MAARVIS.
Stores encrypted user API key credentials for AI providers using AES-256-GCM.
Never returns raw keys to API responses or logs.
Persists credentials in Supabase PostgreSQL (user_provider_credentials) with local fallback.
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from config.settings import get_settings
from security.crypto import (
    derive_encryption_key,
    encrypt_provider_key,
    decrypt_provider_key,
    mask_provider_key,
)
from utils.logging import get_logger

log = get_logger(__name__)

# Aliases for compatibility
_encrypt = encrypt_provider_key
_decrypt = decrypt_provider_key
_mask_key = mask_provider_key


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
    """Create local user_provider_credentials table (for local dev/offline test fallback)."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_provider_credentials (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_prov_uid ON user_provider_credentials(user_id, is_active)")
        conn.commit()


def _is_supabase_ready() -> bool:
    settings = get_settings()
    return bool(settings.supabase_url and settings.supabase_service_role_key)


def _supabase_headers() -> Dict[str, str]:
    settings = get_settings()
    key = settings.supabase_service_role_key
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def create_provider(
    provider: str,
    api_key: str,
    model: str = "",
    label: str = "",
    user_id: str = "default_user",
    is_active: bool = True,
) -> Dict[str, Any]:
    """Store a new provider credential using AES-256-GCM. Returns safe record (never raw key)."""
    ensure_provider_table()
    cred_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    encrypted = encrypt_provider_key(api_key.strip())
    masked = mask_provider_key(api_key.strip())
    norm_provider = provider.strip().lower()
    if norm_provider == "gemini":
        norm_provider = "google"
    elif norm_provider == "web_search":
        norm_provider = "tavily"

    # 1. Supabase PostgreSQL persistence if configured
    if _is_supabase_ready():
        try:
            settings = get_settings()
            url = f"{settings.supabase_url.rstrip('/')}/rest/v1/user_provider_credentials"
            if is_active and norm_provider not in ("jev", "tavily", "web_search"):
                deact_url = f"{url}?user_id=eq.{user_id}&provider=not.in.(jev,tavily,web_search)"
                with httpx.Client(timeout=8.0) as client:
                    client.patch(deact_url, headers=_supabase_headers(), json={"is_active": 0, "updated_at": now})

            payload = {
                "id": cred_id,
                "user_id": user_id,
                "provider": norm_provider,
                "label": label or provider,
                "model": model,
                "encrypted_key": encrypted,
                "key_masked": masked,
                "status": "unchecked",
                "is_active": 1 if is_active else 0,
                "created_at": now,
                "updated_at": now,
            }
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, headers=_supabase_headers(), json=payload)
                if resp.status_code in {200, 201}:
                    log.info("provider_credential_saved_supabase", provider=norm_provider, user_id=user_id)
        except Exception as exc:
            log.warning("supabase_provider_save_notice", error=str(exc))

    # 2. Local database persistence (fallback and sync)
    with _get_conn() as conn:
        if is_active and norm_provider not in ("jev", "tavily", "web_search"):
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

    log.info("provider_credential_created", provider=norm_provider, id=cred_id, user_id=user_id)
    return get_provider(cred_id, user_id=user_id) or {}


def list_providers(user_id: str = "default_user") -> List[Dict[str, Any]]:
    """List all configured providers for user. Scoped strictly to user_id. Never returns raw keys."""
    ensure_provider_table()

    # 1. Supabase PostgreSQL
    if _is_supabase_ready():
        try:
            settings = get_settings()
            url = f"{settings.supabase_url.rstrip('/')}/rest/v1/user_provider_credentials?user_id=eq.{user_id}&order=is_active.desc,updated_at.desc"
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, headers=_supabase_headers())
                if resp.status_code == 200:
                    records = resp.json()
                    safe = []
                    for r in records:
                        item = dict(r)
                        item.pop("encrypted_key", None)
                        item["is_active"] = bool(item.get("is_active"))
                        safe.append(item)
                    return safe
        except Exception as exc:
            log.warning("supabase_list_providers_notice", error=str(exc))

    # 2. Local fallback
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id FROM user_provider_credentials WHERE user_id = ? ORDER BY is_active DESC, updated_at DESC",
            (user_id,),
        ).fetchall()
    return [_safe_record(r["id"]) for r in rows if _safe_record(r["id"]) is not None]


def get_provider(cred_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a safe provider record. Scoped by user_id if provided. Never returns raw key."""
    ensure_provider_table()

    # 1. Supabase PostgreSQL
    if _is_supabase_ready():
        try:
            settings = get_settings()
            query = f"id=eq.{cred_id}"
            if user_id:
                query += f"&user_id=eq.{user_id}"
            url = f"{settings.supabase_url.rstrip('/')}/rest/v1/user_provider_credentials?{query}&select=*"
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, headers=_supabase_headers())
                if resp.status_code == 200 and resp.json():
                    row = resp.json()[0]
                    row.pop("encrypted_key", None)
                    row["is_active"] = bool(row.get("is_active"))
                    return row
        except Exception:
            pass

    # 2. Local fallback
    return _safe_record(cred_id, user_id=user_id)


def set_active_provider(cred_id: str, user_id: str = "default_user") -> bool:
    """Designate a specific provider as active for this user."""
    ensure_provider_table()
    now = datetime.now(timezone.utc).isoformat()

    # Verify ownership
    target = None
    with _get_conn() as conn:
        target = conn.execute(
            "SELECT provider FROM user_provider_credentials WHERE id = ? AND user_id = ?",
            (cred_id, user_id),
        ).fetchone()

    # Supabase PostgreSQL check if not in local
    if not target and _is_supabase_ready():
        try:
            settings = get_settings()
            url = f"{settings.supabase_url.rstrip('/')}/rest/v1/user_provider_credentials?id=eq.{cred_id}&user_id=eq.{user_id}&select=provider"
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, headers=_supabase_headers())
                if resp.status_code == 200 and resp.json():
                    target = resp.json()[0]
        except Exception:
            pass

    if not target:
        return False

    prov_type = target["provider"]

    if _is_supabase_ready():
        try:
            settings = get_settings()
            base = f"{settings.supabase_url.rstrip('/')}/rest/v1/user_provider_credentials"
            with httpx.Client(timeout=8.0) as client:
                if prov_type not in ("jev", "tavily", "web_search"):
                    client.patch(
                        f"{base}?user_id=eq.{user_id}&provider=not.in.(jev,tavily,web_search)",
                        headers=_supabase_headers(),
                        json={"is_active": 0, "updated_at": now},
                    )
                client.patch(
                    f"{base}?id=eq.{cred_id}&user_id=eq.{user_id}",
                    headers=_supabase_headers(),
                    json={"is_active": 1, "updated_at": now},
                )
        except Exception as exc:
            log.warning("supabase_set_active_notice", error=str(exc))

    with _get_conn() as conn:
        if prov_type not in ("jev", "tavily", "web_search"):
            conn.execute(
                "UPDATE user_provider_credentials SET is_active = 0 WHERE user_id = ? AND provider NOT IN ('jev', 'tavily', 'web_search')",
                (user_id,),
            )
        conn.execute(
            "UPDATE user_provider_credentials SET is_active = 1, updated_at = ? WHERE id = ? AND user_id = ?",
            (now, cred_id, user_id),
        )
        conn.commit()
    return True


def update_provider(cred_id: str, updates: Dict[str, Any], user_id: str = "default_user") -> Optional[Dict[str, Any]]:
    """Update provider fields. Encrypts new key if provided. Scoped to user_id."""
    ensure_provider_table()
    now = datetime.now(timezone.utc).isoformat()
    fields = []
    values = []
    supabase_payload: Dict[str, Any] = {"updated_at": now}

    if "api_key" in updates and updates["api_key"]:
        raw_key = updates["api_key"].strip()
        enc = encrypt_provider_key(raw_key)
        masked = mask_provider_key(raw_key)
        fields.append("encrypted_key = ?")
        values.append(enc)
        fields.append("key_masked = ?")
        values.append(masked)
        supabase_payload["encrypted_key"] = enc
        supabase_payload["key_masked"] = masked
    if "model" in updates:
        fields.append("model = ?")
        values.append(updates["model"])
        supabase_payload["model"] = updates["model"]
    if "label" in updates:
        fields.append("label = ?")
        values.append(updates["label"])
        supabase_payload["label"] = updates["label"]
    if "is_active" in updates:
        fields.append("is_active = ?")
        values.append(1 if updates["is_active"] else 0)
        supabase_payload["is_active"] = 1 if updates["is_active"] else 0

    if _is_supabase_ready():
        try:
            settings = get_settings()
            url = f"{settings.supabase_url.rstrip('/')}/rest/v1/user_provider_credentials?id=eq.{cred_id}&user_id=eq.{user_id}"
            with httpx.Client(timeout=8.0) as client:
                client.patch(url, headers=_supabase_headers(), json=supabase_payload)
        except Exception as exc:
            log.warning("supabase_update_provider_notice", error=str(exc))

    if fields:
        fields.append("updated_at = ?")
        values.append(now)
        values.append(cred_id)
        values.append(user_id)
        with _get_conn() as conn:
            conn.execute(
                f"UPDATE user_provider_credentials SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
                values,
            )
            conn.commit()

    return get_provider(cred_id, user_id=user_id)


def delete_provider(cred_id: str, user_id: str = "default_user") -> bool:
    """Delete a provider credential scoped to user_id."""
    ensure_provider_table()
    deleted = False

    if _is_supabase_ready():
        try:
            settings = get_settings()
            url = f"{settings.supabase_url.rstrip('/')}/rest/v1/user_provider_credentials?id=eq.{cred_id}&user_id=eq.{user_id}"
            with httpx.Client(timeout=8.0) as client:
                resp = client.delete(url, headers=_supabase_headers())
                if resp.status_code in {200, 204}:
                    deleted = True
        except Exception:
            pass

    with _get_conn() as conn:
        res = conn.execute(
            "DELETE FROM user_provider_credentials WHERE id = ? AND user_id = ?",
            (cred_id, user_id),
        )
        conn.commit()
        if res.rowcount > 0:
            deleted = True

    return deleted


async def test_provider_connection(cred_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Test whether the stored API key works for the provider. Never logs or leaks raw key."""
    ensure_provider_table()
    row = None

    if _is_supabase_ready():
        try:
            settings = get_settings()
            query = f"id=eq.{cred_id}"
            if user_id:
                query += f"&user_id=eq.{user_id}"
            url = f"{settings.supabase_url.rstrip('/')}/rest/v1/user_provider_credentials?{query}&select=*"
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=_supabase_headers())
                if resp.status_code == 200 and resp.json():
                    row = resp.json()[0]
        except Exception:
            pass

    if not row:
        with _get_conn() as conn:
            if user_id:
                row = conn.execute(
                    "SELECT * FROM user_provider_credentials WHERE id = ? AND user_id = ?",
                    (cred_id, user_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM user_provider_credentials WHERE id = ?",
                    (cred_id,),
                ).fetchone()

    if not row:
        return {"success": False, "error": "Provider not found"}

    try:
        raw_key = decrypt_provider_key(row["encrypted_key"])
        provider = row["provider"]
        model = row["model"]

        result = await _test_connection(provider, raw_key, model)

        now = datetime.now(timezone.utc).isoformat()
        status = "connected" if result.get("success") else "failed"

        # Update status in Supabase & local DB
        if _is_supabase_ready():
            try:
                settings = get_settings()
                url = f"{settings.supabase_url.rstrip('/')}/rest/v1/user_provider_credentials?id=eq.{cred_id}"
                async with httpx.AsyncClient(timeout=8.0) as client:
                    await client.patch(
                        url,
                        headers=_supabase_headers(),
                        json={"status": status, "last_tested_at": now, "updated_at": now},
                    )
            except Exception:
                pass

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


def _safe_record(cred_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return a provider record with key masked. Never returns raw key."""
    with _get_conn() as conn:
        if user_id:
            row = conn.execute(
                "SELECT * FROM user_provider_credentials WHERE id = ? AND user_id = ?",
                (cred_id, user_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM user_provider_credentials WHERE id = ?", (cred_id,)
            ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "user_id": row["user_id"],
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


def get_active_stored_provider(user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve active AI provider credentials from database for the specified user_id.

    CRITICAL SECURITY RULE: Must always scope to the authenticated user_id.
    Never return another user's provider key.
    """
    ensure_provider_table()
    target_user = user_id or "default_user"

    # 1. Supabase PostgreSQL
    if _is_supabase_ready():
        try:
            settings = get_settings()
            url = f"{settings.supabase_url.rstrip('/')}/rest/v1/user_provider_credentials?user_id=eq.{target_user}&is_active=eq.1&provider=not.in.(jev,tavily,web_search)&order=updated_at.desc&limit=1"
            with httpx.Client(timeout=6.0) as client:
                resp = client.get(url, headers=_supabase_headers())
                if resp.status_code == 200 and resp.json():
                    row = resp.json()[0]
                    raw_key = decrypt_provider_key(row["encrypted_key"])
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
            log.warning("failed_querying_supabase_active_provider", error=str(exc))

    # 2. Local fallback
    with _get_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM user_provider_credentials
            WHERE user_id = ?
              AND provider NOT IN ('jev', 'tavily', 'web_search')
              AND is_active = 1
            ORDER BY updated_at DESC LIMIT 1
            """,
            (target_user,),
        ).fetchone()

        if not row:
            row = conn.execute(
                """
                SELECT * FROM user_provider_credentials
                WHERE user_id = ?
                  AND provider NOT IN ('jev', 'tavily', 'web_search')
                ORDER BY updated_at DESC LIMIT 1
                """,
                (target_user,),
            ).fetchone()

        if row:
            try:
                raw_key = decrypt_provider_key(row["encrypted_key"])
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


def get_gemini_credentials(user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve Google Gemini credentials if configured."""
    ensure_provider_table()
    target_user = user_id or "default_user"

    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM user_provider_credentials WHERE user_id = ? AND provider IN ('google', 'gemini') ORDER BY updated_at DESC LIMIT 1",
            (target_user,),
        ).fetchone()
        if row:
            try:
                raw_key = decrypt_provider_key(row["encrypted_key"])
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
            "key_masked": mask_provider_key(raw_key),
        }
    return None


def get_jev_credentials(user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve JEV credentials if configured."""
    ensure_provider_table()
    target_user = user_id or "default_user"

    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM user_provider_credentials WHERE user_id = ? AND provider = 'jev' ORDER BY updated_at DESC LIMIT 1",
            (target_user,),
        ).fetchone()
        if row:
            try:
                raw_key = decrypt_provider_key(row["encrypted_key"])
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
            "key_masked": mask_provider_key(raw_key),
        }
    return None


def get_web_search_credentials(user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve Web Search (Tavily) credentials if configured."""
    ensure_provider_table()
    target_user = user_id or "default_user"

    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM user_provider_credentials WHERE user_id = ? AND provider IN ('tavily', 'web_search') ORDER BY updated_at DESC LIMIT 1",
            (target_user,),
        ).fetchone()
        if row:
            try:
                raw_key = decrypt_provider_key(row["encrypted_key"])
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
            "key_masked": mask_provider_key(raw_key),
        }
    return None


def get_system_capabilities(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Evaluate system capabilities across required AI provider and optional layers. Real state only."""
    active_prov_info = None
    try:
        try:
            from providers.factory import get_active_provider
        except ImportError:
            from backend.providers.factory import get_active_provider
        prov = get_active_provider(user_id=user_id)
        active_prov_info = {
            "connected": True,
            "provider": prov.provider_id,
            "display_name": prov.display_name,
            "model": prov.model,
        }
    except Exception:
        active_prov_info = None

    jev = get_jev_credentials(user_id=user_id)
    web = get_web_search_credentials(user_id=user_id)

    # RAG vector store check (pgvector or local)
    rag_ok = True
    try:
        from rag.vector_store import get_vector_store
        rag_ok = get_vector_store().ping()
    except Exception:
        rag_ok = False

    return {
        "ai_provider": {
            "connected": bool(active_prov_info),
            "required": True,
            "provider": active_prov_info["provider"] if active_prov_info else None,
            "label": active_prov_info["display_name"] if active_prov_info else "AI Provider",
            "model": active_prov_info["model"] if active_prov_info else "None",
            "description": "Core answer generation, reasoning, synthesis, and verification",
        },
        "gemini": {
            "connected": bool(active_prov_info),
            "required": True,
            "model": active_prov_info["model"] if active_prov_info else "None",
            "label": active_prov_info["display_name"] if active_prov_info else "Google Gemini",
            "description": "Core answer generation, reasoning, synthesis, and verification",
        },
        "rag": {
            "connected": rag_ok,
            "required": False,
            "label": "Document RAG (pgvector)",
            "description": "Vector grounding and document chunk retrieval via Supabase pgvector",
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
