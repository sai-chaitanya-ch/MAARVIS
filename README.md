# MAARVIS

### Ask. Analyze. Verify.

**MAARVIS** is a multi-agent AI reasoning and verification intelligence system designed to determine **how much intelligence a query actually needs**.

Instead of sending every user query through a large multi-agent pipeline, MAARVIS first understands the query and selects an appropriate execution path.

> **Not more agents. The right agents, at the right time.**

---

## Why MAARVIS?

While building a multi-agent verification engine, we noticed an important problem:

If a user asks:

> "Hi"

why should multiple AI agents be activated?

If a user asks:

> "What is 2 × 3?"

why should a complete research and verification pipeline run when the answer is deterministic?

This led to the central idea behind MAARVIS:

> **The system should decide how much reasoning a query requires before executing the reasoning.**

A simple query should remain simple.

A deterministic computation should use deterministic computation.

A complex research problem should receive multi-agent reasoning and verification.

---

# Core Architecture

```text
                         USER QUERY
                              │
                              ▼
                    ┌───────────────────┐
                    │   MAARVIS Router  │
                    │ Query Intelligence│
                    └─────────┬─────────┘
                              │
              ┌───────────────┼────────────────┐
              │               │                │
              ▼               ▼                ▼
        DIRECT FAST      DETERMINISTIC    MULTI-AGENT
              │               │                │
              ▼               ▼                ▼
          Direct LLM       Sandbox       Specialized Agents
                              │                │
                              └───────┬────────┘
                                      ▼
                              Verification Layer
                                      │
                                      ▼
                                Final Response
```

MAARVIS supports both automatic routing and explicit user control.

---

# Execution Modes

## Auto

The default mode.

MAARVIS analyzes the query and selects the appropriate execution path.

```text
User Query
    ↓
Query Classification
    ↓
Route Selection
    ↓
Required Agents / Tools
    ↓
Verification
    ↓
Response
```

---

## Direct Fast

Designed for simple and low-complexity requests.

Examples:

* Greetings
* Conversational responses
* Formatting requests
* Simple explanations

This path uses a single AI model call without running unnecessary background agents or complex verification pipelines.

---

## Multi-Agent

Designed for complex reasoning, research, document queries, and claim verification.

Queries in this mode are routed through specialized agents:

```text
                        Multi-Agent Request
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
   Researcher              RAG / Document          Coder / Analyst
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 ▼
                       Fact Verifier / Critic
                                 │
                                 ▼
                            Synthesizer
                                 │
                                 ▼
                            Final Answer
```

Depending on the query, some components may be skipped.

---

# Verification

MAARVIS is designed to make the verification process visible rather than treating the final answer as a black box.

The verification layer evaluates multiple dimensions:

### Computational Verification
* Mathematical correctness
* Numerical precision
* Syntax checks
* Isolated deterministic Python AST sandbox execution
* Execution results

### Factual Verification
* Claim decomposition
* Retrieved evidence
* Source attribution
* Document grounding

### Logical Verification
* Premise consistency
* Deductive validity
* Logical contradictions
* Fallacy screening

### Risk & Contradiction Analysis
* Conflicting evidence
* Unsupported claims
* Potential hallucination signals
* Required caveats

---

# Document RAG

MAARVIS uses user-provided documents as a verified source of context.

```text
Document (PDF, DOCX, TXT)
    ↓
Text Extraction & Chunking
    ↓
768-dim Vector Embeddings
    ↓
Supabase pgvector Storage
    ↓
Relevant Retrieval (Cosine Similarity)
    ↓
Agent Analysis & Claim Extraction
    ↓
Independent Verification
    ↓
Synthesized Answer
```

Users can research their own documents with strict multi-tenant isolation.

---

# Evidence & Transparency

MAARVIS provides a verification-oriented interface where the user can inspect information associated with an execution:

* Execution route & decision engine (Deterministic / JEV AI)
* Provider/model used
* Retrieved document chunks (Supabase pgvector)
* Atomic claims extracted
* Supporting evidence & confidence scores
* Primary sources & domains
* Agents that actually executed
* Execution latency & token usage
* Verification status

The interface is designed around a **glass-box approach** rather than presenting every answer as an unexplained output.

---

# API & Provider Architecture (BYOK)

MAARVIS is designed around a provider abstraction rather than depending on a single AI gateway.

Users can connect supported AI providers using their own API keys (Bring Your Own Key):

```text
API & Providers

Google Gemini       ● Connected (Core / Required)
OpenAI              ○ Configurable
Anthropic           ○ Configurable
Groq                ○ Configurable
DeepSeek            ○ Configurable
```

A single configured provider (such as Google Gemini) is sufficient for core MAARVIS usage.

Additional providers can provide extra capabilities, model choices, or redundancy.

---

# Optional Capabilities

MAARVIS is designed to work gracefully even when optional services are absent:

```text
                 MAARVIS
                    │
        ┌───────────┼────────────┐
        │           │            │
      Gemini       RAG        Web Search
        │           │            │
     Required    Optional      Optional
```

