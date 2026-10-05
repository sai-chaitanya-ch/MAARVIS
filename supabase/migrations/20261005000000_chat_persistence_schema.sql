-- ============================================================================
-- MAARVIS Production Schema Patch: Chat Persistence & Schema Cache Reload
-- Migration: 20261005000000_chat_persistence_schema.sql
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Ensure conversations table exists and has all required columns
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS title TEXT DEFAULT 'New Conversation';
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_conversations_user_updated 
    ON public.conversations(user_id, updated_at DESC);

-- 2. Ensure messages table exists and has all required columns
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
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

-- Add all execution, verification, and claims columns if missing from earlier migrations
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS provider TEXT;
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS model TEXT;
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS execution_id TEXT;
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS routing_json JSONB;
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS verification_json JSONB;
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS execution_trace_json JSONB;
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS sources_json JSONB;
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS events_json JSONB;
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS claims_json JSONB;
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS user_id TEXT;

CREATE INDEX IF NOT EXISTS idx_messages_conversation 
    ON public.messages(conversation_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_messages_execution 
    ON public.messages(execution_id);
CREATE INDEX IF NOT EXISTS idx_messages_user 
    ON public.messages(user_id);

-- 3. Ensure user_provider_credentials columns exist
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

ALTER TABLE public.user_provider_credentials ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'unchecked';
ALTER TABLE public.user_provider_credentials ADD COLUMN IF NOT EXISTS is_active INTEGER DEFAULT 1;
ALTER TABLE public.user_provider_credentials ADD COLUMN IF NOT EXISTS last_tested_at TIMESTAMPTZ;

-- 4. Enable Row Level Security (RLS)
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_provider_credentials ENABLE ROW LEVEL SECURITY;

-- 5. Row Level Security Policies (Idempotent creation)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'conversations' AND policyname = 'Users access own conversations'
    ) THEN
        CREATE POLICY "Users access own conversations"
            ON public.conversations
            FOR ALL
            USING (auth.uid()::text = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'messages' AND policyname = 'Users access own messages'
    ) THEN
        CREATE POLICY "Users access own messages"
            ON public.messages
            FOR ALL
            USING (auth.uid()::text = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'user_provider_credentials' AND policyname = 'Users access own credentials'
    ) THEN
        CREATE POLICY "Users access own credentials"
            ON public.user_provider_credentials
            FOR ALL
            USING (auth.uid()::text = user_id);
    END IF;
END $$;

-- 6. Reload PostgREST schema cache to immediately expose claims_json and new columns
NOTIFY pgrst, 'reload schema';
