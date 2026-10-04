"""
Supabase Storage Service for MAARVIS Documents.
Stores uploaded documents in private Supabase Storage bucket 'documents'
under user-scoped paths: <user_id>/<document_id>/<filename>.
Treats Render local filesystem as ephemeral.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import httpx
from config.settings import get_settings
from utils.logging import get_logger

log = get_logger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parent.parent
LOCAL_UPLOAD_DIR = _BACKEND_DIR / "data" / "uploads"


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.bucket = self.settings.supabase_storage_bucket or "documents"

    @property
    def is_supabase_storage_enabled(self) -> bool:
        return bool(self.settings.supabase_url and self.settings.supabase_service_role_key)

    async def upload_document(
        self,
        file_bytes: bytes,
        filename: str,
        document_id: str,
        user_id: str = "default_user",
        mime_type: str = "application/octet-stream",
    ) -> str:
        """Upload file to Supabase Storage. Path: <user_id>/<document_id>/<filename>.

        Returns the storage path identifier.
        """
        clean_filename = Path(filename).name
        # User-scoped private path: <user_id>/<document_id>/<filename>
        storage_key = f"{user_id}/{document_id}/{clean_filename}"

        # 1. Supabase Storage (Production Primary)
        if self.is_supabase_storage_enabled:
            url = f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/{self.bucket}/{storage_key}"
            headers = {
                "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
                "apikey": self.settings.supabase_service_role_key,
                "Content-Type": mime_type,
                "x-upsert": "true",
            }
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, content=file_bytes, headers=headers)
                if resp.status_code in {200, 201}:
                    log.info("supabase_storage_uploaded", key=storage_key, user_id=user_id)
                    return f"supabase://{self.bucket}/{storage_key}"
                else:
                    log.warning("supabase_storage_failed", status=resp.status_code, body=resp.text[:200])
            except Exception as exc:
                log.warning("supabase_storage_error", error=str(exc))

        # 2. Ephemeral / local fallback storage
        local_dir = LOCAL_UPLOAD_DIR / user_id / document_id
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / clean_filename
        local_path.write_bytes(file_bytes)
        log.info("local_ephemeral_storage_saved", path=str(local_path))
        return local_path.as_posix()

    async def delete_document(self, storage_path: str) -> bool:
        """Delete file from Supabase Storage or local filesystem."""
        if storage_path.startswith("supabase://"):
            if self.is_supabase_storage_enabled:
                clean_path = storage_path.replace(f"supabase://{self.bucket}/", "")
                url = f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/{self.bucket}"
                headers = {
                    "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
                    "apikey": self.settings.supabase_service_role_key,
                    "Content-Type": "application/json",
                }
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.request(
                            "DELETE",
                            url,
                            headers=headers,
                            json={"prefixes": [clean_path]},
                        )
                    return resp.status_code in {200, 204}
                except Exception as exc:
                    log.warning("supabase_storage_delete_error", error=str(exc))
                    return False
            return True

        # Local file delete
        try:
            p = Path(storage_path)
            if p.exists():
                p.unlink()
                return True
        except Exception:
            pass
        return False


_STORAGE_SERVICE: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    global _STORAGE_SERVICE
    if _STORAGE_SERVICE is None:
        _STORAGE_SERVICE = StorageService()
    return _STORAGE_SERVICE
