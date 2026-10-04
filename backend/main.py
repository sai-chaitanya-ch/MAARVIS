from __future__ import annotations

import os
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

register_default_tools()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup initialization
    logger.info("maarvis_api_initialized", environment=settings.environment)
    yield
    # Shutdown


app = FastAPI(
    title="MAARVIS",
    description="AI Verification & Multi-Agent Reasoning Platform",
    version="2.0.0",
    docs_url="/api/docs",
    lifespan=lifespan,
)
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
    return {"name": "MAARVIS", "tagline": "Ask. Analyze. Verify.", "version": "2.0.0"}


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.error("unhandled_error", error=str(exc), path=str(request.url.path))
    return JSONResponse({"detail": str(exc), "type": exc.__class__.__name__}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", getattr(settings, "port", 8000) or 8000))
    logger.info("server_starting", host="0.0.0.0", port=port)
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
