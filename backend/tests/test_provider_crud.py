from starlette.testclient import TestClient
from main import app

client = TestClient(app)
BASE = "/api/providers"

def test_provider_crud_flow():
    # 1. Supported
    sup = client.get(f"{BASE}/supported").json()
    assert "providers" in sup
    assert any(p["id"] == "anthropic" for p in sup["providers"])

    # 2. Create
    res = client.post(BASE, json={
        "provider": "anthropic",
        "api_key": "sk-ant-api03-testkey-1234567890abcdef",
        "model": "claude-3-5-sonnet-latest",
        "label": "Work Anthropic"
    })
    assert res.status_code in (200, 201)
    created = res.json()
    assert created["key_masked"].startswith("sk-a") and created["key_masked"].endswith("cdef")
    assert "*" in created["key_masked"]
    assert "sk-ant-api03-testkey" not in str(created)

    # 3. List
    listed = client.get(BASE).json()
    assert len(listed["providers"]) >= 1

    # 4. Test connection endpoint (will return safe structured result)
    test_res = client.post(f"{BASE}/{created['id']}/test").json()
    assert "success" in test_res

    # 5. Delete
    del_res = client.delete(f"{BASE}/{created['id']}")
    assert del_res.status_code in (200, 204)
