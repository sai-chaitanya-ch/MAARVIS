from __future__ import annotations

import re
from typing import Any, Dict, Optional
import httpx
from fastapi import Header, HTTPException, Request
from config.settings import get_settings
from utils.logging import get_logger

log = get_logger(__name__)

# Sensitive field names to never log
SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "encrypted_key",
    "password",
    "secret",
    "service_role_key",
    "supabase_service_role_key",
    "provider_encryption_key",
    "jwt",
    "access_token",
}


def sanitize_for_logging(data: Any) -> Any:
    """Recursively sanitize sensitive headers, credentials, and passwords from logs."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if str(k).lower() in SENSITIVE_KEYS:
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, (dict, list)):
                sanitized[k] = sanitize_for_logging(v)
            else:
                sanitized[k] = v
        return sanitized
    elif isinstance(data, list):
        return [sanitize_for_logging(item) for item in data]
    return data


async def get_current_user_id(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
) -> str:
    """Extract authenticated user ID from request.

    Supports:
    1. Direct header X-User-Id (for testing & internal dispatch)
    2. Supabase JWT Bearer token via Authorization header
    3. Graceful fallback to 'default_user' in local/dev environments.
    """
    settings = get_settings()

    # 1. Direct explicit test/header override
    if x_user_id and x_user_id.strip():
        return x_user_id.strip()

    # 2. Check Authorization Bearer token
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()

    if token:
        # If Supabase Auth is configured, verify with Supabase
        if settings.supabase_url and (settings.supabase_service_role_key or settings.supabase_anon_key):
            try:
                supabase_key = settings.supabase_service_role_key or settings.supabase_anon_key
                url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(
                        url,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "apikey": supabase_key,
                        },
                    )
                if resp.status_code == 200:
                    user_data = resp.json()
                    user_id = user_data.get("id")
                    if user_id:
                        return str(user_id)
                elif settings.environment == "production":
                    raise HTTPException(status_code=401, detail="Invalid or expired authentication token")
            except HTTPException:
                raise
            except Exception as exc:
                log.warning("supabase_auth_check_failed", error=str(exc))
                if settings.environment == "production":
                    raise HTTPException(status_code=401, detail="Authentication verification failed")

        # In dev/test: allow synthetic user tokens like 'user_123'
        if token.startswith("user_"):
            return token

    # 3. Environment check: require auth only if production flag is explicitly enabled
    if settings.environment == "production" and not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide a valid Bearer token.",
        )

    return "default_user"
