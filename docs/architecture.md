# Verify.ai — Architecture Documentation

Verify.ai is a multi-agent system designed to answer user queries with claim verification, citation tracking, and iterative self-correction.

---

## 1. System Overview

```
User Request
     │
     ▼
[Master Router] ──(Classifies intent: Conversation / Factual / Research / Math / Code / Document)
     │
     ├──► [General Agent]      (Conversational & general queries)
     ├──► [Research Agent]     (Multi-query web search & extraction via Tavily)
     ├──► [RAG Agent]          (Document parsing & Qdrant vector retrieval)
     ├──► [Math Agent]         (Deterministic arithmetic & symbolic checks)
     └──► [Code Agent]         (Code analysis & sandbox execution)
     │
     ▼
[Verification Gate] ──────────► (Checks if verification is necessary)
     │                                │ (If NO)
     │ (If YES)                       ▼
     ▼                           [Finalizer] ──► Final Response
[Verifier Agent]
  - Claim Extraction
  - Evidence Retrieval & Cross-referencing
  - Contradiction Detection & Scoring
     │
     ▼
[Critic Agent] ─── (Acceptable confidence?) ──┐
     │                                        │ (YES)
     ▼ (NO & attempts < MAX_ITERATIONS)       ▼
[Correction Agent] ──► [Verifier Loop]   [Finalizer] ──► Final Response
```

---

## 2. Agent Graph & Workflow

Built on **LangGraph**, the execution state flows through a directed cyclic graph:

1. **`route`**: Analyzes the query using high-precision heuristics and fallback LLM classifier. Routes to the appropriate specialist agent.
2. **Specialist Execution (`general` | `research` | `rag_node` | `math` | `code_agent`)**: Generates a draft answer and collects candidate sources or computational evidence.
3. **`gate`**: Determines whether the draft answer makes factual or verifiable claims requiring verification.
4. **`verify`**: Breaks down the answer into atomic verifiable claims, aligns each claim with retrieved evidence, flags contradictions, and calculates a verification score.
5. **`critic`**: Reviews claim verification status. If critical claims are unverified or contradicted, triggers a correction iteration.
6. **`correct`**: Rewrites contentious or unsupported assertions based strictly on verified evidence.
7. **`finalize`**: Formats the final answer, attaches structured citations, attaches claims metadata, and renders the verification badge.

---

## 3. Core Modules

| Directory | Responsibilities |
| :--- | :--- |
| `backend/agents/` | Specialist agents: Master Router, Research, Math, Code, RAG, Verifier, Critic, Contradiction, Finalizer |
| `backend/graph/` | LangGraph nodes, state definition, and routing logic |
| `backend/verification/` | Claim extraction, evidence scoring, gate logic, and verification engine |
| `backend/tools/` | Deterministic calculator, web search & scraper, sandbox code execution |
| `backend/rag/` | Document ingestion (PDF, DOCX, TXT), chunking, Qdrant vector search |
| `backend/models/` | LLM adapters (Hugging Face Inference, OpenRouter, Qwen models) |
| `backend/api/` | FastAPI REST & SSE streaming endpoints |
| `frontend/` | React 19 + TypeScript + Vite + Tailwind CSS interface with real-time verification indicators |
| `tests/` | Comprehensive test suite (unit, integration, and offline evaluation harness) |

---

## 4. Running the Stack

### Local Development

1. **Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```

2. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Tests**:
   ```bash
   pytest
   python -m tests.evaluation.harness
   ```

### Docker Compose

```bash
docker compose up --build
```
- Frontend: `http://localhost:5173`
- Backend API Docs: `http://localhost:8000/api/docs`
- Qdrant Vector Store: `http://localhost:6333/dashboard`
