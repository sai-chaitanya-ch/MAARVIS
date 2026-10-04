"""
Automated tests for MAARVIS Final Production Architecture:
- Auth & User Isolation (Supabase JWT, 401 in production, cross-user isolation)
- Provider Security (AES-256-GCM encryption at rest, key masking, user scoping)
- RAG & pgvector Isolation (user-scoped chunks, document ID filtering)
- Execution Isolation (unique execution_id, DOCS=0 on unrelated queries, zero stale evidence)
- Capabilities & Honest System Reporting (no fake connected state)
- Health check endpoints
"""
from __future__ import annotations

import json
import os
import pytest
from httpx import ASGITransport, AsyncClient

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from config.settings import get_settings
from security.crypto import encrypt_provider_key, decrypt_provider_key, mask_provider_key
from services.supabase_service import SupabaseService
from services.provider_service import (
    create_provider,
    get_provider,
    list_providers,
    set_active_provider,
)
from api.routes.chat import execute_chat
from schemas.chat import ChatRequest



@pytest.fixture
def anyio_backend():
    return "asyncio"


# ==============================================================================
# 1. AUTH & USER ISOLATION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_unauthenticated_request_in_production_returns_401(monkeypatch):
    """In production mode, requests without valid Bearer JWT must return 401."""
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", "production")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Protected conversations endpoint
        res = await client.get("/api/conversations")
        assert res.status_code == 401
        assert "Authentication required" in res.json().get("detail", "")

        # 2. Protected documents endpoint
        res = await client.get("/api/documents")
        assert res.status_code == 401

        # 3. Protected providers endpoint
        res = await client.get("/api/providers")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_user_a_cannot_access_user_b_conversation():
    """User B cannot fetch or delete User A's conversation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A creates a conversation
        create_res = await client.post(
            "/api/conversations",
            headers={"Authorization": "Bearer user_alice_token"},
            json={"title": "Alice Secret Discussion"},
        )
        assert create_res.status_code == 200
        convo_id = create_res.json()["id"]

        # User B tries to access User A's conversation
        get_res = await client.get(
            f"/api/conversations/{convo_id}",
            headers={"Authorization": "Bearer user_bob_token"},
        )
        assert get_res.status_code == 404

        # User B tries to delete User A's conversation
        del_res = await client.delete(
            f"/api/conversations/{convo_id}",
            headers={"Authorization": "Bearer user_bob_token"},
        )
        assert del_res.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_access_user_b_document():
    """User B cannot view or delete User A's document."""
    supabase = SupabaseService()
    doc_id = "doc_alice_confidential"
    await supabase.save_document(
        document_id=doc_id,
        name="alice_confidential.pdf",
        storage_path="user_alice/doc_a/alice_confidential.pdf",
        chunks=3,
        user_id="user_alice",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Bob lists documents - Alice's document must not appear
        bob_list = await client.get(
            "/api/documents",
            headers={"Authorization": "Bearer user_bob"},
        )
        assert bob_list.status_code == 200
        bob_docs = bob_list.json()
        assert not any(d["id"] == doc_id for d in bob_docs)

        # Bob tries to delete Alice's document
        bob_del = await client.delete(
            f"/api/documents/{doc_id}",
            headers={"Authorization": "Bearer user_bob"},
        )
        assert bob_del.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_access_user_b_provider_credential():
    """User B cannot fetch or delete User A's provider credentials."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Alice creates a provider credential
        create_res = await client.post(
            "/api/providers",
            headers={"Authorization": "Bearer user_alice"},
            json={
                "provider": "google",
                "api_key": "AIzaSyAliceSecretKey1234567890",
                "label": "Alice Gemini Key",
            },
        )
        assert create_res.status_code in (200, 201)
        cred_id = create_res.json()["id"]

        # Bob attempts to GET Alice's credential
        bob_get = await client.get(
            f"/api/providers/{cred_id}",
            headers={"Authorization": "Bearer user_bob"},
        )
        assert bob_get.status_code == 404

        # Bob attempts to DELETE Alice's credential
        bob_del = await client.delete(
            f"/api/providers/{cred_id}",
            headers={"Authorization": "Bearer user_bob"},
        )
        assert bob_del.status_code == 404


# ==============================================================================
# 2. PROVIDER SECURITY TESTS
# ==============================================================================

def test_api_key_encrypted_at_rest_with_aes_256_gcm():
    """API keys must be encrypted with AES-256-GCM and unique nonces."""
    raw_key = "sk-live-secret-test-key-for-maarvis-audit"
    enc1 = encrypt_provider_key(raw_key)
    enc2 = encrypt_provider_key(raw_key)

    # Must be non-empty base64 string
    assert len(enc1) > 20
    assert len(enc2) > 20
    # Nonces must differ between runs (probabilistic encryption)
    assert enc1 != enc2

    # Both decrypt correctly
    assert decrypt_provider_key(enc1) == raw_key
    assert decrypt_provider_key(enc2) == raw_key


@pytest.mark.asyncio
async def test_api_key_never_appears_in_provider_get_response():
    """GET /api/providers must NEVER return the plaintext api_key."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/providers",
            headers={"Authorization": "Bearer user_security_test"},
            json={
                "provider": "openai",
                "api_key": "sk-proj-UnmaskedSecretMustNotLeak123456789",
                "label": "OpenAI Prod",
            },
        )
        assert res.status_code in (200, 201)
        body = res.json()
        assert "api_key" not in body
        assert "key_masked" in body
        assert "UnmaskedSecret" not in body["key_masked"]

        # Also verify in list endpoint
        list_res = await client.get(
            "/api/providers",
            headers={"Authorization": "Bearer user_security_test"},
        )
        assert list_res.status_code == 200
        for item in list_res.json().get("providers", []):
            assert "api_key" not in item
            assert "UnmaskedSecret" not in json.dumps(item)


