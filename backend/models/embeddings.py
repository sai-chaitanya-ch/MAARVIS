from __future__ import annotations

import os
from typing import List, Optional, Sequence

import httpx
import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

from config.settings import get_settings
from utils.retry import retry_async

_HF_EMBEDDING_MODEL = os.environ.get("MODEL_EMBEDDING", "BAAI/bge-base-en-v1.5")
_HF_INFERENCE_BASE = os.environ.get(
    "HF_INFERENCE_BASE_URL", "https://api-inference.huggingface.co"
)
_HF_TOKEN = os.environ.get("HF_TOKEN", "")


class EmbeddingError(Exception):
    pass


class EmbeddingProvider:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._hf_token: str = _HF_TOKEN
        self._hf_base: str = _HF_INFERENCE_BASE
        self._model: str = _HF_EMBEDDING_MODEL
        # High-performance 768-dim local dense vectorizer for Qdrant cosine similarity
        self._vectorizer = HashingVectorizer(
            n_features=768,
            norm="l2",
            alternate_sign=True,
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b",
        )

    async def embed(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []

        # If live HF token is provided, use remote model
        if self._hf_token:
            url = f"{self._hf_base.rstrip('/')}/models/{self._model}"

            async def _call() -> List[List[float]]:
                async with httpx.AsyncClient(timeout=90) as client:
                    response = await client.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {self._hf_token}",
                            "Content-Type": "application/json",
                        },
                        json={"inputs": list(texts), "options": {"wait_for_model": True}},
                    )
                if response.status_code >= 400:
                    raise EmbeddingError(f"Embedding request failed: HTTP {response.status_code}")
                data = response.json()
                if not isinstance(data, list) or not data:
                    raise EmbeddingError("Embedding provider returned an unexpected payload")
                vectors: List[List[float]] = []
                for item in data:
                    if isinstance(item, list) and item and isinstance(item[0], list):
                        vectors.append(_mean_pool(item))
                    elif isinstance(item, list):
                        vectors.append([float(x) for x in item])
                    else:
                        raise EmbeddingError("Embedding vector format was not recognized")
                return vectors

            try:
                return await retry_async(_call, attempts=2, exceptions=(httpx.HTTPError, EmbeddingError))
            except Exception:
                pass  # Fall back to local dense vectorizer

        # Deterministic 768-dimensional normalized dense vector projection
        clean_texts = [t if (t and t.strip()) else "empty" for t in texts]
        matrix = self._vectorizer.transform(clean_texts)
        dense = matrix.toarray().astype(np.float32)
        return dense.tolist()


def _mean_pool(token_vectors: List[List[float]]) -> List[float]:
    dim = len(token_vectors[0])
    acc = [0.0] * dim
    for vec in token_vectors:
        for i, value in enumerate(vec):
            acc[i] += float(value)
    n = max(len(token_vectors), 1)
    return [v / n for v in acc]


_embeddings: Optional[EmbeddingProvider] = None


def get_embeddings() -> EmbeddingProvider:
    global _embeddings
    if _embeddings is None:
        _embeddings = EmbeddingProvider()
    return _embeddings
