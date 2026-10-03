from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List

from qdrant_client.http.models import PointStruct

from rag.chunking import chunk_pages
from rag.embeddings import embed_texts
from rag.vector_store import get_vector_store
from tools.document_parser import parse_document
from tools.ocr import OCRUnavailable, ocr_image


async def ingest_file(
    path: str,
    filename: str,
    document_id: str | None = None,
    user_id: str = "default_user",
) -> Dict[str, Any]:
    document_id = document_id or uuid.uuid4().hex
    parsed = parse_document(path, filename=filename)
    pages = parsed["pages"]
    if parsed.get("needs_ocr"):
        for page in pages:
            image_path = page.get("image_path")
            if image_path and not (page.get("text") or "").strip():
                try:
                    page["text"] = ocr_image(image_path)
                    page["ocr_applied"] = True
                except OCRUnavailable:
                    if parsed["kind"] == "image":
                        raise
    chunks = chunk_pages(pages, document_id=document_id, source=filename)
    if not chunks:
        return {
            "document_id": document_id,
            "filename": filename,
            "pages": parsed.get("page_count", 0),
            "chunks": 0,
            "status": "empty",
        }
    vectors = await embed_texts([c["text"] for c in chunks])
    dim = len(vectors[0])
    points = []
    for chunk, vector in zip(chunks, vectors):
        chunk_payload = dict(chunk)
        chunk_payload["user_id"] = user_id
        points.append(
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, chunk["chunk_id"])),
                vector=vector,
                payload=chunk_payload,
            )
        )
    store = get_vector_store()
    store.upsert(points, dim=dim)
    return {
        "document_id": document_id,
        "filename": filename,
        "pages": parsed.get("page_count", 0),
        "chunks": len(chunks),
        "status": "indexed",
    }