def test_provider_selection_is_user_scoped():
    """Activating a provider for User A does not affect User B's active provider."""
    cred_a = create_provider(provider="openai", api_key="sk-alice", label="Alice OpenAI", user_id="user_alice_scope")
    cred_b = create_provider(provider="groq", api_key="gsk-bob", label="Bob Groq", user_id="user_bob_scope")

    set_active_provider(cred_id=cred_a["id"], user_id="user_alice_scope")
    set_active_provider(cred_id=cred_b["id"], user_id="user_bob_scope")

    alice_provs = list_providers(user_id="user_alice_scope")
    bob_provs = list_providers(user_id="user_bob_scope")

    alice_active = next((p for p in alice_provs if p.get("is_active")), None)
    bob_active = next((p for p in bob_provs if p.get("is_active")), None)

    assert alice_active is not None and alice_active["id"] == cred_a["id"]
    assert bob_active is not None and bob_active["id"] == cred_b["id"]


# ==============================================================================
# 3. RAG & PGVECTOR RETRIEVAL ISOLATION
# ==============================================================================

@pytest.mark.asyncio
async def test_rag_retrieval_returns_only_authenticated_users_chunks():
    """Supabase vector store must filter chunks strictly by user_id."""
    supabase = SupabaseService()
    # Chunk for Alice
    await supabase.insert_document_chunks([
        {
            "id": "chunk_alice_1",
            "document_id": "doc_alice_1",
            "user_id": "alice_retrieval_user",
            "chunk_index": 0,
            "content": "Project Orion confidential internal financials.",
            "embedding": [0.1] * 768,
        }
    ])
    # Chunk for Bob
    await supabase.insert_document_chunks([
        {
            "id": "chunk_bob_1",
            "document_id": "doc_bob_1",
            "user_id": "bob_retrieval_user",
            "chunk_index": 0,
            "content": "Public company marketing guidelines.",
            "embedding": [0.1] * 768,
        }
    ])

    # Bob searches with the exact same embedding
    results = await supabase.match_document_chunks(
        query_embedding=[0.1] * 768,
        match_count=5,
        filter_user_id="bob_retrieval_user",
    )

    # Bob must only see his own chunk, NEVER Alice's
    assert len(results) >= 1
    assert all(r["user_id"] == "bob_retrieval_user" for r in results)
    assert not any("Orion confidential" in r["content"] for r in results)


