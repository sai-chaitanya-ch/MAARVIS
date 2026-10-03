"""
Test suite for Phase 3 (History, RAG Isolation, Execution Scoping, Evidence)
and Phase 4 (Production Health, Configuration, and Security).
"""
from __future__ import annotations

import os
import sys
import uuid
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from memory.conversation import (
    create_conversation,
    list_conversations,
    get_conversation,
    delete_conversation,
    add_message,
    generate_conversation_title,
    get_db,
)
from rag.vector_store import get_vector_store
from agents.rag_agent import run_rag
from schemas.chat import ChatRequest
from api.routes.chat import execute_chat
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Isolate SQLite database to a temporary location for test suite."""
    test_db = backend_dir / "data" / "test_phase3_phase4.sqlite"
    test_db.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SQLITE_PATH", str(test_db))
    monkeypatch.setenv("ENVIRONMENT", "test")
    yield
    # Cleanup test db
    if test_db.exists():
        try:
            os.remove(test_db)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 1. AUTO TITLE GENERATION TESTS
# ---------------------------------------------------------------------------
class TestAutoTitleGeneration:
    def test_google_founder_title(self):
        title = generate_conversation_title("Who founded Google?")
        assert "Google" in title
        assert "Founder" in title

    def test_java_array_debugging_title(self):
        title = generate_conversation_title("Can you help me debug a java array out of bounds error?")
        assert "Java Array Debugging" == title

    def test_research_paper_title(self):
        title = generate_conversation_title("Please do a detailed research paper analysis on attention mechanisms")
        assert "Research Paper Analysis" == title

    def test_generic_filler_stripped(self):
        title = generate_conversation_title("Can you tell me what is quantum computing?")
        assert "Quantum Computing" in title
        assert "Can You Tell Me" not in title

    def test_never_empty_or_new_chat(self):
        title = generate_conversation_title("???")
        assert len(title) > 0
        assert title != "New Chat"


# ---------------------------------------------------------------------------
# 2. USER HISTORY ISOLATION TESTS
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestHistoryIsolation:
    async def test_user_history_isolation(self):
        user_a = f"user_a_{uuid.uuid4().hex[:8]}"
        user_b = f"user_b_{uuid.uuid4().hex[:8]}"

        # User A creates a conversation
        c_a = await create_conversation("User A Private Chat", user_id=user_a)
        await add_message(c_a, "user", "Secret info from User A", user_id=user_a)

        # User B creates a conversation
        c_b = await create_conversation("User B Chat", user_id=user_b)
        await add_message(c_b, "user", "Hello from User B", user_id=user_b)

        # User A listing only sees User A's conversations
        convs_a = await list_conversations(user_id=user_a)
        conv_ids_a = [c["id"] for c in convs_a]
        assert c_a in conv_ids_a
        assert c_b not in conv_ids_a

        # User B listing only sees User B's conversations
        convs_b = await list_conversations(user_id=user_b)
        conv_ids_b = [c["id"] for c in convs_b]
        assert c_b in conv_ids_b
        assert c_a not in conv_ids_b

    async def test_get_conversation_loads_messages_and_trace(self):
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        cid = await create_conversation("Trace Verification Chat", user_id=user_id)
        exec_id = f"exec_{uuid.uuid4().hex[:8]}"

        routing_data = {"route": "MULTI_AGENT", "mode": "AUTO"}
        verification_data = {"status": "verified", "score": 1.0}
        trace_data = {"execution_id": exec_id, "status": "VERIFIED", "agents": []}

        mid = await add_message(
            cid,
            "assistant",
            "Verified answer content",
            user_id=user_id,
            execution_id=exec_id,
            routing=routing_data,
            verification=verification_data,
            execution_trace=trace_data,
        )

        loaded = await get_conversation(cid, user_id=user_id)
        assert loaded is not None
        assert loaded["id"] == cid
        assert len(loaded["messages"]) == 1
        msg = loaded["messages"][0]
        assert msg["id"] == mid
        assert msg["execution_id"] == exec_id
        assert msg["routing"]["route"] == "MULTI_AGENT"
        assert msg["verification"]["status"] == "verified"
        assert msg["execution_trace"]["execution_id"] == exec_id

    async def test_delete_conversation(self):
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        cid = await create_conversation("To be deleted", user_id=user_id)
        await add_message(cid, "user", "Message to delete", user_id=user_id)

        ok = await delete_conversation(cid, user_id=user_id)
        assert ok is True

        loaded = await get_conversation(cid, user_id=user_id)
        assert loaded is None


# ---------------------------------------------------------------------------
# 3. ZERO-CLAIM RULE & EXECUTION ISOLATION IN CHAT
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestExecutionIsolationAndZeroClaims:
    async def test_direct_fast_gives_not_evaluated(self):
        """DIRECT_FAST route with 0 claims must return NOT EVALUATED status."""
        req = ChatRequest(
            message="Hello, good morning!",
            mode="DIRECT",
        )
        res = await execute_chat(req, user_id="test_user")
        assert res["verification"]["status"] == "not_evaluated"
        assert res["verification"]["decision"] == "NOT EVALUATED"
        assert res["verification"]["decision_reason"] == "No verification was required for this response."
        assert res["verification"]["total_claims"] == 0
        assert res["execution_id"] is not None
        assert res["execution_id"].startswith("exec_")

    async def test_zero_claim_factual_gives_not_evaluated(self):
        """When 0 claims are extracted (and not math), status is NOT EVALUATED."""
        req = ChatRequest(
            message="General conversational statement without verifiable facts",
            mode="AUTO",
        )
        # Mock dispatcher returning 0 claims and no sources
        mock_result = {
            "final_answer": "This is a general response.",
            "verification": {"performed": True},
            "sources": [],
            "claim_results": [],
            "task_type": "general",
        }
        with patch("api.routes.chat.dispatch", new_callable=AsyncMock, return_value=mock_result):
            res = await execute_chat(req, user_id="test_user")

        assert res["verification"]["status"] == "not_evaluated"
        assert res["verification"]["decision"] == "NOT EVALUATED"
        assert res["verification"]["decision_reason"] == "No verification was required for this response."


# ---------------------------------------------------------------------------
# 4. RAG ISOLATION & NO STALE RAG ATTACHMENTS
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestRagIsolation:
    async def test_run_rag_without_document_ids_returns_no_passages(self):
        """Request without document_ids must immediately return 0 passages and rag_failed=True."""
        res = await run_rag("What was the revenue?", document_ids=[])
        assert res["rag_failed"] is True
        assert len(res["document_context"]) == 0
        assert len(res["sources"]) == 0

    async def test_vector_store_empty_document_ids_returns_empty(self):
        """vector_store.search with document_ids=[] returns empty list without searching other docs."""
        store = get_vector_store()
        results = store.search([0.1] * 768, document_ids=[], limit=5)
        assert results == []

        chunks = store.get_document_chunks(document_ids=[], limit=5)
        assert chunks == []


# ---------------------------------------------------------------------------
# 5. PRODUCTION HEALTH CHECK
# ---------------------------------------------------------------------------
class TestProductionHealthEndpoint:
    def test_root_health_endpoint(self):
        """GET /health must return status ok and service maarvis-api for Render."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "maarvis-api"

    def test_root_landing(self):
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["name"] == "MAARVIS"
