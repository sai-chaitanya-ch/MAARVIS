"""
Cryptographic utilities for MAARVIS provider credentials.
Implements production-grade authenticated encryption using AES-256-GCM.
Never logs or exposes raw keys.
"""
from __future__ import annotations

import base64
import hashlib
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from config.settings import get_settings
from utils.logging import get_logger

log = get_logger(__name__)


def derive_encryption_key(secret: Optional[str] = None) -> bytes:
    """Derive a 256-bit (32-byte) key for AES-256-GCM from server secret."""
    if not secret:
        settings = get_settings()
        if settings.environment.lower() == "production":
            key_val = settings.provider_encryption_key or settings.verify_api_key
            if not key_val or not key_val.strip():
                raise ValueError(
                    "CRITICAL_CONFIGURATION_ERROR: PROVIDER_ENCRYPTION_KEY is required in production environment. "
                    "Configure PROVIDER_ENCRYPTION_KEY in Render environment settings to enable secure AES-256-GCM encryption."
                )
            secret = key_val.strip()
        else:
            secret = (
                settings.provider_encryption_key
                or settings.verify_api_key
                or "maarvis-production-provider-master-secret-2026"
            )
    seed = f"{secret}:maarvis-aes256-gcm-v1"
    return hashlib.sha256(seed.encode("utf-8")).digest()


def encrypt_provider_key(raw_key: str, key_bytes: Optional[bytes] = None) -> str:
    """Encrypt plaintext API key using AES-256-GCM.

    Returns base64-encoded string: base64(12_byte_nonce + ciphertext_with_auth_tag)
    """
    clean_key = raw_key.strip()
    if not clean_key:
        return ""
    key = key_bytes or derive_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # Standard 96-bit nonce for AES-GCM
    ciphertext = aesgcm.encrypt(nonce, clean_key.encode("utf-8"), None)
    payload = nonce + ciphertext
    return base64.b64encode(payload).decode("ascii")


def decrypt_provider_key(encrypted_str: str, key_bytes: Optional[bytes] = None) -> str:
    """Decrypt an AES-256-GCM encrypted API key.

    Also supports backward-compatibility for legacy XOR-encrypted records during migration.
    """
    if not encrypted_str or not encrypted_str.strip():
        return ""
    clean_str = encrypted_str.strip()
    key = key_bytes or derive_encryption_key()

    try:
        raw_bytes = base64.b64decode(clean_str.encode("ascii"))
        if len(raw_bytes) > 28:  # 12-byte nonce + at least 16-byte auth tag + 1-byte data
            try:
                nonce = raw_bytes[:12]
                ciphertext = raw_bytes[12:]
                aesgcm = AESGCM(key)
                decrypted = aesgcm.decrypt(nonce, ciphertext, None)
                return decrypted.decode("utf-8")
            except Exception:
                pass  # Fall through to legacy check
    except Exception:
        pass

    # Legacy XOR fallback for historical records if any
    try:
        data = base64.b64decode(clean_str.encode("ascii"))
        decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
        text = decrypted.decode("utf-8")
        if text.isprintable():
            return text
    except Exception:
        pass

    raise ValueError("Failed to decrypt provider credential: authentication tag mismatch or invalid key")


def mask_provider_key(key: str) -> str:
    """Return safely masked version of an API key (e.g. AIza************1234)."""
    clean = key.strip()
    if not clean:
        return "********"
    if len(clean) <= 8:
        return "*" * len(clean)
    return clean[:4] + "*" * (len(clean) - 8) + clean[-4:]
