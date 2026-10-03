# MAARVIS Production Deployment Guide

MAARVIS is deployed on a modern, decoupled cloud architecture designed for high availability, zero local machine dependencies, and user-isolated multi-tenant security.

---

## 1. Architecture Overview

| Layer | Provider | Service / Purpose |
| :--- | :--- | :--- |
| **Frontend** | **Netlify** | Vite + React (TypeScript) SPA, global CDN distribution |
| **Backend API** | **Render** | Python FastAPI Web Service running MARVIS Multi-Agent Orchestrator |
| **Database & Auth** | **Supabase** | PostgreSQL, Row-Level Security (RLS), Supabase Auth (JWT) |
| **Vector Database** | **Supabase (pgvector)** | Native 768-dim cosine embeddings for RAG retrieval |
| **File Storage** | **Supabase Storage** | Encrypted object storage bucket for uploaded documents |
| **AI Providers** | **BYOK / Cloud** | Google Gemini (minimum required), OpenAI, Anthropic, Groq, DeepSeek |
| **Optional Decision** | **JEV AI** | Semantic routing & calibrated route confidence |
| **Optional Web** | **Tavily / Search** | Independent live external web verification |

> [!IMPORTANT]
> **No Local Gateway Dependency:** OmniRoute, local Docker sandboxes, and localhost databases have been completely decoupled. The platform runs 100% in the cloud without requiring a local machine to be online.

---

## 2. Supabase Setup (Database, Vector & Storage)

### Step 2.1: Create Project
1. Log in to [Supabase](https://supabase.com) and create a new project (e.g. `maarvis-prod`).
2. Note your **Project URL** and **API Keys** under **Project Settings → API**:
   - `Project URL`
   - `anon / public` key
   - `service_role` key (keep secret!)

### Step 2.2: Apply Database Schema Migration
1. Navigate to the **SQL Editor** in your Supabase dashboard.
2. Open and paste the contents of `supabase/migrations/20261003000000_maarvis_schema.sql` located in this repository.
3. Click **Run**.
4. This migration automatically:
   - Enables the `vector` extension (`pgvector`).
   - Creates tables: `conversations`, `messages`, `documents`, `document_chunks`, `user_provider_credentials`.
   - Enables **Row Level Security (RLS)** with policies guaranteeing users can only read and write their own data.
   - Creates the `documents` storage bucket with private access policies.

---

## 3. Render Backend Deployment (API Web Service)

### Step 3.1: Create Web Service
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Web Service**.
3. Connect your GitHub repository containing the MAARVIS codebase.
4. Configure the service settings:
   - **Name:** `maarvis-api`
   - **Environment:** `Python`
   - **Region:** Choose the region closest to your Supabase project (e.g., `Oregon (US West)` or `Frankfurt (EU)`).
   - **Branch:** `main`
   - **Root Directory:** leave blank or specify `backend`
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `python backend/main.py`
     *(Alternatively, if Root Directory is `backend`: Build: `pip install -r requirements.txt`, Start: `python main.py`)*
   - **Plan:** `Starter` (or free tier)

### Step 3.2: Configure Health Check Path
- Under **Advanced Settings**, set **Health Check Path** to:
  ```
  /health
  ```
  Render will ping this endpoint. It returns `{"status": "ok", "service": "maarvis-api"}` with HTTP 200.

### Step 3.3: Environment Variables on Render
Add the following environment variables in the Render Dashboard (**Environment** tab):

| Variable | Value / Description | Required? |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | **Yes** |
| `PORT` | *(Provided automatically by Render)* | Render defaults |
| `SUPABASE_URL` | `https://<your-project>.supabase.co` | **Yes** |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJ...` (Your Supabase Service Role Secret) | **Yes** |
| `SUPABASE_ANON_KEY` | `eyJ...` (Your Supabase Anon Public Key) | **Yes** |
| `SUPABASE_STORAGE_BUCKET` | `documents` | **Yes** |
| `PROVIDER_ENCRYPTION_KEY` | *(A random 32-character or 64-hex string)* | **Yes** |
| `CORS_ORIGINS` | `https://<your-app>.netlify.app,http://localhost:5173` | **Yes** |
| `GEMINI_API_KEY` | `AIzaSy...` (Optional server default if user does not supply one) | Optional |
| `JEV_API_KEY` | JEV API key for advanced semantic routing | Optional |
| `TAVILY_API_KEY` | Tavily API key for live web research | Optional |

---

## 4. Netlify Frontend Deployment

### Step 4.1: Create Site
1. Log in to [Netlify](https://app.netlify.com).
2. Click **Add new site** → **Import an existing project** → Connect to GitHub.
3. Configure build settings:
   - **Base directory:** `frontend`
   - **Build command:** `npm run build`
   - **Publish directory:** `dist` (or `frontend/dist`)

### Step 4.2: Environment Variables on Netlify
Add the following client-safe environment variables in **Site configuration → Environment variables**:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://maarvis-api.onrender.com` | Your Render backend domain (no trailing slash) |
| `VITE_SUPABASE_URL` | `https://<your-project>.supabase.co` | Supabase Project URL |
| `VITE_SUPABASE_ANON_KEY` | `eyJ...` | Supabase Anon Key (Safe for client-side) |

> [!CAUTION]
> Never put private provider API keys, encryption keys, or Supabase service role keys into `VITE_` variables. Only safe client configuration belongs on Netlify.

### Step 4.3: Netlify SPA Redirects
The project includes a `frontend/public/_redirects` file:
```
/*    /index.html   200
```
This ensures direct navigation to `/evaluation` and client-side routes rewrites to `index.html`.

---

## 5. Post-Deployment Verification & Smoke Tests

Run these smoke tests against your production backend domain:

### Test 1: Production Health Check
```bash
curl -s https://maarvis-api.onrender.com/health
# Expected Output:
# {"status":"ok","service":"maarvis-api"}
```

### Test 2: System Capabilities
```bash
curl -s https://maarvis-api.onrender.com/api/providers/capabilities
# Expected: JSON object showing status of gemini, rag, jev, web_search, sandbox
```

### Test 3: Supported AI Providers
```bash
curl -s https://maarvis-api.onrender.com/api/providers/supported
# Expected: List of Google Gemini, OpenAI, Anthropic, Groq, DeepSeek
```

### Test 4: End-to-End Chat Verification
1. Open your Netlify URL (e.g. `https://maarvis.netlify.app`).
2. If no server key was set, navigate to **Settings → API & Providers** and add your Google Gemini key.
3. Enter query: `Who founded Google?`
   - Verify that the title generates automatically: `"Google Founder Question"`.
   - Verify that the response streams and shows verification metrics.
4. Click **New Chat** (+).
   - Verify that previous attachments and state are cleared cleanly.
5. Open the **History** drawer.
   - Verify that your past chat appears under **Today** with relative timestamp and message count.
