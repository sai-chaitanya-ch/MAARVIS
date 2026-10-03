from __future__ import annotations

from typing import Any, Dict, List, Optional

import asyncio

from rag.embeddings import embed_texts
from rag.reranker import rerank
from rag.vector_store import VectorStoreError, get_vector_store
from models.reranker import RerankerError


async def retrieve(
    query: str,
    *,
    document_ids: Optional[List[str]] = None,
    user_id: Optional[str] = None,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    store = get_vector_store()
    vectors = await embed_texts([query])
    hits = store.search(vectors[0], limit=limit, document_ids=document_ids, user_id=user_id)
    if not hits:
        return []
    # If 3 or fewer hits exist, vector store cosine similarity is already optimal.
    # Avoiding remote reranker saves ~5 seconds of network round-trips.
    if len(hits) <= 3:
        return [{**h, "rerank_score": float(h.get("score") or 1.0)} for h in hits]
    try:
        ranking = await asyncio.wait_for(
            rerank(query, [h["text"] for h in hits], top_k=min(6, len(hits))),
            timeout=2.0,
        )
        return [{**hits[idx], "rerank_score": score} for idx, score in ranking]
    except Exception:
        return [{**h, "rerank_score": float(h.get("score") or 1.0)} for h in hits[:6]]
