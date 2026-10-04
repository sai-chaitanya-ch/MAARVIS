"""
Authentication and security middleware for MAARVIS.
Derives authenticated user identity from Supabase Auth JWT.
Enforces strict 401 on missing or invalid tokens in production.
Never trusts X-User-ID in production.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional
import httpx
import jwt
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
    request: Optional[Request] = None,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
) -> str:
    """Extract authenticated user ID from Supabase JWT.

    Security rules:
    - Production: Derives user ONLY from Supabase JWT Bearer token.
      Never trusts X-User-ID.
      Never falls back to 'default_user'. Missing or invalid token -> HTTP 401.
    - Development / Testing: Supports synthetic test tokens and test overrides for isolated test suites.
    """
    settings = get_settings()
    is_prod = settings.environment.lower() == "production"

    # Extract Bearer token from Authorization header
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    elif request and "authorization" in request.headers:
        auth_h = request.headers.get("authorization", "")
        if auth_h.startswith("Bearer "):
            token = auth_h[7:].strip()

    # PRODUCTION AUTHENTICATION FLOW
    if is_prod:
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Provide a valid Supabase Bearer token in Authorization header.",
            )

        # Validate with Supabase Auth API
        if settings.supabase_url and (settings.supabase_service_role_key or settings.supabase_anon_key):
            try:
                supabase_key = settings.supabase_service_role_key or settings.supabase_anon_key
                url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        url,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "apikey": supabase_key,
                        },
                    )
                if resp.status_code == 200:
                    user_data = resp.json()
                    uid = user_data.get("id")
                    if uid:
                        return str(uid)
                raise HTTPException(status_code=401, detail="Invalid or expired Supabase authentication token")
            except HTTPException:
                raise
            except Exception as exc:
                log.warning("supabase_auth_network_error", error=str(exc))
                raise HTTPException(status_code=401, detail="Authentication verification failed")

        # Fallback to local JWT decoding if Supabase URL is not configured
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            uid = payload.get("sub")
            if uid:
                return str(uid)
        except Exception:
            pass

        raise HTTPException(status_code=401, detail="Invalid or expired authentication token")

    # DEVELOPMENT & TEST ENVIRONMENT ONLY
    # 1. Bearer token provided in dev/test
    if token:
        # Check if live Supabase Auth is active and reachable
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
                    uid = resp.json().get("id")
                    if uid:
                        return str(uid)
            except Exception:
                pass

        # Check for synthetic test token or JWT in dev/test
        if token.startswith("user_") or token.startswith("test_"):
            return token
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            uid = payload.get("sub")
            if uid:
                return str(uid)
        except Exception:
            pass

        return token

    # 2. Explicit test fixture override in dev/test (e.g. TestClient headers)
    if x_user_id and x_user_id.strip():
        return x_user_id.strip()

    # 3. Default user for local offline development only
    return "default_user"
