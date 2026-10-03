from __future__ import annotations

import re
from typing import Any, Dict, List
from config.settings import get_settings


def chunk_pages(
    pages: List[Dict[str, Any]],
    *,
    document_id: str,
    source: str,
    size: int | None = None,
    overlap: int | None = None,
) -> List[Dict[str, Any]]:
    settings = get_settings()
    chunk_size = size or settings.rag_chunk_size or 1000
    chunk_overlap = overlap if overlap is not None else (settings.rag_chunk_overlap or 150)

    chunks: List[Dict[str, Any]] = []
    index = 0
    for page in pages:
        text = _clean((page.get("text") or ""))
        if not text:
            continue
        page_no = int(page.get("page") or 1)
        start = 0
        while start < len(text):
            piece = text[start : start + chunk_size]
            index += 1
            chunks.append(
                {
                    "chunk_id": f"{document_id}:{index}",
                    "document_id": document_id,
                    "page": page_no,
                    "section": page.get("section"),
                    "source": source,
                    "text": piece,
                }
            )
            if start + chunk_size >= len(text):
                break
            start += chunk_size - chunk_overlap
    return chunks


def _clean(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
