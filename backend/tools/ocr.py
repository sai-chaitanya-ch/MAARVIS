from __future__ import annotations

from typing import Any, Dict, List


class OCRUnavailable(Exception):
    pass


def ocr_image(path: str) -> str:
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise OCRUnavailable(
            "PaddleOCR is not available. Install paddleocr to OCR images and scanned PDFs."
        ) from exc
    engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    result = engine.ocr(path, cls=True)
    lines: List[str] = []
    for page in result or []:
        for row in page or []:
            if row and len(row) >= 2 and row[1]:
                lines.append(str(row[1][0]))
    return "\n".join(lines)


def ocr_page_if_needed(page: Dict[str, Any]) -> Dict[str, Any]:
    text = (page.get("text") or "").strip()
    image_path = page.get("image_path")
    if text or not image_path:
        return page
    page["text"] = ocr_image(image_path)
    page["ocr_applied"] = True
    return page
