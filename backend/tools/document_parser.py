from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz

from security.validation import DocumentRejected


SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".docx", ".png", ".jpg", ".jpeg", ".webp"}


def parse_document(path: str, *, filename: str) -> Dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise DocumentRejected(f"Unsupported file type: {suffix}")
    if suffix == ".pdf":
        return _parse_pdf(path, filename)
    if suffix in {".txt", ".md"}:
        return _parse_text(path, filename)
    if suffix == ".docx":
        return _parse_docx(path, filename)
    return _parse_image(path, filename)


def _parse_pdf(path: str, filename: str) -> Dict[str, Any]:
    pages: List[Dict[str, Any]] = []
    needs_ocr = False
    with fitz.open(path) as doc:
        if doc.page_count > 200:
            raise DocumentRejected("PDF exceeds the 200-page limit")
        for index, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            if len(text.strip()) < 20:
                needs_ocr = True
            pages.append({"page": index, "text": text, "section": None})
    return {
        "filename": filename,
        "kind": "pdf",
        "pages": pages,
        "needs_ocr": needs_ocr,
        "page_count": len(pages),
    }


def _parse_text(path: str, filename: str) -> Dict[str, Any]:
    content = Path(path).read_text(encoding="utf-8", errors="replace")
    return {
        "filename": filename,
        "kind": "text",
        "pages": [{"page": 1, "text": content, "section": None}],
        "needs_ocr": False,
        "page_count": 1,
    }


def _parse_docx(path: str, filename: str) -> Dict[str, Any]:
    from docx import Document

    document = Document(path)
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)
    return {
        "filename": filename,
        "kind": "docx",
        "pages": [{"page": 1, "text": text, "section": None}],
        "needs_ocr": False,
        "page_count": 1,
    }


def _parse_image(path: str, filename: str) -> Dict[str, Any]:
    return {
        "filename": filename,
        "kind": "image",
        "pages": [{"page": 1, "text": "", "image_path": path, "section": None}],
        "needs_ocr": True,
        "page_count": 1,
    }


def parse_bytes(data: bytes, filename: str) -> Dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        pages = []
        needs_ocr = False
        with fitz.open(stream=io.BytesIO(data), filetype="pdf") as doc:
            for index, page in enumerate(doc, start=1):
                text = page.get_text("text") or ""
                if len(text.strip()) < 20:
                    needs_ocr = True
                pages.append({"page": index, "text": text})
        return {"filename": filename, "kind": "pdf", "pages": pages, "needs_ocr": needs_ocr, "page_count": len(pages)}
    raise DocumentRejected("In-memory parse only supports PDF")
