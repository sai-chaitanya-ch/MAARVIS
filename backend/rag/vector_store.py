from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchAny, MatchValue, PointStruct, VectorParams

from config.settings import get_settings


class VectorStoreError(Exception):
    pass


class QdrantStore:
    def __init__(self) -> None:
        settings = get_settings()
        kwargs: Dict[str, Any] = {"url": settings.qdrant_url, "timeout": 0.5, "check_compatibility": False}
        if settings.qdrant_api_key:
            kwargs["api_key"] = settings.qdrant_api_key
        self.is_embedded = False
        try:
            client = QdrantClient(**kwargs)
            client.get_collections()
            self.client = client
        except Exception:
            # Fallback to local on-disk embedded Qdrant storage or in-memory
            backend_dir = Path(__file__).resolve().parent.parent
            local_path = backend_dir / "data" / "qdrant_storage"
            local_path.mkdir(parents=True, exist_ok=True)
            try:
                self.client = QdrantClient(path=local_path.as_posix())
            except Exception:
                self.client = QdrantClient(":memory:")
            self.is_embedded = True

        self.collection = settings.qdrant_collection
        self._ensured = False

    def ping(self) -> bool:
        try:
            self.client.get_collections()
            return True
        except Exception as exc:
            raise VectorStoreError(f"Qdrant is unavailable: {exc}") from exc

    def ensure_collection(self, dim: int) -> None:
        if self._ensured:
            return
        try:
            existing = {c.name for c in self.client.get_collections().collections}
            if self.collection not in existing:
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
                )
            self._ensured = True
        except Exception as exc:
            raise VectorStoreError(f"Qdrant collection setup failed: {exc}") from exc

    def upsert(self, points: List[PointStruct], dim: int) -> None:
        self.ensure_collection(dim)
        try:
            self.client.upsert(collection_name=self.collection, points=points)
        except Exception as exc:
            raise VectorStoreError(f"Qdrant upsert failed: {exc}") from exc

    def search(
        self,
        vector: List[float],
        limit: int = 12,
        document_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if document_ids is not None and len(document_ids) == 0:
            return []
        self.ensure_collection(len(vector))
        conditions = []
        if document_ids:
            conditions.append(FieldCondition(key="document_id", match=MatchAny(any=document_ids)))
        if user_id and user_id != "default_user":
            conditions.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))
        query_filter = Filter(must=conditions) if conditions else None
        try:
            if hasattr(self.client, "search"):
                hits = self.client.search(
                    collection_name=self.collection,
                    query_vector=vector,
                    limit=limit,
                    query_filter=query_filter,
                    with_payload=True,
                )
            else:
                query_res = self.client.query_points(
                    collection_name=self.collection,
                    query=vector,
                    limit=limit,
                    query_filter=query_filter,
                    with_payload=True,
                )
                hits = query_res.points
        except UnexpectedResponse as exc:
            raise VectorStoreError(f"Qdrant search failed: {exc}") from exc
        except Exception as exc:
            raise VectorStoreError(f"Qdrant search failed: {exc}") from exc
        results = []
        for hit in hits:
            payload = hit.payload or {}
            results.append(
                {
                    "id": str(hit.id),
                    "score": float(hit.score or 0),
                    "text": payload.get("text", ""),
                    "document_id": payload.get("document_id"),
                    "page": payload.get("page"),
                    "chunk_id": payload.get("chunk_id"),
                    "source": payload.get("source"),
                }
            )
        return results

    def get_document_chunks(
        self,
        document_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        if document_ids is not None and len(document_ids) == 0:
            return []
        self.ensure_collection(768)
        conditions = []
        if document_ids:
            conditions.append(FieldCondition(key="document_id", match=MatchAny(any=document_ids)))
        if user_id and user_id != "default_user":
            conditions.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))
        query_filter = Filter(must=conditions) if conditions else None
        try:
            points, _ = self.client.scroll(
                collection_name=self.collection,
                scroll_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
            results = []
            for hit in points:
                payload = hit.payload or {}
                results.append(
                    {
                        "id": str(hit.id),
                        "score": 1.0,
                        "text": payload.get("text", ""),
                        "document_id": payload.get("document_id"),
                        "page": payload.get("page"),
                        "chunk_id": payload.get("chunk_id"),
                        "source": payload.get("source"),
                        "rerank_score": 1.0,
                    }
                )
            return results
        except Exception:
            return []

    def delete_document_vectors(self, document_id: str) -> None:
        try:
            filter_ = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
            self.client.delete(collection_name=self.collection, points_selector=filter_)
        except Exception:
            pass


_store: Optional[QdrantStore] = None


def get_vector_store() -> QdrantStore:
    global _store
    if _store is None:
        _store = QdrantStore()
    return _store
