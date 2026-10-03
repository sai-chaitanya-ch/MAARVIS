import logging
import sys
from typing import Any, Dict

import structlog

from config.settings import get_settings


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    return structlog.get_logger(name)


def redact_secrets(payload: Dict[str, Any]) -> Dict[str, Any]:
    hidden = {
        "provider_encryption_key",
        "gemini_api_key",
        "openai_api_key",
        "anthropic_api_key",
        "groq_api_key",
        "deepseek_api_key",
        "tavily_api_key",
        "qdrant_api_key",
        "aws_access_key_id",
        "aws_secret_access_key",
        "authorization",
        "api_key",
        "token",
    }
    out: Dict[str, Any] = {}
    for key, value in payload.items():
        if key.lower() in hidden:
            out[key] = "***"
        else:
            out[key] = value
    return out
