import asyncio
import base64
import json
import subprocess
import time
import urllib.request
import websockets
from pathlib import Path

ARTIFACTS_DIR = Path(r"C:\Users\chsai_020\.gemini\antigravity\brain\4fb72ce2-80cd-4037-860a-0046d367a894")
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9222

_req_id = 0

async def cdp_call(ws, method, params=None):
    global _req_id
    _req_id += 1
    my_id = _req_id
    req = {"id": my_id, "method": method, "params": params or {}}
    await ws.send(json.dumps(req))
    while True:
        msg = await ws.recv()
        resp = json.loads(msg)
        if resp.get("id") == my_id:
            return resp.get("result", {})

async def capture_screen(ws, out_path: Path):
    res = await cdp_call(ws, "Page.captureScreenshot", {"format": "png"})
    data = base64.b64decode(res["data"])
    out_path.write_bytes(data)
    print(f"Captured: {out_path.name} ({len(data)} bytes)", flush=True)

async def evaluate(ws, expr):
    res = await cdp_call(ws, "Runtime.evaluate", {"expression": expr, "awaitPromise": True, "returnByValue": True})
    return res.get("result", {}).get("value")

async def main():
    edge_proc = subprocess.Popen([
        EDGE_PATH,
        f"--remote-debugging-port={PORT}",
        "--headless=new",
        "--disable-gpu",
        "--window-size=1280,820",
        "http://localhost:5173/"
    ])
    print("Started Edge on port", PORT, flush=True)
    time.sleep(2.5)

    try:
        tabs = json.loads(urllib.request.urlopen(f"http://localhost:{PORT}/json").read())
        ws_url = tabs[0]["webSocketDebuggerUrl"]
        print("Connecting to CDP:", ws_url, flush=True)

        async with websockets.connect(ws_url, max_size=20_000_000) as ws:
            await asyncio.sleep(2.0)

            # Screenshot 1: Assistant Home
            await capture_screen(ws, ARTIFACTS_DIR / "1_assistant_home.png")

            # Click Settings button (title="Settings")
            await evaluate(ws, """
                const btn = document.querySelector('button[title="Settings"]');
                if (btn) btn.click();
            """)
            await asyncio.sleep(0.8)
            # Screenshot 2: Settings General
            await capture_screen(ws, ARTIFACTS_DIR / "2_settings_general.png")

            # Click API & Providers tab
            await evaluate(ws, """
                const btns = Array.from(document.querySelectorAll('button'));
                const pTab = btns.find(b => b.textContent && b.textContent.includes('API & Providers'));
                if (pTab) pTab.click();
            """)
            await asyncio.sleep(0.8)
            # Screenshot 3: Settings API & Providers
            await capture_screen(ws, ARTIFACTS_DIR / "3_settings_providers.png")

            # Click Add Provider button
            await evaluate(ws, """
                const btns = Array.from(document.querySelectorAll('button'));
                const addBtn = btns.find(b => b.textContent && (b.textContent.includes('Add Provider') || b.textContent.includes('Add Custom Provider')));
                if (addBtn) addBtn.click();
            """)
            await asyncio.sleep(0.8)
            # Screenshot 4: Add Provider Form
            await capture_screen(ws, ARTIFACTS_DIR / "4_add_provider_form.png")

            # Close Settings Modal
            await evaluate(ws, """
                const closeBtn = document.querySelector('button:has(svg.lucide-x)');
                if (closeBtn) closeBtn.click();
            """)
            await asyncio.sleep(0.5)

            # Open Verification Analysis by injecting a verified chat state directly into UI
            print("Populating real verified message trace into UI...", flush=True)
            await evaluate(ws, """
                // Read from window / storage or trigger verification analysis display
                const chatRes = fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: 'Hello', mode: 'AUTO'})
                }).then(r => r.json()).then(data => {
                    window.__last_chat_data = data;
                });
            """)
            await asyncio.sleep(5.0)

            # Type and submit query to see assistant response
            await evaluate(ws, """
                const textarea = document.querySelector('textarea');
                if (textarea) {
                    textarea.value = 'Hello';
                    textarea.dispatchEvent(new Event('input', { bubbles: true }));
                }
                const btn = document.querySelector('button:has(svg.lucide-arrow-up)');
                if (btn) btn.click();
            """)

            # Wait for response
            print("Waiting for chat completion...", flush=True)
            for _ in range(20):
                await asyncio.sleep(1.0)
                has_badge = await evaluate(ws, """
                    Array.from(document.querySelectorAll('button')).some(b => 
                        b.textContent.includes('Verification Analysis') || 
                        b.textContent.includes('Direct Answer') || 
                        b.textContent.includes('Verified') ||
                        b.textContent.includes('Not Verified')
                    )
                """)
                if has_badge:
                    print("Found verification badge in DOM!", flush=True)
                    break

            await asyncio.sleep(1.0)
            await capture_screen(ws, ARTIFACTS_DIR / "5_assistant_message.png")

            # Click Verification Analysis badge
            await evaluate(ws, """
                const btns = Array.from(document.querySelectorAll('button'));
                const badge = btns.find(b => 
                    b.textContent.includes('Verification Analysis') || 
                    b.textContent.includes('Direct Answer') || 
                    b.textContent.includes('Verified') ||
                    b.textContent.includes('Not Verified')
                );
                if (badge) badge.click();
            """)
            await asyncio.sleep(1.0)
            # Screenshot 6: Overview Tab
            await capture_screen(ws, ARTIFACTS_DIR / "6_verification_overview.png")

            # Click Evidence Tab
            await evaluate(ws, """
                const btns = Array.from(document.querySelectorAll('button'));
                const evTab = btns.find(b => b.textContent && b.textContent.includes('Evidence'));
                if (evTab) evTab.click();
            """)
            await asyncio.sleep(0.8)
            # Screenshot 7: Evidence Tab
            await capture_screen(ws, ARTIFACTS_DIR / "7_verification_evidence.png")

            # Click Agents Tab
            await evaluate(ws, """
                const btns = Array.from(document.querySelectorAll('button'));
                const agTab = btns.find(b => b.textContent && b.textContent.includes('Agents'));
                if (agTab) agTab.click();
            """)
            await asyncio.sleep(1.0)
            # Screenshot 8: Agents Tab - Workflow Graph
            await capture_screen(ws, ARTIFACTS_DIR / "8_agents_workflow_graph.png")

            # Click on MARVIS Router node in the graph
            await evaluate(ws, """
                const btns = Array.from(document.querySelectorAll('button'));
                const routerNode = btns.find(b => b.textContent && b.textContent.includes('MARVIS Router'));
                if (routerNode) routerNode.click();
            """)
            await asyncio.sleep(0.8)
            # Screenshot 9: Expanded Agent Details Inspector
            await capture_screen(ws, ARTIFACTS_DIR / "9_agent_details_inspector.png")

            print("SUCCESS: All screenshots captured and saved to brain directory!", flush=True)
    finally:
        edge_proc.terminate()

if __name__ == "__main__":
    asyncio.run(main())
