import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
resp = client.post("/api/chat", json={"message": "What is 17 * 24 + 19?", "mode": "AUTO"})
res = resp.json()
print("Status:", resp.status_code)
print("Route:", json.dumps(res.get("routing"), indent=2))
print("Trace status:", res.get("execution_trace", {}).get("status"))
for a in res.get("execution_trace", {}).get("agents", []):
    if a["status"] == "COMPLETED":
        print(f"Agent: {a['agent_name']} | Status: {a['status']} | Latency: {a['latency_ms']}ms | Gateway: {a['gateway']}")
print("Claims:", json.dumps(res.get("execution_trace", {}).get("evidence", {}).get("claims"), indent=2))
print("Answer:", res.get("answer"))
