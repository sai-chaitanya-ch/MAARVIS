-- ============================================================================
-- MAARVIS Production Schema: PostgreSQL + Supabase pgvector + RLS + Storage
-- Migration: 20261003000000_maarvis_schema.sql
-- ============================================================================

-- 1. Enable pgvector extension for document embedding search
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Conversations table
CREATE TABLE IF NOT EXISTS public.conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_updated 
    ON public.conversations(user_id, updated_at DESC);

-- 3. Messages table (execution-isolated, persisted trace and verification)
CREATE TABLE IF NOT EXISTS public.messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    execution_id TEXT,
    routing_json JSONB,
    verification_json JSONB,
    execution_trace_json JSONB,
    sources_json JSONB,
    events_json JSONB,
    claims_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation 
    ON public.messages(conversation_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_messages_execution 
    ON public.messages(execution_id);
CREATE INDEX IF NOT EXISTS idx_messages_user 
    ON public.messages(user_id);

-- 4. Documents table
CREATE TABLE IF NOT EXISTS public.documents (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    mime_type TEXT,
    storage_path TEXT,
    size_bytes BIGINT DEFAULT 0,
    chunks INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_user 
    ON public.documents(user_id, created_at DESC);

-- 5. Document Chunks table (768-dim embeddings for pgvector)
CREATE TABLE IF NOT EXISTS public.document_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_doc 
    ON public.document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_user 
    ON public.document_chunks(user_id);

-- Vector similarity search function for Supabase pgvector
CREATE OR REPLACE FUNCTION match_document_chunks(
    query_embedding vector(768),
    match_count int DEFAULT 10,
    filter_user_id text DEFAULT NULL,
    filter_document_ids text[] DEFAULT NULL
)
RETURNS TABLE (
    id text,
    document_id text,
    user_id text,
    chunk_index int,
    content text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.document_id,
        dc.user_id,
        dc.chunk_index,
        dc.content,
        dc.metadata,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM public.document_chunks dc
    WHERE
        (filter_user_id IS NULL OR dc.user_id = filter_user_id)
        AND (filter_document_ids IS NULL OR dc.document_id = ANY(filter_document_ids))
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 6. User Provider Credentials table (at-rest encrypted API keys)
CREATE TABLE IF NOT EXISTS public.user_provider_credentials (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    label TEXT,
    model TEXT,
    encrypted_key TEXT NOT NULL,
    key_masked TEXT NOT NULL,
    status TEXT DEFAULT 'unchecked',
    is_active INTEGER DEFAULT 1,
    last_tested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_provider_creds_user 
    ON public.user_provider_credentials(user_id, provider);

-- 7. Enable Row Level Security (RLS) on all user-facing tables
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_provider_credentials ENABLE ROW LEVEL SECURITY;

-- 8. Row Level Security Policies (Access only own data)
CREATE POLICY "Users access own conversations"
    ON public.conversations
    FOR ALL
    USING (auth.uid()::text = user_id);

CREATE POLICY "Users access own messages"
    ON public.messages
    FOR ALL
    USING (auth.uid()::text = user_id);

CREATE POLICY "Users access own documents"
    ON public.documents
    FOR ALL
    USING (auth.uid()::text = user_id);

CREATE POLICY "Users access own document chunks"
    ON public.document_chunks
    FOR ALL
    USING (auth.uid()::text = user_id);

CREATE POLICY "Users access own provider credentials"
    ON public.user_provider_credentials
    FOR ALL
    USING (auth.uid()::text = user_id);

-- 9. Storage Bucket setup for documents
INSERT INTO storage.buckets (id, name, public)
VALUES ('documents', 'documents', false)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Users access own uploaded files"
    ON storage.objects
    FOR ALL
    USING (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);