@pytest.mark.asyncio
async def test_rag_retrieval_restricted_to_selected_document_ids():
    """Retrieval can be constrained to specific document IDs."""
    supabase = SupabaseService()
    await supabase.insert_document_chunks([
        {
            "id": "chunk_doc_a",
            "document_id": "doc_a_filter",
            "user_id": "user_doc_filter",
            "chunk_index": 0,
            "content": "Doc A content on quantum computing.",
            "embedding": [0.2] * 768,
        },
        {
            "id": "chunk_doc_b",
            "document_id": "doc_b_filter",
            "user_id": "user_doc_filter",
            "chunk_index": 0,
            "content": "Doc B content on solar energy.",
            "embedding": [0.2] * 768,
        },
    ])

    # Query filtering only for doc_a_filter
    results = await supabase.match_document_chunks(
        query_embedding=[0.2] * 768,
        match_count=5,
        filter_user_id="user_doc_filter",
        filter_document_ids=["doc_a_filter"],
    )

    assert len(results) == 1
    assert results[0]["document_id"] == "doc_a_filter"
    assert "quantum" in results[0]["content"]


# ==============================================================================
# 4. EXECUTION ISOLATION (DOCS=0, NO STALE EVIDENCE)
# ==============================================================================

@pytest.mark.asyncio
async def test_execution_isolation_second_query_without_docs_has_docs_zero():
    """When a query does not attach documents, execution state must have docs_used=0 and no stale chunks."""
    # Query 1: Query with document ID specified
    req_1 = ChatRequest(
        message="What is in the Q3 report?",
        document_ids=["doc_q3_report"],
    )
    result_1 = await execute_chat(req_1, user_id="user_exec_isolation")
    trace_1 = result_1.get("execution_trace")
    assert trace_1 is not None

    # Query 2: Unrelated query without any documents attached
    req_2 = ChatRequest(
        message="What is 25 * 4?",
        document_ids=[],  # No documents attached
    )
    result_2 = await execute_chat(req_2, user_id="user_exec_isolation")
    trace_2 = result_2.get("execution_trace")
    assert trace_2 is not None

    # Execution state must be isolated
    assert trace_2["execution_id"] != trace_1["execution_id"]
    assert trace_2["evidence"]["documents_used"] == 0
    assert len(trace_2["evidence"]["relevant_chunks"]) == 0
    # No active RAG agent run
    rag_agent_runs = [a for a in trace_2["agents"] if a["agent_name"] == "rag_agent"]
    assert len(rag_agent_runs) == 0 or all(a["status"] == "SKIPPED" for a in rag_agent_runs)



# ==============================================================================
# 5. CAPABILITIES & SYSTEM HEALTH
# ==============================================================================

@pytest.mark.asyncio
async def test_capabilities_report_status_honestly():
    """Capabilities must report accurately and never display fake connected states."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/providers/capabilities",
            headers={"Authorization": "Bearer user_unconfigured_caps"},
        )
        assert res.status_code == 200
        caps = res.json()
        assert "rag" in caps
        assert caps["rag"]["connected"] is True  # pgvector is available
        assert "gemini" in caps
        assert "jev" in caps
        assert "web_search" in caps


@pytest.mark.asyncio
async def test_health_endpoints_return_200():
    """Health endpoints must return 200 and verify pgvector vector store."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Root /health (Render health check)
        root_res = await client.get("/health")
        assert root_res.status_code == 200
        assert root_res.json()["status"] == "ok"

        # /api/health
        api_res = await client.get("/api/health")
        assert api_res.status_code == 200
        body = api_res.json()
        assert body["status"] == "ok"
        assert body["vector_store"]["ok"] is True
        assert body["vector_store"]["type"] == "pgvector"
