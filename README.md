# Verify.ai

> **Think. Search. Verify.** — An autonomous multi-agent assistant designed for fact-checked answers, claim verification, and source transparency.

---

## Features

- **Multi-Agent Orchestration**: Powered by LangGraph with specialized agents for general chat, multi-query research, deterministic math, sandboxed code execution, and document RAG.
- **Claim-Level Fact Checking**: Automatically decomposes answers into discrete claims and verifies each against primary sources, computations, or retrieved context.
- **Iterative Self-Correction**: When claims are contradicted or lack evidence, a Critic and Correction agent loop refines the draft before presentation.
- **Glass-Box Transparency**: Verification badges, confidence scores, interactive claim popovers, and primary source links for every citation.
- **Document RAG**: Ingests PDFs, Word documents, and text files with vector search using Qdrant.
- **Modern UI**: Clean, responsive React 19 + TypeScript + Vite interface with Tailwind CSS and Framer Motion micro-animations.

---

## Project Structure

```
multiagents/
├── backend/                  # FastAPI backend
│   ├── agents/               # Specialist agents (Master, Research, Math, Code, Verifier, etc.)
│   ├── api/                  # FastAPI routes (chat, research, documents, health)
│   ├── config/               # Settings & environment configuration
│   ├── graph/                # LangGraph nodes, state machine, and routers
│   ├── models/               # LLM clients (Hugging Face / Qwen)
│   ├── rag/                  # Document processing, chunking & Qdrant integration
│   ├── security/             # Prompt injection defenses & input sanitization
│   ├── tests/                # Pytest test suite
│   ├── tools/                # Web search, scraper, calculator, code sandbox
│   └── verification/         # Claim extraction, scoring, and verification engine
├── docker/                   # Dockerfiles, Nginx config, and compose files
├── docs/                     # Architecture & technical documentation
├── frontend/                 # React + TypeScript + Vite web application
└── tests/                    # Evaluation harness and offline benchmark cases
```

---

## Quick Start

### 1. Environment Setup

Copy `.env.example` to `.env` and provide your API keys:
```bash
cp .env.example .env
```
Key configuration items:
- `HF_TOKEN`: Hugging Face User Access Token (recommended for full LLM generation)
- `TAVILY_API_KEY`: Tavily API key for web search
- `QDRANT_URL`: URL to your Qdrant instance (default: `http://localhost:6333`)

### 2. Run with Docker Compose

```bash
docker compose up --build
```

Access the services:
- **Web App**: [http://localhost:5173](http://localhost:5173)
- **API Documentation**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **Qdrant Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

### 3. Run Locally for Development

#### Backend
```bash
 cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Testing & Evaluation

Run the unit and integration tests:
```bash
pytest
```

Run the offline evaluation harness:
```bash
$env:PYTHONPATH=".;backend"; python -m tests.evaluation.harness
```

---

## License

MIT
