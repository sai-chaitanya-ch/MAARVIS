"""
Supabase PostgreSQL & PostgREST Client Service for MAARVIS.
Manages conversations, messages, documents, pgvector document_chunks,
and user_provider_credentials scoped strictly to authenticated user_id.

Includes a local state fallback for offline development & isolated pytest runs.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from config.settings import get_settings
from utils.logging import get_logger
from utils.tracing import is_valid_uuid, new_id, new_uuid

log = get_logger(__name__)

# In-memory storage for offline / unit test mode when Supabase credentials are not provided
_MEM_CONVERSATIONS: Dict[str, Dict[str, Any]] = {}
_MEM_MESSAGES: List[Dict[str, Any]] = []
_MEM_DOCUMENTS: Dict[str, Dict[str, Any]] = {}
_MEM_CHUNKS: List[Dict[str, Any]] = []
_MEM_CREDENTIALS: Dict[str, Dict[str, Any]] = {}


class SupabaseService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _validate_user(self, user_id: Optional[str]) -> str:
        from security.auth import get_context_user_id
        ctx_user = get_context_user_id()
        resolved = user_id or ctx_user
        if resolved == "default_user" and ctx_user and ctx_user != "default_user":
            resolved = ctx_user
        if self.settings.is_production:
            if not resolved or resolved == "default_user":
                raise ValueError("AUTHENTICATED_USER_REQUIRED: An authenticated user_id is required in production")
        return resolved or "default_user"

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.supabase_url and self.settings.supabase_service_role_key)

    @property
    def _headers(self) -> Dict[str, str]:
        key = self.settings.supabase_service_role_key
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    @property
    def _rest_url(self) -> str:
        return f"{self.settings.supabase_url.rstrip('/')}/rest/v1"

    # =========================================================================
    # CONVERSATIONS
    # =========================================================================

    async def create_conversation(
        self,
        title: str,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> str:
        effective_user = self._validate_user(user_id)
        cid = conversation_id if (conversation_id and is_valid_uuid(conversation_id)) else new_uuid()
        now = datetime.now(timezone.utc).isoformat()
        clean_title = (title or "New Conversation")[:80]

        if self.is_configured:
            url = f"{self._rest_url}/conversations"
            payload = {
                "id": cid,
                "user_id": effective_user,
                "title": clean_title,
                "created_at": now,
                "updated_at": now,
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=self._headers, json=payload)
                if resp.status_code in {200, 201}:
                    return cid
                log.warning("supabase_create_conversation_failed", status=resp.status_code, body=resp.text[:200])
                if self.settings.is_production:
                    raise RuntimeError(f"Failed to persist conversation to Supabase: HTTP {resp.status_code} - {resp.text[:200]}")

        if self.settings.is_production and not self.is_configured:
            raise RuntimeError("Supabase credentials not configured in production")

        # Local fallback
        _MEM_CONVERSATIONS[cid] = {
            "id": cid,
            "user_id": effective_user,
            "title": clean_title,
            "created_at": now,
            "updated_at": now,
        }
        return cid

    async def list_conversations(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        effective_user = self._validate_user(user_id)
        if self.is_configured:
            url = f"{self._rest_url}/conversations?user_id=eq.{effective_user}&order=updated_at.desc&limit=100"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._headers)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data:
                        item["message_count"] = 0
                    return data
                log.warning("supabase_list_conversations_failed", status=resp.status_code)
                if self.settings.is_production:
                    raise RuntimeError(f"Failed to list conversations from Supabase: HTTP {resp.status_code}")

        if self.settings.is_production and not self.is_configured:
            raise RuntimeError("Supabase credentials not configured in production")

        # Local fallback
        res = [
            {**c, "message_count": sum(1 for m in _MEM_MESSAGES if m.get("conversation_id") == c["id"])}
            for c in _MEM_CONVERSATIONS.values()
            if c.get("user_id") == effective_user
        ]
        res.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return res

    async def get_conversation(self, conversation_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        effective_user = self._validate_user(user_id)
        if self.is_configured:
            url = f"{self._rest_url}/conversations?id=eq.{conversation_id}&user_id=eq.{effective_user}&select=*"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._headers)
                if resp.status_code == 200 and resp.json():
                    conv = resp.json()[0]
                    # Fetch messages
                    m_url = f"{self._rest_url}/messages?conversation_id=eq.{conversation_id}&user_id=eq.{effective_user}&order=created_at.asc"
                    m_resp = await client.get(m_url, headers=self._headers)
                    conv["messages"] = m_resp.json() if m_resp.status_code == 200 else []
                    return conv
                return None

        if self.settings.is_production and not self.is_configured:
            raise RuntimeError("Supabase credentials not configured in production")

        # Local fallback
        conv = _MEM_CONVERSATIONS.get(conversation_id)
        if not conv or conv.get("user_id") != effective_user:
            return None
        msgs = [m for m in _MEM_MESSAGES if m.get("conversation_id") == conversation_id and m.get("user_id") == effective_user]
        msgs.sort(key=lambda x: x.get("created_at", ""))
        return {**conv, "messages": msgs}

    async def touch_conversation(self, conversation_id: str, user_id: Optional[str] = None, title: Optional[str] = None) -> None:
        effective_user = self._validate_user(user_id) if (self.settings.is_production or user_id) else None
        now = datetime.now(timezone.utc).isoformat()
        payload: Dict[str, Any] = {"updated_at": now}
        if title:
            payload["title"] = title[:80]

        if self.is_configured:
            filter_query = f"id=eq.{conversation_id}"
            if effective_user:
                filter_query += f"&user_id=eq.{effective_user}"
            url = f"{self._rest_url}/conversations?{filter_query}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.patch(url, headers=self._headers, json=payload)
                return

        # Local fallback
        if conversation_id in _MEM_CONVERSATIONS:
            _MEM_CONVERSATIONS[conversation_id]["updated_at"] = now
            if title:
                _MEM_CONVERSATIONS[conversation_id]["title"] = title[:80]

    async def delete_conversation(self, conversation_id: str, user_id: Optional[str] = None) -> bool:
        effective_user = self._validate_user(user_id)
        if self.is_configured:
            url = f"{self._rest_url}/conversations?id=eq.{conversation_id}&user_id=eq.{effective_user}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(url, headers=self._headers)
                return resp.status_code in {200, 204}

        if self.settings.is_production and not self.is_configured:
            raise RuntimeError("Supabase credentials not configured in production")

        # Local fallback
        global _MEM_MESSAGES
        if conversation_id in _MEM_CONVERSATIONS and _MEM_CONVERSATIONS[conversation_id].get("user_id") == effective_user:
            del _MEM_CONVERSATIONS[conversation_id]
            _MEM_MESSAGES = [m for m in _MEM_MESSAGES if m.get("conversation_id") != conversation_id]
            return True
        return False

    # =========================================================================
    # MESSAGES
    # =========================================================================

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
        message_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        execution_id: Optional[str] = None,
        routing: Optional[Dict[str, Any]] = None,
        verification: Optional[Dict[str, Any]] = None,
        execution_trace: Optional[Dict[str, Any]] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        events: Optional[List[Dict[str, Any]]] = None,
        claims: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        effective_user = self._validate_user(user_id)
        mid = message_id if (message_id and is_valid_uuid(message_id)) else new_uuid()
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": mid,
            "conversation_id": conversation_id,
            "user_id": effective_user,
            "role": role,
            "content": content,
            "provider": provider,
            "model": model,
            "execution_id": execution_id,
            "routing_json": routing,
            "verification_json": verification,
            "execution_trace_json": execution_trace,
            "sources_json": sources,
            "events_json": events,
            "claims_json": claims,
            "created_at": now,
        }

        if self.is_configured:
            url = f"{self._rest_url}/messages"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=self._headers, json=record)
                if resp.status_code in {200, 201}:
                    await self.touch_conversation(conversation_id, user_id=effective_user)
                    return mid
                log.warning("supabase_add_message_failed", status=resp.status_code, body=resp.text[:200])
                if self.settings.is_production:
                    raise RuntimeError(f"Failed to persist message to Supabase: HTTP {resp.status_code} - {resp.text[:200]}")

        if self.settings.is_production and not self.is_configured:
            raise RuntimeError("Supabase credentials not configured in production")

        # Local fallback
        _MEM_MESSAGES.append(record)
        await self.touch_conversation(conversation_id, user_id=effective_user)
        return mid

    async def recent_messages(self, conversation_id: str, user_id: Optional[str] = None, limit: int = 12) -> List[Dict[str, str]]:
        effective_user = self._validate_user(user_id)
        if self.is_configured:
            url = f"{self._rest_url}/messages?conversation_id=eq.{conversation_id}&user_id=eq.{effective_user}&order=created_at.desc&limit={limit}&select=role,content"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._headers)
                if resp.status_code == 200:
                    rows = resp.json()
                    rows.reverse()
                    return [{"role": r["role"], "content": r["content"]} for r in rows]
                log.warning("supabase_recent_messages_failed", status=resp.status_code)
                if self.settings.is_production:
                    raise RuntimeError(f"Failed to load recent messages from Supabase: HTTP {resp.status_code}")

        if self.settings.is_production and not self.is_configured:
            raise RuntimeError("Supabase credentials not configured in production")

        # Local fallback
        msgs = [m for m in _MEM_MESSAGES if m.get("conversation_id") == conversation_id and m.get("user_id") == effective_user]
        msgs.sort(key=lambda x: x.get("created_at", ""))
        recent = msgs[-limit:]
        return [{"role": m["role"], "content": m["content"]} for m in recent]

    # =========================================================================
    # DOCUMENTS
    # =========================================================================

    async def save_document(
        self,
        document_id: str,
        name: str,
        storage_path: str,
        chunks: int,
        user_id: Optional[str] = None,
        mime_type: str = "application/octet-stream",
        size_bytes: int = 0,
    ) -> None:
        effective_user = self._validate_user(user_id)
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": document_id,
            "user_id": effective_user,
            "name": name,
            "mime_type": mime_type,
            "storage_path": storage_path,
            "size_bytes": size_bytes,
            "chunks": chunks,
            "created_at": now,
        }

        if self.is_configured:
            url = f"{self._rest_url}/documents"
            headers = dict(self._headers)
            headers["Prefer"] = "resolution=merge-duplicates,return=representation"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=headers, json=record)
                if resp.status_code in {200, 201}:
                    return
                log.warning("supabase_save_document_failed", status=resp.status_code, body=resp.text[:200])
                if self.settings.is_production:
                    raise RuntimeError(f"Failed to save document in Supabase: HTTP {resp.status_code}")

        if self.settings.is_production and not self.is_configured:
            raise RuntimeError("Supabase credentials not configured in production")

        # Local fallback
        _MEM_DOCUMENTS[document_id] = record

    async def list_documents(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        effective_user = self._validate_user(user_id)
        if self.is_configured:
            url = f"{self._rest_url}/documents?user_id=eq.{effective_user}&order=created_at.desc"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._headers)
                if resp.status_code == 200:
                    docs = resp.json()
                    for d in docs:
                        d["filename"] = d.get("name", "")
                    return docs
                log.warning("supabase_list_documents_failed", status=resp.status_code)
                if self.settings.is_production:
                    raise RuntimeError(f"Failed to list documents from Supabase: HTTP {resp.status_code}")

        if self.settings.is_production and not self.is_configured:
            raise RuntimeError("Supabase credentials not configured in production")

        # Local fallback
        docs = [d for d in _MEM_DOCUMENTS.values() if d.get("user_id") == effective_user]
        docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        for d in docs:
            d["filename"] = d.get("name", "")
        return docs

    async def get_document(self, document_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        effective_user = self._validate_user(user_id)
        if self.is_configured:
            url = f"{self._rest_url}/documents?id=eq.{document_id}&user_id=eq.{effective_user}&select=*"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._headers)
                if resp.status_code == 200 and resp.json():
                    doc = resp.json()[0]
                    doc["filename"] = doc.get("name", "")
                    return doc
                return None

        if self.settings.is_production and not self.is_configured:
            raise RuntimeError("Supabase credentials not configured in production")

        # Local fallback
        doc = _MEM_DOCUMENTS.get(document_id)
        if doc and doc.get("user_id") == effective_user:
            res = dict(doc)
            res["filename"] = res.get("name", "")
            return res
        return None

    async def delete_document(self, document_id: str, user_id: Optional[str] = None) -> bool:
        effective_user = self._validate_user(user_id)
        if self.is_configured:
            url = f"{self._rest_url}/documents?id=eq.{document_id}&user_id=eq.{effective_user}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(url, headers=self._headers)
                return resp.status_code in {200, 204}

        if self.settings.is_production and not self.is_configured:
            raise RuntimeError("Supabase credentials not configured in production")

        # Local fallback
        global _MEM_CHUNKS
        if document_id in _MEM_DOCUMENTS and _MEM_DOCUMENTS[document_id].get("user_id") == effective_user:
            del _MEM_DOCUMENTS[document_id]
            _MEM_CHUNKS = [c for c in _MEM_CHUNKS if c.get("document_id") != document_id]
            return True
        return False

    # =========================================================================
    # DOCUMENT CHUNKS (pgvector)
    # =========================================================================

    async def insert_document_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        if not chunks:
            return
        if self.is_configured:
            url = f"{self._rest_url}/document_chunks"
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, headers=self._headers, json=chunks)
                if resp.status_code in {200, 201}:
                    return
                log.warning("supabase_insert_chunks_failed", status=resp.status_code, body=resp.text[:300])
                if self.settings.is_production:
                    raise RuntimeError(f"Failed to insert document chunks into Supabase: HTTP {resp.status_code}")

        if self.settings.is_production and not self.is_configured:
            raise RuntimeError("Supabase credentials not configured in production")

        # Local fallback
        _MEM_CHUNKS.extend(chunks)

    async def delete_document_chunks(self, document_id: str, user_id: Optional[str] = None) -> None:
        effective_user = self._validate_user(user_id)
        if self.is_configured:
            url = f"{self._rest_url}/document_chunks?document_id=eq.{document_id}&user_id=eq.{effective_user}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.delete(url, headers=self._headers)
                return

        if self.settings.is_production and not self.is_configured:
            raise RuntimeError("Supabase credentials not configured in production")

        # Local fallback
        global _MEM_CHUNKS
        _MEM_CHUNKS = [c for c in _MEM_CHUNKS if not (c.get("document_id") == document_id and c.get("user_id") == effective_user)]

    async def match_document_chunks(
        self,
        query_embedding: List[float],
        match_count: int = 10,
        filter_user_id: Optional[str] = None,
        filter_document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Call Supabase pgvector RPC match_document_chunks."""
        if filter_document_ids is not None and len(filter_document_ids) == 0:
            return []

        if self.is_configured:
            url = f"{self._rest_url}/rpc/match_document_chunks"
            payload: Dict[str, Any] = {
                "query_embedding": query_embedding,
                "match_count": match_count,
                "filter_user_id": filter_user_id,
                "filter_document_ids": filter_document_ids if filter_document_ids else None,
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=self._headers, json=payload)
                if resp.status_code == 200:
                    hits = resp.json()
                    formatted = []
                    for h in hits:
                        meta = h.get("metadata") or {}
                        formatted.append({
                            "id": h.get("id"),
                            "chunk_id": h.get("id"),
                            "document_id": h.get("document_id"),
                            "score": float(h.get("similarity", 0.0)),
                            "text": h.get("content", ""),
                            "content": h.get("content", ""),
                            "page": meta.get("page", 1),
                            "source": meta.get("source", "Uploaded Document"),
                            "user_id": h.get("user_id"),
                        })
                    return formatted
                log.warning("supabase_match_chunks_failed", status=resp.status_code, body=resp.text[:200])

        # Local fallback cosine similarity search
        import numpy as np
        q_vec = np.array(query_embedding, dtype=np.float32)
        norm_q = np.linalg.norm(q_vec)
        if norm_q > 0:
            q_vec = q_vec / norm_q

        candidates = []
        for c in _MEM_CHUNKS:
            if filter_user_id and c.get("user_id") != filter_user_id:
                continue
            if filter_document_ids and c.get("document_id") not in filter_document_ids:
                continue
            c_vec = np.array(c.get("embedding", []), dtype=np.float32)
            norm_c = np.linalg.norm(c_vec)
            sim = float(np.dot(q_vec, c_vec / norm_c)) if norm_c > 0 else 0.0
            meta = c.get("metadata") or {}
            candidates.append({
                "id": c.get("id"),
                "chunk_id": c.get("id"),
                "document_id": c.get("document_id"),
                "score": sim,
                "text": c.get("content", ""),
                "content": c.get("content", ""),
                "page": meta.get("page", 1),
                "source": meta.get("source", "Uploaded Document"),
                "user_id": c.get("user_id"),
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:match_count]

    async def get_document_chunks(
        self,
        document_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        if document_ids is not None and len(document_ids) == 0:
            return []

        if self.is_configured:
            filter_query = f"limit={limit}&order=chunk_index.asc"
            if user_id:
                filter_query += f"&user_id=eq.{user_id}"
            if document_ids:
                filter_query += f"&document_id=in.({','.join(document_ids)})"
            url = f"{self._rest_url}/document_chunks?{filter_query}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._headers)
                if resp.status_code == 200:
                    rows = resp.json()
                    return [
                        {
                            "id": r["id"],
                            "chunk_id": r["id"],
                            "document_id": r["document_id"],
                            "score": 1.0,
                            "text": r["content"],
                            "page": (r.get("metadata") or {}).get("page", 1),
                            "source": (r.get("metadata") or {}).get("source", "Uploaded Document"),
                            "user_id": r.get("user_id"),
                        }
                        for r in rows
                    ]

        # Local fallback
        matched = []
        for c in _MEM_CHUNKS:
            if user_id and c.get("user_id") != user_id:
                continue
            if document_ids and c.get("document_id") not in document_ids:
                continue
            meta = c.get("metadata") or {}
            matched.append({
                "id": c["id"],
                "chunk_id": c["id"],
                "document_id": c["document_id"],
                "score": 1.0,
                "text": c["content"],
                "page": meta.get("page", 1),
                "source": meta.get("source", "Uploaded Document"),
                "user_id": c.get("user_id"),
            })
            if len(matched) >= limit:
                break
        return matched

    # =========================================================================
    # USER PROVIDER CREDENTIALS
    # =========================================================================

    async def create_provider_credential(
        self,
        cred_id: str,
        user_id: str,
        provider: str,
        label: str,
        model: str,
        encrypted_key: str,
        key_masked: str,
        is_active: bool = True,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        norm_provider = provider.strip().lower()

        if self.is_configured:
            # If activating, deactivate other core AI providers for this user
            if is_active and norm_provider not in ("jev", "tavily", "web_search"):
                deact_url = f"{self._rest_url}/user_provider_credentials?user_id=eq.{user_id}&provider=not.in.(jev,tavily,web_search)"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.patch(deact_url, headers=self._headers, json={"is_active": 0, "updated_at": now})

            record = {
                "id": cred_id,
                "user_id": user_id,
                "provider": norm_provider,
                "label": label or provider,
                "model": model,
                "encrypted_key": encrypted_key,
                "key_masked": key_masked,
                "status": "unchecked",
                "is_active": 1 if is_active else 0,
                "created_at": now,
                "updated_at": now,
            }
            url = f"{self._rest_url}/user_provider_credentials"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=self._headers, json=record)
                if resp.status_code in {200, 201}:
                    safe = dict(record)
                    del safe["encrypted_key"]
                    return safe

        # Local fallback
        if is_active and norm_provider not in ("jev", "tavily", "web_search"):
            for cred in _MEM_CREDENTIALS.values():
                if cred.get("user_id") == user_id and cred.get("provider") not in ("jev", "tavily", "web_search"):
                    cred["is_active"] = 0
        record = {
            "id": cred_id,
            "user_id": user_id,
            "provider": norm_provider,
            "label": label or provider,
            "model": model,
            "encrypted_key": encrypted_key,
            "key_masked": key_masked,
            "status": "unchecked",
            "is_active": 1 if is_active else 0,
            "created_at": now,
            "updated_at": now,
        }
        _MEM_CREDENTIALS[cred_id] = record
        safe = dict(record)
        del safe["encrypted_key"]
        return safe

    async def list_provider_credentials(self, user_id: str) -> List[Dict[str, Any]]:
        if self.is_configured:
            url = f"{self._rest_url}/user_provider_credentials?user_id=eq.{user_id}&order=is_active.desc,updated_at.desc"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._headers)
                if resp.status_code == 200:
                    rows = resp.json()
                    safe = []
                    for r in rows:
                        item = dict(r)
                        item.pop("encrypted_key", None)
                        item["is_active"] = bool(item.get("is_active"))
                        safe.append(item)
                    return safe

        # Local fallback
        creds = [c for c in _MEM_CREDENTIALS.values() if c.get("user_id") == user_id]
        creds.sort(key=lambda x: (x.get("is_active", 0), x.get("updated_at", "")), reverse=True)
        safe = []
        for c in creds:
            item = dict(c)
            item.pop("encrypted_key", None)
            item["is_active"] = bool(item.get("is_active"))
            safe.append(item)
        return safe

    async def get_provider_credential(self, cred_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if self.is_configured:
            filter_query = f"id=eq.{cred_id}"
            if user_id:
                filter_query += f"&user_id=eq.{user_id}"
            url = f"{self._rest_url}/user_provider_credentials?{filter_query}&select=*"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._headers)
                if resp.status_code == 200 and resp.json():
                    return resp.json()[0]
                return None

        # Local fallback
        cred = _MEM_CREDENTIALS.get(cred_id)
        if cred and (user_id is None or cred.get("user_id") == user_id):
            return dict(cred)
        return None

    async def get_active_provider_credential(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve active core provider for this user."""
        if self.is_configured:
            url = f"{self._rest_url}/user_provider_credentials?user_id=eq.{user_id}&is_active=eq.1&provider=not.in.(jev,tavily,web_search)&order=updated_at.desc&limit=1"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self._headers)
                if resp.status_code == 200 and resp.json():
                    return resp.json()[0]
                # Fallback to any core provider if none active
                f_url = f"{self._rest_url}/user_provider_credentials?user_id=eq.{user_id}&provider=not.in.(jev,tavily,web_search)&order=updated_at.desc&limit=1"
                f_resp = await client.get(f_url, headers=self._headers)
                if f_resp.status_code == 200 and f_resp.json():
                    return f_resp.json()[0]
                return None

        # Local fallback
        user_creds = [c for c in _MEM_CREDENTIALS.values() if c.get("user_id") == user_id and c.get("provider") not in ("jev", "tavily", "web_search")]
        active = [c for c in user_creds if c.get("is_active") == 1]
        if active:
            return dict(active[0])
        if user_creds:
            return dict(user_creds[0])
        return None

    async def set_active_provider_credential(self, cred_id: str, user_id: str) -> bool:
        cred = await self.get_provider_credential(cred_id, user_id=user_id)
        if not cred:
            return False
        now = datetime.now(timezone.utc).isoformat()
        norm_provider = cred.get("provider", "").lower()

        if self.is_configured:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if norm_provider not in ("jev", "tavily", "web_search"):
                    deact_url = f"{self._rest_url}/user_provider_credentials?user_id=eq.{user_id}&provider=not.in.(jev,tavily,web_search)"
                    await client.patch(deact_url, headers=self._headers, json={"is_active": 0, "updated_at": now})
                act_url = f"{self._rest_url}/user_provider_credentials?id=eq.{cred_id}&user_id=eq.{user_id}"
                resp = await client.patch(act_url, headers=self._headers, json={"is_active": 1, "updated_at": now})
                return resp.status_code in {200, 204}

        # Local fallback
        if norm_provider not in ("jev", "tavily", "web_search"):
            for c in _MEM_CREDENTIALS.values():
                if c.get("user_id") == user_id and c.get("provider") not in ("jev", "tavily", "web_search"):
                    c["is_active"] = 0
        if cred_id in _MEM_CREDENTIALS:
            _MEM_CREDENTIALS[cred_id]["is_active"] = 1
            _MEM_CREDENTIALS[cred_id]["updated_at"] = now
            return True
        return False

    async def update_provider_credential(self, cred_id: str, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cred = await self.get_provider_credential(cred_id, user_id=user_id)
        if not cred:
            return None
        now = datetime.now(timezone.utc).isoformat()
        payload = dict(updates)
        payload["updated_at"] = now

        if self.is_configured:
            url = f"{self._rest_url}/user_provider_credentials?id=eq.{cred_id}&user_id=eq.{user_id}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.patch(url, headers=self._headers, json=payload)
                if resp.status_code in {200, 204}:
                    updated = await self.get_provider_credential(cred_id, user_id=user_id)
                    if updated:
                        updated.pop("encrypted_key", None)
                    return updated
                return None

        # Local fallback
        if cred_id in _MEM_CREDENTIALS:
            _MEM_CREDENTIALS[cred_id].update(payload)
            res = dict(_MEM_CREDENTIALS[cred_id])
            res.pop("encrypted_key", None)
            return res
        return None

    async def delete_provider_credential(self, cred_id: str, user_id: str) -> bool:
        if self.is_configured:
            url = f"{self._rest_url}/user_provider_credentials?id=eq.{cred_id}&user_id=eq.{user_id}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(url, headers=self._headers)
                return resp.status_code in {200, 204}

        # Local fallback
        if cred_id in _MEM_CREDENTIALS and _MEM_CREDENTIALS[cred_id].get("user_id") == user_id:
            del _MEM_CREDENTIALS[cred_id]
            return True
        return False


_supabase_service: Optional[SupabaseService] = None


def get_supabase_service() -> SupabaseService:
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
    return _supabase_service
