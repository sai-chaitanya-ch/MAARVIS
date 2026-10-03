from __future__ import annotations

import os
from typing import List, Optional, Sequence, Tuple

import httpx

from config.settings import get_settings

# Reranker via HF Inference API — optional, same as embeddings.
# Set HF_TOKEN (and optionally MODEL_RERANKER / HF_INFERENCE_BASE_URL) in .env
# to enable live reranking. Without a token the method returns a linear fallback
# score so retrieval still works.
_HF_RERANKER_MODEL = os.environ.get("MODEL_RERANKER", "BAAI/bge-reranker-v2-m3")
_HF_INFERENCE_BASE = os.environ.get(
    "HF_INFERENCE_BASE_URL", "https://api-inference.huggingface.co"
)
_HF_TOKEN = os.environ.get("HF_TOKEN", "")


class RerankerError(Exception):
    pass


class RerankerProvider:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._hf_token: str = _HF_TOKEN
        self._hf_base: str = _HF_INFERENCE_BASE
        self._model: str = _HF_RERANKER_MODEL

    async def rerank(self, query: str, documents: Sequence[str], top_k: int = 6) -> List[Tuple[int, float]]:
        if not documents:
            return []

        if not self._hf_token:
            # No reranker configured — return top-k by insertion order with
            # linear scores so the pipeline doesn't break.
            return [(i, 1.0 - (i * 0.05)) for i in range(min(top_k, len(documents)))]

        url = f"{self._hf_base.rstrip('/')}/models/{self._model}"
        pairs = [{"text": query, "text_pair": doc[:4000]} for doc in documents]
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self._hf_token}",
                        "Content-Type": "application/json",
                    },
                    json={"inputs": pairs, "options": {"wait_for_model": True}},
                )
            if response.status_code >= 400:
                raise RerankerError(f"Reranker request failed: HTTP {response.status_code}")
            data = response.json()
            scores: List[float] = []
            if isinstance(data, list):
                items = (
                    data[0]
                    if (len(data) == 1 and isinstance(data[0], list) and len(data[0]) == len(documents))
                    else data
                )
                for item in items:
                    if isinstance(item, dict) and "score" in item:
                        scores.append(float(item["score"]))
                    elif isinstance(item, (int, float)):
                        scores.append(float(item))
                    elif isinstance(item, list) and item:
                        scores.append(float(item[0].get("score", 0) if isinstance(item[0], dict) else item[0]))
            if len(scores) == len(documents):
                ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
                return ranked[:top_k]
        except Exception:
            pass

        return [(i, 1.0 - (i * 0.05)) for i in range(min(top_k, len(documents)))]


_reranker: Optional[RerankerProvider] = None


def get_reranker() -> RerankerProvider:
    global _reranker
    if _reranker is None:
        _reranker = RerankerProvider()
    return _reranker
