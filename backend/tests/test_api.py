from __future__ import annotations

from typing import Any, Dict, List

import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from tools.calculator import parse_math_query


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "qdrant" in body


@pytest.mark.asyncio
async def test_math_chat(monkeypatch):
    from api.routes import chat as chat_routes

    async def fake_workflow(payload, bus=None):
        from agents.math_agent import run_math

        result = run_math(payload["user_message"])
        return {
            "final_answer": result["draft_answer"],
            "verification": result.get("tool_verification") or {"performed": False},
            "sources": result.get("sources") or [],
            "agent_events": [{"event": "calculation", "status": "completed"}],
            "claim_results": result.get("claims") or [],
            "task_type": "math",
            "errors": [],
        }

    monkeypatch.setattr("marvis.dispatcher.run_workflow", fake_workflow)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chat", json={"message": "17 * 24"})
    assert response.status_code == 200
    body = response.json()
    assert "408" in body["answer"]
    assert body["verification"]["is_math"] is True


@pytest.mark.asyncio
async def test_tavily_failure_is_honest(monkeypatch):
    from tools.web_search import TavilyError
    from api.routes import research as research_routes

    async def boom(query):
        raise TavilyError("Tavily search failed: HTTP 401")

    monkeypatch.setattr(research_routes, "run_research", boom)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/research", json={"query": "latest python"})
    assert response.status_code == 503
    assert "Tavily" in response.json()["detail"]
