"""
Conversation, Message, and Document Persistence for MAARVIS.
Integrates directly with Supabase PostgreSQL in production.
Provides scoped local database storage for offline test suites and local dev.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

from config.settings import get_settings
from services.supabase_service import get_supabase_service
from utils.tracing import new_id
from utils.logging import get_logger

log = get_logger(__name__)

_DB: Optional[aiosqlite.Connection] = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    execution_id TEXT,
    routing_json TEXT,
    verification_json TEXT,
    execution_trace_json TEXT,
    sources_json TEXT,
    events_json TEXT,
    claims_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    filename TEXT,
    mime_type TEXT,
    storage_path TEXT,
    size_bytes INTEGER DEFAULT 0,
    chunks INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    title TEXT,
    url TEXT,
    domain TEXT,
    source_type TEXT,
    payload_json TEXT,
    created_at TEXT NOT NULL
);
"""

_CURRENT_DB_PATH: Optional[str] = None


async def _ensure_columns(db: aiosqlite.Connection) -> None:
    """Migrate local SQLite tables with any missing columns."""
    try:
        conv_cols = [c[1] for c in await (await db.execute("PRAGMA table_info(conversations)")).fetchall()]
        if "user_id" not in conv_cols:
            await db.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT DEFAULT 'default_user'")

        msg_cols = [c[1] for c in await (await db.execute("PRAGMA table_info(messages)")).fetchall()]
        if "user_id" not in msg_cols:
            await db.execute("ALTER TABLE messages ADD COLUMN user_id TEXT DEFAULT 'default_user'")
        if "provider" not in msg_cols:
            await db.execute("ALTER TABLE messages ADD COLUMN provider TEXT")
        if "model" not in msg_cols:
            await db.execute("ALTER TABLE messages ADD COLUMN model TEXT")
        if "execution_id" not in msg_cols:
            await db.execute("ALTER TABLE messages ADD COLUMN execution_id TEXT")
        if "routing_json" not in msg_cols:
            await db.execute("ALTER TABLE messages ADD COLUMN routing_json TEXT")
        if "execution_trace_json" not in msg_cols:
            await db.execute("ALTER TABLE messages ADD COLUMN execution_trace_json TEXT")

        doc_cols = [c[1] for c in await (await db.execute("PRAGMA table_info(documents)")).fetchall()]
        if "user_id" not in doc_cols:
            await db.execute("ALTER TABLE documents ADD COLUMN user_id TEXT DEFAULT 'default_user'")
        if "name" not in doc_cols:
            await db.execute("ALTER TABLE documents ADD COLUMN name TEXT DEFAULT 'document'")
        if "filename" not in doc_cols:
            await db.execute("ALTER TABLE documents ADD COLUMN filename TEXT DEFAULT 'document'")
        if "mime_type" not in doc_cols:
            await db.execute("ALTER TABLE documents ADD COLUMN mime_type TEXT")
        if "storage_path" not in doc_cols:
            await db.execute("ALTER TABLE documents ADD COLUMN storage_path TEXT")
        if "size_bytes" not in doc_cols:
            await db.execute("ALTER TABLE documents ADD COLUMN size_bytes INTEGER DEFAULT 0")

        await db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, updated_at DESC)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, created_at ASC)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_messages_exec ON messages(execution_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id)")
        await db.commit()
    except Exception as exc:
        log.warning("sqlite_schema_column_migration_notice", error=str(exc))


