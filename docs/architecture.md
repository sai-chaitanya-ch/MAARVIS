# MAARVIS — Architecture Documentation

MAARVIS (Multi-Agent AI Reasoning & Verification Intelligence System) is an enterprise-grade multi-agent reasoning and verification platform designed for grounded answers, claim-level verification, mathematical certainty, and source provenance.

---

## 1. System Overview

```
User Request
     │
     ▼
[MARVIS Triage & Router] ──(Stage 1: Attachments | Stage 2: Fast Heuristics | Stage 3: JEV AI Semantic Router)
     │
     ├──► [General Agent]      (Conversational & general queries)
     ├──► [Research Agent]     (Live web search & extraction via Tavily)
     ├──► [RAG Agent]          (Document parsing & Supabase pgvector retrieval)
     ├──► [Math Agent]         (Deterministic arithmetic & symbolic checks)
     └──► [Code Agent]         (Code analysis & sandbox execution)
     │
     ▼
[Verification Gate] ──────────► (Checks if verification is necessary)
     │                                │ (If NO)
     │ (If YES)                       ▼
     ▼                           [Synthesizer] ──► Final Response
[Verifier Agent]
  - Claim Extraction
  - Evidence Retrieval & Cross-referencing
  - Contradiction Detection & Scoring
     │
     ▼
[Critic Agent] ─── (Acceptable confidence?) ──┐
     │                                        │ (YES)
     ▼ (NO & attempts < MAX_ITERATIONS)       ▼
[Correction Agent] ──► [Verifier Loop]   [Synthesizer] ──► Final Response
```

---

## 2. Agent Graph & Workflow

Built on **LangGraph**, the execution state flows through a directed cyclic graph:

1. **`route`**: Analyzes the query using high-precision heuristics and JEV AI semantic classifier. Routes to the appropriate specialist agent.
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
| `backend/agents/` | Specialist agents: Master Router, Research, Math, Code, RAG, Verifier, Critic, Contradiction, Synthesizer |
| `backend/graph/` | LangGraph nodes, state definition, and routing logic |
| `backend/verification/` | Claim extraction, evidence scoring, gate logic, and verification engine |
| `backend/tools/` | Deterministic calculator, web search & scraper, sandbox code execution |
| `backend/rag/` | Document ingestion (PDF, DOCX, TXT), chunking, Supabase pgvector search |
| `backend/providers/` | Cloud AI provider adapters (Gemini, OpenAI, Anthropic, Groq, DeepSeek) |
| `backend/security/` | AES-256-GCM encryption at rest, Supabase JWT auth, input sanitization |
| `backend/services/` | Supabase PostgREST client, Storage service, and BYOK Provider service |
| `backend/api/` | FastAPI REST & SSE streaming endpoints |
| `frontend/` | React 18 + TypeScript + Vite + Tailwind CSS interface with real-time verification indicators |
| `backend/tests/` | Automated pytest test suite |

---

## 4. Running the Stack

### Local Development

1. **Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   python main.py
   ```

2. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Tests**:
   ```bash
   py -m pytest backend/tests -v
   ```
