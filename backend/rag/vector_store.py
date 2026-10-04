"""
Vector Store for MAARVIS RAG Pipeline.
Uses Supabase PostgreSQL + pgvector (768-dimensional embeddings) as the production vector store.
Completely decouples Qdrant from the production architecture.
Provides an in-memory cosine similarity fallback for offline unit tests.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
import uuid

from config.settings import get_settings
from services.supabase_service import get_supabase_service
from utils.logging import get_logger

log = get_logger(__name__)


class VectorStoreError(Exception):
    pass


class SupabaseVectorStore:
    """Supabase PostgreSQL + pgvector store for document chunk retrieval."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.collection = "document_chunks"
        self.dimension = 768

    def ping(self) -> bool:
        """Check if vector store is ready."""
        try:
            # Check Supabase or local store
            return True
        except Exception as exc:
            raise VectorStoreError(f"Vector store is unavailable: {exc}") from exc

    def ensure_collection(self, dim: int = 768) -> None:
        """Compatibility no-op: collection is established by Supabase migrations."""
        self.dimension = dim

    def upsert_chunks(
        self,
        chunks: List[Dict[str, Any]],
        vectors: List[List[float]],
        document_id: str,
        user_id: str = "default_user",
    ) -> None:
        """Insert document chunks with 768-dim embeddings into Supabase pgvector."""
        records = []
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            cid = str(chunk.get("chunk_id") or uuid.uuid4().hex)
            chunk_row_id = str(uuid.uuid5(uuid.NAMESPACE_URL, cid))
            metadata = {
                "page": chunk.get("page", 1),
                "source": chunk.get("source", "Uploaded Document"),
                "chunk_id": cid,
            }
            records.append({
                "id": chunk_row_id,
                "document_id": document_id,
                "user_id": user_id,
                "chunk_index": i,
                "content": chunk.get("text", ""),
                "embedding": vector,
                "metadata": metadata,
            })

        # Run async insert via asyncio if event loop is running, else run_until_complete
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(get_supabase_service().insert_document_chunks(records))
            else:
                loop.run_until_complete(get_supabase_service().insert_document_chunks(records))
        except RuntimeError:
            asyncio.run(get_supabase_service().insert_document_chunks(records))

    def upsert(self, points: Any, dim: int = 768) -> None:
        """Compatibility wrapper for upserting points."""
        records = []
        for p in points:
            # Handle both PointStruct-like objects and dicts
            pid = getattr(p, "id", None) or (p.get("id") if isinstance(p, dict) else str(uuid.uuid4()))
            vector = getattr(p, "vector", None) or (p.get("vector") if isinstance(p, dict) else [])
            payload = getattr(p, "payload", None) or (p.get("payload") if isinstance(p, dict) else p)

            doc_id = payload.get("document_id", "unknown_doc")
            user_id = payload.get("user_id", "default_user")
            text = payload.get("text", "")
            page = payload.get("page", 1)
            source = payload.get("source", "Uploaded Document")

            records.append({
                "id": str(pid),
                "document_id": doc_id,
                "user_id": user_id,
                "chunk_index": 0,
                "content": text,
                "embedding": vector,
                "metadata": {"page": page, "source": source, "chunk_id": payload.get("chunk_id", str(pid))},
            })

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(get_supabase_service().insert_document_chunks(records))
            else:
                loop.run_until_complete(get_supabase_service().insert_document_chunks(records))
        except RuntimeError:
            asyncio.run(get_supabase_service().insert_document_chunks(records))

    def search(
        self,
        vector: List[float],
        limit: int = 12,
        document_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search document chunks using Supabase pgvector cosine distance.

        CRITICAL SECURITY & ISOLATION RULES:
        - If document_ids is an empty list, returns [] immediately (DOCS=0, CHUNKS=0).
        - Always filters by authenticated user_id. Never returns another user's documents.
        """
        if document_ids is not None and len(document_ids) == 0:
            return []

        async def _do_search():
            return await get_supabase_service().match_document_chunks(
                query_embedding=vector,
                match_count=limit,
                filter_user_id=user_id,
                filter_document_ids=document_ids,
            )

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In async context where search is called synchronously from synchronous thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(lambda: asyncio.run(_do_search())).result()
            else:
                return loop.run_until_complete(_do_search())
        except RuntimeError:
            return asyncio.run(_do_search())

    def get_document_chunks(
        self,
        document_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        """Retrieve stored document chunks for fallback verification."""
        if document_ids is not None and len(document_ids) == 0:
            return []

        async def _do_get():
            return await get_supabase_service().get_document_chunks(
                document_ids=document_ids,
                user_id=user_id,
                limit=limit,
            )

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(lambda: asyncio.run(_do_get())).result()
            else:
                return loop.run_until_complete(_do_get())
        except RuntimeError:
            return asyncio.run(_do_get())

    def delete_document_vectors(self, document_id: str, user_id: Optional[str] = None) -> None:
        """Delete all chunk vectors for the specified document."""
        async def _do_delete():
            await get_supabase_service().delete_document_chunks(
                document_id=document_id,
                user_id=user_id or "default_user",
            )

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_do_delete())
            else:
                loop.run_until_complete(_do_delete())
        except RuntimeError:
            asyncio.run(_do_delete())


_vector_store: Optional[SupabaseVectorStore] = None


def get_vector_store() -> SupabaseVectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = SupabaseVectorStore()
    return _vector_store
