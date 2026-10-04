import fitz
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from main import app


def main():
    # 1. Generate real PDF
    pdf_path = Path("tests/sample_q3_report.pdf")
    doc = fitz.open()
    page = doc.new_page()
    text = """Acme Corp Q3 Financial Performance Report
Fiscal Year 2026

Executive Summary:
Acme Corp delivered exceptional third-quarter results. Revenue was $25.5B with 8.9% growth year-over-year.
The AI Infrastructure division generated $4.2B in cloud services revenue, up 34% compared to Q3 2025.
Operating margin expanded to 28.4% driven by efficiency gains across all business units.
"""
    page.insert_text((50, 72), text, fontsize=12)
    doc.save(str(pdf_path))
    doc.close()
    print("PDF created successfully at", pdf_path)

    # 2. Upload via TestClient
    client = TestClient(app)
    with open(pdf_path, "rb") as f:
        resp = client.post("/api/documents/upload", files={"file": ("sample_q3_report.pdf", f, "application/pdf")})

    print("Upload status:", resp.status_code)
    upload_data = resp.json()
    print("Upload response:", json.dumps(upload_data, indent=2))
    doc_id = upload_data.get("document_id")
    assert doc_id, "No document_id returned"

    # 3. Query chat with attachment in AUTO mode
    chat_resp = client.post("/api/chat", json={
        "message": "What was the revenue of Acme Corp in Q3 and how much did it grow?",
        "mode": "AUTO",
        "document_ids": [doc_id]
    })

    print("Chat status:", chat_resp.status_code)
    res = chat_resp.json()
    print("=== MARVIS ROUTING ===")
    print(json.dumps(res.get("routing"), indent=2))
    print("=== EXECUTION TRACE AGENTS ===")
    for a in res.get("execution_trace", {}).get("agents", []):
        print(f"Agent: {a['agent_name']} | Status: {a['status']} | Latency: {a['latency_ms']}ms | Gateway: {a['gateway']}")
    print("=== EVIDENCE CHUNKS RETRIEVED ===")
    for c in res.get("execution_trace", {}).get("evidence", {}).get("relevant_chunks", []):
        chunk_txt = c.get("text", "")[:80].replace("\n", " ")
        print(f"Chunk ID: {c.get('chunk_id')} | Similarity: {c.get('similarity')} | Text: {chunk_txt}...")
    print("=== CLAIMS EVALUATED ===")
    for cl in res.get("execution_trace", {}).get("evidence", {}).get("claims", []):
        print(f"Claim: {cl.get('text')} | Status: {cl.get('status')} | Confidence: {cl.get('confidence')}")
    print("=== SYNTHESIZED ANSWER ===")
    print(res.get("answer"))

    # Save full output for report
    with open("tests/rag_test_result.json", "w") as out:
        json.dump(res, out, indent=2)
    print("Saved full result to tests/rag_test_result.json")


if __name__ == "__main__":
    main()