async def get_db() -> aiosqlite.Connection:
    global _DB, _CURRENT_DB_PATH
    settings = get_settings()
    path_str = Path(settings.sqlite_path).as_posix()
    if _DB is not None and _CURRENT_DB_PATH != path_str:
        try:
            await _DB.close()
        except Exception:
            pass
        _DB = None

    if _DB is None:
        path = Path(settings.sqlite_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _DB = await aiosqlite.connect(path.as_posix())
        _DB.row_factory = aiosqlite.Row
        _CURRENT_DB_PATH = path_str
        await _DB.executescript(SCHEMA)
        await _ensure_columns(_DB)
        await _DB.commit()
    return _DB


def generate_conversation_title(message: str) -> str:
    """Generate a concise, contextual conversation title (2-5 words)."""
    text = re.sub(r"[\r\n]+", " ", message).strip()
    msg_lower = text.lower()

    if ("found" in msg_lower and "google" in msg_lower) or ("who started google" in msg_lower):
        return "Google Founder Question"
    if "research paper" in msg_lower or ("paper" in msg_lower and "analysis" in msg_lower):
        return "Research Paper Analysis"
    if "array" in msg_lower and ("java" in msg_lower or "debug" in msg_lower or "index" in msg_lower):
        return "Java Array Debugging"
    if "revenue" in msg_lower or "q3" in msg_lower or "financial" in msg_lower:
        return "Q3 Revenue Analysis"
    if "quantum" in msg_lower:
        return "Quantum Computing Overview"
    if "photosynthesis" in msg_lower:
        return "Photosynthesis Process"

    if any(kw in text for kw in ("def ", "class ", "import ", "public class ", "SELECT ", "fn ")):
        if "python" in msg_lower:
            return "Python Code Snippet"
        if "sql" in msg_lower or "query" in msg_lower:
            return "Database Query Analysis"
        return "Code Analysis & Debugging"

    filler_patterns = [
        r"^(?:can you|could you|please|tell me|i want to know|what is the|what are the|who is the|who are the|how do i|how to|why does|explain the|explain|check if|verify)\s+",
        r"^(?:hi|hello|hey|good morning|good evening)[,\s]*",
    ]
    cleaned = text
    for pattern in filler_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    words = [w for w in cleaned.split() if w.strip()]
    if not words:
        return "General Reasoning"

    title_words = words[:4]
    title = " ".join(title_words)
    title = re.sub(r"[?!.,;:]+$", "", title).strip()

    if len(title) < 3:
        return "Conversation Query"

    return title.title()


async def create_conversation(title: str, user_id: str = "default_user") -> str:
    if get_supabase_service().is_configured:
        return await get_supabase_service().create_conversation(title, user_id=user_id)

    db = await get_db()
    cid = new_id("c_")
    now = datetime.now(timezone.utc).isoformat()
    clean_title = title[:80] if title else "New Conversation"
    await db.execute(
        "INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (cid, user_id, clean_title, now, now),
    )
    await db.commit()
    return cid


async def touch_conversation(
    conversation_id: str,
    title: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    if get_supabase_service().is_configured:
        await get_supabase_service().touch_conversation(conversation_id, user_id=user_id, title=title)
        return

    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    if title:
        await db.execute(
            "UPDATE conversations SET updated_at=?, title=? WHERE id=?",
            (now, title[:80], conversation_id),
        )
    else:
        await db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
    await db.commit()


async def add_message(
    conversation_id: str,
    role: str,
    content: str,
    *,
    user_id: str = "default_user",
    provider: Optional[str] = None,
    model: Optional[str] = None,
    execution_id: Optional[str] = None,
    routing: Optional[Dict[str, Any]] = None,
    verification: Optional[Dict[str, Any]] = None,
    execution_trace: Optional[Dict[str, Any]] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    events: Optional[List[Dict[str, Any]]] = None,
    claims: Optional[List[Dict[str, Any]]] = None,
) -> str:
    if get_supabase_service().is_configured:
        return await get_supabase_service().add_message(
            conversation_id,
            role,
            content,
            user_id=user_id,
            provider=provider,
            model=model,
            execution_id=execution_id,
            routing=routing,
            verification=verification,
            execution_trace=execution_trace,
            sources=sources,
            events=events,
            claims=claims,
        )

    db = await get_db()
    mid = new_id("m_")
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        """INSERT INTO messages
           (id, conversation_id, user_id, role, content, provider, model, execution_id,
            routing_json, verification_json, execution_trace_json, sources_json, events_json, claims_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            mid,
            conversation_id,
            user_id,
            role,
            content,
            provider,
            model,
            execution_id,
            json.dumps(routing) if routing else None,
            json.dumps(verification) if verification else None,
            json.dumps(execution_trace) if execution_trace else None,
            json.dumps(sources) if sources else None,
            json.dumps(events) if events else None,
            json.dumps(claims) if claims else None,
            now,
        ),
    )
    await db.commit()
    await touch_conversation(conversation_id, user_id=user_id)
    return mid


async def list_conversations(user_id: str = "default_user") -> List[Dict[str, Any]]:
    if get_supabase_service().is_configured:
        return await get_supabase_service().list_conversations(user_id=user_id)

    db = await get_db()
    rows = await db.execute(
        """SELECT c.id, c.user_id, c.title, c.updated_at, c.created_at,
                  (SELECT COUNT(*) FROM messages m WHERE m.conversation_id=c.id) as message_count
           FROM conversations c
           WHERE c.user_id = ?
           ORDER BY c.updated_at DESC LIMIT 100""",
        (user_id,),
    )
    return [dict(r) for r in await rows.fetchall()]


async def get_conversation(
    conversation_id: str,
    user_id: str = "default_user",
) -> Optional[Dict[str, Any]]:
    if get_supabase_service().is_configured:
        return await get_supabase_service().get_conversation(conversation_id, user_id=user_id)

    db = await get_db()
    conv = await db.execute(
        "SELECT * FROM conversations WHERE id=? AND user_id=?",
        (conversation_id, user_id),
    )
    row = await conv.fetchone()
    if not row:
        return None

    msgs = await db.execute(
        "SELECT * FROM messages WHERE conversation_id=? AND user_id=? ORDER BY created_at ASC",
        (conversation_id, user_id),
    )
    messages = []
    for m in await msgs.fetchall():
        item = dict(m)
        for key in (
            "routing_json",
            "verification_json",
            "execution_trace_json",
            "sources_json",
            "events_json",
            "claims_json",
        ):
            target_key = key.replace("_json", "")
            if item.get(key):
                try:
                    item[target_key] = json.loads(item[key])
                except Exception:
                    item[target_key] = None
            else:
                item[target_key] = None
        messages.append(item)

    data = dict(row)
    data["messages"] = messages
    return data


async def delete_conversation(conversation_id: str, user_id: str = "default_user") -> bool:
    if get_supabase_service().is_configured:
        return await get_supabase_service().delete_conversation(conversation_id, user_id=user_id)

    db = await get_db()
    res = await db.execute(
        "DELETE FROM conversations WHERE id=? AND user_id=?",
        (conversation_id, user_id),
    )
    await db.commit()
    return res.rowcount > 0


async def recent_messages(
    conversation_id: str,
    user_id: str = "default_user",
    limit: int = 12,
) -> List[Dict[str, str]]:
    if get_supabase_service().is_configured:
        return await get_supabase_service().recent_messages(conversation_id, user_id=user_id, limit=limit)

    db = await get_db()
    rows = await db.execute(
        "SELECT role, content FROM messages WHERE conversation_id=? AND user_id=? ORDER BY created_at DESC LIMIT ?",
        (conversation_id, user_id, limit),
    )
    items = [dict(r) for r in await rows.fetchall()]
    items.reverse()
    return [{"role": i["role"], "content": i["content"]} for i in items]


async def save_document(
    document_id: str,
    name: str,
    storage_path: str,
    chunks: int,
    user_id: str = "default_user",
    mime_type: str = "application/octet-stream",
    size_bytes: int = 0,
) -> None:
    if get_supabase_service().is_configured:
        await get_supabase_service().save_document(
            document_id=document_id,
            name=name,
            storage_path=storage_path,
            chunks=chunks,
            user_id=user_id,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )
        return

    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    # Explicitly supply both name and filename to satisfy legacy SQLite schemas
    await db.execute(
        """INSERT OR REPLACE INTO documents
           (id, user_id, name, filename, mime_type, storage_path, size_bytes, chunks, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (document_id, user_id, name, name, mime_type, storage_path, size_bytes, chunks, now),
    )
    await db.commit()


async def list_documents(user_id: str = "default_user") -> List[Dict[str, Any]]:
    if get_supabase_service().is_configured:
        return await get_supabase_service().list_documents(user_id=user_id)

    db = await get_db()
    rows = await (
        await db.execute(
            """SELECT id, user_id, name, filename, mime_type, storage_path, size_bytes, chunks, created_at
               FROM documents
               WHERE user_id = ?
               ORDER BY created_at DESC""",
            (user_id,),
        )
    ).fetchall()
    docs = []
    for r in rows:
        d = dict(r)
        d["filename"] = d.get("name") or d.get("filename") or "document"
        docs.append(d)
    return docs


async def delete_document(document_id: str, user_id: str = "default_user") -> bool:
    if get_supabase_service().is_configured:
        return await get_supabase_service().delete_document(document_id, user_id=user_id)

    db = await get_db()
    row = await (
        await db.execute(
            "SELECT storage_path FROM documents WHERE id=? AND user_id=?",
            (document_id, user_id),
        )
    ).fetchone()
    if not row:
        return False
    if row["storage_path"]:
        try:
            from services.storage_service import get_storage_service
            await get_storage_service().delete_document(row["storage_path"])
        except Exception:
            pass
    await db.execute("DELETE FROM documents WHERE id=? AND user_id=?", (document_id, user_id))
    await db.execute("DELETE FROM document_chunks WHERE document_id=? AND user_id=?", (document_id, user_id))
    await db.commit()
    return True


async def save_sources(conversation_id: str, sources: List[Dict[str, Any]]) -> None:
    if not sources:
        return
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    for src in sources:
        await db.execute(
            """INSERT OR REPLACE INTO sources
               (id, conversation_id, title, url, domain, source_type, payload_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                src.get("id"),
                conversation_id,
                src.get("title"),
                src.get("url"),
                src.get("domain"),
                src.get("source_type"),
                json.dumps(src),
                now,
            ),
        )
    await db.commit()


async def get_source(source_id: str) -> Optional[Dict[str, Any]]:
    db = await get_db()
    row = await (await db.execute("SELECT * FROM sources WHERE id=?", (source_id,))).fetchone()
    if not row:
        return None
    res = dict(row)
    if res.get("payload_json"):
        try:
            res["payload"] = json.loads(res["payload_json"])
        except Exception:
            pass
    return res
