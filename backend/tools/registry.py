from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Optional

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    name: str
    description: str
    permissions: str = "restricted"
    timeout: int = 30


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, spec: ToolSpec, fn: Callable[..., Awaitable[Any]]) -> None:
        self._tools[spec.name] = {"spec": spec, "fn": fn}

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)

    def list(self) -> list[ToolSpec]:
        return [item["spec"] for item in self._tools.values()]


registry = ToolRegistry()


def register_default_tools() -> None:
    from tools.calculator import parse_math_query
    from tools.code_executor import code_execute
    from tools.document_parser import parse_document
    from tools.ocr import ocr_image
    from tools.web_search import web_extract, web_search

    async def _calc(expression: str):
        return parse_math_query(expression)

    async def _parse(path: str, filename: str):
        return parse_document(path, filename=filename)

    async def _ocr(path: str):
        return ocr_image(path)

    registry.register(ToolSpec(name="web_search", description="Search the public web", timeout=30), web_search)
    registry.register(ToolSpec(name="web_extract", description="Extract a web page", timeout=45), web_extract)
    registry.register(ToolSpec(name="calculator", description="Deterministic calculator", timeout=5), _calc)
    registry.register(ToolSpec(name="code_execute", description="Execute code in a Docker sandbox", timeout=20), code_execute)
    registry.register(ToolSpec(name="document_parse", description="Parse uploaded documents", timeout=30), _parse)
    registry.register(ToolSpec(name="ocr", description="OCR images and scanned pages", timeout=60), _ocr)
