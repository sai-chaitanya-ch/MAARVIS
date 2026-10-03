from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from api.router import api_router
from config.settings import get_settings
from tools.registry import register_default_tools
from utils.logging import configure_logging, get_logger
from utils.tracing import bind_context, new_id

configure_logging()
logger = get_logger("maarvis")
settings = get_settings()
limiter = Limiter(key_func=get_remote_address)

Path("data").mkdir(exist_ok=True)
register_default_tools()


async def _reindex_missing_documents() -> None:
    """
    On startup, scan all documents registered in SQLite.
    If the vector store has 0 chunks for a document, re-ingest the file.
    This ensures Qdrant embedded mode works across server restarts.
    """
    try:
        from memory.conversation import list_documents
        from rag.ingestion import ingest_file
        from rag.vector_store import get_vector_store

        docs = await list_documents()
        if not docs:
            return

        store = get_vector_store()
        store.ensure_collection(768)

        for doc in docs:
            doc_id = doc.get("id")
            file_path = doc.get("path")
            filename = doc.get("filename", "")

            if not doc_id or not file_path:
                continue

            path = Path(file_path)
            if not path.exists():
                # Try alternate path relative to backend dir
                backend_dir = Path(__file__).resolve().parent
                alt = backend_dir / "data" / "uploads" / f"{doc_id}_{filename}"
                if alt.exists():
                    path = alt
                else:
                    logger.warning("startup_reindex_skip", doc_id=doc_id, reason="file not found")
                    continue

            # Check if chunks exist in vector store
            chunks = store.get_document_chunks(document_ids=[doc_id], limit=1)
            if not chunks:
                logger.info("startup_reindex_start", doc_id=doc_id, filename=filename)
                try:
                    result = await ingest_file(str(path), filename, document_id=doc_id)
                    logger.info("startup_reindex_done", doc_id=doc_id, chunks=result.get("chunks", 0))
                except Exception as exc:
                    logger.error("startup_reindex_failed", doc_id=doc_id, error=str(exc))
    except Exception as exc:
        logger.error("startup_reindex_error", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: re-index any documents missing from Qdrant
    asyncio.ensure_future(_reindex_missing_documents())
    yield
    # Shutdown (nothing to clean up for now)


app = FastAPI(title="MAARVIS", description="AI Verification & Reasoning Platform", version="2.0.0", docs_url="/api/docs", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or new_id("req_")
        bind_context(request_id)
        if settings.verify_api_key:
            provided = request.headers.get("x-api-key", "")
            # Whitelist public health endpoints and docs from API key requirement
            if request.url.path not in {"/", "/health", "/api/health", "/api/docs", "/api/openapi.json"}:
                if request.url.path.startswith("/api/"):
                    if provided != settings.verify_api_key:
                        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response


app.add_middleware(RequestContextMiddleware)
app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    """Production health check endpoint for Render / monitoring."""
    return {"status": "ok", "service": "maarvis-api"}


@app.get("/")
async def root():
    return {"name": "MAARVIS", "tagline": "Verify. Reason. Trust.", "version": "2.0.0"}


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.error("unhandled_error", error=str(exc), path=str(request.url.path))
    return JSONResponse({"detail": str(exc), "type": exc.__class__.__name__}, status_code=500)


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", getattr(settings, "port", 8000) or 8000))
    logger.info("server_starting", host="0.0.0.0", port=port)
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