* **JEV AI**: Optional semantic triage, calibrated confidence & advanced classification. When absent, high-precision deterministic AST/pattern fallbacks take over seamlessly.
* **Tavily / Web Search**: Optional live web search verification. When absent, the system honestly reports external research unavailable without crashing.
* **Document RAG**: Enabled automatically whenever documents are uploaded.

Missing optional capabilities honestly reduce available functionality rather than making the application unusable.

---

# Production Architecture

```text
                     MAARVIS
                        │
              ┌─────────┴─────────┐
              │                   │
           Netlify              Render
         React / Vite         FastAPI API
              │                   │
              └─────────┬─────────┘
                        │
                    Supabase
         ┌──────────────┼──────────────┐
         │              │              │
      Supabase      PostgreSQL      Supabase
        Auth        + pgvector      Storage
         │              │              │
         └──────────────┴──────────────┘
                        │
                        ▼
                User AI Providers
          Gemini / OpenAI / Anthropic /
                Groq / DeepSeek
```

The production architecture does **not** depend on:
* A developer's laptop
* A locally running AI gateway
* OmniRoute
* Qdrant
* Persistent local SQLite databases
* Hardcoded provider credentials

---

# Security Principles

MAARVIS enforces server-side handling and strict encryption for all provider credentials:

* **AES-256-GCM Encryption**: API keys are encrypted at rest using AES-256-GCM with unique 12-byte initialization vectors (nonces) and SHA-256 key derivation.
* **Never Exposed to Frontend**: Raw keys never appear in GET responses, error traces, or logs. Responses return masked strings (e.g., `sk-...abcd`).
* **Server-Side Only**: Decrypted keys exist solely in memory during transient provider calls.
* **Strict User Isolation**: Conversations, messages, documents, chunks, and credentials are authenticated via Supabase JWT and isolated via Row Level Security (RLS).
* **Production Authentication**: Unauthenticated requests in production return `401 Unauthorized`.

---

# Project Structure

```text
MAARVIS/
├── backend/
│   ├── agents/               # Specialist agents (RAG, Math, Research, Coder, Verifier, Synthesizer)
│   ├── api/                  # FastAPI routes (chat, documents, providers, health, evaluation)
│   ├── config/               # Settings & environment configuration
│   ├── graph/                # State machine & agent workflows
│   ├── marvis/               # Router, dispatcher, and triage classification
│   ├── memory/               # Conversation and document state persistence
│   ├── models/               # LLM and embedding interfaces
│   ├── providers/            # Direct provider adapters (Gemini, OpenAI, Anthropic, Groq, DeepSeek)
│   ├── rag/                  # Ingestion, chunking, and Supabase pgvector store
│   ├── security/             # AES-256-GCM encryption, JWT auth, and input sanitization
│   ├── services/             # Supabase PostgREST client, Storage service, and Provider service
│   └── tests/                # Automated pytest test suite (106 tests)
├── frontend/
│   ├── public/               # Static assets & Netlify _redirects
│   └── src/                  # React 18 + Vite components, screens, hooks, and API client
├── docs/                     # Architecture & technical documentation
└── supabase/
    └── migrations/           # PostgreSQL, pgvector & RLS schema migrations
```

---

# Quick Start (Development)

### 1. Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows (or source venv/bin/activate on Unix)
pip install -r requirements.txt
cp ../.env.example .env
python main.py
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 3. Run Automated Tests

```bash
py -m pytest backend/tests -v
```

---

# Deployment

Refer to [`DEPLOYMENT.md`](./DEPLOYMENT.md) for full step-by-step instructions to deploy:
- Database, Auth & Vector Search on **Supabase**
- Backend API on **Render**
- Frontend Web App on **Netlify**

---

# Current Development Status

MAARVIS is actively maintained and fully migrated to production cloud architecture.

### Implemented & Verified

* [x] MAARVIS assistant interface
* [x] Auto / Direct Fast / Multi-Agent modes
* [x] Multi-agent workflow architecture
* [x] Verification analysis interface
* [x] Document RAG workflow
* [x] Agent execution visualization
* [x] Persistent conversation history (Supabase PostgreSQL)
* [x] Production provider management (BYOK)
* [x] Secure provider credential storage (AES-256-GCM at rest)
* [x] Production RAG infrastructure (Supabase pgvector, 768-dim)
* [x] Production deployment (Netlify + Render + Supabase)
* [x] Expanded provider support (Gemini, OpenAI, Anthropic, Groq, DeepSeek)
* [x] Comprehensive automated test suite (106 passed tests)

---

# Vision

MAARVIS is not built around the idea that every question needs more AI.

It is built around a different principle:

> **Give each problem the amount of intelligence it actually needs.**

Simple questions should remain simple.

Deterministic problems should be computed deterministically.

Complex problems should receive deeper reasoning.

And when verification matters, the user should be able to understand **why the system reached its answer.**

---

# MAARVIS

### Ask. Analyze. Verify.

Built during **HackFusion 2026**.

---

## License

MIT License
