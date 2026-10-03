import requests

BASE = "http://127.0.0.1:8000/api/providers"

# 1. Supported
sup = requests.get(f"{BASE}/supported").json()
print("Supported providers:", [p["id"] for p in sup["providers"]])

# 2. Create
created = requests.post(BASE, json={
    "provider": "anthropic",
    "api_key": "sk-ant-api03-testkey-1234567890abcdef",
    "model": "claude-3-5-sonnet-latest",
    "label": "Work Anthropic"
}).json()
print("Created provider:", created["id"], created["provider"], created["key_masked"])
assert created["key_masked"].startswith("sk-a") and created["key_masked"].endswith("cdef")
assert "*" in created["key_masked"]
assert "sk-ant-api03-testkey" not in str(created)

# 3. List
listed = requests.get(BASE).json()
print("Configured count:", len(listed["providers"]))

# 4. Test connection endpoint (will return result safely)
test_res = requests.post(f"{BASE}/{created['id']}/test").json()
print("Test result:", test_res)

# 5. Delete
del_res = requests.delete(f"{BASE}/{created['id']}").json()
print("Delete result:", del_res)
print("ALL PROVIDER TESTS PASSED")
