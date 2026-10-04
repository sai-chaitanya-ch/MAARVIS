"""
Document Ingestion Pipeline for MAARVIS.
Parses documents, generates chunks and 768-dim embeddings,
and indexes into Supabase pgvector scoped to user_id.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List

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
    store = get_vector_store()
    store.upsert_chunks(chunks, vectors, document_id=document_id, user_id=user_id)
    return {
        "document_id": document_id,
        "filename": filename,
        "pages": parsed.get("page_count", 0),
        "chunks": len(chunks),
        "status": "indexed",
    }
