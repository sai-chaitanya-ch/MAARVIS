````markdown
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
````

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
* Basic explanations
* Simple definitions
* Low-risk summaries
* Straightforward conversations

The objective is to avoid unnecessary orchestration.

---

## Multi-Agent Force

Allows the user to explicitly request the multi-agent workflow.

This is useful when the user wants deeper analysis, multiple stages of reasoning, or visible agent execution.

---

# Intelligent Routing

MAARVIS categorizes queries before deciding how they should be processed.

Example categories include:

### Conversational

```text
"Hi"
"Explain recursion."
"What is an API?"
```

→ Direct response

### Quantitative / Deterministic

```text
"What is 238 × 421?"
"Convert 100 million to the Indian numbering system."
```

→ Deterministic computation / sandbox

### Code & Analysis

```text
"Analyze this Python code."
"Find the bug in this program."
```

→ Coder / Analyst / sandbox where required

### Factual / Document Research

```text
"What does this PDF say about revenue?"
```

→ RAG / document retrieval

### Complex Research

```text
"Compare these conflicting claims and determine what the evidence supports."
```

→ Multi-agent research and verification

---

# Multi-Agent Intelligence

For complex tasks, MAARVIS can activate specialized components instead of sending every request through every agent.

A typical workflow can look like:

```text
                    MARVIS Router
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   Researcher       RAG / Document   Coder / Analyst
        │                │                │
        └────────────────┼────────────────┘
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

The verification layer can evaluate different dimensions.

### Computational Verification

* Mathematical correctness
* Numerical precision
* Syntax checks
* Sandbox execution
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

MAARVIS can use user-provided documents as a source of context.

```text
Document
    ↓
Text Extraction
    ↓
Chunking
    ↓
Embeddings
    ↓
Vector Storage
    ↓
Relevant Retrieval
    ↓
Agent Analysis
    ↓
Verification
    ↓
Answer
```

The goal is to allow users to research their own documents without leaving the MAARVIS workspace.

---

# Evidence & Transparency

MAARVIS provides a verification-oriented interface where the user can inspect information associated with an execution.

Depending on the query and available capabilities, this can include:

* Execution route
* Provider/model used
* Retrieved document chunks
* Claims
* Supporting evidence
* Sources
* Agents that actually executed
* Execution timing
* Verification status

The interface is designed around a **glass-box approach** rather than presenting every answer as an unexplained output.

---

# API & Provider Architecture

MAARVIS is designed around a provider abstraction rather than depending on a single AI gateway.

Users can connect supported AI providers using their own API keys.

Example:

```text
API & Providers

Google Gemini       ● Connected
OpenAI              ○ Not configured
Anthropic           ○ Not configured
Groq                ○ Not configured
DeepSeek            ○ Not configured
```

A single configured provider should be sufficient for basic MAARVIS usage.

Additional providers can provide additional capabilities, model choices, or redundancy.

---

# Optional Capabilities

MAARVIS is designed to work without requiring every external service.

For example:

```text
                 MAARVIS
                    │
        ┌───────────┼────────────┐
        │           │            │
      Gemini       RAG        Web Search
        │           │            │
     Required    Optional      Optional
```

Other optional capabilities may include:

* JEV AI for advanced decision/routing capabilities
* Web search for current external information
* Additional AI providers
* Code execution/sandbox capabilities
* Document retrieval

Missing optional capabilities should reduce available functionality rather than make the entire application unusable.

---

# Human + AI Development Philosophy

One of the main lessons behind MAARVIS was that building an AI system is not simply about giving instructions to an AI coding tool.

The human still needs to determine:

```text
Problem
   ↓
Architecture
   ↓
Decisions
   ↓
Query Categories
   ↓
Routing Logic
   ↓
Agent Responsibilities
   ↓
Verification Strategy
   ↓
Implementation
```

AI can accelerate implementation, experimentation, debugging, and iteration.

But the system's architecture and decisions still need human reasoning.

This project was built around that principle:

> **Use AI as a powerful worker, while keeping the human responsible for the direction and decisions.**

---

# Project Structure

```text
MAARVIS/
│
├── backend/
│   ├── agents/
│   ├── api/
│   ├── config/
│   ├── graph/
│   ├── models/
│   ├── rag/
│   ├── security/
│   ├── tools/
│   └── verification/
│
├── frontend/
│   ├── components/
│   ├── pages/
│   ├── services/
│   └── ...
│
├── docs/
│   ├── architecture/
│   ├── research/
│   └── ...
│
├── tests/
│
└── README.md
```

---

# Production Architecture

The planned production architecture is intentionally simple.

```text
                     MAARVIS
                        │
              ┌─────────┴─────────┐
              │                   │
           Netlify              Render
          Frontend             Backend API
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                 AI APIs        RAG         Optional APIs
                    │             │             │
                    │          Supabase        │
                    │             │             │
                    └─────────────┴─────────────┘
                                  │
                              Supabase
                         Auth / Database /
                         Storage / Vector
```

The production architecture does **not** depend on:

* A developer's laptop
* A locally running AI gateway
* OmniRoute
* Hardcoded provider credentials

---

# Security Principles

MAARVIS is designed around server-side handling of provider credentials.

Provider API keys should:

* Never be exposed to client-side JavaScript
* Never be committed to Git
* Never be stored in browser localStorage
* Never appear in logs
* Be encrypted at rest
* Be scoped to the authenticated user

---

# Development

Clone the repository:

```bash
git clone <repository-url>
cd MAARVIS
```

Install the required dependencies according to the frontend and backend setup.

Development instructions will be maintained as the production architecture is finalized.

---

# Current Development Status

MAARVIS is an active development project.

### Implemented / In Development

* [x] MAARVIS assistant interface
* [x] Auto / Direct Fast / Multi-Agent modes
* [x] Multi-agent workflow architecture
* [x] Verification analysis interface
* [x] Document RAG workflow
* [x] Agent execution visualization
* [ ] Persistent conversation history
* [ ] Production provider management
* [ ] Secure provider credential storage
* [ ] Production RAG infrastructure
* [ ] Production deployment
* [ ] Expanded provider support

---

# Research & Documentation

The project documentation covers:

* System architecture
* Query classification
* Intelligent routing
* Execution modes
* Agent responsibilities
* Verification architecture
* RAG
* Decision-making concepts
* Evaluation and testing

See the `/docs` directory for the technical documentation.

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

```
```
