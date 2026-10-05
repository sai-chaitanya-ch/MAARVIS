from __future__ import annotations

import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

request_id_var: ContextVar[str] = ContextVar("request_id", default="")
conversation_id_var: ContextVar[str] = ContextVar("conversation_id", default="")


def new_id(prefix: str = "") -> str:
    value = uuid.uuid4().hex
    return f"{prefix}{value}" if prefix else value


def new_uuid() -> str:
    return str(uuid.uuid4())


def is_valid_uuid(val: Optional[str]) -> bool:
    if not val or not isinstance(val, str):
        return False
    try:
        uuid_obj = uuid.UUID(val)
        return str(uuid_obj) == val.lower()
    except (ValueError, AttributeError):
        return False


class Timer:
    def __init__(self) -> None:
        self.start = time.perf_counter()

    def ms(self) -> int:
        return int((time.perf_counter() - self.start) * 1000)


def bind_context(request_id: Optional[str] = None, conversation_id: Optional[str] = None) -> Dict[str, Any]:
    rid = request_id or new_id("req_")
    request_id_var.set(rid)
    if conversation_id:
        conversation_id_var.set(conversation_id)
    return {"request_id": rid, "conversation_id": conversation_id or conversation_id_var.get()}
